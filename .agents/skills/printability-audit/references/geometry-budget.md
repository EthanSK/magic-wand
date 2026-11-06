# Geometry work without hard RAM limits

User-requested — 2026-11-06: “dont add a hard memory limit remov ethat and chekc”. Fix excessive allocations and retained resources in our own CAD, queries, exporters and viewers. Do not impose a hard RAM cap or refuse work based on the host memory-pressure level. Keep actual causes separate from a suspected leak or a third-party app bug.

Use the shared Fleet coordinator when a suitable worker has capacity. Reserve before direct SSH or submit a managed job. Required dependencies may be explicitly prepared in a disposable job; do not alter installed worker apps or services just because a probe reports something missing.

Run finite CAD/export/query units serially from the repository root:

```sh
python3 .agents/skills/printability-audit/scripts/geometry_budget.py \
  --timeout-seconds 900 --receipt /task/scratch/check.json \
  -- /path/to/cad-python path/to/check.py
```

The legacy filename now refers to query-work and time budgets, not a memory limit. The runner owns one host-wide kernel lease independent of TMPDIR, stops owned work on cancellation or timeout, and rejects leftover background descendants. It refreshes the process-group snapshot after leader exit, defers cancellation until the new child handle is saved, and finishes cleanup despite repeated signals. The direct child inherits the lease, preventing a replacement job overlapping that survivor after forced supervisor termination. Confirm and stop an owned survivor before retrying. This is process ownership, not a sandbox or protection against unrelated apps.

Import `geometry_budget.py` for `contains(mesh, points)` and `closest_point(mesh, points)` instead of one large raw trimesh query. Calls retain every point and result in original order, splitting by point count and a worst-case 500,000 triangle-candidate batch. This is an allocation-efficient algorithm, not a RAM cap or subsampling. If one point is too complex, use exact sections or smaller query geometry and re-establish equivalence.

The triangle-ray backend accumulates candidates then materializes arrays for them. Small input grids can therefore demand large temporary allocations. Prefer an equivalent exact section for planar questions. Likewise, do not construct a giant 3D union of a detailed part at hundreds of poses when consumers only need subtraction or layer sections: distribute those operations over the complete poses, preserving shapes, positions, tolerances and loading coverage. Check the result against independent final-mesh and actual-bead evidence.

A timeout is not a completed check. Confirm owned processes stopped before retrying. Reuse hash-bound evidence only for unchanged artifacts. Never replay the known dangerous query to demonstrate prevention. Reviewers using execution tools follow the same serial ownership and allocation-efficient query workflow.

Run the focused tests and a tiny real-library equivalence fixture after relevant changes. The tests cover complete ordered results, no RAM-limit option or pressure gate, cross-TMPDIR exclusion, timeout and child cleanup, all supported cancellation signals, cancellation during launch, and repeated cancellation during cleanup. Do not use the original large allocation as a fixture.
