# Temporary review gesture capture

Use this while testing Magic Wand Review changes (Ethan's “eyes mode”) and Stage files
(his “bang mode”). The normal receiver log records commands, not the points that led
to them. Capture is off by default. Enable it locally until the tester is happy with
the gesture behavior, then turn it off:

```sh
python3 scripts/review_trace.py capture on
python3 scripts/review_trace.py capture status
python3 scripts/review_trace.py capture off
```

The installed receiver reads the switch within about a second, without an app restart.
Its next status heartbeat reports `reviewTrace.enabled` and any writer error. A disabled
or failed trace writer never blocks review input. Keep Agent Flow running during testing.

## What it records

Files stay in `~/Library/Application Support/WandReceiver/review-traces/` with owner-only
permissions. The configuration is `review-trace.json` in the parent directory. The
writer keeps four files of at most 2 MiB each and a bounded 512-record pending buffer;
it drops diagnostic records if the writer cannot keep up. JSON encoding and disk access
run on a separate utility queue. It does not increase the Puck's sample rate or send
extra sensor requests.

Each review input includes the delivered `@NAV` point, the rotation-corrected point
and delta, monotonic time, eligibility or rejection reason, the classifier's diagnostic
state, and the resulting next/previous step. Boundaries identify review entry, exit,
commit, held-button suppression and resets. Separate request records show what the
receiver queued to Better Git; they do not prove that the editor executed it.

“Raw point” means the NAV value delivered by the existing firmware, before Mac
orientation projection. It is not an unfiltered gyro sample: the firmware's noise
threshold may already have removed very small physical motion. Capture includes no
audio, screenshots, document text, chat contents or Bluetooth device identity.
Keep these private files out of Git, public reports and model prompts unless sharing
the particular trace is authorized.

## Replay without moving anything

On macOS with the Xcode command line tools:

```sh
python3 scripts/review_trace.py replay --report /tmp/wand-review-report.json
# Or replay a copied capture directory:
python3 scripts/review_trace.py replay /path/to/private/capture
```

The command compiles the canonical `WandPointerControl.swift` with an offline reader.
It runs the real review classifier, not a second port of it, and never creates the
receiver, connects to Bluetooth, posts mouse events or calls Better Git. The report
compares recorded and replayed steps, identifies malformed/dropped records and records
the classifier source hash. `--source` selects a different saved canonical Swift source
when comparing revisions.

A rotated file set can start midway through a gesture. Live capture can also start
after noise learning has begun, and replaying with changed source naturally changes
decisions. The report calls out these limits; a difference alone is not a confirmed
bug. Inspect the recorded state and the full gesture boundary before drawing a conclusion.

## Testing workflow

1. Note the installed receiver build, control version and enabled review option.
2. Turn capture on before the gesture test. Check for a capture header and writer errors.
3. Enter Review changes or Stage files and try the particular motion. Record what the
   tester intended separately; the point history is evidence of input, not mind reading.
4. Preserve only the relevant local capture before another long session rotates it away.
5. Replay the points, compare actual decisions with intent, add an anonymized synthetic
   regression, then verify the fix. Keep physical acceptance separate from passing traces.
6. Turn capture off once the tester accepts the behavior. The bounded files remain local
   for inspection; disabling capture does not delete them.
