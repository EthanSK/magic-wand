"""Build the R45 key-carrier-only candidate from the archived R44 native layout."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from xml.etree import ElementTree as E
import numpy as np
import manifold3d as mf
import trimesh
from holder45 import HERE,R44,underside_cradle

MODEL='3D/3dmodel.model'
SETTINGS='Metadata/model_settings.config'
PROJECT='Metadata/project_settings.config'
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
E.register_namespace('',NS)
def tag(name):return '{'+NS+'}'+name
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mesh_resource(resources,number,name,solid):
    resource=E.SubElement(resources,tag('object'),id=str(number),type='model',name=name)
    mesh=E.SubElement(resource,tag('mesh'));vs=E.SubElement(mesh,tag('vertices'));ts=E.SubElement(mesh,tag('triangles'))
    raw=solid.to_mesh()
    for x,y,z in raw.vert_properties[:,:3]:
        E.SubElement(vs,tag('vertex'),x=f'{x:.12g}',y=f'{y:.12g}',z=f'{z:.12g}')
    for a,b,c in raw.tri_verts:
        E.SubElement(ts,tag('triangle'),v1=str(a),v2=str(b),v3=str(c))

def layout(out, tilt_x=270., tilt_y=0., *, rear_drawer=None, cradle_only=False, standing_comb=None):
    out.mkdir(parents=True,exist_ok=True)
    source=R44/'exports/key-holder-only/R44-Key-Holder-Only-layout.3mf'
    with ZipFile(source) as z:files={n:z.read(n) for n in z.namelist()}
    model=E.fromstring(files[MODEL]);settings=E.fromstring(files[SETTINGS]);obj=settings.find('object')
    resources=model.find('./{*}resources');parts=resources.find('./{*}object[@id="2"]/{*}components')
    removed=set()
    for part in list(obj.findall('part')):
        label=part.find("metadata[@key='name']").get('value','')
        if part.get('subtype') in ('support_enforcer','support_blocker') or 'tear-off pads' in label:
            removed.add(part.get('id'));obj.remove(part)
    for ref in list(parts):
        if ref.get('objectid') in removed:parts.remove(ref)
    for r in list(resources):
        if r.get('id') in removed:resources.remove(r)
    old=np.array(json.loads((R44/'exports/manifest.json').read_text())['parts']['Key_Carrier']['print_to_assembly'])
    # Almost-flat keys-up orientation retains the bought-part geometry;
    # the two explicitly removable helpers support its concealed undersides.
    rot=trimesh.transformations.euler_matrix(np.deg2rad(tilt_x),np.deg2rad(tilt_y),0)[:3,:3]
    vertices=lambda r:r.findall('./{*}mesh/{*}vertices/{*}vertex')
    def points(vv):return np.array([[float(v.get(k)) for k in 'xyz'] for v in vv])@old[:3,:3].T@rot.T+rot@old[:3,3]
    body=resources.find('./{*}object[@id="1"]')
    v=points(vertices(body));low=v.min(0)
    frame=np.eye(4);frame[:3,:3]=rot.T;frame[:3,3]=rot.T@low
    for r in resources:
        vv=vertices(r)
        if vv:
            for vert,point in zip(vv,points(vv)-low):
                for k,val in zip('xyz',point):vert.set(k,f'{val:.9g}')
    faces=np.array([[int(t.get(k)) for k in ('v1','v2','v3')] for t in body.findall('./{*}mesh/{*}triangles/{*}triangle')],dtype=np.uint32)
    solid=mf.Manifold(mf.Mesh(np.asarray(v-low,dtype=np.float32),faces))
    assert solid.status()==mf.Error.NoError and solid.volume()>1000
    # Compose the local inter-band saddle relief with the original carrier.
    from roof45 import prepare
    assembly=solid.transform(frame[:3])
    standing=(abs(tilt_x%360.-270.)<1e-8 and abs(tilt_y%360.)<1e-8)
    if standing_comb is None:standing_comb=standing and not cradle_only
    if rear_drawer is None:rear_drawer=standing_comb and not cradle_only
    diamond=abs(tilt_x%360.-270.)<1.e-8 and abs(tilt_y%360.-45.)<1.e-8
    if diamond:
        if not cradle_only:raise ValueError('The diagonal standing trial uses the conventional cradle and tabs.')
        repair_report=dict(removed_mm3=0.,added_mm3=0.,feature='Intact R44 carrier; 270-degree standing pitch followed by 45-degree roll about print Y')
    elif (cradle_only or standing_comb) and standing:
        from standing45 import prepare as standing_repair
        repaired,repair_report=standing_repair(solid,frame,out)
        if standing_comb:
            from standing_web45 import prepare as standing_web
            from standing_board45 import prepare as board_relief
            repaired,web_report=standing_web(repaired,frame,out)
            repaired=board_relief(repaired,frame,out).simplify(.00001)
            repair_report['shared_left_guard_buttress_receipt']='standing-web.json'
            repair_report['op1_lower_ledge_receipt']='standing-board-relief.json'
        assembly=repaired.transform(frame[:3])
    else:
        assembly,repair_report=prepare(assembly)
    solid=assembly.transform(np.linalg.inv(frame)[:3])
    resources.remove(body);mesh_resource(resources,1,"Key_Carrier",solid)
    (out/"backplate-repair.json").write_text(json.dumps(repair_report,indent=2)+"\n")
    # The previous flat slice left an unfilled corner in the R2 guard root.
    # Cover the whole measured joint with a local fine-width solid selector.
    # Neighbouring socket and finger-rest dimensions are unchanged.
    root=mf.Manifold.cube((4.0,3.5,3.2),center=True).translate((22.2,14.35,8.5))
    from holder45 import inherited
    rest=inherited.d.finger_rest_interfaces()['R44 R middle branch-to-outer guard bond']
    bounds=rest.bounding_box()
    rest_selector=mf.Manifold.cube(tuple(bounds[i+3]-bounds[i]+.6 for i in range(3))).translate(tuple(bounds[i]-.3 for i in range(3)))
    for number,label,region in [(405,'Solid R2 guard root',root),
                                (406,'Solid middle finger-rest joint',rest_selector)]:
        mesh_resource(resources,number,label,region.transform(np.linalg.inv(frame)[:3]))
        E.SubElement(parts,tag('component'),objectid=str(number))
        modifier=E.SubElement(obj,'part',id=str(number),subtype='modifier_part')
        for key,val in {'name':label,'sparse_infill_density':'100%','wall_loops':'4',
                        'outer_wall_line_width':'0.34','inner_wall_line_width':'0.34',
                        'internal_solid_infill_line_width':'0.34'}.items():
            E.SubElement(modifier,'metadata',key=key,value=val)
    print('Constructing pull-off ribs',flush=True)
    ribs,tabs=underside_cradle(solid,frame)
    if (rear_drawer and cradle_only) or (standing_comb and (cradle_only or not standing)):
        raise ValueError('Choose either the cradle-only or rear-drawer arrangement')
    shelf=rear=mf.Manifold()
    if not cradle_only:
        from shelf45 import make as make_shelf,clear_cradle
        if standing_comb:
            from standing_comb45 import make as make_guard_comb
            shelf,shelf_report=make_guard_comb(solid,tabs,ribs)
            from comb_pieces45 import flare,record as record_front_pieces
            shelf,tabs,shelf_report['prop_foot_flare']=flare(shelf,solid,tabs,ribs)
            shelf_report['volume_mm3']=shelf.volume()
            shelf_report.pop('required_separate_pieces',None)
            record_front_pieces(out,shelf,shelf_report)
        else:shelf,shelf_report=make_shelf(solid,tabs)
        rear=mf.Manifold()
        if rear_drawer:
            if standing_comb:
                from standing_aperture45 import make as make_aperture_prop
                rear,rear_report=make_aperture_prop(solid,tabs,ribs,shelf)
            else:rear,rear_report=make_shelf(solid,tabs+shelf,rear=True)
            (out/'rear-shelf-cad.json').write_text(json.dumps(rear_report,indent=2)+'\n')
            mesh_resource(resources,412,'Rear_pull_shelf',rear)
            E.SubElement(parts,tag('component'),objectid='412')
            rear_part=E.SubElement(obj,'part',id='412',subtype='normal_part')
            E.SubElement(rear_part,'metadata',key='name',value='Rear_pull_shelf')
        if not standing_comb:ribs=clear_cradle(ribs,shelf+rear)
        if not rear_drawer and not standing_comb:
            from deck_support45 import make as deck_lands
            lands,land_report=deck_lands(solid,tabs,shelf)
            ribs+=lands
            (out/'deck-lands.json').write_text(json.dumps(land_report,indent=2)+'\n')
        print("SIDE SHELF",shelf_report,flush=True)
        (out/'shelf-cad.json').write_text(json.dumps(shelf_report,indent=2)+'\n')
        mesh_resource(resources,410,'Front_pull_shelf',shelf)
        E.SubElement(parts,tag('component'),objectid='410')
        sp=E.SubElement(obj,'part',id='410',subtype='normal_part')
        E.SubElement(sp,'metadata',key='name',value='Front_pull_shelf')
    assert ribs.status()==mf.Error.NoError and ribs.volume()>100
    from geometry45 import scan
    starts=scan(solid,ribs+shelf+rear,frame)
    (out/'cad-starts.json').write_text(json.dumps(starts,indent=2)+'\n')
    print('CAD unsupported starts:',[(p['layer_top'],p['assembly_center']) for p in starts],flush=True)
    mesh_resource(resources,400,'Removable external cradle',ribs)
    mesh_resource(resources,402,'Release_tabs',tabs)
    E.SubElement(parts,tag('component'),objectid='402')
    tp=E.SubElement(obj,'part',id='402',subtype='normal_part')
    E.SubElement(tp,'metadata',key='name',value='Release_tabs')
    E.SubElement(parts,tag('component'),objectid='400')
    pm=E.SubElement(obj,'part',id='400',subtype='normal_part')
    E.SubElement(pm,'metadata',key='name',value='REMOVE - external pull-off ribs')
    for name,shape in [('R45-Key-Carrier',solid),('R45-Key-Carrier-assembly',assembly),('R45-release-tabs',tabs)]:
        raw=shape.to_mesh()
        trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts,process=False).export(out/(name+'.stl'))
    if not cradle_only:
        raw=shelf.to_mesh()
        trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts,process=False).export(out/'R45-front-pull-shelf.stl')
    if rear_drawer:
        raw=rear.to_mesh()
        trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts,process=False).export(out/'R45-rear-pull-shelf.stl')
    from shelf45 import bind_report
    if not cradle_only:bind_report(out)
    if rear_drawer:bind_report(out,rear=True)
    raw=ribs.to_mesh()
    trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts,process=False).export(out/'R45-external-cradle.stl')
    for m in obj.findall('metadata'):
        if m.get('key')=='enable_support':m.set('value','0')
        if m.get('key')=='support_type':m.set('value','normal(manual)')
        if m.get('key')=='bridge_no_support':m.set('value','1')
    model.find('./{*}build/{*}item').set('transform','1 0 0 0 1 0 0 0 1 50 70 0')
    settings.find("plate/metadata[@key='plater_name']").set('value','R45 key carrier - external pull-off cradle')
    files[MODEL]=E.tostring(model,encoding='utf-8',xml_declaration=True);files[SETTINGS]=E.tostring(settings,encoding='utf-8',xml_declaration=True)
    files['Metadata/layer_config_ranges.xml']=b'<?xml version="1.0" encoding="utf-8"?><objects />'
    target=out/'R45-Key-Carrier-layout.3mf'
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr(name,data)
    (out/'frame.json').write_text(json.dumps(dict(print_to_assembly=frame.tolist(),bed_translation=[50,70,0],cradle_volume_mm3=ribs.volume(),print_height_mm=solid.bounding_box()[5],helper_configuration=('standing finger-side comb and switch aperture prop' if standing_comb and rear_drawer else 'standing finger-side comb' if standing_comb else 'cradle only' if cradle_only else 'front and rear shelves' if rear_drawer else 'front shelf'),tilt_degrees=[tilt_x,tilt_y],source_sha256=digest(source),layout_sha256=digest(target)),indent=2)+'\n')
    from owner45 import split_owner
    split_owner(target)
    from process45 import bridge_angle
    bridge_angle(target,target,90,True)
    from saddle_bridge45 import apply as apply_saddle_direction
    apply_saddle_direction(target)
    record=json.loads((out/'frame.json').read_text());record['layout_sha256']=digest(target)
    record['bridge_angle_deg']=90;record['carrier_infill_first']=True
    (out/'frame.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Prepared',target.name,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--tilt',type=float,nargs=2,default=(270.,0.));p.add_argument('--rear-drawer',action=argparse.BooleanOptionalAction,default=None);p.add_argument('--cradle-only',action='store_true');p.add_argument('--standing-comb',action=argparse.BooleanOptionalAction,default=None);a=p.parse_args();layout(a.output,*a.tilt,rear_drawer=a.rear_drawer,cradle_only=a.cradle_only,standing_comb=a.standing_comb)
