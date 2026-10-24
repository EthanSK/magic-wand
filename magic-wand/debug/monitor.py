"""Read-only model of the installed Wand Receiver's own status and log files.

Nothing here opens Bluetooth, signals a process, writes a file or posts input.
The Magic Wand has exactly one Bluetooth owner: the installed Wand Receiver.
This module only reads the private files that receiver already maintains and
turns them into a sanitised snapshot for the local debug page.
"""
from __future__ import annotations

import json
import os
import plistlib
import re
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

DEFAULT_SUPPORT = Path.home() / "Library" / "Application Support" / "WandReceiver"
COMPONENT = Path(__file__).resolve().parents[1]
STATUS_NAME = "status.json"
LOG_NAME = "receiver.log"
PREVIOUS_LOG_NAME = "receiver.previous.log"
DEBUG_NAME = "debug.json"
RECEIVER_PROCESS = "WandReceiver"

MAX_JSON_BYTES = 64 * 1024
INITIAL_TAIL_BYTES = 384 * 1024
MAX_READ_BYTES = 1024 * 1024
MAX_PARTIAL_BYTES = 64 * 1024
TIMELINE_LIMIT = 600
TIMELINE_SENT = 300
RAW_TAIL_LIMIT = 80
DEBUG_SNAPSHOT_MAX_AGE = 10.0
SNAPSHOT_CACHE_SECONDS = 0.4

# --- sanitising -----------------------------------------------------------

_UUID = re.compile(r"\b[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}\b")
_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
_PATH = re.compile(
    r"(?:file://)?(?:~|/(?:Users|home|private|var|tmp|Volumes|Applications|Library|System|opt|root))"
    r"(?:/[^\s'\"`,;)\]}]*)+"
)
_PUCK_NAME = re.compile(r"puck\.js\s+[0-9a-f]{4}\b", re.IGNORECASE)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_CALIBRATION = re.compile(
    r"\{[^{}]*\bx\"?\s*:\s*-?[\d.eE+-]+[^{}]*\by\"?\s*:[^{}]*\bz\"?\s*:[^{}]*\}"
)
_RESTORE_CALL = re.compile(r"restoreWandCalibration\([^)]*\)")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def sanitize(text: object, limit: int = 240) -> str:
    """Remove identities, home paths and calibration values; bound the length."""
    value = _CONTROL.sub(" ", str(text))
    value = _UUID.sub("‹id›", value)
    value = _MAC.sub("‹id›", value)
    value = _PUCK_NAME.sub("Puck.js ‹id›", value)
    value = _EMAIL.sub("‹email›", value)
    value = _PATH.sub("‹path›", value)
    value = _RESTORE_CALL.sub("restoreWandCalibration(‹hidden›)", value)
    value = _CALIBRATION.sub("{‹calibration hidden›}", value)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > limit:
        value = value[: limit - 1].rstrip() + "…"
    return value


# --- device line classification --------------------------------------------

_RUNTIME_PREFIX = re.compile(
    r"^(?:Uncaught\b|ERROR:|WAND_DIAG EXCEPTION\b|OUT OF MEMORY|Execution Interrupted|FIFO_FULL)"
)
_CODE_HINT = re.compile(r"function\s*\(|\)\s*\{|;|=>|\bif\s*\(|\bprint\s*\(|\bglobal\.")


def classify_device_line(payload: str) -> str:
    """Return "runtime" for an actual device failure and "echo" for echoed source.

    The receiver logs any device line containing "Error" as DEVICE_ERROR. When the
    Espruino console echoes uploaded JavaScript, a line such as
    ``if(!global.wandDiagError){...}`` matches too, but it is source, not a failure.
    """
    text = payload.lstrip("> :\t")
    if _RUNTIME_PREFIX.match(text):
        return "runtime"
    if "OUT OF MEMORY" in text and not _CODE_HINT.search(text):
        return "runtime"
    return "echo"


def summarize_runtime_error(payload: str) -> str:
    text = payload.lstrip("> :\t")
    if text.startswith("WAND_DIAG EXCEPTION"):
        body = text[len("WAND_DIAG EXCEPTION"):].strip()
        try:
            value = json.loads(body)
        except ValueError:
            value = None
        if isinstance(value, dict):
            message = sanitize(value.get("message", "Exception"), 140)
            stack = str(value.get("stack", ""))
            frame = re.search(r"at\s+([A-Za-z_$][\w$.]*)", stack)
            return message + (" in " + frame.group(1) if frame else "")
        return sanitize(body or "Exception", 160)
    return sanitize(text, 160)


# --- log line parsing ------------------------------------------------------

_LINE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2}))\s+(\S+)(?:\s+(.*))?$"
)
_EVENT_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
_HIDDEN_VALUES = {"WAND_CALIBRATED", "REST_SAMPLE", "NATIVE_MOTION_CONFIG"}


def parse_time(text: str) -> Optional[float]:
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def parse_line(line: str) -> Optional[tuple[float, str, str]]:
    """Return (epoch seconds, event, argument text) or None for an unparseable line."""
    match = _LINE.match(line.rstrip("\r\n"))
    if not match:
        return None
    moment = parse_time(match.group(1))
    if moment is None:
        return None
    token = match.group(2).lstrip(">")
    args = match.group(3) or ""
    if token not in ("DEVICE", "DEVICE_ERROR") and ("WAND_CALIBRATED" in token or "WAND_CALIBRATED" in args[:40]):
        return moment, "WAND_CALIBRATED", ""
    if not _EVENT_NAME.match(token):
        return moment, "OTHER", (token + " " + args).strip()
    return moment, token, args


def _bool(text: str) -> Optional[bool]:
    return {"true": True, "false": False, "1": True, "0": False}.get(text.strip().lower())


def _int(text: str) -> Optional[int]:
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _keyed(args: str) -> dict[str, str]:
    """Read "name value name value" pairs such as TABLE_REST_CONFIRMED's arguments."""
    parts = args.split()
    return {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}


RADIO_STATES = {0: "Bluetooth state unknown", 1: "Bluetooth resetting", 2: "Bluetooth unsupported",
                3: "Bluetooth not allowed", 4: "Bluetooth off", 5: "Bluetooth on"}
CONTROL_VERSIONS = {1: "V1 · Pointer", 2: "V2 · Hold to scroll", 3: "V3 · Hold to continue scrolling"}
OPTION_LABELS = {
    "flickScroll": "Flick to scroll",
    "orientationCompensation": "Rotation-independent controls",
    "reviewAxisGestures": "Review with nods and shakes",
    "heldScrollDiagnostics": "Held scroll summary",
}
REVIEW_MODES = {"changes": "Review changes", "files": "Stage files"}
HOLD_TARGETS = {"scroll": "scroll", "drag": "drag", "unknown": "unknown target, scrolling",
                "explicit drag": "tap-then-hold drag", "late (scroll)": "late target, scrolling"}
