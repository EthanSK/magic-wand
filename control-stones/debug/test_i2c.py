"""Exercise the production I2C deadline and recovery with fake MCU registers."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class I2CDeadlineTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('c++'), 'Host C++ compiler is unavailable')
    def test_stuck_transfer_times_out_and_next_transfer_can_succeed(self):
        stubs = ROOT / 'tests' / 'timed_i2c'
        with tempfile.TemporaryDirectory(prefix='stones-i2c-') as directory:
            binary = Path(directory) / 'test'
            compiled = subprocess.run(['c++', '-std=c++17', '-I' + str(stubs),
                            '-I' + str(ROOT / 'firmware' / 'imu_debug'),
                            str(stubs / 'test.cpp'), '-o', str(binary)],
                           capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            tested = subprocess.run([str(binary)], timeout=5,
                                    capture_output=True, text=True)
            self.assertEqual(tested.returncode, 0, tested.stdout + tested.stderr)
