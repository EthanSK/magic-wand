"""Check that the procedural R45/R46 sources reproduce R46's printed carrier.

Usage (through geometry_budget.py): check46.py OUT.json
Runs at R46's own parameters in its own process; it must not import
holder47, which re-sets the shared inherited modules.

build47.py builds R47 by running R45's standing generators and R46's brace
stations on the R47 body. Here the same chain runs on R44's procedural
carrier at R46's parameters, including R45's old OP1-ledge relief
(standing_board45), which R45 applied and R47 does not. Its result is
compared with R46's published carrier at every standing print layer
(layers47.layer_differences).
"""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import manifold3d as mf
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
R46 = HERE.parent / 'carbon-rod-holders-r46-middle-to-edge'
sys.dont_write_bytecode = True
sys.path.insert(0, str(R46))
sys.path.insert(0, str(HERE))
import holder46 as h46  # noqa: E402
import layers47  # noqa: E402
import standing45  # noqa: E402
import standing_board45  # noqa: E402
import standing_web45  # noqa: E402

PUBLISHED = R46 / 'exports/key-holder-only/R46-Key-Carrier-assembly.stl'


def load(path):
    t = trimesh.load_mesh(path)
    return mf.Manifold(mf.Mesh64(t.vertices, np.asarray(t.faces, np.uint64)))


def main(out):
    frame = layers47.print_frame()
    inverse = np.linalg.inv(frame)[:3]
    r44 = h46.d.geometry()[0]
    original = h46.mesh
    with tempfile.TemporaryDirectory(dir=Path(out).parent) as tmp:
        work = Path(tmp)
        # Float64 input, as build47 gives it (R45 itself started from a
        # float32 layout body; see the floor-band note below).
        body, chamfer = standing45.prepare(r44.transform(inverse), frame, work)
        body, web = standing_web45.prepare(body, frame, work)
        body = standing_board45.prepare(body, frame, work).simplify(.00001)
        r45 = body.transform(frame[:3])
        r45_name = 'R45-Key-Carrier-assembly.stl'
        with patch.object(h46, 'mesh', lambda path: r45 if Path(path).name == r45_name else original(path)):
            full, braces = h46.design(work / 'r46')
    published = load(PUBLISHED)
    layers = layers47.layer_differences(published, full)
    result = {
        'chain': 'R44 procedural at R46 -> standing45 -> standing_web45 -> standing_board45 -> holder46 braces',
        'compared_with': PUBLISHED.name,
        'volumes_mm3': {'reproduced': round(full.volume(), 4), 'published': round(published.volume(), 4)},
        'r45_chamfer_added_mm3': round(chamfer['added_mm3'], 4),
        'r45_lip_relief_removed_mm3': round(chamfer['lower_lip_relief']['original_removed_mm3'], 4),
        'r45_web_added_mm3': round(web['added_mm3'], 4),
        'r46_braces_added_mm3': round(braces['added_mm3'], 4),
        'layers': layers,
        'prints_alike': layers47.prints_alike(layers),
        # R45 started from R44's float32 layout body; its lip relief is cut
        # layer by layer from whatever body it is given, so inside R45's
        # lower-floor band the reproduction may differ in sub-millimetre steps.
        'alike_outside_r45_floor_band': layers['largest_change_outside_r45_floor_band_mm2'] < .01,
        'r45_published_lip_relief_removed_mm3': 75.391,
    }
    Path(out).write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
