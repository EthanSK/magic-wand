"""USB-only Control Stones debug viewer. Does not control the mouse or flash firmware."""
import json
import asyncio
import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import serial
from serial.tools import list_ports
from bleak import BleakClient, BleakScanner

ROOT = Path(__file__).parent
LOCK = threading.Lock()
STATE = {"status": "Waiting for Sense", "sample": None, "count": 0, "received": 0}
BLE_STATE = {"status": "Searching Bluetooth", "sample": None, "count": 0, "received": 0}
UART_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
AXES = ("ax", "ay", "az", "gx", "gy", "gz")

def parse_sample(line):
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError("Not a sample")
    if "error" in value:
        raise ValueError(str(value["error"]))
    if not all(type(value.get(key)) in (int, float) and math.isfinite(value[key]) for key in AXES):
        raise ValueError("Invalid axes")
    sample = {key: value[key] for key in (*AXES, "ms") if key in value}
    if type(value.get("idle")) is bool:
        sample["idle"] = value["idle"]
        sample["sleep_ready"] = value.get("sleep_ready") is True
    battery = value.get("battery_v")
    if type(battery) in (int, float) and math.isfinite(battery) and 0 < battery < 6:
        sample["battery_v"] = battery
        sample["charging"] = value.get("charging") is True
    return sample

async def read_bluetooth():
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
                        sample = parse_sample(line)
                    except (ValueError, UnicodeError):
                        continue
                    with LOCK:
                        BLE_STATE.update(status="Live", sample=sample, received=time.monotonic(), count=BLE_STATE["count"] + 1)
            async with BleakClient(matches[0]) as client:
                await client.start_notify(UART_TX, receive)
                while client.is_connected:
                    await asyncio.sleep(1)
        except Exception:
            with LOCK:
                BLE_STATE.update(status="Bluetooth disconnected", sample=None)
            await asyncio.sleep(2)

def read_sensor():
    while True:
        devices = [p for p in list_ports.comports() if "XIAO" in (p.product or "").upper() and p.vid == 0x2886]
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
                        sample = parse_sample(line)
                    except (ValueError, UnicodeError) as error:
                        if str(error) == "Built-in sensor not found":
                            with LOCK:
                                STATE.update(status="Built-in sensor not found", sample=None)
                        continue
                    with LOCK:
                        STATE.update(status="Live", sample=sample, received=time.monotonic(), count=STATE["count"] + 1)
        except (serial.SerialException, OSError):
            with LOCK:
                STATE.update(status="USB disconnected", sample=None)
            time.sleep(1)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/sample":
            with LOCK:
                use_ble = BLE_STATE["sample"] is not None and time.monotonic() - BLE_STATE["received"] < 2
                payload = dict(BLE_STATE if use_ble else STATE)
                payload["transport"] = "Bluetooth" if use_ble else "USB"
            payload["age"] = time.monotonic() - payload.pop("received") if payload["sample"] else None
            if payload["age"] is not None and payload["age"] > 2:
                payload.update(status="No recent readings", sample=None)
            data = json.dumps(payload, allow_nan=False).encode()
            content_type = "application/json"
        elif self.path in ("/", "/index.html"):
            data = (ROOT / "index.html").read_bytes()
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

    def log_message(self, *_):
        pass

if __name__ == "__main__":
    threading.Thread(target=read_sensor, daemon=True).start()
    threading.Thread(target=lambda: asyncio.run(read_bluetooth()), daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", 8769), Handler)
    print("Control Stones debug: http://127.0.0.1:8769/", flush=True)
    server.serve_forever()
