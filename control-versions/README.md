# Control versions

Control versions preserve interaction rules independently of physical hardware prototypes.
Do not move a published control-version tag. The matching tag includes the device code,
bridge, receiver and public settings manifest; a private snapshot also preserves the
installed application and local settings.

- **Control V1**: `controls-v1.0.0`, receiver 1.2.44 (49). Original Bottom pointer
  gestures and optional flick scrolling.
- **Control V2**: context-sensitive Bottom hold: scroll over a scroll area, or drag elsewhere.
  Short taps and other controls retain their existing behavior. Flick and circle
  recognition are off. Select either version from the receiver menu.

The original `prototype-v1.0.0` hardware baseline remains separate and unchanged.
