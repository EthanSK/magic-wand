"""Complete R71 key-holder plate: nine pieces. Five are new: the key holder, the paddle,
the two-post bar and the two touch-board clips.

The retainer is R70's file, copied byte for byte into this revision. The hinge pin, the
centre clip and its spare are the unchanged older files. Every piece keeps its R70 bed
position. The two clips are printed top face down: frame and spring arms on the bed, feet last.

Holder base. R70's five fins were full 1.7 mm strips where they met the plate, and three
of them were full width at the holder too. Pulled, they came away hard and left stubs.
In R71 every fin has one neck, 0.02 mm from the holder's face and 0.45 mm long, and is
full width from there to its post on the plate. The neck is the smallest section on the
fin, so that is where it breaks: the fin stays on the plate and at most 0.47 mm of it
stays on the holder. (A second neck at the plate, tried first, was as weak as the one at
the holder; a fin that broke there would have left 1.5 mm on the holder.)

    +y  X -26.45  roof strip over the outer rail and its pad  neck 1.26 mm
    -y  X -27.00  heel under the outer rail                   neck 0.84 mm
    -y  X -12.60  underside of the left key bank              neck 1.26 mm
    -y  X  -7.40  underside of the deck                       neck 1.26 mm
    -y  X  13.00  underside of the right key bank             neck 1.26 mm

The left bank's rear is now the mirror image of the right bank's, so its top no longer
reaches the bed outside the open hinge bay: the fin that stood on it (X -16.4) moves to
its underside (X -12.6), the mirror of the right bank's fin. The two rail fins stand on
the new rail: the roof strip is backed by the outer wall and its pad rib (4.2 mm of plastic),
and the outer lip has a 0.8 mm heel for its first 2.2 mm. The panel and its size are R70's.
 — Claude Fable 5.2"""
from os.path import relpath
from pathlib import Path
import argparse
import sys

import manifold3d as mf

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
if str(HERE.parent / 'carbon-rod-holders-r70-short-holder') not in sys.path:
    sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r70-short-holder'))
import kit70  # noqa: E402

import design71  # noqa: E402
import hinge71  # noqa: E402

hinge70 = hinge71.h70

kit64, printer, p54, panel55 = kit70.kit64, kit70.printer, kit70.p54, kit70.panel55
COMPLETE = kit70.COMPLETE
NEW = {'Key_Carrier': design71.HOLDER, 'Touch_Paddle': hinge71.PADDLE, 'DFR_Post_Bar': hinge71.POST_BAR, 'OP1_Lid_Stop': hinge71.LID,
       'DFR_Clip_Left': hinge71.CLIPS['Left'], 'DFR_Clip_Right': hinge71.CLIPS['Right']}
TITLE = 'R71 key holder with the battery inside its outline, spring clips and nine fittings'

FIN = 1.70                                                 # full fin width (R70)
MAIN, SLIM = 1.26, 0.84                                    # neck widths: three and two 0.42 mm lines
HOLDER_NECK = (0.02, 0.45)                                 # beside the holder: start beyond its face, length (R70: 0.08, 0.60)
PLATE_NECK = (0.03, 0.50)                                  # at the plate, when a tie asks for one: gap to the fin's post, length
RAIL_FIN = 1.80                                            # the two fins on the battery rail (the heel is 2.2 mm long)
CARRIER_TIES = (                                           # no plate_neck: the only weak section is the one beside the holder
    dict(face='+y', at=-26.45, height=RAIL_FIN, neck=MAIN),
    dict(face='-y', at=-27.00, height=RAIL_FIN, neck=SLIM),
    dict(face='-y', at=-12.60, height=kit70.DECK_FIN, neck=MAIN),
    dict(face='-y', at=-7.40, height=kit70.DECK_FIN, neck=MAIN),
    dict(face='-y', at=13.00, height=kit70.DECK_FIN, neck=MAIN),
)
CLIP_PRINT = (180, 0)                                      # the two touch-board clips: turned over, top face on the bed
CLIP_PANEL = dict(size=(12, 13.3), ties=[(0, 1)], clip_mouth=[0, -1])     # tear tab on the rear bar, open lane along the mouth; 1.3 mm longer for the longer clip


def pouch_mouth():
    """Bed-frame box (print X = assembly X, print Y = assembly Z) the panel stays out of:
    the open end of the pouch lane, between its two walls. — Claude Fable 5.2"""
    d = design71
    return [round(d.PACK_X[0] - d.CLEAR, 2), round(d.LIP_TOP, 2), round(d.INNER_X[1], 2), round(d.DECK - .02, 2)]


def carrier_panel(panel):
    """R70's panel with the pouch mouth at its R71 place and the R71 fins."""
    keep = [list(box) for box in panel['keep_clear']]
    mouths = [box for box in keep if abs(box[2] + 9.30) < .01 and box[3] < 8.]
    assert len(mouths) == 1, 'expected one pouch-mouth box in the R70 panel'
    mouths[0][:] = pouch_mouth()
    return dict(panel, fin_thickness=FIN, keep_clear=keep, ties=[dict(tie) for tie in CARRIER_TIES])


def layout(path):
    sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r65-op1-seat'))
    from plate_preview import embed
    printer.write_layout(parts(), Path(path), kit64.kit63.plate.plate60.prior.p58.TOWER, TITLE, panel_builder=panel_builder)
    embed(Path(path))


