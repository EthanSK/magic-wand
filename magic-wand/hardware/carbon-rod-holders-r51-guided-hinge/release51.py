"""Package a reviewed three-part native slice and check its actual printer commands."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import build48
from plate38 import command_audit, recipe
from check_lid51 import check as check_lid

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package(archive, layout, report, destination):
    with ZipFile(layout) as source:
        cfg=json.loads(source.read('Metadata/project_settings.config'))
    with ZipFile(archive) as z:
        settings=ET.fromstring(z.read('Metadata/model_settings.config'))
        names={n.find("metadata[@key='name']").get('value') for n in settings.findall('object')}
        functional={'Key_Carrier','DFRobot_Hole_Bracket','Battery_End_Door'}
        assert names == functional, names
        holder = next(obj for obj in settings.findall('object') if obj.find("metadata[@key='name']").get('value') == 'Key_Carrier')
        helper = 'External_peel_support'
        assert any(part.get('subtype') == 'normal_part' and part.find("metadata[@key='name']").get('value') == helper
                   for part in holder.findall('part'))
        assert json.loads(z.read('Metadata/project_settings.config'))['filament_type'] == ['PETG']
        code=z.read('Metadata/plate_1.gcode')
        for name in z.namelist():
            if name.endswith(('.model','.json','.xml','.config','.gcode')):
                assert not re.search(rb'/Users/|/Volumes/|/private/(?:tmp|var)/',z.read(name)),name
    support=json.loads(report.read_text())
    assert support['archive_sha256']==digest(archive)
    assert not support['warning']
    frame = layout.with_suffix('.frame.json')
    assert support['frame_sha256'] == digest(frame)
    frame_data = json.loads(frame.read_text())
    assert frame_data['layout_sha256'] == digest(layout)
    assert frame_data['parts']['Battery_End_Door']['source_sha256'] == digest(HERE/'exports'/'Battery_End_Door-print.stl')
    props = support['parts']['Key_Carrier']['external_props']
    assert props['native_continuous_sequences'] > 0 and props['mixed_model_prop_sequences'] == 0
    assert set(support['parts']) >= {'Key_Carrier','DFRobot_Hole_Bracket'}
    for name in ('Key_Carrier','DFRobot_Hole_Bracket'):
        component=support['parts'][name]
        assert component['source_sha256']==digest(HERE/'exports'/(name+'-assembly.stl'))
        assert not component['completely_unrooted_model_islands'], name
        assert not any(component['protected_support'].values()),name
        bore = component['bearing_space']
        assert bore['conservative_native_radius_mm'] >= bore['hardware_radius_mm'], name
    mechanical=json.loads((HERE/'exports/mechanical-fit.json').read_text())
    assert all(mechanical['gates'].values())
    machine=command_audit(archive,cfg)
    assert machine['passed'] and machine['first_object_nozzle_target_c']==245
    assert machine['first_object_bed_target_c']==60 and machine['ending_heater_targets_c']==[0,0]
    destination.mkdir(exist_ok=True,parents=True)
    check_lid(archive,destination/'combined-lid-paths.json')
    (destination/'machine-check.json').write_text(json.dumps(machine,indent=2)+'\n')
    final=destination/'Magic-Wand-R51-Changed-Parts-print-only.3mf'
    recipe.make_print_only(archive,destination).replace(final)
    with ZipFile(final) as z:
        assert z.testzip() is None and z.read('Metadata/plate_1.gcode')==code
    receipt=destination/'print-only.json'
    record=json.loads(receipt.read_text())
    assert record['sha256']==digest(final)
    record.update(file=final.name, parts=sorted(functional), removable_helpers=[helper],
                  exterior_prop_count=frame_data['parts']['Key_Carrier']['peel_support']['pieces'],
                  support_audit_sha256=digest(report))
    receipt.write_text(json.dumps(record,indent=2)+'\n')
    return final


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('archive','layout','report','destination'):
        p.add_argument(arg,type=Path)
    args=p.parse_args()
    print(package(args.archive,args.layout,args.report,args.destination))
