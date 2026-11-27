"""Click-end finger-rest study. Coordinates are in the R74 assembly frame, millimetres."""
from hashlib import sha256
import json
from pathlib import Path
import sys

import manifold3d as mf

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r74-smooth-through'))
import design74 as prior
import click_end

b = prior.b
HOLDER = prior.HOLDER


def reference_fork():
    # Ethan rests his index finger at the click end, opposite the mouth of the
    # battery slot. Copy the two long curves which land on that rounded edge.
    # The small loop and long bar pointing away from the click are not the target.
    return b.union([prior.r71.r61.curve(prior.fit.smooth_return(x), prior.RADIUS)
                    for x in (14.2, 28.3)])


def level_key_seats(body, occupied):
    # Restore a continuous plane from a section through solid key-seat material.
    # Keep through-holes, the socket insertion path and the rounded outside edges.
    deck = prior.DECK
    added = []
    for sign in (-1, 1):
        x0, x1 = sorted([sign * 10.7, sign * 28.2])
        face = mf.CrossSection.square((x1-x0, 32.0)).translate((x0, -6.15))
        plan = body.slice(deck + .52) ^ face
        repair = plan.extrude(.55).translate((0, 0, deck)) - body
        repair -= occupied
        added.extend(part for part in repair.decompose() if part.volume() > .003)
    # The old rail left a rectangular step toward the rod on each key bank.
    # Plane its floor to the underside. Keep the central housing and wire entry
    # open throughout their real insertion movement, even outside the key seats.
    import audit71
    central_parts = b.union([b.union(route) for route in audit71.op1_routes().values()])
    for sign in (-1, 1):
        x0, x1 = sorted([sign * 7.05, sign * 14.30])
        window = mf.CrossSection.square((x1-x0,17.1)).translate((x0,-6.70))
        plan = body.slice(deck+1.03) ^ window
        fill = plan.extrude(1.07).translate((0,0,deck)) - body - occupied - central_parts
        added.extend(piece for piece in fill.decompose() if piece.volume() > .003)
    return b.union(added)


def clean_export(path, shape):
    for _ in range(3):
        b.save_closed(path, shape)
        reread = b.load(path)
        pieces = sorted(reread.decompose(), key=lambda item: -item.volume())
        if len(pieces) == 1 and reread.status() == mf.Error.NoError:
            return reread
        if sum(abs(part.volume()) for part in pieces[1:]) > .00001:
            raise ValueError('Unexpected detached material during mesh export')
        shape = pieces[0]
    raise ValueError('Carrier export contains more than one solid')


def low_battery_guides(body):
    # The tiny switch pins alone do not set this gap. The fitted solder and wire
    # envelope comes within 0.20 mm of the pack, so keep its protected height.
    # Replace the three full-height spacers by slim upper lips on the two rails.
    x0, x1 = prior.PACK_X
    start, end = prior.r71.PAD_FROM_Y, prior.r71.BED
    top = prior.r71.PAD_Z
    pocket = b.box(x0 - .03, x1 + .30, start-.03, end+.05, top-.02, prior.DECK-.15)
    body = body - pocket
    soft = prior.r71.r61.soft
    lips = [soft(a, c, start+.05, end+.20, top, top+.90, .22)
            for a,c in [(x0-.20,x0+1.15), (x1-1.15,prior.r71.INNER_X[1]+prior.r72.INBOARD-.10)]]
    # End both lips exactly with their rails, keeping the rear seating face flat.
    stock = b.box(x0-2.,x1+2.,start-.2,end,top-.2,top+1.5)
    return body + (b.union(lips) ^ stock)


def build():
    source = prior.OUT / HOLDER
    old = b.load(source)
    old_base = b.load(prior.r71.OUT / HOLDER)
    clear = low_battery_guides(prior.clear_left_underside(old, old_base))
    mirror = reference_fork().mirror((1, 0, 0))
    # Maintain the rear load path where the fork joins the body between the keys.
    support = click_end.rear()
    hardware, spaces = prior.key_models()
    occupied = b.union([b.union(group) for group in spaces.values()])
    patch = level_key_seats(clear, occupied)
    fork = click_end.inner() + click_end.outer()
    guard = fork + support
    # Levelling the imported key seats leaves two isolated flakes in the old
    # floor (0.0096 and 0.0047 mm³). Exclude them from the printable body.
    # A separate guard, rail or other feature must still fail the build.
    shells = sorted((clear + support + fork + patch).decompose(), key=lambda piece: -piece.volume())
    for piece in shells[1:]:
        if piece.volume() > .001:
            _, _, bottom, _, _, top = piece.bounding_box()
            if piece.volume() > .011 or bottom < 7.36 or top > 7.68:
                raise ValueError('Unexpected detached material outside the key-seat repair')
    result = shells[0]
    OUT.mkdir(exist_ok=True)
    path = OUT / HOLDER
    mesh = clean_export(path,result)
    _, passage = prior.battery_path(mesh)
    gaps = {key:round(max((guard ^ pose).volume() for pose in poses),5)
            for key, poses in spaces.items() if key.startswith('key_0')}
    evidence = dict(revision='R75', use='shape preview', physical_fit_verified=False,
                    base_sha256=sha256(source.read_bytes()).hexdigest(),
                    carrier_sha256=sha256(path.read_bytes()).hexdigest(),
                    solid_count=len(mesh.decompose()), valid=mesh.status()==mf.Error.NoError,
                    restored_face_mm3=round(patch.volume(),3),
                    literal_mirror_in_seated_socket_mm3=round((mirror ^ hardware['socket_0']).volume(),3),
                    fitted_socket_overlap_mm3=round((fork ^ hardware['socket_0']).volume(),5),
                    literal_mirror_in_battery_exit_mm3=round((mirror ^ passage).volume(),3),
                    fork_in_battery_exit_mm3=round((fork ^ passage).volume(),5),
                    socket_pose_overlap_mm3=gaps)
    (OUT/'check75.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if not evidence['valid'] or evidence['solid_count']!=1:
        raise ValueError(evidence)
    return evidence


if __name__=='__main__':
    print(build())
