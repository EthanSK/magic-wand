"""Generate and slice the R46 carrier using the established standing R45 plate recipe."""
import argparse
import json
import manifold3d as mf
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile,ZIP_DEFLATED
from xml.etree import ElementTree as ET

from holder46 import BASE, design, mesh
import plate45
import standing_board45

def prepare(out):
    assembly,_=design(out)
    old=standing_board45.prepare
    def finished_body(repaired,frame,directory):
        old(repaired,frame,directory)  # retain the inherited provenance and board-relief receipt
        import numpy as np
        return assembly.transform(np.linalg.inv(frame)[:3])
    with patch.object(standing_board45,'prepare',finished_body):
        plate45.layout(out)
    return add_local_recipes(out)

def add_local_recipes(out):
    project=out/'R45-Key-Carrier-layout.3mf'
    with ZipFile(project) as z:files={n:z.read(n) for n in z.namelist()}
    settings=ET.fromstring(files[plate45.SETTINGS])
    model=ET.fromstring(files[plate45.MODEL])
    resources=model.find('./{*}resources')
    parts=resources.find('./{*}object[@id="2"]/{*}components')
    for number,filename,label in [(460,'R46-L-deck-return-base-bond','Solid left deck landing'),
                                  (461,'R46-R-cross-brace','Solid right middle-to-edge brace')]:
        bounds=mesh(out/(filename+'.stl')).bounding_box()
        region=mf.Manifold.cube(tuple(bounds[i+3]-bounds[i]+1.2 for i in range(3))).translate(tuple(bounds[i]-.6 for i in range(3)))
        plate45.mesh_resource(resources,number,label,region)
        ET.SubElement(parts,plate45.tag('component'),objectid=str(number))
        part=ET.SubElement(settings.find('object'),'part',id=str(number),subtype='modifier_part')
        for key,value in {'name':label,'sparse_infill_density':'100%','wall_loops':'4',
                'inner_wall_line_width':'0.34','outer_wall_line_width':'0.34','internal_solid_infill_line_width':'0.34'}.items():
            ET.SubElement(part,'metadata',key=key,value=value)
    files[plate45.MODEL]=ET.tostring(model,encoding='utf-8',xml_declaration=True)
    settings.find("plate/metadata[@key='plater_name']").set('value','R46 middle-to-edge key carrier')
    files[plate45.SETTINGS]=ET.tostring(settings,encoding='utf-8',xml_declaration=True)
    with ZipFile(project,'w',ZIP_DEFLATED) as z:
        for n,v in files.items():z.writestr(n,v)
    f=out/'frame.json';info=json.loads(f.read_text());info['layout_sha256']=plate45.digest(project)
    info['carrier_base_assembly_sha256']=plate45.digest(BASE/'R45-Key-Carrier-assembly.stl')
    info['added_braces_sha256']=plate45.digest(out/'r46-braces.json')
    f.write_text(json.dumps(info,indent=2)+'\n')
    return project

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path)
    prepare(p.parse_args().output)