def parts():
    rows = []
    for row in kit70.parts():
        row = dict(row)
        name = row['name']
        if name in NEW:
            source = OUT / NEW[name]
            row['source'] = source
            if name in kit64.PRINT_POSES:
                row['assembly_to_print'] = printer.pose_for(source, *kit64.PRINT_POSES[name])
            if name == 'DFR_Post_Bar':
                row['assembly_to_print'] = printer.pose_for(source, 0, 0)       # upright, as R70
            if name.startswith('DFR_Clip_'):
                row['assembly_to_print'] = printer.pose_for(source, *CLIP_PRINT)
                row['panel'] = dict(row['panel'], **CLIP_PANEL)
        if name == 'Key_Carrier':
            row['panel'] = carrier_panel(row['panel'])
        row['mesh_reference'] = relpath(row['source'], OUT)
        rows.append(row)
    names = [row['name'] for row in rows]
    if set(names) != COMPLETE or len(names) != len(set(names)):
        raise ValueError(f'Incomplete kit: {names}')
    return rows


def neck_spans(root):
    """(from, to, width) along the fin, measured outward from the holder: the neck beside the
    holder's face and the neck beside the fin's post on the plate. — Claude Fable 5.2"""
    tie, spans = root['tie'], []
    if tie.get('neck'):
        spans.append((root['outer'] + HOLDER_NECK[0], root['outer'] + sum(HOLDER_NECK), tie['neck'], 'holder'))
    if tie.get('plate_neck'):
        spans.append((root['start'] - sum(PLATE_NECK), root['start'] - PLATE_NECK[0], tie['plate_neck'], 'plate'))
    for a0, a1, _, _ in spans:
        assert root['outer'] < a0 < a1 < root['start'], 'a neck must lie inside the moat'
    assert len(spans) < 2 or spans[0][1] < spans[1][0], 'the two necks must not meet'
    return spans


def neck_cuts(body, options):
    """The side notches that neck every fin at both ends. — Claude Fable 5.2"""
    lay = p54.layout54(body, panel55.settings(options))
    cuts = []
    for root in lay['roots']:
        for a0, a1, width, _ in neck_spans(root):
            full = p54._oriented(root, a0, a1, lay['fin'] / 2 + .10)
            core = p54._oriented(root, a0 - 1., a1 + 1., width / 2)
            cuts.append(p54._solid(full - core, -.01, root['height'] + .10))
    return cuts


def panel_builder(body, options):
    panel = printer.panel_builder(body, options)
    if options.get('wire_exit'):
        pose = printer.pose_for(OUT / hinge70.PADDLE, *kit64.PRINT_POSES['Touch_Paddle'])
        clearance = hinge70.wired_lead().transform(pose[:3]).project().offset(.65).extrude(1).translate((0, 0, -.2))
        panel -= clearance - body
    if any(isinstance(tie, dict) and (tie.get('neck') or tie.get('plate_neck')) for tie in options.get('ties', ())):
        removed = mf.Manifold.batch_boolean(neck_cuts(body, options), mf.OpType.Add)
        assert float((removed ^ body).volume()) < 1e-6, 'a neck notch touches the holder'
        panel -= removed
        assert len([s for s in panel.decompose() if abs(s.volume()) > 1e-6]) == 1, 'a necked fin no longer joins the holder'
    return panel


def bed_body(source):
    pose = printer.pose_for(source, *kit64.PRINT_POSES['Key_Carrier'])
    body = printer.load_solid(source).transform(pose[:3])
    return sorted(body.decompose(), key=lambda s: -abs(s.volume()))[0]


def base_report(source, panel):
    """Fin by fin: where it meets the holder, and its section at the holder, in the
    middle and at the plate. Works for the R69 and R70 panels too. — Claude Fable 5.2"""
    body = bed_body(source)
    report = panel55.report55(body, panel)
    fins = []
    for row, tie in zip(report['fins'], panel['ties']):
        full = row['section_mm2']
        at = lambda key: round((tie.get(key) or row['fin_thickness']) * row['fin_height'], 2)
        fins.append(dict(face=row['face'], at_x_mm=tie['at'], meets_holder_at_print_xy_mm=row['cut_at_xy'], height_mm=row['fin_height'],
                         full_section_mm2=full, at_the_holder_mm2=at('neck'), at_the_plate_mm2=at('plate_neck'),
                         rooted_volume_mm3=row['rooted_volume_mm3']))
    total = lambda key: round(sum(f[key] for f in fins), 2)
    return dict(holder_first_layer_mm2=report['holder_first_layer_mm2'], panel_sheet_mm2=report['panel_sheet_mm2'],
                first_layer_pieces=report['first_layer_pieces'], panel_pieces=report['panel_pieces'], fins=fins,
                total_full_section_mm2=total('full_section_mm2'), total_at_the_holder_mm2=total('at_the_holder_mm2'),
                total_at_the_plate_mm2=total('at_the_plate_mm2'),
                weakest_path_mm2=round(sum(min(f['at_the_holder_mm2'], f['at_the_plate_mm2']) for f in fins), 2),
                base_volume_in_hinge_bay_mm3=report['base_volume_in_hinge_bay_mm3'],
                print_height_mm=round(float(body.bounding_box()[5]), 2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path, help='destination .3mf; its layout.frame.json is written beside it')
    layout(parser.parse_args().layout)
