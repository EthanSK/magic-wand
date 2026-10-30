# Magic Wand live monitor

A local page to leave open beside your work. It shows what Wand Receiver and the wand
are doing now (connection, awake, desk idle or deep sleep, the light, each button's
lane) and what happened recently.

```sh
# From the magic-wand folder
python3 debug/server.py
# then open http://127.0.0.1:8770/
```

Options: `--port 8771` picks another port (`0` picks a free one) and `--support-dir PATH`
reads a copied receiver folder instead of the live one. It needs only Python 3.9+ from
the standard library. The page has no npm packages and makes no remote requests; it
reuses the published site's fonts from `../docs/fonts/`.

## Reading the page

- **Headline**: what the wand is doing now, in words (Pointer On, Scrolling, HUD Open,
  Recording, Idle, Desk Idle, Deep Sleep), taken from its light and the receiver status.
  Connection problems (Disconnected, Receiver Stopped) replace it.
- **Buttons**: each button's jobs with a one-line reminder of how they work. "Can’t tell"
  means the wand's single light is showing something with higher priority, or the wand
  isn't connected; the page explains which instead of guessing.
- **Errors**: only errors from the current connection count. Older ones stay under
  "earlier errors" so a past failure doesn't look current.
- **Activity**: Key events by default. Buttons adds clicks and presses; Everything also
  shows light changes, motion samples and wand diagnostics. Clicks and quick speech button taps are
  merged into one row, and back-to-back repeats show a count.

## One Bluetooth owner

The installed Wand Receiver is the wand's only Bluetooth owner. A second Bluetooth or
serial reader can make a working wand look disconnected, so this monitor has none.
It is observational only:

- It reads Wand Receiver's own `status.json`, `receiver.log` and `receiver.previous.log`,
  plus an optional `debug.json` (below). It never reads `calibrations/`,
  `desk-reference.json`, option files, review traces or maintenance files.
- It never connects to the wand, signals, restarts or reconfigures the receiver, writes
  a receiver file or posts input. Its API has one read-only endpoint, `GET /api/state`.
  `POST`, `PUT`, `PATCH` and `DELETE` return 405.
- It listens only on `127.0.0.1` and refuses requests whose `Host` isn't
  `127.0.0.1:PORT` or `localhost:PORT`, so another web page can't read it through
  DNS rebinding. Request paths map to a fixed list of page files; nothing else is served.
- To identify the receiver it runs `ps -o comm= -p PID` (or reads `/proc` on Linux)
  for the PID in `status.json`, checks liveness with a signal-0 existence check that
  delivers nothing, and reads the running app's `Info.plist` for its version.

The Control Stones viewer (`../../control-stones/debug/`) owns its own Bluetooth and
USB readers because nothing else reads that board. Only its plain, high-contrast
presentation is reused here; its device readers are deliberately not.

## Where each value comes from

