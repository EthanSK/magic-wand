#!/usr/bin/env python3
"""Exercise complete batched queries, owned cleanup and cross-job locking.

Fixtures are tiny; never replay the incident workload.
Run with Python's standard library, locally or through The Fleet.
"""
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/geometry_budget.py'
spec = importlib.util.spec_from_file_location('geometry_budget', SCRIPT)
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)


class GeometryBudgetTests(unittest.TestCase):
    def test_batch_size_accounts_for_faces_and_both_ray_directions(self):
        self.assertEqual(budget.query_batch_size(50_944), 4)
        self.assertEqual(budget.query_batch_size(12), 128)
        with self.assertRaises(ValueError):
            budget.query_batch_size(500_001)

    def test_contains_keeps_every_point_in_order(self):
        calls = []
        mesh = SimpleNamespace(faces=range(17))
        def classify(points):
            calls.append(list(points))
            return [point % 3 == 0 for point in points]
        mesh.contains = classify
        fake_numpy = SimpleNamespace(empty=lambda n, dtype: [None] * n)
        points = list(range(513))
        with patch.dict(sys.modules, {'numpy': fake_numpy}):
            result = budget.contains(mesh, points, pair_budget=70)
        self.assertEqual(result, [p % 3 == 0 for p in points])
        self.assertEqual([p for call in calls for p in call], points)
        self.assertTrue(all(len(call) <= 2 for call in calls))

    def test_closest_point_keeps_positions_distances_and_triangle_ids(self):
        calls = []
        def allocate(shape, dtype):
            return [[None] * shape[1] for _ in range(shape[0])] if isinstance(shape, tuple) else [None] * shape
        def nearest(mesh, points):
            calls.append(list(points))
            return ([[p, 0, 0] for p in points], [p / 10 for p in points], list(points))
        fake_numpy = SimpleNamespace(empty=allocate, int64=int)
        fake_trimesh = SimpleNamespace(proximity=SimpleNamespace(closest_point=nearest))
        with patch.dict(sys.modules, {'numpy': fake_numpy, 'trimesh': fake_trimesh}):
            positions, distances, triangles = budget.closest_point(SimpleNamespace(faces=range(17)), list(range(23)), pair_budget=70)
        self.assertEqual(positions, [[p, 0, 0] for p in range(23)])
        self.assertEqual(distances, [p / 10 for p in range(23)])
        self.assertEqual(triangles, list(range(23)))
        self.assertTrue(all(len(call) <= 4 for call in calls))

    def launch(self, code, *, timeout=10, receipt=None, **kwargs):
        command = [sys.executable, '-B', str(SCRIPT), '--timeout-seconds', str(timeout)]
        if receipt:
            command += ['--receipt', str(receipt)]
        return subprocess.run(command + ['--', sys.executable, '-B', '-c', code], capture_output=True, text=True, timeout=15, **kwargs)

    def test_success_and_original_exit_code_survive(self):
        result = self.launch('print("checked");raise SystemExit(7)')
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIn('checked', result.stdout)

    def test_ram_limit_option_is_not_available(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--memory-mib', '64'],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn('unrecognized arguments', result.stderr)

    def test_host_pressure_is_not_an_execution_gate(self):
        with patch.object(budget.subprocess, 'check_output', side_effect=AssertionError('no pressure gate')):
            self.assertEqual(budget.run([sys.executable, '-c', 'pass'], 10), 0)

    def test_time_limit_stops_the_owned_command(self):
        result = self.launch('import time;time.sleep(10)', timeout=.3)
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertIn('time-limit', result.stderr)

    def test_background_work_cannot_outlive_a_successful_leader(self):
        code = 'import subprocess,sys;subprocess.Popen([sys.executable,"-c","import time;time.sleep(10)"])'
        result = self.launch(code)
        self.assertEqual(result.returncode, 125, result.stderr)
        self.assertIn('background-descendants', result.stderr)

    def test_cancelling_the_launcher_stops_its_owned_process(self):
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
            with self.subTest(signal=number):
                self.assert_signal_cleanup(number)

    def test_cancellation_during_launch_still_cleans_the_new_child(self):
        real_popen = subprocess.Popen
        command = [sys.executable, '-c', 'import time;time.sleep(10)']
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
            with self.subTest(signal=number):
                owned = []

                def cancel_before_return(argv, **kwargs):
                    child = real_popen(argv, **kwargs)
                    if argv == command:
                        owned.append(child)
                        os.kill(os.getpid(), number)
                    return child

                try:
                    with patch.object(budget.subprocess, 'Popen', cancel_before_return):
                        with self.assertRaises(SystemExit) as raised:
                            budget.run(command, 10)
                    self.assertEqual(raised.exception.code, 128 + number)
                    self.assertEqual(len(owned), 1)
                    self.assertIsNotNone(owned[0].poll(), 'launch cancellation left the child alive')
                finally:
                    for child in owned:
                        if child.poll() is None:
                            os.killpg(child.pid, signal.SIGKILL)
                        child.wait()

    def test_repeated_signal_cannot_interrupt_owned_cleanup(self):
        real_popen, real_stop = subprocess.Popen, budget.stop_group
        command = [sys.executable, '-c', 'import time;time.sleep(10)']
        owned = []

        def first_signal(argv, **kwargs):
            child = real_popen(argv, **kwargs)
            if argv == command:
                owned.append(child)
                os.kill(os.getpid(), signal.SIGINT)
            return child

        def second_signal(group):
            os.kill(os.getpid(), signal.SIGTERM)
            real_stop(group)

        try:
            with patch.object(budget.subprocess, 'Popen', first_signal), \
                 patch.object(budget, 'stop_group', second_signal):
                with self.assertRaises(SystemExit) as raised:
                    budget.run(command, 10)
            self.assertEqual(raised.exception.code, 128 + signal.SIGINT)
            self.assertIsNotNone(owned[0].poll(), 'second signal interrupted cleanup')
        finally:
            for child in owned:
                if child.poll() is None:
                    real_stop(child.pid)
                child.wait()

    def assert_signal_cleanup(self, number):
        command = [sys.executable, '-B', str(SCRIPT), '--', sys.executable, '-u', '-c',
                   'import os,time;print(os.getpid(),flush=True);time.sleep(10)']
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertTrue(select.select([process.stdout], [], [], 5)[0])
            child = int(process.stdout.readline().strip())
            os.kill(process.pid, number)
            output, errors = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 128 + number, errors)
            self.assertIn('cancelled', errors)
            with self.assertRaises(ProcessLookupError):
                os.kill(child, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

    def test_forced_supervisor_exit_keeps_the_child_lease(self):
        command = [sys.executable, '-B', str(SCRIPT), '--', sys.executable, '-u', '-c',
                   'import os,time;print(os.getpid(),flush=True);time.sleep(10)']
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        child = None
        try:
            self.assertTrue(select.select([process.stdout], [], [], 5)[0])
            child = int(process.stdout.readline().strip())
            process.kill()
            process.wait(timeout=3)
            result = self.launch('print("must not overlap")')
            self.assertEqual(result.returncode, 125, result.stderr)
            self.assertNotIn('must not overlap', result.stdout)
            self.assertIn('Another guarded geometry job', result.stderr)
        finally:
            if child is not None:
                budget.stop_group(child)
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

    def test_cleanup_refreshes_a_snapshot_that_missed_a_new_child(self):
        self.assert_exit_snapshot([[], [123456790]], expected_code=125)

    def test_cleanup_refreshes_a_snapshot_with_an_already_finished_child(self):
        self.assert_exit_snapshot([[123456790], []], expected_code=0)

    def assert_exit_snapshot(self, samples, expected_code):
        with tempfile.TemporaryDirectory() as work:
            fd = budget.acquire_lock(Path(work) / 'test.lock')
            fake = SimpleNamespace(pid=123456789, poll=lambda: 0, wait=lambda: 0)
            with patch.object(budget, 'acquire_lock', return_value=fd), \
                 patch.object(budget, 'group_pids', side_effect=samples) as sample, \
                 patch.object(budget, 'stop_group') as stop, \
                 patch.object(budget.subprocess, 'Popen', return_value=fake):
                result = budget.run(['synthetic-command'], 10)
                self.assertEqual(result, expected_code)
                self.assertEqual(sample.call_count, 2)
                self.assertEqual(stop.call_count, int(expected_code != 0))

    def test_second_job_is_refused_before_its_command_starts(self):
        command = [sys.executable, '-B', str(SCRIPT), '--timeout-seconds', '10', '--', sys.executable, '-u', '-c', 'import sys;print("ready",flush=True);sys.stdin.read(1)']
        first = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertTrue(select.select([first.stdout], [], [], 5)[0])
            self.assertEqual(first.stdout.readline().strip(), 'ready')
            with tempfile.TemporaryDirectory() as other_tmp:
                result = self.launch('print("must not run")', env={**os.environ, 'TMPDIR': other_tmp})
            self.assertEqual(result.returncode, 125, result.stderr)
            self.assertNotIn('must not run', result.stdout)
            self.assertIn('Another guarded geometry job', result.stderr)
        finally:
            output, errors = first.communicate('x', timeout=5)
        self.assertEqual(first.returncode, 0, errors)

    def test_lock_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            (root / 'target').write_text('preserve')
            (root / 'lock').symlink_to(root / 'target')
            with self.assertRaises(OSError):
                budget.acquire_lock(root / 'lock')
            self.assertEqual((root / 'target').read_text(), 'preserve')


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GeometryBudgetTests))
    if result.wasSuccessful():
        print(f'geometry-budget-tests={result.testsRun}')
    sys.exit(not result.wasSuccessful())
