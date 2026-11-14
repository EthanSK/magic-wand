"""Prepare a separate R39 plate with the established A1 mini PETG recipe.

No printer connection. Slice and audit this plate before calling it print-ready.
"""
from pathlib import Path
import argparse
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET
import json
import holder39 as design
import plate38 as previous
HERE=Path(__file__).resolve().parent
command_audit=previous.command_audit
support_boxes=previous.support_boxes

def configure_motion(target):
    plate=previous.plate
    with ZipFile(target) as source:
        files={n:source.read(n) for n in source.namelist()}
    settings=ET.fromstring(files[plate.MODEL_SETTINGS])
    for obj in settings.findall('object'):
        name=obj.find("metadata[@key='name']").get('value')
        if name in ('Key_Carrier','Grove_Touch_Bracket'):
            values={'outer_wall_speed':'40','inner_wall_speed':'65','outer_wall_acceleration':'1000','inner_wall_acceleration':'1500','top_surface_speed':'30'}
            if name=='Grove_Touch_Bracket': values.update(sparse_infill_density='100%',wall_loops='4')
            for key,value in values.items():
                item=obj.find(f"metadata[@key='{key}']")
                if item is None:item=ET.SubElement(obj,'metadata',key=key)
                item.set('value',value)
    config=json.loads(files['Metadata/project_settings.config'])
    config['reduce_crossing_wall']='1'
    files['Metadata/project_settings.config']=json.dumps(config).encode()
    files[plate.MODEL_SETTINGS]=ET.tostring(settings,encoding='utf-8',xml_declaration=True)
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for name,content in files.items():archive.writestr(name,content)


def make(output):
    output.mkdir(parents=True,exist_ok=True)
    assert not any(output.iterdir()), 'Use a fresh preparation directory'
    plate=previous.plate
    selected={n for g in plate.read_json(HERE/plate.BOM)['groups'].values() for n in g['parts']}
    plate.BRACKET=design.previous.BRACKET
    plate.CLIPS=()
    plate.LOCAL_PADS=(plate.KEY,plate.BRACKET)
    plate.ORIGINS={n:v for n,v in previous.pads.ORIGINS.items() if n in selected}
    plate.BRIM_WIDTH=6
    plate.stage_parts=previous.stage_parts
    plate.configure_layout=previous.configure_layout
    plate.build(HERE,output,plate.FLASHFORGE_PROFILE,False,True)
    target=output/'R39-Complete-A1-mini-PETG-layout.3mf'
    configure_motion(target)
    report_path=output/'print-checks.json'
    report=plate.read_json(report_path)
    report.update(layout_sha256=plate.digest(target),small_part_recipe='40 mm/s outer, 65 mm/s inner, 1000/1500 mm/s2; bracket 4 walls and solid infill',driver_sha256=plate.digest(Path(__file__)),recipe_source_sha256=plate.digest(previous.BASE),physical_success_verified=False)
    with ZipFile(target) as z:config=json.loads(z.read('Metadata/project_settings.config'))
    report['effective_filament_settings']={k:config[k] for k in report['effective_filament_settings']}
    report_path.write_text(previous.json.dumps(report,indent=2)+'\n')
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    print(make(p.parse_args().output.resolve()))
