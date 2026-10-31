#!/usr/bin/env python3
"""Toggle temporary local review capture, or replay it with the real Swift classifier."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, REPOSITORY, DOCS
SUPPORT = Path.home() / "Library/Application Support/WandReceiver"

def trace_files(path: Path) -> list[Path]:
    if path.is_dir():
        files = [path / f"trace.{i}.jsonl" for i in range(7, 0, -1)] + [path / "trace.jsonl"]
        files = [p for p in files if p.is_file() and not p.is_symlink()]
    else:
        files = [path] if path.is_file() and not path.is_symlink() else []
    if not files:
        raise ValueError("No local trace files found. Capture begins when review input is received.")
    if sum(p.stat().st_size for p in files) > 32 * 1024 * 1024:
        raise ValueError("Trace input exceeds the 32 MiB offline replay limit.")
    return files

def report_target(requested: Path) -> Path:
    """Private reports may use external paths or explicitly ignored scratch folders."""
    target = requested.expanduser().resolve()
    try:
        relative = target.relative_to(REPOSITORY)
    except ValueError:
        return target
    if relative.parts[:1] == ("work",) or relative.parts[:2] == ("magic-wand", "work"):
        return target
    raise ValueError("Keep private reports outside the public repository, or in an ignored work folder.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture", help="Change the local diagnostic switch; never restarts an app")
    capture.add_argument("state", choices=["on", "off", "status"])
    capture.add_argument("--support", type=Path, default=SUPPORT)
    replay = commands.add_parser("replay", help="Replay saved points without sending any live input")
    replay.add_argument("trace", type=Path, nargs="?", default=SUPPORT / "review-traces")
    replay.add_argument("--source", type=Path, default=ROOT / "receiver/Sources/WandPointerControl.swift")
    replay.add_argument("--report", type=Path, help="Save a private JSON report outside the public source tree")
    args = parser.parse_args()
    if args.command == "replay" and args.report:
        args.report = report_target(args.report)
    if args.command == "capture":
        path = args.support.expanduser() / "review-trace.json"
        if args.state == "status":
            value = {}
            try:
                info = path.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022 or info.st_size > 1024:
                    raise ValueError("Untrusted diagnostic configuration")
                value = json.loads(path.read_text())
                if not isinstance(value, dict): raise ValueError("Invalid capture configuration")
                enabled = value.get("enabled") is True and time.time() < value.get("captureUntil", 0)
            except (OSError, ValueError, TypeError):
                enabled = False
            print(json.dumps({"enabled": enabled, "configuration": str(path), "captureUntil": value.get("captureUntil") if enabled else None}))
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        end = time.time() + 600
        # The same explicit window controls both existing recorders. Merely
        # reading a dashboard or restarting a receiver does not renew it.
        for target in (path, path.parent / "DebugReadings/capture-window.json"):
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            info = target.parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
                raise ValueError("Untrusted capture directory")
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, prefix=".capture-", delete=False) as f:
                temporary = Path(f.name)
                try:
                    os.chmod(temporary, 0o600)
                    value = {"enabled": args.state == "on"}
                    if args.state == "on":
                        value.update(captureUntil=end, deleteAfter=end + 7200)
                    else:
                        try:
                            old = json.loads(target.read_text())
                            value.update({k: old[k] for k in ("captureUntil", "deleteAfter") if k in old})
                        except (OSError, ValueError): pass
                    json.dump(value, f)
                    f.write("\n"); f.flush()
                    os.fsync(f.fileno())
                except BaseException:
                    temporary.unlink(missing_ok=True)
                    raise
            os.replace(temporary, target)
        print(f"Review capture {args.state}. The running receiver reads the switch without a restart.")
        return
    if sys.platform != "darwin":
        raise ValueError("The native Swift review replay needs macOS and the Xcode command line tools.")
    compiler = shutil.which("swiftc")
    if not compiler:
        raise ValueError("swiftc is unavailable; no compiler was installed automatically.")
    files = trace_files(args.trace.expanduser())
    source = args.source.expanduser().resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="wand-review-replay-", suffix=".noindex") as folder:
        folder = Path(folder)
        runner = folder / "main.swift"
        shutil.copy2(ROOT / "scripts/replay_review.swift", runner)
        binary = folder / "replay"
        subprocess.run([compiler, "-O", str(source), str(runner), "-o", str(binary)], check=True, capture_output=True, text=True)
        result = subprocess.run([str(binary), *map(str, files)], check=True, capture_output=True, text=True)
        report = json.loads(result.stdout)
    report["classifierSHA256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    encoded = json.dumps(report, indent=2) + "\n"
    if args.report:
        target = args.report
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, prefix=".review-report-", delete=False) as f:
            temporary = Path(f.name)
            try:
                os.chmod(temporary, 0o600)
                f.write(encoded); f.flush()
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        os.replace(temporary, target)
    print(encoded, end="")

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Review trace: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr, file=sys.stderr)
        raise SystemExit(1)
