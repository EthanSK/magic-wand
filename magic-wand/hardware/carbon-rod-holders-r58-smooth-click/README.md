# R58 flush key seats, battery tray and smooth click

**Status: approved for one monitored fit trial.** Printed fit, strength, comfort and repeated click operation still need bench testing. R57 is the bench-tested reference for the pin hinge.

R58 keeps the R57 pin hinge: same cheeks, same 3.0 mm pin, same clip. It changes the key holder, the paddle and the OP1 board retainer.

## What changes

| Bench finding or request | R58 | Evidence (file) |
| --- | --- | --- |
| The raised platforms under the four outer keys are no longer wanted | The four key seats are 1.42 mm lower and flush with the centre deck (11.12 mm). All 336 inherited key, socket, tape and loading spaces were re-checked 1.42 mm lower: none is entered. | `carrier.json` |
| The two rows are too far apart | The upper row moves 1.4 mm toward the lower row. The centres are now 19.95 mm apart, with 2.55 mm between the keycap envelopes. | `carrier.json` |
| Battery inside the key holder | A tray under the upper-left key holds the Micron 72217 pouch across the holder. A sprung finger hooks behind its end. The separate rod-mounted battery holder is dropped from this assembly. | `carrier.json` |
| The paddle sometimes jams with the retainer in | The new retainer still holds the OP1 board. Its lower stops limit lift to 0.88 mm at the button and give the paddle about 0.96 mm of clearance around the old tower area. | `mechanical-fit.json` |
| The paddle nudges forward and back on the hinge | The paddle bore is narrowed fore and aft only, from a 3.6 mm round hole to a 3.4 mm slot. Largest fore-aft play 1.19 mm → 0.99 mm with the standard pin, or 0.55 mm with the optional 3.2 mm pin. Sideways play along the pin is unchanged at 0.25 mm each way. | `mechanical-fit.json` |
| The dip between the two contact bumps may catch | One convex bar. It meets the button at the same paddle angle as R57 for either switch direction. Recess between the stations: 0.39 mm → 0.01 mm. | `mechanical-fit.json` |
| The holder base was tough to cut away | Six rim tabs connect the holder to the large base. Each tab narrows from 1.68 to 1.47 mm, and the open area around the hinge is wider. | `plate58.py` |

## Print and reuse

| Print for R58 | Optional prints | Reuse from the R57 print |
| --- | --- | --- |
| Key_Carrier, Touch_Paddle, OP1_Lid_Stop, Socket_Backer_Left, Socket_Backer_Right | Hinge_Pin_Snug is included on the plate | Standard hinge pin, pin clip and spare, post bar, both post clips, tall clips |

The earlier retainer with towers is for the R57 paddle. CAD also places the new paddle and retainers in the R57 holder. The R58 plate and assembly guide use the retainer with a lift stop.

## Key seats

- Everything in the two key banks above Z 6.4 moved down 1.42 mm as one piece, with every print fix made since R45. The holder prints rear face down, so the move is inside each print layer.
- The centre deck, OP1 pocket, rails and hinge cheeks keep their positions. The protective finger rests extend downward below their original positions.
- The socket and loading spaces were cut again at the shifted positions, removing about 29 mm³ from the slab and root columns.
- The upper-left socket has a 0.25 mm local wall relief at its inboard end. It gives the largest modeled socket the clearance lost when the slicer drew a full-width line there.
- Estimated heights: keycap top 21.34 → 19.92 mm; touch surface 20.90 mm. The keycaps were 0.44 mm above the touch surface and are now 0.98 mm below it when both are released. At a full click the touch surface is 20.17 mm beside the bottom row and 20.70 mm beside the top row.
- The lowered socket slide path runs 0.37 mm above the round guard ribs (2.57 against 2.20 mm).
- The root columns under the upper bank stay in place. The shifted banks retain 92% or more of the original between-row web cross-section through at least 0.8 mm of thickness. All 336 modeled switch, socket, tape and loading poses are clear. A tighter spacing calculated against the upper-left loading space starts cutting the nearby rest beam at about 1.45 mm of movement.

## Battery tray

