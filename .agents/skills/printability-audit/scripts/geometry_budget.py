#!/usr/bin/env python3
"""Run one owned CAD check at a time and batch complete geometry queries.

No hard RAM limit or host-pressure gate is imposed. Fix allocations at their source.
Use this launcher for CAD/export/review commands, including one-off probes.
Import contains/closest_point for bounded trimesh queries; point count alone
does not bound trimesh's temporary triangle/ray candidate arrays.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt
    import trimesh

PAIR_BUDGET = 500_000


def query_batch_size(face_count: int, *, ray_multiplier: int = 2,
                     pair_budget: int = PAIR_BUDGET) -> int:
    """Bound worst-case candidate pairs, including forward/backward rays."""
    if face_count < 1 or ray_multiplier < 1 or pair_budget < 1:
        raise ValueError('Geometry-query limits must be positive.')
    count = min(128, pair_budget // (face_count * ray_multiplier))
    if count < 1:
        raise ValueError('One query exceeds the candidate budget; use sections or split the query geometry.')
    return count


def contains(mesh: trimesh.Trimesh, points: npt.NDArray[np.float64], *,
             pair_budget: int = PAIR_BUDGET) -> npt.NDArray[np.bool_]:
    """Classify every point in original order, without one giant ray query."""
    import numpy as np
    size = query_batch_size(len(mesh.faces), pair_budget=pair_budget)
    result = np.empty(len(points), dtype=bool)
    for start in range(0, len(points), size):
        result[start:start + size] = mesh.contains(points[start:start + size])
    return result


def closest_point(mesh: trimesh.Trimesh, points: npt.NDArray[np.float64], *,
                  pair_budget: int = PAIR_BUDGET) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.int64]]:
    """Preserve all nearest-point results while bounding point/triangle pairs."""
    import numpy as np
    import trimesh
    size = query_batch_size(len(mesh.faces), ray_multiplier=1, pair_budget=pair_budget)
    positions = np.empty((len(points), 3), dtype=float)
    distances = np.empty(len(points), dtype=float)
    triangles = np.empty(len(points), dtype=np.int64)
    for start in range(0, len(points), size):
        end = start + size
        positions[start:end], distances[start:end], triangles[start:end] = trimesh.proximity.closest_point(mesh, points[start:end])
    return positions, distances, triangles


def acquire_lock(path: Path) -> int:
    """One kernel-held lease across chats, independent of their TMPDIRs."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        os.close(fd)
        raise RuntimeError('Unsafe geometry lock ownership.')
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        raise RuntimeError('Another guarded geometry job is running on this host.') from None
    return fd


def group_pids(group: int) -> list[int]:
    listing = subprocess.run(['ps', '-axo', 'pid=,pgid='], check=True,
                             capture_output=True, text=True).stdout
    return [int(pid) for pid, pgid in (line.split() for line in listing.splitlines())
            if int(pgid) == group]


def stop_group(group: int) -> None:
    try:
        os.killpg(group, signal.SIGKILL)
    except ProcessLookupError:
        pass


def cancel(signum: int, _frame: object) -> None:
    # Forward a normal launcher cancellation through the same owned cleanup.
    # SIGKILL cannot be caught; this is not an OS sandbox or a global watchdog.
    raise SystemExit(128 + signum)


def run(command: list[str], timeout_seconds: float,
        receipt: Path | None = None) -> int:
    if not 0 < timeout_seconds <= 3600:
        raise ValueError('Use a finite time budget up to one hour.')
    # A stable user-owned location makes separate chats share one lease.
    fd = acquire_lock(Path.home() / '.cache/magic-wand/geometry.lock')
    process = None
    started = time.monotonic()
    record: dict[str, int | float | str] = {'timeout_seconds': timeout_seconds,
        'samples': 0, 'reason': 'not-started'}
    launching = False
    pending_signal: int | None = None
    cancelling = False

    def handle_cancel(signum: int, frame: object) -> None:
        nonlocal pending_signal, cancelling
        if cancelling:
            return
        # Popen can have started the child before its handle reaches us.
        # Save that handle before raising, so ordinary cleanup owns the job.
        # Defer only in the parent; do not alter the child's signal mask.
        if launching:
            if pending_signal is None:
                pending_signal = signum
            return
        cancelling = True
        cancel(signum, frame)

    previous_signals = {number: signal.signal(number, handle_cancel) for number in
                        (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT)}
    try:
        # Keep the lease in the job too. Even if this supervisor is forcibly
        # killed, a surviving direct child must block overlapping work.
        launching = True
        try:
            process = subprocess.Popen(command, start_new_session=True, pass_fds=(fd,))
        finally:
            launching = False
        record['pid'] = process.pid
        if pending_signal is not None:
            cancelling = True
            cancel(pending_signal, None)
        record['reason'] = 'running'
        while True:
            group_pids(process.pid)
            record['samples'] += 1
            if time.monotonic() - started > timeout_seconds:
                record['reason'] = 'time-limit'
                stop_group(process.pid)
                process.wait()
                return 124
            code = process.poll()
            if code is not None:
                # A timed-out foreground command must not leave its expensive
                # background children alive while the next check starts.
                # The leader may spawn or reap a child after our first sample.
                # Its exit is the boundary at which cleanup needs a NEW read.
                remaining = group_pids(process.pid)
                if remaining:
                    stop_group(process.pid)
                    record['reason'] = 'background-descendants'
                    return 125
                record['reason'] = 'completed'
                record['exit_code'] = code
                return code
            try:
                process.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                pass
    except BaseException as error:
        cancelling = True
        record['reason'] = 'cancelled' if isinstance(error, (SystemExit, KeyboardInterrupt)) else 'supervisor-error'
        if process is not None:
            stop_group(process.pid)
            process.wait()
        raise
    finally:
        try:
            record['elapsed_seconds'] = round(time.monotonic() - started, 3)
            if receipt:
                receipt.parent.mkdir(parents=True, exist_ok=True)
                receipt.write_text(json.dumps(record, indent=2) + '\n')
            print('Geometry job: ' + json.dumps(record), file=sys.stderr, flush=True)
        finally:
            for number, previous in previous_signals.items():
                signal.signal(number, previous)
            os.close(fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout-seconds', type=float, default=900)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('Supply a command after --.')
    try:
        sys.exit(run(command, args.timeout_seconds, args.receipt))
    except (ValueError, RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(125)
