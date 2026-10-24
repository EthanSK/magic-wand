"""Opt-in, lease-limited gyro pointer test; independent of the Wand receiver."""
import ctypes
import math
import sys
import time


class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class MacPointer:
    def __init__(self):
        self.lib = None
        if sys.platform == "darwin":
            self.lib = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
            self.lib.AXIsProcessTrusted.restype = ctypes.c_bool
            self.lib.CGEventCreate.argtypes = [ctypes.c_void_p]
            self.lib.CGEventCreate.restype = ctypes.c_void_p
            self.lib.CGEventGetLocation.argtypes = [ctypes.c_void_p]
            self.lib.CGEventGetLocation.restype = Point
            self.lib.CGEventCreateMouseEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint32, Point, ctypes.c_uint32]
            self.lib.CGEventCreateMouseEvent.restype = ctypes.c_void_p
            self.lib.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
            self.lib.CFRelease.argtypes = [ctypes.c_void_p]

    def available(self):
        return bool(self.lib and self.lib.AXIsProcessTrusted())

    def move(self, dx, dy):
        if not self.available():
            return
        event = self.lib.CGEventCreate(None)
        if not event:
            return
        point = self.lib.CGEventGetLocation(event)
        self.lib.CFRelease(event)
        motion = self.lib.CGEventCreateMouseEvent(None, 5, Point(point.x + dx, point.y + dy), 0)
        if motion:
            self.lib.CGEventPost(0, motion)
            self.lib.CFRelease(motion)


class MouseTest:
    def __init__(self, pointer=None, clock=time.monotonic):
        self.pointer = pointer or MacPointer()
        self.clock = clock
        self.source = "finger:2"
        self.until = 0
        self.last = None
        self.horizontal, self.vertical = "gz", "gx"
        self.gain = 3.0
        self.invert_x = self.invert_y = False
        self.bias = {}
        self.calibration = []
        self.calibrating = False

    def status(self):
        return {"active": self.clock() < self.until, "available": self.pointer.available(),
                "source": self.source, "calibrating": self.calibrating,
                "calibrated": self.source in self.bias}

    def command(self, value):
        action = value.get("action")
        if action == "stop":
            self.until = 0
            self.last = None
            return
        if action == "configure":
            source = value.get("source", self.source)
            if source not in {"hand", *(f"finger:{i}" for i in range(2, 7))}:
                raise ValueError("Invalid sensor")
            h, v = value.get("horizontal", "gz"), value.get("vertical", "gx")
            gain = value.get("gain", 3)
            if h not in ("gx", "gy", "gz") or v not in ("gx", "gy", "gz"):
                raise ValueError("Invalid axis")
            if type(gain) not in (int, float) or not math.isfinite(gain) or not 0.1 <= gain <= 10:
                raise ValueError("Invalid sensitivity")
            self.source, self.horizontal, self.vertical, self.gain = source, h, v, gain
            self.invert_x, self.invert_y = value.get("invert_x") is True, value.get("invert_y") is True
            self.until, self.last, self.calibrating = 0, None, False
        elif action == "calibrate":
            self.until, self.last = 0, None
            self.calibration, self.calibrating = [], True
        elif action == "hold":
            if not self.pointer.available():
                raise ValueError("Allow Accessibility access for the reader's Python in System Settings")
            if self.calibrating:
                raise ValueError("Keep the sensor still until calibration finishes")
            if self.clock() >= self.until:
                self.last = None
            self.until = self.clock() + 0.6
        else:
            raise ValueError("Unknown mouse action")

    def sample(self, key, sample):
        if key != self.source:
            return
        stamp = sample.get("ms")
        if type(stamp) not in (int, float):
            return
        if self.last == stamp:
            return  # Same packet received by both USB and Bluetooth.
        previous, self.last = self.last, stamp
        if self.calibrating:
            self.calibration.append([sample[k] for k in ("gx", "gy", "gz")])
            if len(self.calibration) >= 50:
                self.bias[key] = dict(zip(("gx", "gy", "gz"),
                    (sum(row[i] for row in self.calibration) / len(self.calibration) for i in range(3))))
                self.calibrating = False
            return
        if self.clock() >= self.until or sample.get("idle") or previous is None:
            return
        dt = (stamp - previous) / 1000
        if not 0 < dt <= 0.25:
            return  # No jump after reconnect, reboot, or a stale packet.
        bias = self.bias.get(key, {})
        def delta(axis, invert):
            speed = sample[axis] - bias.get(axis, 0)
            if abs(speed) < 1.5:
                return 0
            return max(-20, min(20, speed * dt * self.gain * (-1 if invert else 1)))
        dx, dy = delta(self.horizontal, self.invert_x), delta(self.vertical, self.invert_y)
        if dx or dy:
            self.pointer.move(dx, dy)
