"""Validate wire-format packets without importing transports or touching hardware."""
import json
import math

FINGERS = {2: "Thumb", 3: "Index", 4: "Middle", 5: "Ring", 6: "Little"}
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
    if type(sample.get("ms")) not in (int, float) or not math.isfinite(sample["ms"]):
        raise ValueError("Invalid timestamp")
    sensor = value.get("sensor", "hand")
    if sensor not in ("hand", "finger"):
        raise ValueError("Invalid sensor")
    sample["sensor"] = sensor
    if sensor == "finger":
        channel = value.get("channel")
        if type(channel) is not int or channel not in FINGERS:
            raise ValueError("Invalid finger channel")
        sample["channel"] = channel
        sample["finger"] = FINGERS[channel]
    if type(value.get("idle")) is bool:
        sample["idle"] = value["idle"]
        sample["sleep_ready"] = value.get("sleep_ready") is True
    if type(value.get("i2c_timeouts")) is int and value["i2c_timeouts"] >= 0:
        sample["i2c_timeouts"] = value["i2c_timeouts"]
    battery = value.get("battery_v")
    if type(battery) in (int, float) and math.isfinite(battery) and 0 < battery < 6:
        sample["battery_v"] = battery
        sample["charging"] = value.get("charging") is True
    return sample
