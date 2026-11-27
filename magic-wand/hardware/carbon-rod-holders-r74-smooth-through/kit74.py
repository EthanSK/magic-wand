"""Place the new carrier with the eight previously fitted parts on the R73 plate."""
from os.path import relpath
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r73-inset-guard'))
import kit73

HOLDER = kit73.model.HOLDER
base_plate = kit73.previous.previous


def parts():
    rows = kit73.parts()
    for row in rows:
        if row['name'] == 'Key_Carrier':
            row['source'] = OUT / HOLDER
            row['assembly_to_print'] = base_plate.printer.pose_for(
                row['source'], *base_plate.kit64.PRINT_POSES['Key_Carrier'])
        row['mesh_reference'] = relpath(row['source'], OUT)
    return rows


def layout(path):
    from plate_preview import embed
    from native_layout53 import MODEL, SETTINGS, add_modifiers, tag, value
    rows = parts()
    base_plate.printer.write_layout(
        rows, path, base_plate.kit64.kit63.plate.plate60.prior.p58.TOWER,
        'R74 complete key holder', panel_builder=base_plate.panel_builder)
    # At the edge of the filled pocket, Arachne produced an isolated 0.05 mm
    # loop in midair. Use one wider classic perimeter just around this pocket.
    # A plate-wide change also dropped useful bonds at the other switch seats.
    with ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    model = ET.fromstring(files[MODEL])
    config = ET.fromstring(files[SETTINGS])
    owner = next(node for node in config.findall('object')
                 if node.find("metadata[@key='name']").get('value') == 'Key_Carrier')
    resources = model.find(tag('resources'))
    carrier = resources.find(tag('object') + f"[@id='{owner.get('id')}']")
    row = next(row for row in rows if row['name'] == 'Key_Carrier')
    # End before the socket's seating face at Y -3.55. Extending this setting
    # to that face makes the wider wall obstruct the seated socket.
    area = kit73.model.b.box(-27.85, -26.10, -4.60, -4.03, 6.75, 7.92)
    area = area.transform(np.asarray(row['assembly_to_print'])[:3])
    modifier_id = 7459
    assert resources.find(tag('object') + f"[@id='{modifier_id}']") is None
    add_modifiers(resources, carrier, owner, {'Minimum line at the lower-left socket pocket': area},
                  modifier_id, 'modifier_part')
    pocket = owner.find(f"part[@id='{modifier_id}']")
    for key, val in dict(wall_generator='classic', wall_loops='1', outer_wall_line_width='0.48',
                         inner_wall_line_width='0.48', detect_thin_wall='0').items():
        value(pocket, key, val)
    for name, tree in ((MODEL, model), (SETTINGS, config)):
        files[name] = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
    with ZipFile(path, 'w', ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    embed(path)


if __name__ == '__main__':
    layout(Path(sys.argv[1]))
