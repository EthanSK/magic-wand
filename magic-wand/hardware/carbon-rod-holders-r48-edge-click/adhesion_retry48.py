"""Prepare the R48 whole-plate retry with wider removable bracket pads."""

import argparse
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import manifold3d as mf
import numpy as np


BRACKET = "DFRobot_Hole_Bracket"
SHIFT_XY = (7, 23)
TITLE = "Magic Wand R48 wide-base retry - A1 mini PETG"
MODEL = "3D/3dmodel.model"
SETTINGS = "Metadata/model_settings.config"


def update_fields(element, fields):
    for key, value in fields.items():
        entry = element.find(f"metadata[@key='{key}']")
        if entry is None:
            entry = ET.SubElement(element, "metadata", key=key)
        entry.set("value", value)


def mesh_points(mesh):
    return [[float(vertex.get(axis)) for axis in "xyz"]
            for vertex in mesh.find("{*}vertices")]


def wide_pads(original, bracket_body):
    mesh = original.find("{*}mesh")
    points = np.array(mesh_points(mesh), dtype=np.float32)
    faces = np.array([[int(t.get(axis)) for axis in ("v1", "v2", "v3")]
                      for t in mesh.find("{*}triangles")], dtype=np.uint32)
    old = mf.Manifold(mf.Mesh(points, faces))
    assert old.status() == mf.Error.NoError and len(old.decompose()) == 2
    # Each pad continues away from the centre slot and overlaps its original
    # foot. The original tear-off ties and their contact with the part stay.
    left = [(-33, -12), (-29, -16), (-5, -16), (-1.3, -12),
            (-1.3, 25), (-5, 29), (-29, 29), (-33, 25)]
    right = [(21.2 - x, y) for x, y in reversed(left)]
    part_x = [vertex[0] for vertex in mesh_points(bracket_body.find("{*}mesh"))]
    assert min(part_x) - max(x for x, _ in left) > .5
    assert min(x for x, _ in right) - max(part_x) > .5
    extensions = [mf.CrossSection([outline]).extrude(.4) for outline in (left, right)]
    pads = old + extensions[0] + extensions[1]
    assert pads.status() == mf.Error.NoError and len(pads.decompose()) == 2
    assert (old - pads).volume() < .00001
    assert pads.volume() > 1000
    widened = pads.to_mesh()
    # Keep the enclosing 3MF namespace and every unrelated mesh unchanged.
    body = ET.Element("mesh")
    vertices = ET.SubElement(body, "vertices")
    for vertex in widened.vert_properties[:, :3]:
        ET.SubElement(vertices, "vertex", **{axis: f"{coord:.9g}"
                                           for axis, coord in zip("xyz", vertex)})
    triangles = ET.SubElement(body, "triangles")
    for face in widened.tri_verts:
        ET.SubElement(triangles, "triangle", **{axis: str(index)
                                               for axis, index in zip(("v1", "v2", "v3"), face)})
    return ET.tostring(body, encoding="utf-8")


def make_layout(original, target):
    with ZipFile(original) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    settings = ET.fromstring(files[SETTINGS])
    (bracket,) = [
        obj for obj in settings.findall("object")
        if obj.find("metadata[@key='name']").get("value") == BRACKET
    ]
    assert bracket.find("metadata[@key='brim_type']").get("value") == "no_brim"
    (pad,) = [part for part in bracket.findall("part") if "tear-off pads" in
              part.find("metadata[@key='name']").get("value")]
    update_fields(settings.find("plate"), {"plater_name": TITLE})

    model = ET.fromstring(files[MODEL])
    pad_id = pad.get("id")
    pad_object = model.find(f"{{*}}resources/{{*}}object[@id='{pad_id}']")
    object_id = bracket.get("id")
    components = model.find(f"{{*}}resources/{{*}}object[@id='{object_id}']/{{*}}components")
    normal_ids = {part.get("id") for part in bracket.findall("part")
                  if part.get("subtype") == "normal_part"} - {pad_id}
    (body_id,) = normal_ids
    assert all("transform" not in node.attrib for node in components
               if node.get("objectid") in {body_id, pad_id})
    bracket_body = model.find(f"{{*}}resources/{{*}}object[@id='{body_id}']")
    match = rb'(<object id="' + pad_id.encode() + rb'"[^>]*>)<mesh>.*?</mesh>(</object>)'
    replacement = wide_pads(pad_object, bracket_body)
    files[MODEL], count = re.subn(match, lambda m: m[1] + replacement + m[2], files[MODEL])
    assert count == 1
    instance = model.find(f"{{*}}build/{{*}}item[@objectid='{object_id}']")
    transform = instance.get("transform").split()
    assert transform[9:] == ["109", "120", "0"]
    # Move the bracket into the open rear half so the pads clear the XIAO
    # holder and key-carrier props without shifting any other object.
    for index, shift in enumerate(SHIFT_XY, start=9):
        transform[index] = str(int(transform[index]) + shift)
    # Preserve Bambu's default namespace and original mesh XML byte-for-byte.
    old_item = (
        f'<item objectid="{object_id}" transform="{instance.get("transform")}" printable="1" />'
    ).encode()
    new_item = old_item.replace(instance.get("transform").encode(), " ".join(transform).encode())
    assert files[MODEL].count(old_item) == 1
    files[MODEL] = files[MODEL].replace(old_item, new_item)
    files[SETTINGS] = ET.tostring(settings, encoding="utf-8", xml_declaration=True)
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    make_layout(args.original, args.output)
