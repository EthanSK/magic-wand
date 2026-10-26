"""Run the actual finger driver against independently controllable sensor states."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class FingerRecoveryTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('c++'), 'Host C++ compiler is unavailable')
    def test_stale_and_reconnected_sensor_recover_without_resetting_healthy_sensor(self):
        with tempfile.TemporaryDirectory(prefix='stones-fingers-') as directory:
            binary = Path(directory) / 'test'
            built = subprocess.run(['c++', '-std=c++17', '-I'+str(ROOT/'firmware/imu_debug'),
                                    str(ROOT/'tests/finger_recovery/test.cpp'), '-o', str(binary)],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            checked = subprocess.run([str(binary)], timeout=5, capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout+checked.stderr)
