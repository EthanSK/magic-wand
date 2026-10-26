import json
import unittest
from unittest.mock import patch
from telemetry import parse_packet
import server

def health(**updates):
    value = dict(sensor='health', firmware='cs-recovery-20261026', ms=1234,
                 finger_state=[1, 1, 2, 3, 0], finger_restarts=[0, 1, 2, 0, 0],
                 i2c_timeouts=3, ble_drops=2)
    value.update(updates)
    return value

class HealthTests(unittest.TestCase):
    def tearDown(self):
        server.HEALTH.clear()

    def test_diagnostics_do_not_become_motion_or_require_finite_axes(self):
        packet = parse_packet(json.dumps(health()))
        with patch.object(server.MOUSE, 'sample', side_effect=AssertionError('Diagnostic moved pointer')):
            server.record(packet, server.BLE_STATE, 'Bluetooth')
        self.assertEqual(server.health_state()['finger_restarts'], [0, 1, 2, 0, 0])

    def test_invalid_diagnostics_are_rejected(self):
        for updates in ({'ms': True}, {'finger_state':[1]*4}, {'finger_state':[7]*5},
                        {'finger_restarts':[False]*5}, {'ble_drops':-1}):
            with self.assertRaises(ValueError):
                parse_packet(json.dumps(health(**updates)))

    def test_expired_diagnostics_do_not_claim_firmware_is_current(self):
        with patch.object(server.time, 'monotonic', return_value=1):
            server.record(health(), server.BLE_STATE, 'Bluetooth')
        with patch.object(server.time, 'monotonic', return_value=5):
            self.assertIsNone(server.health_state())
