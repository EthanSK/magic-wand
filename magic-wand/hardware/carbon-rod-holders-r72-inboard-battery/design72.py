"""Build the R72 carrier from the checked R71 carrier. Run this file to export the STL.

The cell moves sideways toward the rod. Its depth, fore-aft stop and the top
of the key banks stay in the R71 frame. All loose kit parts still use R71's
original meshes. Dimensions are mm in the assembly frame. — GPT-6.2 Astra
"""
from hashlib import sha256
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / 'carbon-rod-holders-r71-contained-battery'
sys.path.insert(0, str(PRIOR))
import design71 as prev

OUT = HERE / 'exports'
HOLDER = prev.HOLDER
INBOARD = 8.0
SOURCE_SHA = '2a7e2047f1f960c38f71fbb778b9d4a26c347ba9154d6dfbae47a3253bca8160'
b, r64 = prev.b, prev.r70.r64


def carrier() -> mf.Manifold:
    path = prev.OUT / HOLDER
    if sha256(path.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('R71 carrier differs from the checked source')
    original = b.load(path)
    # Strip the previous rail beneath its deck. The upper surface, including
    # the symmetrical bank tapers, remains the original mesh. — GPT-6.2 Astra
    ox, _ = prev.outer_wall_x()
    lane = b.box(ox - .06, prev.INNER_X[1] + .06, prev.RAIL_FROM_Y - .06,
                 prev.BED + .1, prev.LOW - prev.HEEL[1] - .1, prev.DECK - .001)
    rail = (original ^ lane).translate((INBOARD, 0, 0))
    # The new rail keys into the underside of the deck. Only solid bearing
    # lands of the original rail are extended across the seam. — GPT-6.2 Astra
    lands = (rail ^ b.box(-38, -3, 17, prev.BED + .1, prev.DECK - .05, prev.DECK)).translate((0, 0, .035))
    # One of the switch's three legs enters the leading end of a rail pad.
    # Leave assembly clearance around that leg while preserving the spring.
    switch = r64.fitted_key_hardware()['switch_3']
    for tip in (switch ^ b.box(-33, -5, 16., 23., 0., prev.DECK - .02)).decompose():
        if tip.volume() < .01 or (tip ^ (rail + lands)).volume() < .00001:
            continue
        x0, y0, z0, x1, y1, z1 = tip.bounding_box()
        clearance = b.box(x0-.22, x1+.22, y0-.22, y1+.22, z0-.20, z1+.2)
        rail -= clearance
        lands -= clearance
    old_upper = prev._mirror(prev.r61.run(prev.arm_path(), prev.ARM_R + .08))
    old_root = prev.old_top_arm(.10)
    upper_cut = (old_upper + old_root) ^ b.box(-31, -5, prev.HUB[1] - 1.8, prev.BED, -5, prev.DECK)
    outer = r64.smooth_return(prev.old.LEFT_RAIL_X)
    end = r64.bezier(outer, .50)
    turn = np.array([25.5, -2.65, .85])
    tangent = np.array([27.15, -1.95, .68])
    old_lower = prev._mirror(b.union([
        prev.r61.curve(outer, 1.40),
        prev.r61.curve([prev.r62.CROWN_END, (26.6, 1.5, .75), tangent, turn], 1.31),
        prev.r61.curve([turn, 2*turn-tangent, (20.1, -2.55, 2.55), end], 1.31)]))
    inner = prev._mirror(prev.r61.curve(r64.smooth_return(14.2), 1.35))
    # The left side used a closed return attached to the closely spaced inner
    # pair. Replace the return and its adjacent branch with one wide fork.
    # Protect the original deck and the crown where the two arms join. — GPT-6.2 Astra
    lower_cut = (old_lower - inner) ^ b.box(
        -36, -12, -12, prev.r62.CROWN_END[1] - .10, -5, prev.DECK - .001)
    # This small under-deck tip intruded 0.39 mm³ into the newly positioned pouch.
    # Clear its full approach with a rounded relief, well below the PCB bearing seat.
    relief = prev.r61.soft(-14.1, -10.1, 10.7, 16.4, -.1, prev.PACK_Z[1] + .45, .38)
    crown_bars = prev._mirror(b.union(prev.r61.curve(path, prev.BAR_R) for path in prev.bar_paths()))
    under = (original - lane - upper_cut - lower_cut - relief) + crown_bars
    arm = upper_support()
    fork = fork_support()
    # Tie the original outer roof into the relocated rail with a short transverse rib.
    # Both breakaway tabs now load that rib instead of twisting the thin roof alone.
    backing = prev.r61.soft(-27.6, -19.6, prev.BED-2.5, prev.BED+.4, prev.DECK-1.35, prev.DECK+.02, .40)
    backing ^= b.box(-30., -17., prev.BED-3., prev.BED, 4., prev.DECK)
    return prev.old.one_piece(under + rail + lands + arm + fork + backing, 'R72 carrier', limit=.01)


def upper_support() -> mf.Manifold:
    """Round guard spine in front of the cell and a longitudinal support beside it."""
    x, z = -5.60, 2.4
    root = (x, 20.8, 5.5)
    # Keep a rounded bearing at the pouch's near front corner and blend it
    # directly into the inboard stem. The oblique face continues toward the
    # finger rest without presenting a detached flat crest to the slicer.
    cheek = (-6.08, 10.6, prev.PACK_MID)
    corner = (-6.55, 8.65, prev.PACK_MID)
    bend = (-8.45, 7.64, prev.PACK_MID-.07)
    hub = (-prev.HUB[0], prev.HUB[1], prev.HUB[2])
    support = b.union([
        prev.r61.curve([root, (x,18.,z), (-6.08,12.4,prev.PACK_MID), cheek], prev.ARM_R),
        prev.r61.curve([cheek, (-6.08,9.65,prev.PACK_MID),
                        (-6.27,9.03,prev.PACK_MID), corner], prev.ARM_R),
        prev.r61.curve([corner, (-7.1,7.96,prev.PACK_MID),
                        (-7.77,7.78,prev.PACK_MID), bend], prev.ARM_R),
        prev.r61.curve([bend, (-10.7,7.16,2.1),
                        (-11.9,5.0,1.2), (-14.2,5.0,1.05)], prev.ARM_R),
        prev.r61.curve([(-14.2,5.0,1.05), (-16.4,5.0,.92),
                        (-18.7,7.3,hub[2]), hub], prev.ARM_R)])
    # A short rounded strut grows from the solid deck between the two keys.
    # This gives the arch its second anchor without crossing the swept socket
    # or adding an outer wall beside the pouch.
    root = (-20.9, 10.9, 8.1)
    toe = (-20.6, 8.25, .88)
    fillet = mf.Manifold.sphere(.94, 24)
    brace = mf.Manifold.batch_hull([fillet.translate(point) for point in (root, toe, hub)])
    return support + brace


def fork_support() -> mf.Manifold:
    """The far root curves toward the front to leave the socket its side-loading route."""
    tip = (-22.1, 5.2, .88)
    knee = (-27.2, -4.5, .88)
    return prev.r61.curve([(-28.2, -8.8, 8.12), (-28.2, -8.8, 6.8),
                           (-27.2, -6.1, .88), knee], 1.35) + prev.r61.curve(
        [knee, (-27.2, -1.8, .88), (-24.8, 3.0, .88), tip], 1.35)


def export() -> None:
    OUT.mkdir(exist_ok=True)
    path = OUT / HOLDER
    b.save_closed(path, carrier())
    closed = b.load(path)
    for _ in range(3):
        if closed.status() == mf.Error.NoError and len(closed.decompose()) == 1:
            return
        b.save_closed(path, prev.old.one_piece(closed, 'float32 export residue', limit=.00001))
        closed = b.load(path)
    raise ValueError('Exported R72 carrier must reload as one closed solid')


if __name__ == '__main__':
    export()