ERROR_EVENTS = {
    "CONNECT_FAILED": "Connection failed", "WRITE_FAILED": "Bluetooth write failed",
    "NOTIFY_FAILED": "Bluetooth notifications failed", "UART_UNAVAILABLE": "Wand Bluetooth service missing",
    "OPTION_SAVE_FAILED": "Couldn’t save option", "KNOWN_CALIBRATION_SAVE_FAILED": "Couldn’t save calibration",
    "BRIDGE_CACHE_FAILED": "Couldn’t save device code cache", "POWER_POLICY_FAILED": "Power policy failed to load",
    "RUNTIME_LOAD_REJECTED": "Device code load rejected", "BRIDGE_LOAD_REJECTED": "Mode bridge load rejected",
    "VSCODE_REVIEW_FAILED": "VS Code review request failed", "MAINTENANCE_REJECTED": "Maintenance file rejected",
    "LEGACY_STOP_FAILED": "Couldn’t stop old receiver", "DEVICE_NOT_CONFIGURED": "Wand not configured",
}

# Facts that belong to one receiver process. A new STARTED clears them.
_SESSION_FACTS = ("connection", "readyAt", "deepRequested", "deepResumed", "desk", "rest", "pickup",
                  "putDown", "light", "review", "hud", "holdTarget", "movement", "pointer", "button",
                  "attempts", "disconnectedAt", "radio", "powerPolicy", "runtime", "scroll")


