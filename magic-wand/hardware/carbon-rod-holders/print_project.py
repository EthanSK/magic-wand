#!/usr/bin/env python3
"""Compose the existing Bambu project builder, with front faces on the bed.

Only the two holder meshes are printable. This is an accessory-pair project,
not a full wand project or either handed Shard grip.
"""
from pathlib import Path
import argparse, importlib.util, json, os, subprocess, zipfile
import xml.etree.ElementTree as ET
import trimesh
import cad
HERE=Path(__file__).resolve().parent

def build(out,scratch,do_slice):
    source=HERE.parent/'printed-loop-wand/shard-tube-r2/print_projects.py'
    spec=importlib.util.spec_from_file_location('existing_bambu_builder',source)
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    settings=builder.settings()
    settings.update({'enable_support':'0','support_type':'normal(auto)','support_on_build_plate_only':'1','layer_height':'0.2','wall_loops':'3','brim_type':'outer_only','brim_width':'3'})
    builder.settings=lambda:settings
    manifest=json.loads((out/'manifest.json').read_text())
    parts=[]
    for name,record in manifest['parts'].items():
        mesh=trimesh.load_mesh(out/(name+'-assembly.stl'))
        parts.append(dict(name=name,**record,assembly_vertices=mesh.vertices.tolist(),assembly_faces=mesh.faces.tolist()))
    layout=out/'Holder-pair-layout.3mf'
    if layout.exists():layout.unlink()
    builder.make(list(manifest['parts']),[(85,100),(150,100)],layout,{'parts':parts})
    with zipfile.ZipFile(layout)as z:data={n:z.read(n)for n in z.namelist()}
    cfg=ET.fromstring(data['Metadata/model_settings.config'])
    for metadata in cfg.findall("plate/metadata[@key='plater_name']"):
        metadata.set('value','Carbon rod holder pair - dimensional prototype')
    for obj in cfg.findall('object'):
        meta={m.get('key'):m for m in obj.findall('metadata')};name=meta['name'].get('value')
        meta['enable_support'].set('value','0')
        if name=='Key_Battery_Carrier':ET.SubElement(obj,'metadata',key='brim_type',value='no_brim')
    data['Metadata/model_settings.config']=ET.tostring(cfg)
    with zipfile.ZipFile(layout,'w',zipfile.ZIP_DEFLATED)as z:
        for n,b in data.items():z.writestr(n,b)
    receipt={'project':layout.name,'sha256':cad.sha(layout),'builder_sha256':cad.sha(source),'generator_sha256':cad.sha(Path(__file__)),'physical_print_verified':False,'parts':list(manifest['parts'])}
    if do_slice:
        scratch.mkdir(parents=True,exist_ok=True);(scratch/'tmp').mkdir(exist_ok=True)
        base=source.parent/'print-settings'
        cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--datadir',str(scratch/'bambu-data'),'--debug','2','--load-settings',str(base/'machine.json')+';'+str(base/'process.json'),'--load-filaments',str(base/'filament.json'),'--orient','0','--arrange','0','--slice','0','--export-3mf','Holder-pair-sliced.3mf','--outputdir',str(scratch),str(layout)]
        with (scratch/'slice.log').open('w')as log:
            subprocess.run(cmd,cwd=scratch,stdout=log,stderr=subprocess.STDOUT,check=True,env={**os.environ,'TMPDIR':str(scratch/'tmp')})
        result=json.loads((scratch/'result.json').read_text())
        assert result['return_code']==0,result
        receipt['slice']=result
        receipt['warnings']=[p.get('warning_message','')for p in result.get('sliced_plates',[])if p.get('warning_message')]
        # Keep diagnostics honest even when Bambu reports a bridge warning.
        # The separate extrusion audit decides geometry/clearance evidence;
        # it never substitutes for a physical bridge-quality test.
        target=out/'Holder-pair-sliced.3mf';target.write_bytes((scratch/target.name).read_bytes())
        receipt['sliced_project_sha256']=cad.sha(target)
    (out/'print-checks.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scratch',type=Path,required=True);p.add_argument('--slice',action='store_true');a=p.parse_args();build(HERE/'exports',a.scratch.resolve(),a.slice)