Every lane shows its source: **Status** (Wand Receiver's status file), **Light** (the
wand's last light report), **Log** (best effort from the receiver log) or **Receiver**
(the optional snapshot). Unknown means the evidence isn't there; it never means zero
or off.

| Shown | Source | Notes |
| --- | --- | --- |
| Connected, ready, recording, desk idle, light, options, permissions | `status.json` | Authoritative while the receiver process is verified. |
| Receiver running | PID check | Cached for 10 s; liveness is checked every poll. |
| Deep sleep | Log | `DEEP_STANDBY_REQUESTED` after the last `RUNTIME_READY`, then no connection. |
| Mouse, HUD, scroll | Light priority | The wand shows one light. A higher-priority light (for example Pointer) hides the HUD state, so that lane says Unknown instead of guessing. |
| Review selection | Log | `WAND_REVIEW_SHORTCUT` / `WAND_REVIEW_EXIT`, labelled best effort. |
| Motion delivery | `RAW_DELIVERY` | Reports, window length and largest gap from the receiver's own 5-second windows during continuous motion, with the time it was measured. It is a delivery rate, not latency, and isn't extrapolated into a live rate. |
| Pointer moves | `MOVEMENT_REPORTS_POSTED` | Logged at the first and every 100th move since the receiver started. |
| Errors | `DEVICE_ERROR` and receiver failure lines | Grouped and counted. |
| Battery | Receiver status | Puck voltage-based percentage and voltage, with sample age. Last reading remains labelled stale while disconnected or asleep. |
| Raw sensor values | — | Live sensor values are not logged. |

### Freshness

`status.json`'s `updatedAt` is the time state last *changed*, not a heartbeat: the
receiver rewrites the file only when something changes. The monitor never calls healthy
data stale because nothing changed. Liveness comes from verifying that the status PID is
a running process named `WandReceiver`. If that process has stopped, or the PID belongs
to something else, the page says Receiver Stopped and labels the values as its last status.
A quiet log likewise doesn't mean the wand disconnected.

### Sleep

- **Desk idle**: after a minute resting, lights turn off and Bluetooth stays connected.
  Picking the wand up wakes it.
- **Deep sleep**: after five minutes resting, the receiver asks the wand to switch off
  Bluetooth, motion sensing and lights. Only a custom grip button wakes it; pickup alone
  can't. The disconnect that follows is expected, so the page says Deep Sleep, not
  Disconnected.
- If the receiver can't see the wand for another reason, the power state is Unknown. The
  wand's own power policy darkens its lights after a minute offline and turns its radio
  off after five minutes offline.

## Privacy

Output is sanitised before it leaves the server: Bluetooth identifiers, MAC addresses,
Puck names, email addresses and home or system paths are replaced, and calibration values
(`WAND_CALIBRATED`, `REST_SAMPLE`, `NATIVE_MOTION_CONFIG`, restore calls) are hidden.
Messages are bounded in length. Unknown `status.json` keys are dropped rather than echoed.
Never commit receiver logs, status files or screenshots containing private details; the
test fixtures are synthetic.

## Limits

- History starts from the last 384 KiB of each log file when the monitor starts, then
  follows new lines, including across the receiver's 512 KiB rotation. The page keeps the
  latest 600 events in memory; restarting the monitor rereads the tails.
- Log timestamps have one-second resolution. If the receiver writes more than a megabyte
  between polls, the skipped byte count is shown in Raw Diagnostics.
- Lane values from the light can lag a hold that starts and ends between light reports.
- On a system without `ps` or `/proc`, a live PID is shown as "Found, name unchecked".

## Optional receiver snapshot (`debug.json`)

The current receiver doesn't write this file; the monitor works without it. A future
receiver can write `debug.json` next to `status.json` to make lane values authoritative.
It is used only when `schema` is 1, `pid` matches `status.json` and `generatedAt` is
within 10 seconds. Unknown keys and wrongly typed values are ignored. `middleHeld` and
`bottomHeld` keep the earlier button names: they report the HUD and mouse buttons.

```json
{
  "schema": 1,
  "pid": 12345,
  "generatedAt": "2026-10-24T17:43:05Z",
  "lanes": {
    "mouseFollow": true,
    "hudOpen": false,
    "middleHeld": false,
    "bottomHeld": false,
    "scrollActive": false,
    "heldScroll": null,
    "reviewMode": null
  },
  "power": {
    "restParked": false,
    "deskSleeping": false,
    "deepStandbyPending": false,
    "powerPolicyReady": true
  }
}
```

`reviewMode` is `"changes"`, `"files"` or `null`. The page currently uses `mouseFollow`, `hudOpen`,
`scrollActive`, `reviewMode`, `deskSleeping` and `deepStandbyPending`; the other fields are reserved. Write it atomically and keep it free of
device identifiers, positions and calibration values.

## Tests

```sh
node --test tests/debug-monitor.test.mjs
```

They start the real server against synthetic files in a temporary folder and cover
freshness (a quiet live receiver stays connected; a stopped or different process
doesn't), malformed and missing files, log rotation and truncation, echoed source
versus runtime errors, deep sleep and desk idle, sanitising, local binding, refused
hosts and methods, and the page's basic accessibility.

## Battery source

The receiver queries the Puck's built-in `E.getBattery()` percentage and
`NRF.getBattery()` voltage on its existing connection, at most once per minute
while connected and awake. The dashboard is still read-only; it never connects
to the device or sends a battery command itself.

The percentage assumes a normal CR2032 cell and is a voltage estimate, not a
measured capacity or remaining-runtime prediction. Load and temperature affect
it. See the [Puck battery reference](https://www.espruino.com/Puck.js#battery-level).
Missing, invalid and future-dated readings are not presented as current; readings
older than two minutes or from a disconnected receiver are labelled stale.
