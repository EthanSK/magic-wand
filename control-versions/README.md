# Control versions

Control versions preserve interaction rules independently of physical hardware prototypes.
Do not move a published control-version tag. The matching tag includes the device code,
bridge, receiver and public settings manifest; a private snapshot also preserves the
installed application and local settings.

- **Control V1**: `controls-v1.0.0`, receiver 1.2.44 (49). Original Bottom pointer
  gestures and optional flick scrolling.
- **Control V2**: a plain Bottom hold always scrolls. Start left/right for horizontal
  or up/down for vertical, then U-turn either way to continue. Reverse circling
  to reverse the scrolling direction without releasing. Tap, then hold the second
  press for a native drag; release to drop. A plain hold never selects text.
  Release stops scrolling. Standalone flick and circle triggers stay off. Select either version
  from the receiver menu. Bottom double tap globally returns to centred mouse follow.

The original `prototype-v1.0.0` hardware baseline remains separate and unchanged.
