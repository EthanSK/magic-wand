# R53 mechanical notes

All dimensions are millimetres in the assembly frame used since R48: the rod runs along Y through X = Z = 0, +Y points to the two-key row and +Z is up. Every number below is a CAD value. None is a measurement of a printed part.

## Switch and board

The [Omron D2FC drawing](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/5389/D2FC_Datasheet_EN.pdf) gives the switch body as 12.8 ± 0.15 long, 5.8 ± 0.15 wide and 6.5 high. The button is 2.9 × 1.2 and sits 5.2 ± 0.2 from the far mounting hole, which is 4.45 from one end of the body. Its free height is at most 7.35 above the base and it operates at 6.9 ± 0.2. Pretravel is 0.3 ± 0.2 and overtravel at least 0.2.

- The three pins are evenly spaced, so the switch also plugs in reversed. The button then sits 3.9 further along the board. The paddle has one crown at each station.
- The 30 × 10 board outline, 1.6 thickness, eyelet pitch, socket barrels and plug are estimated from the kit photographs. Two tapered fingers on 0.88 mm flexible leaves locate the eyelets from the underside. The sliding retainer holds the board down. [OP1 Universal Switch Set](https://endgamegear.com/products/op1-universal-switch-set)
- The pocket is R51's, with 0.45 at each side of the board and 0.65 at each end. The openings for the socket barrels, connector and plug are widened by 0.45 so the parts under the board can move as far as the board can.
- Other switches in the kit may be taller. The sleeve, crowns and stop all refer to the switch itself, so a taller body moves the paddle's rest position. The lid stop is fixed to the holder and assumes the Omron height.

## Paddle

- Flat top at Z 19.3, 1.6 thick, printed top down. The touch board sits where it did in R52.
- Sleeve: 1.2 walls on both long sides and the rear end of the switch body, open at the front where the body reaches the paddle edge. It overlaps the body by 2.9 at rest. Five rounded lands leave 0.35 to the nominal body. Elsewhere the gap is 0.5, with a 0.55 entry bevel at the rim.
- The two contacts have 4.8 mm shoulders and gently curved 3 mm tips. Their modelled heights differ by 0.094 mm to account for the hinge arc. The 0.2 mm slice gives each a contact face wider than 3 mm. The printed movement needs a physical click-and-return test.
- Travel: the lever from hinge to button is 33.1, so 1° moves the button 0.58. The crown reaches the switch case after 0.85 of button travel. The lowest operating point allowed by the drawing needs 0.65, and 0.75 leaves 0.1 in hand. The next contact with any fixed part would come at 1.14.
- Above each crown the paddle skin is 0.4 thick. The touch board lies directly on it and backs the crown.
- Two ribs under the long edges stiffen it. A window clears the Gravity pin tails.

## Hinge

- Axis at Y 29.3, Z 18.3. The axle bar is a 4 mm round with a flat on top at the paddle surface, so it prints lying on the bed.
- Each journal (|X| 7.4 to 9.6) rests in a V seat with a 40° front flank and a 50° rear flank. A V holds a round bar in one place under load and tolerates a bar that prints slightly large or small. The journal centres are 17 apart.
- End float is 0.12 each way, taken by the keel under the middle of the bar against the inner cheek faces.
- The yoke is a rear wall on the print bed with two cheeks. Nothing overhangs by more than 45° in the rear-down print.
- The cap slides in a 45° dovetail. Its flat underside clears both axle journals by 0.20 mm. A 0.4 mm ridge at the back retains the cap. Two reliefs under its rear edge take a fingernail.
- Without the lid the paddle can swing up about 5 mm at the front before the bar's flat meets the cap.

## OP1 lid

- A 1.2 thick fork, 0.15 above the board, covering 1.4 of each long board edge. It slides along the board from the front in two rails. The left rail runs most of the board length and the right rail stops before the right-hand key.
- The rail lips stay outside the board's drop-in opening, so the board still lowers straight in.
- A spring strip on the left edge carries a 0.5 latch bump that drops into a notch in the rail.
- Two towers rise beside the sleeve. Their 45° lips sit above a matching 45° flange on the sleeve. The standard lid lets the button station rise 0.43 from the modelled rest. The optional lid allows about 0.17. A real switch with a typical 7.2 free height rests 0.15 lower, which adds 0.15 to both.
- Sideways, the towers stand 0.32 from the sleeve flange.

## Touch board

- The post bar is the R48 pair of posts on a bar that sits under the paddle. The necks and heads are unchanged, so the existing clips fit. Posts stay 15.5 apart and tolerate 15.0 to 16.0 hole spacing as before.
- The posts leave the board about 0.4 of sideways room in 3.0 holes, as in R48. A strip of thin double-sided tape on the flat paddle top would stop the board shifting under a sliding finger.

## Open questions for the printed trial

1. Does the sleeve slide freely on the real switch, and does the paddle return every time? The 0.35 mm clearance per side is a guess at PETG shrinkage on an inside dimension.
2. How high does the paddle rest? That decides which lid suits, or if the lid stop needs moving.
3. Do the cap and lid latches hold and release by hand?
4. Do the two PCB eyelets seat over the flexible pins with light hand pressure, and can the pre-wired board lift out freely?
5. The yoke adds a 23 mm wide wall at the rear. Check it against the Gravity lead.
6. Free play at the pad when the wand is turned over. There is no spring holding the paddle down, so it can lift by the lid gap.

## Print notes for packaging

- Give each body its own bed-contact base and keep them separate on the tray.
- Paddle: attach a base to the plate edges only. Keep it off the two journal ends.
- Lid: outer outline only. Nothing in the slit beside the spring strip or in the U slot.
- Cap: outer outline only.
- Key holder: the rear wall, its arch and the two nail reliefs sit on the bed. Keep base material out of the arch.
- The post bar has only 35 mm² of bed contact and needs the largest base for its size.
- The four switches retain the R52 spacing. Shaped undersides and a permanent brace under the finger rest let every socket print open. The production slice uses zero support. [Printer path checks](exports/print-mechanisms/layers.json)
