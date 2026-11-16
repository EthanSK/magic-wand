"""Place a native bridge-direction selector under the rear carrier deck."""
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from xml.etree import ElementTree as E
import numpy as np
import manifold3d as mf
from plate45 import MODEL,SETTINGS,tag,mesh_resource,digest

def apply(path):
    frame_path=path.parent/'frame.json'
    info=json.loads(frame_path.read_text())
    with ZipFile(path) as z:files={n:z.read(n) for n in z.namelist()}
    model=E.fromstring(files[MODEL]);settings=E.fromstring(files[SETTINGS])
    resources=model.find('./{*}resources')
    parts=resources.find('./{*}object[@id="2"]/{*}components')
    # Restrict transverse bridges to the underside over the longitudinal
    # saddle. Elsewhere the 90-degree direction fits the outer key bays.
    # 180 means transverse. Zero requests the slicer's automatic direction.
    region=mf.Manifold.cube((18.,16.,1.)).translate((-9.,17.,7.05))
    # Higher roof strokes extend beyond the saddle onto both rear floors.
    # They can run across the short dimension without changing the outer bays.
    region+=mf.Manifold.cube((37.,16.,.53)).translate((-18.5,17.,7.52))
    mesh_resource(resources,407,'Transverse rear saddle bridges',region.transform(np.linalg.inv(info['print_to_assembly'])[:3]))
    E.SubElement(parts,tag('component'),objectid='407')
    modifier=E.SubElement(settings.find("object[@id='2']"),'part',id='407',subtype='modifier_part')
    for k,v in {'name':'Transverse rear saddle bridges','bridge_angle':'180'}.items():
        E.SubElement(modifier,'metadata',key=k,value=v)
    if info['tilt_degrees']==[270.,0.]:
        # The left outside key floor starts at native Z30.6 with a
        # 10.5-mm-wide free hairpin in its inner perimeter. Print the
        # surrounding perimeter first, then span the 0.8-mm short axis.
        local=mf.Manifold.cube((11.9,2.68,3.25)).translate((-.20,11.63,27.85))
        mesh_resource(resources,408,'Standing left key floor perimeter',local)
        E.SubElement(parts,tag('component'),objectid='408')
        patch=E.SubElement(settings.find("object[@id='2']"),'part',id='408',subtype='modifier_part')
        values={'name':'Standing left key floor perimeter','wall_loops':'4',
                'wall_sequence':'outer wall/inner wall','bridge_angle':'90',
                'outer_wall_line_width':'0.34','inner_wall_line_width':'0.34','internal_solid_infill_line_width':'0.34',
                'sparse_infill_density':'100%'}
        for key,value in values.items():E.SubElement(patch,'metadata',key=key,value=value)
        # Native sparse infill under the raised floors leaves the local
        # vertical shell unsupported despite full previous CAD sections.
        lands=mf.Manifold.batch_boolean([
            mf.Manifold.cube((9.5,2.5,2.8)).translate((x,13.65,z))
            for x,z in ((46.3,.21),(46.3,21.1),(4.3,21.1))],mf.OpType.Add)
        for x,y,z,w,h,depth in [(1.8,13.15,.21,3.3,1.65,1.50),(12.8,14.45,.21,3.1,1.9,1.9),
                                 (33.6,14.1,.8,3.5,2.,2.25),(30.5,12.3,5.1,2.3,2.1,2.15),
                                 (11.3,13.9,19.7,3.,2.15,2.05)]:
            lands+=mf.Manifold.cube((w,h,depth)).translate((x,y,z))
        mesh_resource(resources,409,'Solid backing under raised key floors',lands)
        E.SubElement(parts,tag('component'),objectid='409')
        patch=E.SubElement(settings.find("object[@id='2']"),'part',id='409',subtype='modifier_part')
        for key,value in {'name':'Solid backing under raised key floors','sparse_infill_density':'100%',
                          'wall_loops':'4','internal_solid_infill_line_width':'0.34'}.items():
            E.SubElement(patch,'metadata',key=key,value=value)
    files[MODEL]=E.tostring(model,encoding='utf-8',xml_declaration=True)
    files[SETTINGS]=E.tostring(settings,encoding='utf-8',xml_declaration=True)
    with ZipFile(path,'w',ZIP_DEFLATED) as z:
        for n,d in files.items():z.writestr(n,d)
    info['saddle_bridge_angle_deg']=180;info['layout_sha256']=digest(path)
    frame_path.write_text(json.dumps(info,indent=2)+'\n')
if __name__=='__main__':
    import sys
    apply(Path(sys.argv[1]))
