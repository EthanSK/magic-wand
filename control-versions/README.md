# Control versions

Control versions preserve interaction rules independently of physical hardware prototypes.
Do not move a published control-version tag. The matching tag includes the device code,
bridge, receiver and public settings manifest; a private snapshot also preserves the
installed application and local settings.

- **Control V1**: `controls-v1.0.0`, receiver 1.2.44 (49). Original Bottom pointer
  gestures and optional flick scrolling.
- **Control V2**: `controls-v2.0.0` preserves the final V2 baseline, receiver 1.2.74 (79). A plain Bottom hold always scrolls. Start left/right for horizontal
  or up/down for vertical, then U-turn either way to continue. Reverse circling
  to reverse the scrolling direction without releasing. Tap, then hold the second
  press for a native drag; release to drop. A plain hold never selects text.
  Release stops scrolling. Standalone flick and circle triggers stay off. Select a version
  from the receiver menu. Bottom double tap globally returns to centred mouse follow.

- **Control V3**: hold Bottom and drag in any direction. The initial stroke sets wheel direction and speed; holding still keeps scrolling. Drag the other way to reverse during the same hold, or start another stroke to change speed. Release stops immediately and returns to mouse follow. Circular page scrolling is disabled. Taps, explicit tap-then-hold dragging, Middle review and Top dictation remain independent. V2 is preserved in `v2-manifest.json` and remains selectable.

The original `prototype-v1.0.0` hardware baseline remains separate and unchanged.
