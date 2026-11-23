"""Measure how the real keypad underside supports the broad face of the wrapped cell."""
from pathlib import Path
import json

import numpy as np
from kit63 import OUT, R62
import design62

r61 = design62.r61


def measure(body, pack, deck):
    lo, hi = np.array(pack.bounding_box()).reshape(2, 3)
    assert np.allclose(hi - lo, [11.8, 27, 3.9], atol=.015)
    contacts = 0
    original_underface = []
    depths = []
    step = .5
    for x in np.arange(lo[0]+step/2,hi[0],step):
        for y in np.arange(lo[1]+step/2,hi[1],step):
            upper = hi[2]
            start = (x,y,upper-.10)
            stop = (x,y,upper+18)
            structural = deck.ray_cast(start,stop)
            above = body.ray_cast(start,stop)
            if not structural or not above:
                continue
            gap = structural[0].position[2]-upper
            original_underface.append(gap)
            if abs(above[0].position[2]-upper) <= .08 and gap < .35:
                contacts += 1
            below = body.ray_cast((x,y,lo[2]-15), (x,y,lo[2]+.20))
            if below:
                depths.append(structural[0].position[2]-below[0].position[2])
    assert len(original_underface)>80 and len(depths)>40
    return dict(pack_bounds_mm=[lo.tolist(),hi.tolist()], grid_mm=step,
                median_gap_to_keypad_underface_mm=round(float(np.median(original_underface)),3),
                broad_face_supported_at_keypad_mm2=round(contacts*step**2,2),
                deepest_material_under_pack_from_deck_mm=round(max(depths),3))


def main():
    deck = design62.compact_tail(r61.prior.geometry()[1])
    old = measure(r61.b.load(R62/"exports/Key_Carrier-assembly.stl"), r61.pouch(), deck)
    new = measure(r61.b.load(OUT/"Key_Carrier-assembly.stl"), r61.b.load(OUT/"Battery_Pack-assembly.stl"), deck)
    evidence = dict(previous=old, replacement=new, method="0.5 mm grid over the nominal pack face, in assembly coordinates; bearing measured at the structural underside shared with the original keypad.")
    (OUT/"battery-seat.json").write_text(json.dumps(evidence, indent=2)+"\n")
    print(json.dumps(evidence, indent=2))
    assert old["median_gap_to_keypad_underface_mm"] > 7.5
    assert new["broad_face_supported_at_keypad_mm2"] >= 20
    assert new["deepest_material_under_pack_from_deck_mm"] < old["deepest_material_under_pack_from_deck_mm"] - 2


if __name__ == "__main__":
    main()
