"""Export the purchased carbon stock as a reference mesh, with its free end at Y=0."""
import json
from pathlib import Path

import manifold3d as mf
import trimesh

HOLDERS = Path(__file__).resolve().parents[1]
TARGET = HOLDERS / 'exports/carbon-stock-tube.stl'


def export():
    hardware = HOLDERS.parent
    stock = json.loads((hardware / 'assembly-blueprint/manifest.json').read_text())['products']['tube']
    diameters = json.loads((hardware / 'carbon-rod-holders-r4/parameters.json').read_text())['rod']
    length = stock['nominal_stock_length_mm']
    outside, inside = diameters['diameter'] / 2, diameters['inside_diameter'] / 2
    tube = mf.Manifold.cylinder(length, outside, outside, 96) - mf.Manifold.cylinder(length, inside, inside, 96)
    mesh = tube.rotate((-90, 0, 0)).to_mesh()
    model = trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts, process=False)
    assert model.is_watertight
    assert abs(model.extents[1] - length) < .001
    model.export(TARGET)


if __name__ == '__main__':
    export()