class LogModel:
    """Chronological event history plus the latest facts derived from it."""

    def __init__(self) -> None:
        self.timeline: deque = deque(maxlen=TIMELINE_LIMIT)
        self.raw_tail: deque = deque(maxlen=RAW_TAIL_LIMIT)
        self.delivery: deque = deque(maxlen=24)
        self.errors: dict[tuple[str, str], dict] = {}
        self.facts: dict[str, dict] = {}
        self.echoes = 0
        self.last_echo_at: Optional[float] = None
        self.lines = 0
        self.unparsed = 0
        self.hidden_samples = 0
        self.last_event_at: Optional[float] = None
        self.first_event_at: Optional[float] = None

    def fact(self, name: str) -> Optional[dict]:
        return self.facts.get(name)

    def _set(self, name: str, value, moment: float) -> None:
        self.facts[name] = {"value": value, "t": moment}

    def _add(self, moment: float, event: str, category: str, summary: str,
             detail: Optional[str] = None, level: str = "info") -> None:
        self.timeline.append({"t": moment, "event": event, "category": category, "summary": summary,
                              "detail": detail, "level": level})

    def _error(self, moment: float, kind: str, summary: str) -> None:
        key = (kind, summary)
        entry = self.errors.get(key)
        if entry is None:
            entry = self.errors[key] = {"kind": kind, "summary": summary, "count": 0, "first": moment, "last": moment}
        entry["count"] += 1
        entry["last"] = moment

    def feed(self, line: str) -> None:
        parsed = parse_line(line)
        if parsed is None:
            if line.strip():
                self.unparsed += 1
            return
        moment, event, args = parsed
        self.lines += 1
        self.last_event_at = moment
        if self.first_event_at is None:
            self.first_event_at = moment
        shown = "‹values hidden›" if event in _HIDDEN_VALUES and args else sanitize(args, 200)
        stamp = datetime.fromtimestamp(moment, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.raw_tail.append((stamp + " " + event + (" " + shown if shown else "")).strip())
        self._apply(moment, event, args)

    def _apply(self, t: float, event: str, args: str) -> None:  # noqa: C901 - one table of receiver events
        a = args.strip()
        parts = a.split()
        add = self._add
        if event == "STARTED":
            for name in _SESSION_FACTS:
                self.facts.pop(name, None)
            self._set("receiverStarted", True, t)
            self._set("connection", "starting", t)
            add(t, event, "connection", "Receiver started")
        elif event in ("STOPPING", "STOPPED"):
            self._set("receiverStopping", True, t)
            add(t, event, "connection", "Receiver stopping" if event == "STOPPING" else "Receiver stopped")
        elif event == "ALREADY_RUNNING":
            add(t, event, "connection", "Second receiver launch ignored", "Another copy already owns the wand.")
        elif event == "RADIO_STATE":
            state = _int(parts[0]) if parts else None
            self._set("radio", state, t)
            add(t, event, "connection", RADIO_STATES.get(state, "Bluetooth state " + sanitize(a, 20)),
                level="warn" if state in (2, 3, 4) else "info")
        elif event == "SCANNING_FOR_PUCK":
            self._set("connection", "scanning", t)
            add(t, event, "connection", "Scanning for wand")
        elif event == "CONNECTING":
            self._set("connection", "connecting", t)
            attempts = (self.fact("attempts") or {}).get("value", 0) + 1
            self._set("attempts", attempts, t)
            add(t, event, "connection", "Connecting to wand")
        elif event == "CONNECTED_TO_PUCK":
            self._set("connection", "bluetooth", t)
            add(t, event, "connection", "Bluetooth connected", "Loading device code next.")
        elif event == "CHECKING_RUNTIME":
            self._set("runtime", sanitize(a, 40), t)
            add(t, event, "connection", "Checking device code", sanitize(a, 40) or None)
        elif event == "UPLOADING_RUNTIME":
            self._set("connection", "uploading", t)
            add(t, event, "maintenance", "Uploading device code", (sanitize(a, 12) + " commands") if a else None)
        elif event == "RUNTIME_READY":
            self._set("connection", "ready", t)
            self._set("readyAt", True, t)
            self.facts.pop("attempts", None)
            self.facts.pop("disconnectedAt", None)
            add(t, event, "connection", "Ready")
        elif event == "DISCONNECTED":
            self._set("connection", "disconnected", t)
            self._set("disconnectedAt", True, t)
            self._set("desk", False, t)
            self._set("rest", False, t)
            self._set("light", {"mode": "disconnected", "levels": None}, t)
            reason = sanitize(a, 120)
            add(t, event, "connection", "Disconnected", None if reason in ("", "cleanly") else reason, "warn")
        elif event == "CONNECTION_TIMEOUT":
            self._set("connection", "retrying", t)
            add(t, event, "connection", "Connection attempt timed out")
        elif event in ERROR_EVENTS:
            detail = sanitize(a, 160) or None
            if event in ("CONNECT_FAILED", "WRITE_FAILED", "NOTIFY_FAILED", "UART_UNAVAILABLE"):
                self._set("connection", "retrying", t)
            self._error(t, "Receiver", ERROR_EVENTS[event] + (": " + detail if detail else ""))
            add(t, event, "error", ERROR_EVENTS[event], detail, "error")
        elif event == "DEEP_STANDBY_REQUESTED":
            self._set("deepRequested", True, t)
            add(t, event, "sleep", "Deep sleep requested", "After five minutes resting. Bluetooth, motion and lights turn off.")
        elif event == "DEEP_STANDBY_RESUMED":
            resume = _bool(parts[0]) if parts else None
            self._set("deepResumed", resume, t)
            add(t, event, "sleep", "Woke from deep sleep",
                "Pointer resumed" if resume else "Pointer stayed off" if resume is False else None)
        elif event == "POWER_POLICY_READY":
            self._set("powerPolicy", True, t)
            add(t, event, "sleep", "Power policy ready")
        elif event in ("DESK_SLEEP", "DESK_WAKE"):
            sleeping = event == "DESK_SLEEP"
            self._set("desk", sleeping, t)
            add(t, event, "sleep", "Desk idle: lights off" if sleeping else "Woke from desk idle")
        elif event == "TABLE_REST_CONFIRMED":
            values = _keyed(a)
            follow = _bool(values.get("follow", ""))
            self._set("rest", True, t)
            add(t, event, "sleep", "Resting on the desk",
                "Pointer was on" if follow else "Pointer was off" if follow is False else None)
        elif event in ("AUTO_PICKUP", "AUTO_PICKUP_KEPT_STATE"):
            self._set("rest", False, t)
            if event == "AUTO_PICKUP":
                self._set("pickup", "resumed", t)
                add(t, event, "sleep", "Picked up: pointer resumed")
            else:
                follow = _bool(parts[0]) if parts else None
                self._set("pickup", "kept", t)
                add(t, event, "sleep", "Picked up: kept previous state",
                    "Pointer on" if follow else "Pointer off" if follow is False else None)
        elif event == "AUTO_PUT_DOWN":
            self._set("putDown", True, t)
            add(t, event, "sleep", "Put down: pointer paused")
        elif event == "DEVICE_LIGHT":
            mode = parts[0] if parts else "unknown"
            levels = None
            found = re.search(r"\[([^\]]*)\]", a)
            if found:
                try:
                    levels = [round(float(v), 3) for v in found.group(1).split(",")]
                except ValueError:
                    levels = None
                if levels is not None and len(levels) != 3:
                    levels = None
            self._set("light", {"mode": sanitize(mode, 20), "levels": levels}, t)
            add(t, event, "light", "Light: " + LIGHT_NAMES.get(mode, sanitize(mode, 20)), None)
        elif event == "RECORDING_STATE":
            active = _bool(parts[0]) if parts else None
            self._set("recordingLog", active, t)
            add(t, event, "recording", "Recording started" if active else "Recording stopped")
        elif event == "SPEECH_BUTTON":
            down = parts[0] == "1" if parts else None
            sent = len(parts) > 1 and parts[1] == "SENT"
            self._set("speechButton", {"down": down, "sent": sent}, t)
            add(t, event, "buttons", ("Top pressed" if down else "Top released") + (": sent to Agent Flow" if sent else ": Agent Flow unavailable"),
                level="info" if sent else "warn")
        elif event == "HUD_CLOSED":
            self._set("hud", {"open": False, "reason": sanitize(a, 60)}, t)
            add(t, event, "hud", "HUD closed", sanitize(a, 60) or None)
        elif event in ("HUD_HOLD_RELEASED", "HUD_TAP_USED"):
            self._set("hud", {"open": None, "used": True}, t)
            add(t, event, "hud", "HUD hold released: card used" if event == "HUD_HOLD_RELEASED" else "HUD tap: card used")
        elif event == "POINTER_MODE_ENTERED":
            self._set("pointer", "mode", t)
            add(t, event, "buttons", "Pointer mode")
        elif event == "POINTER_RECENTER":
            self._set("pointer", "recentered", t)
            add(t, event, "buttons", "Pointer recentered", "Bottom double tap")
        elif event == "HIGH_DWELL_CLICK":
            add(t, event, "buttons", "Stop-to-click")
        elif event == "BUTTON":
            side = "Left" if parts[:1] == ["LEFT"] else "Right" if parts[:1] == ["RIGHT"] else "Mouse"
            edge = "down" if "DOWN" in parts[1:2] else "up" if "UP" in parts[1:2] else ""
            self._set("button", {"side": side, "edge": edge}, t)
            add(t, event, "buttons", (side + " button " + edge).strip())
        elif event == "CONSUMED_HOLD_CLICK_DROPPED":
            add(t, event, "buttons", "Held click dropped", "The hold was used for scrolling.")
        elif event == "FIRST_DEVICE_REPORT_VALIDATED":
            add(t, event, "motion", "First pointer report accepted")
        elif event == "BOTTOM_HOLD_TARGET":
            target = HOLD_TARGETS.get(a, sanitize(a, 40))
            self._set("holdTarget", target, t)
            add(t, event, "buttons", "Bottom hold: " + target)
        elif event == "BOTTOM_HOLD_RECOVERED":
            add(t, event, "buttons", "Bottom hold ended", sanitize(a, 80) or None)
        elif event in ("SCROLL_BEGIN", "SCROLL_END", "SCROLL_FINISHED_MOUSE_ON"):
            self._set("scroll", event == "SCROLL_BEGIN", t)
            label = {"SCROLL_BEGIN": "Chord scroll started", "SCROLL_END": "Chord scroll ended",
                     "SCROLL_FINISHED_MOUSE_ON": "Scroll finished: pointer on"}[event]
            add(t, event, "buttons", label)
        elif event == "V3_SCROLL_HOLD":
            add(t, event, "buttons", "Held scroll summary", sanitize(a, 200) or None)
        elif event == "WAND_REVIEW_SHORTCUT":
            self._set("review", {"mode": a if a in REVIEW_MODES else None, "active": True}, t)
            add(t, event, "review", REVIEW_MODES.get(a, "Review") + " tracking")
        elif event == "WAND_REVIEW_EXIT":
            self._set("review", {"mode": None, "active": False}, t)
            add(t, event, "review", "Review exited", sanitize(a, 40) or None)
        elif event == "WAND_REVIEW_COMMIT":
            add(t, event, "review", "Review set staged", REVIEW_MODES.get(parts[0], None) if parts else None)
        elif event == "VSCODE_REVIEW_SENT":
            add(t, event, "review", "Sent to VS Code", sanitize(a, 60) or None)
        elif event == "VSCODE_REVIEW_MODE":
            add(t, event, "review", "VS Code review mode", sanitize(a, 40) or None)
        elif event == "RAW_DELIVERY":
            reports = _int(parts[0]) if parts else None
            values = _keyed(" ".join(parts[1:]))
            try:
                seconds = float(values.get("seconds", "nan"))
            except ValueError:
                seconds = float("nan")
            gap = _int(values.get("maxGapMs", ""))
            if reports is not None and seconds == seconds and seconds > 0:
                self.delivery.append({"t": t, "reports": reports, "seconds": seconds, "maxGapMs": gap,
                                      "rate": round(reports / seconds, 1)})
                add(t, event, "motion", "Motion delivery: %d in %.2f s" % (reports, seconds),
                    ("max gap %d ms" % gap) if gap is not None else None)
        elif event == "MOVEMENT_REPORTS_POSTED":
            total = _int(parts[0]) if parts else None
            if total is not None:
                self._set("movement", total, t)
                add(t, event, "motion", "Pointer moves posted: %s" % format(total, ","))
        elif event == "WAND_CALIBRATED":
            self._set("calibrated", True, t)
            add(t, event, "maintenance", "Calibrated", "Values hidden")
        elif event == "KNOWN_CALIBRATION_RESTORE_REQUESTED":
            add(t, event, "maintenance", "Saved calibration restore requested")
        elif event == "KNOWN_CALIBRATION_SAVED":
            add(t, event, "maintenance", "Calibration saved on this Mac")
        elif event == "NATIVE_MOTION_CONFIG":
            add(t, event, "maintenance", "Motion zero applied", "Values hidden")
        elif event == "REST_SAMPLE":
            self.hidden_samples += 1
        elif event == "DEVICE_ERROR":
            if classify_device_line(a) == "runtime":
                summary = summarize_runtime_error(a)
                self._error(t, "Device", summary)
                add(t, event, "error", "Device error", summary, "error")
            else:
                self.echoes += 1
                self.last_echo_at = t
                add(t, event, "diagnostic", "Echoed device code (not an error)", sanitize(a.lstrip("> :"), 120))
        elif event == "DEVICE":
            text = a.lstrip("> ")
            if text.startswith("WAND_RECORDING_LIGHT") or text.endswith(("WAND_RECORDING_LIGHT 0", "WAND_RECORDING_LIGHT 1")):
                add(t, event, "recording", "Recording light " + ("on" if text.endswith("1") else "off"))
            else:
                add(t, event, "diagnostic", "Device diagnostic", sanitize(text, 160))
        elif event == "OPTION_CHANGED":
            label = OPTION_LABELS.get(parts[0], sanitize(parts[0], 40)) if parts else "Option"
            value = _bool(parts[1]) if len(parts) > 1 else None
            add(t, event, "settings", label + (": on" if value else ": off" if value is False else " changed"))
        elif event == "CONTROL_VERSION":
            version = _int(parts[0]) if parts else None
            add(t, event, "settings", "Control version: " + CONTROL_VERSIONS.get(version, sanitize(a, 10)))
        elif event == "ORIENTATION_COMPENSATION":
            value = _bool(parts[0]) if parts else None
            add(t, event, "settings", "Rotation-independent controls: " + ("on" if value else "off"))
        elif event == "ACCESSIBILITY":
            value = _bool(parts[0]) if parts else None
            add(t, event, "connection", "Accessibility allowed" if value else "Accessibility not allowed",
                level="info" if value else "warn")
        elif event == "MAINTENANCE_QUEUED":
            add(t, event, "maintenance", "Maintenance sent to wand", (sanitize(a, 12) + " bytes") if a else None)
        elif event == "MAINTENANCE_NOT_READY":
            add(t, event, "maintenance", "Maintenance waiting for connection")
        elif event == "BRIDGE_CACHE_SAVED":
            add(t, event, "maintenance", "Device code cache saved")
        elif event == "RELOADING_SAVED_PROGRAM":
            add(t, event, "maintenance", "Reloading saved device program")
        elif event in ("LEGACY_HANDOVER_COMPLETE", "STOPPING_LEGACY_RECEIVER"):
            add(t, event, "maintenance", "Old receiver handover" if event == "LEGACY_HANDOVER_COMPLETE" else "Stopping old receiver")
        else:
            add(t, event, "diagnostic", event.replace("_", " ").capitalize(), sanitize(a, 160) or None)


# --- light names (from the one maintained wand description) ---------------

_FALLBACK_LIGHTS = [
    {"mode": "update", "name": "Updating", "display": "#ff8a20", "detail": "Receiver is updating the device code"},
    {"mode": "disconnected", "name": "Disconnected", "display": "#ff8a20", "detail": "Orange while unavailable"},
    {"mode": "calibration", "name": "Calibrating", "display": "#ff8a20", "detail": "Keep it still with no buttons pressed for two seconds"},
    {"mode": "sleep", "name": "Sleeping", "display": "#4a4268", "detail": "Off after a minute on the desk; pickup restores the light"},
    {"mode": "scroll", "name": "Scrolling", "display": "#19e3f0", "detail": "Cyan"},
    {"mode": "app", "name": "App review", "display": "#22e871", "detail": "Green for app review; purple for VS Code file staging",
     "variants": [{"name": "File staging", "levels": [1, 0, 1], "display": "#c96bff"}]},
    {"mode": "mouse", "name": "Pointer", "display": "#4469ff", "detail": "Steady blue, including while recording"},
    {"mode": "hud", "name": "HUD", "display": "#ff5a1f", "detail": "Orange"},
    {"mode": "recording", "name": "Recording", "display": "#ff2e3a", "detail": "Steady red while idle."},
    {"mode": "idle", "name": "Idle", "display": "#4a4268", "detail": "Off"},
]


def load_manifest(path: Path = COMPONENT / "wand.json") -> tuple[list[dict], dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        lights = [entry for entry in data.get("lights", []) if isinstance(entry, dict) and "mode" in entry]
        versions = data.get("versions", {}) if isinstance(data.get("versions"), dict) else {}
        return (lights or _FALLBACK_LIGHTS), versions
    except (OSError, ValueError):
        return _FALLBACK_LIGHTS, {}


LIGHTS, PUBLISHED_VERSIONS = load_manifest()
LIGHT_NAMES = {entry["mode"]: entry.get("name", entry["mode"]) for entry in LIGHTS}
LIGHT_MODES = set(LIGHT_NAMES) | {"unknown"}
# Device priority from the mode bridge's updateLights(): an earlier mode hides every later one.
LIGHT_PRIORITY = ["update", "disconnected", "calibration", "sleep", "scroll", "app", "mouse", "hud", "recording", "idle"]


# --- following the rotating log -------------------------------------------

class LogFollower:
    """Incrementally read receiver.log, finishing the old file across rotation."""

    def __init__(self, directory: Path, tail_bytes: int = INITIAL_TAIL_BYTES) -> None:
        self.current = directory / LOG_NAME
        self.previous = directory / PREVIOUS_LOG_NAME
        self.tail_bytes = tail_bytes
        self.identity: Optional[tuple[int, int]] = None
        self.offset = 0
        self.partial = b""
        self.started = False
        self.rotations = 0
        self.truncations = 0
        self.skipped_bytes = 0
        self.bytes_read = 0
        self.present = False
        self.error: Optional[str] = None

    @staticmethod
    def _identity(stat: os.stat_result) -> tuple[int, int]:
        return stat.st_dev, stat.st_ino

    def _read(self, path: Path, start: int, limit: int, drop_first: bool, keep_partial: bool) -> tuple[list[str], int]:
        with open(path, "rb") as handle:
            handle.seek(start)
            data = handle.read(limit)
        self.bytes_read += len(data)
        buffer = (self.partial if keep_partial else b"") + data
        pieces = buffer.split(b"\n")
        rest = pieces.pop()
        if drop_first and pieces:
            pieces = pieces[1:]
        elif drop_first:
            rest = b""
        if keep_partial:
            self.partial = rest if len(rest) <= MAX_PARTIAL_BYTES else b""
        lines = [piece.decode("utf-8", "replace") for piece in pieces]
        if not keep_partial and rest:
            lines.append(rest.decode("utf-8", "replace"))
        return lines, len(data)

    def _tail(self, path: Path) -> list[str]:
        try:
            size = os.stat(path).st_size
        except OSError:
            return []
        start = max(0, size - self.tail_bytes)
        lines, _ = self._read(path, start, self.tail_bytes, start > 0, keep_partial=False)
        return lines

    def poll(self) -> list[str]:
        try:
            return self._poll()
        except OSError as error:
            self.error = sanitize(error.strerror or type(error).__name__, 80)
            return []

    def _poll(self) -> list[str]:
        self.error = None
        lines: list[str] = []
        try:
            stat: Optional[os.stat_result] = os.stat(self.current)
        except FileNotFoundError:
            stat = None
        if not self.started:
            self.started = True
            lines += self._tail(self.previous)
            if stat is not None:
                start = max(0, stat.st_size - self.tail_bytes)
                read, count = self._read(self.current, start, stat.st_size - start, start > 0, keep_partial=True)
                lines += read
                self.identity, self.offset = self._identity(stat), start + count
            self.present = stat is not None or self.previous.exists()
            return lines
        if stat is None:
            if self.identity is not None:
                self.rotations += 1
            lines += self._finish_rotated()
            self.present = self.previous.exists()
            return lines
        self.present = True
        identity = self._identity(stat)
        if self.identity is not None and identity != self.identity:
            lines += self._finish_rotated()
            self.rotations += 1
            self.identity, self.offset, self.partial = identity, 0, b""
        elif stat.st_size < self.offset:
            self.truncations += 1
            self.offset, self.partial = 0, b""
        if self.identity is None:
            self.identity, self.offset = identity, 0
        if stat.st_size > self.offset:
            available = stat.st_size - self.offset
            drop = False
            if available > MAX_READ_BYTES:
                self.skipped_bytes += available - MAX_READ_BYTES
                self.offset = stat.st_size - MAX_READ_BYTES
                self.partial, drop = b"", True
            read, count = self._read(self.current, self.offset, stat.st_size - self.offset, drop, keep_partial=True)
            lines += read
            self.offset += count
        return lines

    def _finish_rotated(self) -> list[str]:
        """The receiver renames receiver.log to receiver.previous.log; read what we missed."""
        if self.identity is None:
            return []
        try:
            stat = os.stat(self.previous)
        except OSError:
            return []
        if self._identity(stat) != self.identity:
            return []
        lines: list[str] = []
        if stat.st_size > self.offset:
            lines, _ = self._read(self.previous, self.offset, min(stat.st_size - self.offset, MAX_READ_BYTES), False, keep_partial=True)
        if self.partial:
            lines.append(self.partial.decode("utf-8", "replace"))
        self.partial = b""
        self.identity, self.offset = None, 0
        return lines

    def describe(self) -> dict:
        return {"present": self.present, "rotationsSeen": self.rotations, "truncationsSeen": self.truncations,
                "bytesRead": self.bytes_read, "bytesSkipped": self.skipped_bytes, "error": self.error}


# --- status and optional receiver snapshot --------------------------------

def _read_json(path: Path) -> tuple[Optional[dict], Optional[str], Optional[float]]:
    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return None, "missing", None
    except OSError as error:
        return None, sanitize(error.strerror or "unreadable", 60), None
    if stat.st_size > MAX_JSON_BYTES:
        return None, "file is too large", stat.st_mtime
    try:
        value = json.loads(path.read_bytes())
    except (OSError, ValueError, UnicodeDecodeError):
        return None, "not valid JSON", stat.st_mtime
    if not isinstance(value, dict):
        return None, "not a JSON object", stat.st_mtime
    return value, None, stat.st_mtime


def _typed(value, kind):
    if kind is bool:
        return value if isinstance(value, bool) else None
    if kind is int:
        return value if isinstance(value, int) and not isinstance(value, bool) else None
    if kind is str:
        return value if isinstance(value, str) else None
    return None


def read_status(path: Path) -> dict:
    """Normalise status.json to known fields. Unknown keys are dropped, not echoed."""
    raw, error, mtime = _read_json(path)
    if raw is None:
        return {"present": error != "missing", "valid": False, "error": None if error == "missing" else error, "mtime": mtime}
    options = raw.get("options") if isinstance(raw.get("options"), dict) else {}
    trace = raw.get("reviewTrace") if isinstance(raw.get("reviewTrace"), dict) else {}
    light = _typed(raw.get("lightMode"), str)
    updated = _typed(raw.get("updatedAt"), str)
    fields = {
        "pid": _typed(raw.get("pid"), int),
        "connected": _typed(raw.get("connected"), bool),
        "ready": _typed(raw.get("ready"), bool),
        "recording": _typed(raw.get("recording"), bool),
        "deskSleeping": _typed(raw.get("deskSleeping"), bool),
        "lightMode": light if light in LIGHT_MODES else ("unknown" if light is None else sanitize(light, 20)),
        "accessibility": _typed(raw.get("accessibility"), bool),
        "bluetoothAuthorization": _typed(raw.get("bluetoothAuthorization"), int),
        "options": {
            "controlVersion": _typed(options.get("controlVersion"), int),
            "flickScroll": _typed(options.get("flickScroll"), bool),
            "orientationCompensation": _typed(options.get("orientationCompensation"), bool),
            "reviewAxisGestures": _typed(options.get("reviewAxisGestures"), bool),
        },
        "reviewTrace": {key: _typed(trace.get(key), kind) for key, kind in (
            ("enabled", bool), ("buffered", int), ("dropped", int), ("diskError", bool),
            ("maximumFileBytes", int), ("maximumFiles", int))},
        "updatedAt": parse_time(updated) if updated else None,
    }
    if fields["connected"] is None or fields["ready"] is None:
        return {"present": True, "valid": False, "error": "missing connected or ready", "mtime": mtime}
    return {"present": True, "valid": True, "error": None, "mtime": mtime, "fields": fields}


DEBUG_LANES = {"mouseFollow": bool, "hudOpen": bool, "middleHeld": bool, "bottomHeld": bool,
               "scrollActive": bool, "heldScroll": str, "reviewMode": str}
DEBUG_POWER = {"restParked": bool, "deskSleeping": bool, "deepStandbyPending": bool, "powerPolicyReady": bool}


def read_debug_snapshot(path: Path, pid: Optional[int], now: float) -> dict:
    """Optional future receiver snapshot (see README). Ignored unless fresh and from the same receiver."""
    raw, error, _ = _read_json(path)
    if raw is None:
        return {"present": error != "missing", "used": False, "reason": None if error == "missing" else error}
    generated = parse_time(raw["generatedAt"]) if isinstance(raw.get("generatedAt"), str) else None
    if raw.get("schema") != 1:
        return {"present": True, "used": False, "reason": "unsupported schema"}
    if pid is None or _typed(raw.get("pid"), int) != pid:
        return {"present": True, "used": False, "reason": "from a different receiver process"}
    if generated is None or now - generated > DEBUG_SNAPSHOT_MAX_AGE or generated - now > 2:
        return {"present": True, "used": False, "reason": "not fresh"}
    def pick(source, schema):
        source = source if isinstance(source, dict) else {}
        out = {}
        for key, kind in schema.items():
            value = source.get(key)
            if value is None or _typed(value, kind) is not None:
                out[key] = None if value is None else (sanitize(value, 20) if kind is str else value)
        return out
    return {"present": True, "used": True, "reason": None, "generatedAt": generated,
            "lanes": pick(raw.get("lanes"), DEBUG_LANES), "power": pick(raw.get("power"), DEBUG_POWER)}


# --- process verification --------------------------------------------------

_VERSION_TEXT = re.compile(r"^[\w.+-]{1,32}$")


def _ps_command(pid: int) -> Optional[str]:
    if sys.platform.startswith("linux"):
        try:
            return os.readlink(f"/proc/{pid}/exe")
        except OSError:
            try:
                return Path(f"/proc/{pid}/comm").read_text().strip()
            except OSError:
                pass
    try:
        result = subprocess.run(["ps", "-o", "comm=", "-p", str(pid)], capture_output=True, text=True, timeout=1.5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    text = result.stdout.strip()
    return text or ("" if result.returncode != 0 else None)


class ProcessProbe:
    """Check the status file's PID belongs to a live Wand Receiver. Read-only: sends no signals."""

    def __init__(self, expected: str = RECEIVER_PROCESS, ttl: float = 10.0,
                 command: Callable[[int], Optional[str]] = _ps_command,
                 alive: Optional[Callable[[int], Optional[bool]]] = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.expected, self.ttl, self.command, self.clock = expected, ttl, command, clock
        self.alive = alive or self._alive
        self.cache: dict[int, tuple[float, str, dict]] = {}

    @staticmethod
    def _alive(pid: int) -> Optional[bool]:
        # Signal 0 performs only the existence and permission check; nothing is delivered.
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return None
        return True

    def check(self, pid: Optional[int]) -> dict:
        if not isinstance(pid, int) or pid <= 0:
            return {"state": "unknown"}
        alive = self.alive(pid)
        if alive is False:
            self.cache.pop(pid, None)
            return {"state": "stopped"}
        cached = self.cache.get(pid)
        now = self.clock()
        if cached and now - cached[0] < self.ttl:
            return {"state": cached[1], **cached[2]}
        command = self.command(pid)
        if command is None:
            state, extra = ("unverified" if alive else "unknown"), {}
        elif command == "":
            state, extra = "stopped", {}
        elif os.path.basename(command) == self.expected:
            state, extra = "running", self._version(command)
        else:
            state, extra = "other", {}
        self.cache = {pid: (now, state, extra)}
        return {"state": state, **extra}

    def _version(self, command: str) -> dict:
        path = Path(command)
        if path.parent.name != "MacOS" or path.parent.parent.name != "Contents":
            return {}
        try:
            with open(path.parent.parent / "Info.plist", "rb") as handle:
                info = plistlib.load(handle)
        except (OSError, ValueError, plistlib.InvalidFileException):
            return {}
        out = {}
        for key, name in (("CFBundleShortVersionString", "version"), ("CFBundleVersion", "build")):
            value = info.get(key)
            if isinstance(value, str) and _VERSION_TEXT.match(value):
                out[name] = value
        return out


# --- the snapshot ----------------------------------------------------------

def _since(fact: Optional[dict]) -> Optional[float]:
    return fact["t"] if fact else None


class Monitor:
    def __init__(self, support: Path = DEFAULT_SUPPORT, probe: Optional[ProcessProbe] = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.support = Path(support)
        self.probe = probe or ProcessProbe()
        self.clock = clock
        self.follower = LogFollower(self.support)
        self.model = LogModel()
        self.lock = threading.Lock()
        self.cached: Optional[dict] = None
        self.cached_at = 0.0

    def snapshot(self) -> dict:
        with self.lock:
            now = self.clock()
            if self.cached is not None and 0 <= now - self.cached_at < SNAPSHOT_CACHE_SECONDS:
                return self.cached
            for line in self.follower.poll():
                self.model.feed(line)
            status = read_status(self.support / STATUS_NAME)
            fields = status.get("fields") or {}
            process = self.probe.check(fields.get("pid")) if status["valid"] else {"state": "unknown"}
            debug = read_debug_snapshot(self.support / DEBUG_NAME, fields.get("pid"), now) if status["valid"] else {"present": False, "used": False}
            self.cached = build_snapshot(now, status, process, self.model, self.follower, debug)
            self.cached_at = now
            return self.cached


def _light_entry(mode: str) -> dict:
    for entry in LIGHTS:
        if entry.get("mode") == mode:
            return entry
    return {}


def build_snapshot(now: float, status: dict, process: dict, model: LogModel, follower: LogFollower, debug: dict) -> dict:  # noqa: C901
    fields = status.get("fields") or {}
    valid = bool(status.get("valid"))
    pstate = process.get("state", "unknown")
    live = valid and pstate in ("running", "unverified")
    connected = live and fields.get("connected") is True
    ready = connected and fields.get("ready") is True
    ready_fact = model.fact("readyAt")
    ready_at = _since(ready_fact)
    deep_fact = model.fact("deepRequested")
    disconnected_fact = model.fact("disconnectedAt")
    radio = (model.fact("radio") or {}).get("value")
    dbg_lanes = debug.get("lanes") if debug.get("used") else None
    dbg_power = debug.get("power") if debug.get("used") else None

    deep_after_ready = deep_fact is not None and (ready_at is None or deep_fact["t"] >= ready_at)
    deep_sleep = live and not connected and deep_after_ready
    deep_pending = connected and deep_after_ready and not (dbg_power and dbg_power.get("deepStandbyPending") is False)

    # Connection headline -----------------------------------------------------------------
    attempts = (model.fact("attempts") or {}).get("value", 0)
    if not status.get("present"):
        conn = {"state": "no-status", "title": "No Receiver Status", "tone": "unknown",
                "detail": "Wand Receiver hasn’t written a status file here."}
    elif not valid:
        conn = {"state": "unreadable", "title": "Status Unreadable", "tone": "warn",
                "detail": "status.json couldn’t be read: %s." % (status.get("error") or "unknown problem")}
    elif pstate == "stopped":
        conn = {"state": "receiver-stopped", "title": "Receiver Stopped", "tone": "off",
                "detail": "Wand Receiver isn’t running. Showing its last status."}
    elif pstate == "other":
        conn = {"state": "receiver-stopped", "title": "Receiver Stopped", "tone": "off",
                "detail": "The process in status.json isn’t Wand Receiver. Showing its last status."}
    elif pstate == "unknown":
        conn = {"state": "unknown", "title": "Receiver Unknown", "tone": "unknown",
                "detail": "status.json has no usable process ID to check."}
    elif fields.get("accessibility") is False:
        conn = {"state": "permission", "title": "Accessibility Needed", "tone": "warn",
                "detail": "Wand Receiver can’t connect until it’s allowed in Privacy & Security → Accessibility."}
    elif fields.get("bluetoothAuthorization") not in (None, 3):
        conn = {"state": "permission", "title": "Bluetooth Permission Needed", "tone": "warn",
                "detail": "Allow Wand Receiver in Privacy & Security → Bluetooth."}
    elif ready:
        conn = {"state": "ready", "title": "Connected", "tone": "good",
                "detail": "Ready. Deep sleep requested; waiting for the wand to turn its radio off." if deep_pending else "Ready."}
    elif connected:
        conn = {"state": "loading", "title": "Loading Device Code", "tone": "warn",
                "detail": "Bluetooth is connected; the receiver is checking or loading the wand’s code."}
    elif deep_sleep:
        conn = {"state": "deep-sleep", "title": "Deep Sleep", "tone": "sleep",
                "detail": "Press any grip button to wake it. Picking it up alone won’t."}
    elif radio == 4:
        conn = {"state": "bluetooth-off", "title": "Bluetooth Off", "tone": "warn",
                "detail": "Turn Bluetooth on to reconnect."}
    else:
        conn = {"state": "disconnected", "title": "Disconnected", "tone": "warn",
                "detail": "Wand Receiver is retrying." + (" %d attempts so far." % attempts if attempts > 1 else "")}
    conn["since"] = (_since(disconnected_fact) if conn["state"] in ("disconnected", "deep-sleep", "bluetooth-off") else
                     ready_at if conn["state"] == "ready" else None)
    if conn["state"] == "deep-sleep" and disconnected_fact and deep_fact and disconnected_fact["t"] < deep_fact["t"]:
        conn["since"] = deep_fact["t"]
    if pstate == "unverified" and conn["state"] in ("ready", "loading", "disconnected", "deep-sleep"):
        conn["detail"] += " The receiver process was found but its name couldn’t be checked here."

    # Power ------------------------------------------------------------------------------
    desk_fact = model.fact("desk")
    if deep_sleep:
        power = {"state": "deep-sleep", "label": "Deep sleep", "basis": "log",
                 "detail": "Bluetooth, motion and lights are off. Any grip button wakes it; pickup alone can’t.",
                 "since": conn["since"]}
    elif ready and (fields.get("deskSleeping") is True or (dbg_power or {}).get("deskSleeping") is True):
        power = {"state": "desk-idle", "label": "Desk idle", "basis": "status",
                 "detail": "Lights off and still connected. Picking it up wakes it. Deep sleep follows after five minutes resting.",
                 "since": desk_fact["t"] if desk_fact and desk_fact["value"] else None}
    elif ready:
        resting = (model.fact("rest") or {}).get("value") is True
        power = {"state": "awake", "label": "Awake", "basis": "status",
                 "detail": "Resting on the desk; lights turn off after a minute." if resting else None,
                 "since": desk_fact["t"] if desk_fact and desk_fact["value"] is False else ready_at}
    elif connected:
        power = {"state": "awake", "label": "Awake", "basis": "status", "detail": "Loading device code.", "since": None}
    elif live and conn["state"] in ("disconnected", "bluetooth-off"):
        offline = now - disconnected_fact["t"] if disconnected_fact else None
        detail = "The receiver can’t see the wand, so its power state isn’t reported."
        if offline is not None and offline >= 300:
            detail += " After five minutes offline the wand turns its own radio off; a grip button wakes it."
        else:
            detail += " After five minutes offline it turns its own radio off."
        power = {"state": "unknown", "label": "Unknown", "basis": "log", "detail": detail, "since": None}
    else:
        power = {"state": "unknown", "label": "Unknown", "basis": "none",
                 "detail": "Unknown until Wand Receiver is running.", "since": None}

    # Light ------------------------------------------------------------------------------
    mode = fields.get("lightMode", "unknown") if live else "unknown"
    light_fact = model.fact("light")
    levels = light_fact["value"].get("levels") if light_fact and light_fact["value"].get("mode") == mode else None
    entry = _light_entry(mode)
    if deep_sleep:
        light = {"mode": "off", "name": "Off", "display": "#4a4268", "detail": "Deep sleep turns every light off.", "basis": "log"}
    elif live and not connected:
        light = {"mode": "unreported", "name": "Not reported", "display": None, "basis": "status",
                 "detail": "The receiver can’t see the wand. It shows orange while unavailable and goes dark after a minute offline."}
    elif not live or mode == "unknown" or not entry:
        light = {"mode": "unknown", "name": "Not reported", "display": None, "basis": "none",
                 "detail": "No light report from the wand yet." if live else "Needs a running Wand Receiver."}
    else:
        name, display = entry.get("name", mode), entry.get("display")
        for variant in entry.get("variants", []) or []:
            if levels and [round(float(v), 3) for v in variant.get("levels", [])] == levels:
                name, display = variant.get("name", name), variant.get("display", display)
        light = {"mode": mode, "name": name, "display": display, "detail": entry.get("detail"), "basis": "status"}
    light["levels"] = levels
    light["since"] = light_fact["t"] if light_fact and light_fact["value"].get("mode") == mode and light["mode"] == mode else None

    # Lanes ------------------------------------------------------------------------------
    rank = LIGHT_PRIORITY.index(mode) if mode in LIGHT_PRIORITY else -1
    shown = light["name"] if light["mode"] == mode else "nothing"

    def from_light(own: str, on: str, off: str) -> tuple[str, str, Optional[str]]:
        """Use the device light priority: a higher-priority mode hides this lane."""
        if not ready:
            return "Unknown", "unknown", None
        if mode == own:
            return on, "on", None
        own_rank = LIGHT_PRIORITY.index(own)
        if rank > own_rank:
            return off, "off", None
        return "Unknown", "unknown", "The light shows %s, which hides this." % shown

    def ago(fact: Optional[dict], label: str) -> Optional[dict]:
        return {"label": label, "t": fact["t"]} if fact else None

    lanes = []
    rec_fact = model.fact("recordingLog")
    recording = fields.get("recording") if live else None
    speech = model.fact("speechButton")
    lanes.append({
        "id": "speech", "button": "Top", "lane": "Speech",
        "value": "Recording" if recording else "Off" if recording is False else "Unknown",
        "tone": "on" if recording else "off" if recording is False else "unknown",
        "basis": "status" if recording is not None else "none",
        "since": rec_fact["t"] if rec_fact and rec_fact["value"] == recording else None,
        "note": None,
        "last": ago(speech, "Last Top press" if speech["value"].get("sent") else "Last Top press: Agent Flow unavailable") if speech else None,
    })
    hud_fact = model.fact("hud")
    value, tone, note = from_light("hud", "Open", "Closed")
    basis = "light"
    if dbg_lanes and dbg_lanes.get("hudOpen") is not None:
        value, tone, note, basis = ("Open", "on", None, "receiver") if dbg_lanes["hudOpen"] else ("Closed", "off", None, "receiver")
    hud_last = None
    if hud_fact:
        hud_last = ago(hud_fact, "HUD closed" + (" (" + hud_fact["value"]["reason"] + ")" if hud_fact["value"].get("reason") else "")
                       if hud_fact["value"].get("open") is False else "HUD card used")
    lanes.append({"id": "hud", "button": "Middle", "lane": "HUD", "value": value, "tone": tone,
                  "basis": basis if tone != "unknown" else "none", "since": light["since"] if tone == "on" and basis == "light" else None,
                  "note": note, "last": hud_last})
    review_fact = model.fact("review")
    if not ready:
        rv = ("Unknown", "unknown", "none", None)
    elif dbg_lanes and "reviewMode" in dbg_lanes:
        selected = dbg_lanes.get("reviewMode")
        rv = (REVIEW_MODES.get(selected or "", "None selected"), "on" if selected else "off", "receiver", None)
    elif review_fact and review_fact["value"].get("active"):
        rv = (REVIEW_MODES.get(review_fact["value"].get("mode") or "", "Review"), "on", "log", review_fact["t"])
    elif review_fact:
        rv = ("None selected", "off", "log", review_fact["t"])
    else:
        rv = ("Unknown", "unknown", "none", None)
    lanes.append({"id": "review", "button": "Middle", "lane": "Review", "value": rv[0], "tone": rv[1], "basis": rv[2],
                  "since": rv[3], "note": "Best effort from the log." if rv[2] == "log" else ("No review events logged this session." if ready and rv[2] == "none" else None),
                  "last": None})
    value, tone, note = from_light("mouse", "On", "Off")
    basis = "light"
    if dbg_lanes and dbg_lanes.get("mouseFollow") is not None:
        value, tone, note, basis = ("On", "on", None, "receiver") if dbg_lanes["mouseFollow"] else ("Off", "off", None, "receiver")
    pointer_last = None
    for name, label in (("putDown", "Put down"), ("pickup", "Picked up"), ("pointer", "Pointer mode"), ("button", "Mouse button")):
        candidate = model.fact(name)
        if candidate and (pointer_last is None or candidate["t"] > pointer_last["t"]):
            if name == "pointer" and candidate["value"] == "recentered":
                label = "Recentered"
            pointer_last = {"label": label, "t": candidate["t"]}
    lanes.append({"id": "mouse", "button": "Bottom", "lane": "Mouse", "value": value, "tone": tone,
                  "basis": basis if tone != "unknown" else "none", "since": light["since"] if tone == "on" and basis == "light" else None,
                  "note": note, "last": pointer_last})
    value, tone, note = from_light("scroll", "Scrolling", "Idle")
    basis = "light"
    if dbg_lanes and dbg_lanes.get("scrollActive") is not None:
        value, tone, note, basis = ("Scrolling", "on", None, "receiver") if dbg_lanes["scrollActive"] else ("Idle", "off", None, "receiver")
    hold = model.fact("holdTarget")
    lanes.append({"id": "scroll", "button": "Bottom", "lane": "Scroll", "value": value, "tone": tone,
                  "basis": basis if tone != "unknown" else "none", "since": light["since"] if tone == "on" and basis == "light" else None,
                  "note": note, "last": ago(hold, "Last hold: " + hold["value"]) if hold else None})

    # Delivery and errors ----------------------------------------------------------------------
    delivery = list(model.delivery)
    movement = model.fact("movement")
    errors = sorted(model.errors.values(), key=lambda e: e["last"], reverse=True)[:30]
    since_ready = sum(1 for item in model.timeline if item["level"] == "error" and ready_at is not None and item["t"] >= ready_at)

    options = fields.get("options") or {}
    version = options.get("controlVersion")
    published = {key: PUBLISHED_VERSIONS.get(key) for key in ("receiver", "receiverBuild", "deviceRuntime", "persistentImage")}
    auth = fields.get("bluetoothAuthorization")
    return {
        "schema": 1,
        "now": now,
        "headline": conn,
        "power": power,
        "light": light,
        "lanes": lanes,
        "battery": {"state": "not-reported", "detail": "The receiver doesn’t read battery level."},
        "delivery": {"latest": delivery[-1] if delivery else None, "history": delivery},
        "movement": {"total": movement["value"], "t": movement["t"]} if movement else None,
        "settings": {
            "controlVersion": CONTROL_VERSIONS.get(version, None if version is None else "V%d" % version),
            "flickScroll": options.get("flickScroll"),
            "orientationCompensation": options.get("orientationCompensation"),
            "reviewAxisGestures": options.get("reviewAxisGestures"),
            "reviewTrace": fields.get("reviewTrace") if valid else None,
        } if valid else None,
        "receiver": {
            "process": pstate,
            "version": process.get("version"),
            "build": process.get("build"),
            "deviceCode": (model.fact("runtime") or {}).get("value"),
            "published": published,
            "accessibility": fields.get("accessibility") if valid else None,
            "bluetooth": {0: "Not asked yet", 1: "Restricted", 2: "Denied", 3: "Allowed"}.get(auth, None if auth is None else "Code %d" % auth),
            "powerPolicyReadyAt": _since(model.fact("powerPolicy")),
            "startedAt": _since(model.fact("receiverStarted")),
            "calibratedAt": _since(model.fact("calibrated")),
        },
        "errors": {"groups": errors, "sinceReady": since_ready, "echoes": model.echoes, "lastEchoAt": model.last_echo_at},
        "timeline": list(model.timeline)[-TIMELINE_SENT:][::-1],
        "sources": {
            "status": {"present": bool(status.get("present")), "valid": valid, "error": status.get("error"),
                       "changedAt": fields.get("updatedAt"), "modifiedAt": status.get("mtime")},
            "process": {"state": pstate, "checkedAt": now if valid else None},
            "log": {**follower.describe(), "lines": model.lines, "unparsed": model.unparsed,
                    "firstEventAt": model.first_event_at, "lastEventAt": model.last_event_at,
                    "hiddenRestSamples": model.hidden_samples},
            "debug": {"present": bool(debug.get("present")), "used": bool(debug.get("used")), "reason": debug.get("reason")},
        },
        "raw": {"status": {k: v for k, v in fields.items()} if valid else None, "log": list(model.raw_tail)},
    }
