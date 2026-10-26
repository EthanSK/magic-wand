"""Local Control Stones telemetry and explicitly held mouse test. Never flashes firmware."""
import json
import asyncio
import threading
import time
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from mouse import MouseTest
from telemetry import parse_sample, parse_packet, FINGERS

ROOT = Path(__file__).parent
LOCK = threading.Lock()
STATE = {"status": "Waiting for Sense", "sample": None, "count": 0, "received": 0}
BLE_STATE = {"status": "Searching Bluetooth", "sample": None, "count": 0, "received": 0}
SENSORS = {}
HEALTH = {}
MOUSE = MouseTest()
TOKEN = secrets.token_urlsafe(32)
UART_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


def is_sense_serial(port):
    # The original Sense bootloader keeps the XIAO product name, but PID 0x0045
    # belongs to its firmware uploader. Opening it here prevents flashing.
    return (port.vid == 0x2886 and port.pid != 0x0045 and
            "XIAO" in (port.product or "").upper())


def record(sample, state, transport):
    if sample['sensor'] == 'health':
        with LOCK:
            HEALTH[transport] = dict(sample=sample, received=time.monotonic())
        return
    key = "hand" if sample["sensor"] == "hand" else f"finger:{sample['channel']}"
    with LOCK:
        state.update(status="Live", sample=sample, received=time.monotonic(), count=state["count"] + 1)
        by_transport = SENSORS.setdefault(key, {})
        count = by_transport.get(transport, {}).get("count", 0) + 1
        by_transport[transport] = dict(sample=sample, received=time.monotonic(), count=count)
        # Prefer one live transport, avoiding out-of-order duplicate movement.
        ble = by_transport.get("Bluetooth", {})
        if transport == "Bluetooth" or time.monotonic() - ble.get("received", 0) >= 2:
            MOUSE.sample(key, sample)

def sensor_state(key):
    transports = SENSORS.get(key, {})
    now = time.monotonic()
    item = transports.get("Bluetooth")
    transport = "Bluetooth"
    if not item or now - item["received"] >= 2:
        item, transport = transports.get("USB"), "USB"
    if not item:
        return {"status": "Waiting for sensor readings", "sample": None, "age": None, "count": 0, "transport": None}
    age = now - item["received"]
    return {"status": "Live" if age < 2 else "No recent readings", "sample": item["sample"] if age < 2 else None,
            "age": age, "count": item["count"], "transport": transport}

def health_state():
    now = time.monotonic()
    for transport in ('Bluetooth', 'USB'):
        item = HEALTH.get(transport)
        if item and now - item['received'] < 3:
            return dict(item['sample'], age=now-item['received'], transport=transport)
    return None

async def read_bluetooth():
    from bleak import BleakClient, BleakScanner
    while True:
        try:
            found = await BleakScanner.discover(timeout=4, return_adv=True)
            matches = [device for device, adv in found.values()
                       if adv.local_name == "Control Stones" and UART_SERVICE in adv.service_uuids]
            if len(matches) != 1:
                with LOCK:
                    BLE_STATE.update(status="Searching Bluetooth" if not matches else "Multiple Sense boards found", sample=None)
                continue
            buffer = bytearray()
            def receive(_, data):
                buffer.extend(data)
                if len(buffer) > 4096:
                    buffer.clear()
                    return
                while b"\n" in buffer:
                    line, _, rest = buffer.partition(b"\n")
                    buffer[:] = rest
                    try:
                        sample = parse_packet(line)
                    except (ValueError, UnicodeError):
                        continue
                    record(sample, BLE_STATE, "Bluetooth")
            async with BleakClient(matches[0]) as client:
                await client.start_notify(UART_TX, receive)
                while client.is_connected:
                    await asyncio.sleep(1)
        except Exception:
            with LOCK:
                BLE_STATE.update(status="Bluetooth disconnected", sample=None)
            await asyncio.sleep(2)

def read_sensor():
    import serial
    from serial.tools import list_ports
    while True:
        devices = [p for p in list_ports.comports() if is_sense_serial(p)]
        if len(devices) != 1:
            with LOCK:
                STATE.update(status="Waiting for one Sense over USB", sample=None)
            time.sleep(1)
            continue
        try:
            with serial.Serial(devices[0].device, 115200, timeout=1) as port:
                with LOCK:
                    STATE.update(status="Waiting for sensor readings", port=devices[0].device, sample=None)
                while True:
                    line = port.read_until(b"\n", 512)
                    if not line:
                        continue
                    try:
                        sample = parse_packet(line)
                    except (ValueError, UnicodeError) as error:
                        if str(error) == "Built-in sensor not found":
                            with LOCK:
                                STATE.update(status="Built-in sensor not found", sample=None)
                        continue
                    record(sample, STATE, "USB")
        except (serial.SerialException, OSError):
            with LOCK:
                STATE.update(status="USB disconnected", sample=None)
            time.sleep(1)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/sample":
            source = parse_qs(url.query).get("source", ["hand"])[0]
            with LOCK:
                payload = sensor_state(source)
                payload["sensors"] = {key: sensor_state(key) for key in ("hand", *(f"finger:{i}" for i in FINGERS))}
                payload["mouse"] = MOUSE.status()
                payload["health"] = health_state()
            data = json.dumps(payload, allow_nan=False).encode()
            content_type = "application/json"
        elif self.path in ("/", "/index.html"):
            data = (ROOT / "index.html").read_text().replace("__CONTROL_TOKEN__", TOKEN).encode()
            content_type = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        origin = self.headers.get("Origin")
        if (self.path != "/api/mouse" or self.headers.get("X-Control-Token") != TOKEN or
            origin not in (None, "http://127.0.0.1:8769", "http://localhost:8769") or
            self.headers.get("Content-Type") != "application/json"):
            self.send_error(403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 2048:
                raise ValueError("Invalid command length")
            value = json.loads(self.rfile.read(length))
            if not isinstance(value, dict):
                raise ValueError("Invalid command")
            with LOCK:
                MOUSE.command(value)
                data = json.dumps(MOUSE.status()).encode()
        except (ValueError, TypeError) as error:
            self.send_error(400, str(error))
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume-file', type=Path, help='Keep HTTP available while an authorised firmware upload owns the transports')
    options = parser.parse_args()
    def start_readers():
        while options.resume_file and not options.resume_file.exists():
            time.sleep(0.1)
        threading.Thread(target=read_sensor, daemon=True).start()
        threading.Thread(target=lambda: asyncio.run(read_bluetooth()), daemon=True).start()
    threading.Thread(target=start_readers, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", 8769), Handler)
    print("Control Stones debug: http://127.0.0.1:8769/", flush=True)
    server.serve_forever()
