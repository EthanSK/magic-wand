"""Place the restored carrier on the complete R64 fitting plate."""
from pathlib import Path
from os.path import relpath
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r64-under-entry'))
import kit64


def parts():
    rows = kit64.parts()
    carrier = next(row for row in rows if row['name'] == 'Key_Carrier')
    source = OUT / 'Key_Carrier-assembly.stl'
    carrier.update(source=source, assembly_to_print=kit64.kit63.plate.printer.pose_for(
        source, *kit64.PRINT_POSES['Key_Carrier']))
    sled = OUT / 'OP1_Seat_Sled-assembly.stl'
    rows.append(dict(name='OP1_Seat_Sled', source=sled, bed_center=(111, 14.0),
                     assembly_to_print=kit64.kit63.plate.printer.pose_for(sled, 0, -74),
                     panel=dict(front_pad=True)))
    for row in rows:
        row['mesh_reference'] = relpath(row['source'], OUT)
    return rows


def panel_builder(body, options):
    if not options.get('front_pad'):
        return kit64.panel_builder(body, options)
    import design65 as seat
    # The slab itself lies on the bed. Put a small two-layer grip at the closed
    # nose, leaving the opposite end completely open for the wired connector.
    z = seat.FLOOR
    pad = seat.b.ubox(-5.2,3.2,-15.5,-12.35,z,z+.40)
    for x in (-3.6,1.8):
        pad += seat.b.ubox(x-.65,x+.65,-12.60,-11.00,z,z+.20)
    pose = kit64.kit63.plate.printer.pose_for(OUT/seat.SLED_FILE,0,-74)
    panel = body + pad.transform(pose[:3])
    assert len(panel.decompose()) == 1
    return panel


def layout(destination):
    from plate_preview import embed
    kit64.kit63.plate.printer.write_layout(
        parts(), destination, kit64.kit63.plate.plate60.prior.p58.TOWER,
        'R65 key holder and complete hinge fittings', panel_builder=panel_builder)
    embed(destination)


if __name__ == '__main__':
    layout(Path(sys.argv[1]))
