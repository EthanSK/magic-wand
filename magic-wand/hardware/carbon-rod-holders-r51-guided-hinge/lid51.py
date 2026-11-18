"""Feather-pattern lid for the existing Micron cassette, using its tested sliding rim."""
from pathlib import Path
from unittest.mock import patch
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r48-edge-click'))
import battery48 as old
from battery48 import mf, np, trimesh


def openings():
    # Parallel slanted veins meet a longitudinal spine. The narrowing leaf
    # ends keep the spring, front retaining lips and gripping end solid.
    leaves = []
    for y, length in [(-12.2, 3.55), (-7.9, 4.5), (-3.6, 4.5), (.7, 4.5), (5., 4.5), (9.3, 3.55)]:
        points = [[.68, y], [length + .38, y + 1.55], [length + .38, y + 3.4], [.68, y + 2.5]]
        window = mf.CrossSection([points]).offset(-.29, mf.JoinType.Round).offset(.29, mf.JoinType.Round, 2., 48)
        leaves += [window, window.mirror((1., 0.))]
    return mf.CrossSection.batch_boolean(leaves, mf.OpType.Add)


def generate(out):
    out.mkdir(parents=True, exist_ok=True)
    pattern = openings()
    with patch.object(old, 'petal_windows', lambda: pattern):
        lid = old.panel.__wrapped__()
    original = old.panel()
    body = old.body()
    # Changes are confined to the central sheet. Reuse the R48 rail and
    # spring-motion proofs only if the entire mating geometry is identical.
    difference = (original - lid) + (lid - original)
    safe_zone = old.box(-4.94, 4.94, -12.3, 12.8, 10.87, 11.73)
    outside = (difference - safe_zone).volume()
    assert outside < 1e-5, outside
    assert lid.status() == mf.Error.NoError and len(lid.decompose()) == 1
    assert len(pattern.decompose()) == 12 and len(lid.slice(11.2).offset(-.37).decompose()) == 1
    assert (lid ^ body).volume() < .00001 and (lid ^ old.cell()).volume() < .00001
    assert np.allclose(lid.bounding_box(), original.bounding_box(), atol=.001)
    frame = old.print_frame(old.PANEL, lid)
    source = out / 'Battery_End_Door-assembly.stl'
    old.save(lid, source)
    old.save(lid.transform(np.linalg.inv(frame)[:3]), out / 'Battery_End_Door-print.stl')
    mesh = trimesh.load_mesh(source, process=False)
    mesh.vertices += old.deflect(mesh.vertices)
    mesh.export(out / 'Battery_End_Door-released.stl')
    report = {'opening_count': 12, 'sheet_thickness_mm': .8, 'spine_width_mm': 1.36,
              'cad_volume_old_mm3': original.volume(), 'cad_volume_new_mm3': lid.volume(),
              'material_saved_percent': 100 * (1 - lid.volume() / original.volume()),
              'changed_outside_central_sheet_mm3': outside, 'print_to_assembly': frame.tolist(),
              'assembled_lid_sha256': old.file_sha(source), 'physical_fit_verified': False}
    (out / 'lid-checks.json').write_text(json.dumps(report, indent=2)+'\n')
    print(report)


if __name__ == '__main__':
    generate(HERE / 'exports')