- Pouch 27 × 11.8 × 3.9 mm in a 28.1 × 12.9 × 4.55 mm space, X −37.6 to −9.5, Y 18.75 to 31.65, Z 0.65 to 5.2. Play 1.1 mm along, 1.1 mm across, 0.65 mm in thickness. Nothing squeezes it.
- It slides in from the left over a 1.2 mm shelf, under a roof strip and one roof rib. The sprung finger is cut from the rear wall and its hook reaches 1.2 mm behind the pouch end (calculated bending strain 1.2%).
- **The tray stands 8.85 mm past the holder's left edge and the pouch end 7.05 mm.** The pouch is 27 mm long and the free width between the rod's wire lane and the edge is about 21 mm. Lengthwise it would lie under the finger rest or block two sockets.
- The left end is open and leaves the ordered two-pin Molex 2 mm plug outside the tray. If the leads exit at the inboard end, lay them in through the opening in front of the end wall. The pack has 35 mm leads and a matching 100 mm socket lead. Check exit direction, connector placement and slack on the actual pack.
- Supplier dimensions and wiring are documented with the [100 mAh cell](https://www.micronradiocontrol.co.uk/lipo_1s.html) and [Molex 2 mm leads](https://www.micronradiocontrol.co.uk/conn_molex2mm.html).
- A 20 × 12 × 10 mm hand-access envelope fits outside the tray on the left and below the holder in front of the inboard exit. The plug and socket mate in this free space. The envelope is a clearance check and does not represent a measured connector shell or the path of the real wires.
- The shelf stops at Y 20.6 across the upper-left socket's loading path. That socket loads and unloads with the battery out. No other key path is affected.
- Clear of the rod, the wire lane beside it, the OP1 lead and every fitted switch and socket (0 mm³ each).
- The slopes at the front edge and roof rib print at 45° in the rear-down orientation. The rear wall adds a 30 × 6.5 mm strip to the first layer.
- The sprung finger bends 1.2 mm past the holder's rear face. Anything mounted on the rod directly behind the holder would block it.

## Hinge and lift

- Fore-aft play is along Y, measured by moving the pin and paddle meshes inside their holes. At rest it is 0.04 mm. It opens to the figures above only when the hinge end rides up in its holes.
- The cheek holes are unchanged. Their pointed print roof adds 0.09 mm toward the front (0.34 against 0.25 mm).
- With the plain retainer nothing is designed to stop the paddle lifting. It lifts 18.8° before the touch board meets the hinge cheeks, and the sleeve leaves the switch body at 7.5°.
- The plate's stop retainer limits lift to 0.88 mm at the button. Its stops stand 0.96 mm from the paddle (R53: 0.32 mm). In the three most extreme reachable poses the sleeve flange just touches a stop stem (0.004 mm³). Hold the paddle down while sliding in the retainer over the OP1 board.
- Insert the through pin before fitting the upper keycaps, then slide the separate clip into the pin groove from the middle. The R57 plate had two clips, including the spare.

## Finger rest

- Every guard and rest member under the key banks is extended 0.8 mm downward. Each rounded beam goes from 1.9 mm round to a 1.9 × 2.7 mm rounded section, and its legs and joints deepen with it. Nothing grows upward or sideways, so no socket path narrows.
- At the R57 finger-rest view point [13.2, 3.45, 1.25] and its mirror: area 2.99 → 4.63 mm², section modulus for a finger load 0.69 → 1.60 mm³.
- Along all eight beams, sampled every 0.5 mm, the weakest section gains at least 1.74 times in section modulus.
- The rest plane under the finger is 0.8 mm lower (Z 0.3 → −0.5).
- These are section figures. The break location is unknown and no strength was measured.

## Less material

- Lowering the seats left the old frame's bottom 1.42 mm hanging under them (Z 5.85 to 7.27). The R42-height design had 36 mm³ in that layer; R57 after the move had 1,039 mm³. 930 mm³ is removed. 109 mm³ stays as rounded columns over every member that comes up from below.
- The material directly above the rest and guard members stays in place. The shifted seat regions retain the joint to these members.
- Solid PETG volume at 1.27 g/cm³ estimates 12.09 g for the R57 holder, 3.02 g for its separate R48 battery tray and door, and 12.29 g for the R58 holder with tray. This is about 2.8 g saved across the assembly.
- The print proxy counts candidate bridges and isolated starts together. Use the native sliced-path report for a print decision.

## Lower socket access

- Straight up between the rest beams is mostly blocked: 37 mm² of the left socket's 94 mm² underside is open and 47 mm² of the right, in fragments.
- Each lower socket's own sideways loading path stays clear under the seated socket for a flat tongue 6.25 mm wide and 1.6 mm thick. `Socket_Backer_Left` and `Socket_Backer_Right` are that tongue with a 12 mm grip. Each backs 32 mm² of its socket and clears the holder and every other fitted part along a 26 mm slide.
- Brace the strip close to the socket. The printed strip is 6.25 mm wide and 1.6 mm thick. The 12 mm outer extension lets you slide it in and out. Pressing while holding just the far end can flex or crack the strip. The actual press-in force still needs a bench check.
- The sockets keep their existing orientation and the strips supply the missing support from the side. Press each switch in while holding the strip below the socket, then pull the strip out. Turning a lower socket 180° would point its hole roofs at the bed in the rear-down orientation.

## Assembly guide

Use the pin-hinge view to see the bought OP1 board, lead, switch, loose pin and pin clip. The lower-socket view shows both backing strips. The whole-rod view includes the battery sliding into the key holder and uses the full 500 mm rod.

## Sliced fit-trial plate

[A1 mini PETG print file](exports/print-mechanisms/R58-Smooth-Click-A1-mini-PETG-print-only.3mf) and [independent review](exports/print-mechanisms/review.json).

- Both native slices contain six separate objects and zero slicer-generated support moves. All 52 fit-route records clear. The holder is attached to its own wide pad by six fins, with a measured 23.13 mm² joint across 12 layers. R57 measured 24.79 mm². The hinge bay is open and 3.5 mm from the pad at its nearest point.
- Studio still issues its model-shape support advisory. The deposited-bead checks find zero fully unsupported starts. The reviewed contours either receive no extrusion or belong to a connected footprint backed by the prior layer. The small anchored ledge by the OP1 pocket may leave a surface whisker, and the right-side rim tabs may take a firmer nip. The exact findings are bound to both archive hashes in the review.

## Build order

Fresh process each, through the guarded geometry runner with the Wand CAD environment.

1. `build58.py` writes the paddle, both retainers, the snug pin and `dimensions.json`.
2. `checks58.py` writes `mechanical-fit.json`.
3. `carrier58.py` writes the key holder, the battery reference mesh and `carrier.json`. It needs step 1.
4. `guide58.py` copies the meshes and results into `exports/` and writes `exports/assembly-guide.json`. `--register` adds it to the catalog as `r58`.
5. `plate58.py LAYOUT.3mf`, then the saved headless A1 mini slicer.
6. `verify58.py PLATE_FOLDER` checks the deposited paths.
7. Reopen and re-slice the same editable plate. After independent review of the exact slice, `release58.py PLATE_FOLDER REOPENED_FOLDER` packages the checked instructions.
