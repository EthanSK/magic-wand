import json
import unittest
import threading
import urllib.request
import urllib.error

from mouse import MouseTest
from telemetry import parse_sample


class FakePointer:
    def __init__(self): self.moves = []
    def available(self): return True
    def move(self, dx, dy): self.moves.append((dx, dy))


def sample(ms=100, **extra):
    return dict(ax=0, ay=0, az=1, gx=20, gy=0, gz=40, ms=ms, **extra)


class ReaderTests(unittest.TestCase):
    def test_unseen_sensor_does_not_claim_a_usb_connection(self):
        import server
        with server.LOCK:
            state = server.sensor_state('finger:unknown')
        self.assertIsNone(state['transport'])
        self.assertIsNone(state['sample'])

    def test_legacy_hand_and_thumb_are_distinct(self):
        self.assertEqual(parse_sample(json.dumps(sample()))['sensor'], 'hand')
        thumb = parse_sample(json.dumps(sample(sensor='finger', channel=2)))
        self.assertEqual((thumb['finger'], thumb['channel']), ('Thumb', 2))
        for channel in (0, 1, 7, True):
            with self.assertRaises(ValueError):
                parse_sample(json.dumps(sample(sensor='finger', channel=channel)))

    def test_invalid_data_is_not_telemetry(self):
        for overrides in ({'gx': True}, {'az': float('nan')}, {'ms': None}, {'sensor': 'wrong'}):
            raw = sample(); raw.update(overrides)
            with self.assertRaises(ValueError): parse_sample(json.dumps(raw))

    def test_pointer_is_off_until_held_and_expires(self):
        pointer = FakePointer(); clock = [1.0]
        mouse = MouseTest(pointer, lambda: clock[0])
        mouse.sample('finger:2', sample(100)); mouse.sample('finger:2', sample(120))
        self.assertEqual(pointer.moves, [])
        mouse.command({'action': 'hold'})
        mouse.sample('finger:2', sample(140)); mouse.sample('finger:2', sample(160))
        self.assertEqual(len(pointer.moves), 1)
        clock[0] = 1.7
        mouse.sample('finger:2', sample(180))
        self.assertEqual(len(pointer.moves), 1)

    def test_duplicates_other_sensors_and_reconnect_do_not_move(self):
        pointer = FakePointer(); mouse = MouseTest(pointer, lambda: 1.0)
        mouse.command({'action': 'hold'})
        mouse.sample('finger:2', sample(100)); mouse.sample('finger:2', sample(100))
        mouse.sample('finger:3', sample(120)); mouse.sample('finger:2', sample(1000))
        mouse.sample('finger:2', sample(10))
        self.assertEqual(pointer.moves, [])
        mouse.sample('finger:2', sample(30))
        self.assertEqual(len(pointer.moves), 1)
        mouse.command({'action':'stop'}); mouse.sample('finger:2',sample(50))
        self.assertEqual(len(pointer.moves),1)

    def test_calibration_removes_still_sensor_bias(self):
        pointer = FakePointer(); mouse = MouseTest(pointer, lambda: 1.0)
        mouse.command({'action': 'calibrate'})
        for ms in range(0, 1000, 20): mouse.sample('finger:2', sample(ms))
        self.assertTrue(mouse.status()['calibrated'])
        mouse.command({'action': 'hold'})
        mouse.sample('finger:2',sample(1020));mouse.sample('finger:2',sample(1040))
        self.assertEqual(pointer.moves, [])

    def test_http_mouse_commands_require_local_token(self):
        import server
        from http.server import ThreadingHTTPServer
        http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        threading.Thread(target=http.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{http.server_port}/api/mouse'
        try:
            request = urllib.request.Request(url, data=b'{"action":"stop"}', headers={'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(request)
            self.assertEqual(error.exception.code, 403)
            error.exception.close()
            request.add_header('X-Control-Token', server.TOKEN)
            with urllib.request.urlopen(request) as response:
                self.assertFalse(json.load(response)['active'])
            request.add_header('Origin', 'https://unrelated.example')
            with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(request)
            self.assertEqual(error.exception.code, 403)
            error.exception.close()
        finally:
            http.shutdown(); http.server_close()


if __name__ == '__main__': unittest.main()
