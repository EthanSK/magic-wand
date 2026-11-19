"""Build the selected key-carrier and paddle plate and share the accessory layout helpers."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import manifold3d as mf
import numpy as np

from tower52 import add_tower_base
from sockets52 import HERE, PREVIOUS, socket_blocks
from orient51 import digest, load_solid, oriented
from plate51 import MODEL, SETTINGS, PROJECT, resource, value

OLD_PLATE = PREVIOUS/'exports/print/trial.3mf'
SPARES = HERE.parent/'carbon-rod-holders-r48-edge-click/exports/wide-pad-retry/R48-Wide-Pads-layout.3mf'
EXTRAS = {'XIAO_Rod_Holder': (0, 61), 'Battery_Holder': (0, 67),
          'DFR0030_Post_Clip': (0, 0), 'DFR0030_Post_Clip_2': (0, 0),
          'XIAO_Near_Keeper': (0, 0), 'Cable_Clip_12_Wire': (0, 0)}


def tag(name):
    return '{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'+name


def decode(obj):
    raw = obj.find(tag('mesh'))
    v = np.array([[float(n.get(k)) for k in 'xyz'] for n in raw.find(tag('vertices'))], np.float32)
    f = np.array([[int(n.get(k)) for k in ('v1','v2','v3')] for n in raw.find(tag('triangles'))], np.uint32)
    mesh = mf.Mesh(v, f)
    mesh.merge()
    solid = mf.Manifold(mesh)
    assert solid.status() == mf.Error.NoError
    return solid


def shoulder_tab():
    """Print-only convex starter on the fixed OP1 shoulder, in machine coordinates."""
    def wafer(x, y, z):
        return mf.Manifold.cylinder(.32,.55,.55,20).scale((1,2.0,1)).translate((x,y,z))
    return mf.Manifold.batch_hull([wafer(62.57,92.49,28.30),wafer(62.27,92.49,29.48)])


def adhesion_ears(body, rod_xy):
    """Four low external pads follow the bed-contact outline, away from the rod."""
    surface=body.slice(.10)
    verts=np.concatenate(surface.to_polygons())
    disks=[]
    for axis in (0,1):
        for sign in (-1.,1.):
            i=np.argmax(sign*verts[:,axis])
            centre=verts[i].copy()
            centre[axis]+=sign*1.35
            disks.append(mf.CrossSection.circle(4.5,56).translate(centre))
    pads=mf.CrossSection.batch_boolean(disks,mf.OpType.Add)-surface.offset(-.10)
    pads-=mf.CrossSection.circle(5.5,80).translate(rod_xy)
    return pads.extrude(.20)


def release_metadata(info, cfg):
    for row in info['parts'].values():
        owner=cfg.find("object[@id='%s']"%row['owner'])
        row['settings']={n.get('key'):n.get('value') for n in owner.findall('metadata') if n.get('key')!='name'}
    carrier=info['parts']['Key_Carrier']
    carrier['peel_support']=dict(part_id=97,name='External_peel_support',straight_pull_props=8,
        fixed_shoulder_tabs=1,external_bed_ears=4,source='plate52.py / adhesion_ears and shoulder_tab; original eight routes in R51 external-prop-paths.json')


def add_modifiers(resources, compound, owner, shapes, first, kind):
    for idx,(name,shape) in enumerate(shapes.items(), first):
        resource(resources,tag,idx,name,shape)
        ET.SubElement(compound.find(tag('components')),tag('component'),objectid=str(idx))
        value(ET.SubElement(owner,'part',id=str(idx),subtype=kind),'name',name)


def append_extras(resources, model, config, ranges):
    with ZipFile(SPARES) as archive:
        package = ET.fromstring(archive.read(MODEL))
        old = ET.fromstring(archive.read(SETTINGS))
        regions = ET.fromstring(archive.read('Metadata/layer_config_ranges.xml'))
    ids = {o.get('id'):o for o in package.find(tag('resources'))}
    build = model.find(tag('build'))
    plate = config.find('plate')
    actual = []
    for ix,it in enumerate(package.find(tag('build')),1):
        ident = it.get('objectid')
        owner = old.find(f"object[@id='{ident}']")
        name = owner.find("metadata[@key='name']").get('value')
        if name not in EXTRAS:
            continue
        # Keep the thermal settings, exact oriented meshes and native adhesion
        # pads that worked on the R48 retry. Only the bed XY translation changes.
        convert = lambda raw: str(1000+int(raw))
        item = deepcopy(it)
        own = deepcopy(owner)
        native = deepcopy(ids[ident])
        native.set('id',convert(ident))
        own.set('id',convert(ident))
        for child in native.iter(tag('component')):
            raw = child.get('objectid')
            obj = deepcopy(ids[raw])
            obj.set('id',convert(raw))
            resources.append(obj)
            child.set('objectid',convert(raw))
        for part in own.findall('part'):
            part.set('id',convert(part.get('id')))
        resources.append(native)
        config.insert(list(config).index(plate),own)
        item.set('objectid',convert(ident))
        tf = item.get('transform').split()
        dx,dy = EXTRAS[name]
        tf[9:11] = [str(float(tf[9])+dx),str(float(tf[10])+dy)]
        item.set('transform',' '.join(tf))
        build.append(item)
        idx = len(build)
        for region in regions.findall(f"object[@id='{ix}']"):
            copy = deepcopy(region)
            copy.set('id',str(idx))
            ranges.append(copy)
        instance = ET.SubElement(plate,'model_instance')
        for key,val in [('object_id',convert(ident)),('instance_id',0),('identify_id',convert(ident))]:
            value(instance,key,val)
        actual.append(name)
    assert set(actual) == set(EXTRAS)


def compose(output, models):
    extra_blocks={}
    with ZipFile(OLD_PLATE) as archive:
        files = {k:archive.read(k) for k in archive.namelist()}
    m = ET.fromstring(files[MODEL])
    ET.register_namespace('',m.tag[1:].split('}')[0])
    cfg = ET.fromstring(files[SETTINGS])
    ranges = ET.fromstring(files['Metadata/layer_config_ranges.xml'])
    res = m.find(tag('resources'))
    info = json.loads(OLD_PLATE.with_suffix('.frame.json').read_text())
    for name in ('Key_Carrier', 'DFRobot_Hole_Bracket'):
        frame = info['parts'][name]
        ident = str(frame['owner'])
        owner = cfg.find(f"object[@id='{ident}']")
        native = res.find(tag('object')+f"[@id='{ident}']")
        item = m.find(tag('build')+'/'+tag('item')+f"[@objectid='{ident}']")
        tr = np.asarray([float(x) for x in item.get('transform').split()[-3:]])
        placement = np.array(frame['assembly_to_machine'])
        placement[:3,3] -= tr
        source = models/(name+'-assembly.stl')
        source_body = load_solid(source)
        if name=='Key_Carrier':
            import build52
            from clearance51 import patches
            patches()
            extra_blocks={**(extra_blocks or {}),name:{'OP1 retaining arm lift and board entry':build52.support_keepouts(source_body)}}
        body = source_body.transform(placement[:3])
        assert abs(body.bounding_box()[2]) < .03,(name,body.bounding_box())
        normal = owner.find('part').get('id')
        res.remove(res.find(tag('object')+f"[@id='{normal}']"))
        resource(res,tag,normal,name,body)
        frame.update(source_sha256=digest(source),model_volume_mm3=round(body.volume(),3),height_mm=round(body.bounding_box()[5],4))
        if name=='Key_Carrier':
            value(owner,'brim_type','no_brim')
            value(owner,'brim_width',0)
            ref=res.find(tag('object')+"[@id='97']")
            pieces=decode(ref).decompose()
            # The ninth R51 prop approached the old screwed seat. It now lands
            # on an R52 spring, so keep just the eight outer front props.
            separate=sorted(pieces,key=lambda piece:piece.bounding_box()[4])
            assert len(separate)==9,len(separate)
            remaining=mf.Manifold.batch_boolean(separate[:8],mf.OpType.Add)
            remaining+=adhesion_ears(body,placement[:2,3])
            res.remove(ref)
            resource(res,tag,97,'External_peel_support',remaining)
            # A tiny pull-out starter touches the fixed snap-leaf shoulder.
            # Its contact is above the wire exit rather than continuing as a
            # column down through that opening. Force is taken at the fixed end.
            short=shoulder_tab()
            ref=res.find(tag('object')+"[@id='97']")
            from arm_fixture52 import carrier_fixture
            fixture,_=carrier_fixture(np.array(frame['assembly_to_machine']))
            from wide_bases52 import build as wide_bases
            helpers=decode(ref).translate(tr)+short+fixture
            sheets,_,_=wide_bases(name,body.translate(tr),helpers)
            replaced=(helpers+sheets).translate(-tr)
            res.remove(ref)
            resource(res,tag,97,'External_peel_support',replaced)
            corner=mf.Manifold.cube((2.0,2.2,1.4)).translate((35.7,88.75,17.05)).translate(-tr)
            add_modifiers(res,native,owner,{'Upper left socket corner line width':corner},599,'modifier_part')
            modifier=owner.find("part[@id='599']")
            for k,v in dict(wall_loops=2,wall_generator='classic',inner_wall_line_width=.28,outer_wall_line_width=.30,
                            internal_solid_infill_line_width=.32).items():value(modifier,k,v)
        # Preserve inherited key-layout initialization before adding arm and socket masks.
        masks = {}
        if name=='Key_Carrier':
            # The hardware itself stays open at every layer; a wide cuboid
            # around all assembly poses would suppress exterior lip contacts.
            from sockets52 import key_spaces
            from clearance51 import blockers
            from build52 import old
            exact=key_spaces()
            masks={n:v[0] for n,v in exact.items() if len(v)==1 and n.endswith(('_mount_opening','_switch','_socket','_clip_relief'))}
            masks.update(blockers(name,contact_only=False))
            masks['carbon rod']=old.h.base.rod()
            marked=json.loads((HERE/'exterior-targets52.json').read_text())['exterior_contacts']
            solid_marks={}
            for it,(layer,x,y) in enumerate(marked):
                w,h=(2.2,.65) if layer==92 else (2.5,2.5)
                mark=mf.Manifold.cube((w,h,1.7)).translate((x-w/2,y-h/2,layer*.2-.8))
                solid_marks[f'Outside bearing {it+1}']=mark.translate(-tr)
            value(owner,'support_on_build_plate_only',0)
            value(owner,'support_object_xy_distance',.20)
            add_modifiers(res,native,owner,solid_marks,550,'support_enforcer')
        if extra_blocks:
            masks = {**masks,**extra_blocks.get(name,{})}
        local = {n:s.transform(placement[:3]) for n,s in masks.items()}
        if local:
            shadow = mf.CrossSection.batch_boolean([s.project().offset(.60) for s in local.values()],mf.OpType.Add)
            shaft = shadow.extrude(body.bounding_box()[5]+2).translate((0,0,-1))
            if name=='Key_Carrier':
                baseline_masks={**socket_blocks(),**(extra_blocks or {}).get(name,{})}
                shadow=mf.CrossSection.batch_boolean([s.transform(placement[:3]).project().offset(.60) for s in baseline_masks.values()],mf.OpType.Add)
                shaft=shadow.extrude(body.bounding_box()[5]+2).translate((0,0,-1))
            for part in list(owner.findall("part[@subtype='support_enforcer']")):
                if name=='Key_Carrier' and int(part.get('id'))>=550:
                    continue
                pid = part.get('id')
                obj = res.find(tag('object')+f"[@id='{pid}']")
                safe = decode(obj)-shaft
                res.remove(obj)
                if safe.is_empty():
                    owner.remove(part)
                    comps = native.find(tag('components'))
                    comps.remove(comps.find(tag('component')+f"[@objectid='{pid}']"))
                else:
                    resource(res,tag,pid,'Exterior supports',safe)
                    value(part,'name','Exterior supports')
            add_modifiers(res,native,owner,local,300 if name=='Key_Carrier' else 400,'support_blocker')
        # Perimeters spanning a square key aperture need a straight bridge.
        if name=='Key_Carrier':
            value(owner,'bridge_angle',90)
            # The removable triangulated fixture backs both complete spring
            # noses and shanks. Exclude slender native columns in this bay.
            spring_bay=mf.Manifold.cube((21,20,47)).translate((48.8,90.5,0)).translate(-tr)
            add_modifiers(res,native,owner,{'Spring fixture replaces skinny columns':spring_bay},590,'support_blocker')
        if name=='DFRobot_Hole_Bracket':
            from paddle_plate52 import lay_on_side
            lay_on_side(m,cfg,frame,source_body)
            from wide_bases52 import build as wide_bases
            placed=source_body.transform(np.array(frame['assembly_to_machine'])[:3])
            sheets,_,_=wide_bases(name,placed)
            add_modifiers(res,native,owner,{'Paddle tear-off base plates':sheets.translate(-tr)},605,'normal_part')
            value(owner,'brim_type','no_brim')
    build=m.find(tag('build'))
    keep={str(info['parts'][n]['owner']) for n in ('Key_Carrier','DFRobot_Hole_Bracket')}
    plate=cfg.find('plate')
    for item in list(build):
        if item.get('objectid') not in keep: build.remove(item)
    for node in list(cfg.findall('object')):
        if node.get('id') not in keep: cfg.remove(node)
    for inst in list(plate.findall('model_instance')):
        if inst.find("metadata[@key='object_id']").get('value') not in keep: plate.remove(inst)
    resources=keep|{part.get('id') for o in cfg.findall('object') for part in o.findall('part')}
    for obj in list(res):
        if obj.get('id') not in resources: res.remove(obj)
    for obj in list(ranges):
        if int(obj.get('id'))>2: ranges.remove(obj)
    info['parts'].pop('Battery_End_Door')
    value(cfg.find('plate'),'plater_name','R52 key carrier and paddle')
    for key,node in [(MODEL,m),(SETTINGS,cfg),('Metadata/layer_config_ranges.xml',ranges)]:
        files[key] = ET.tostring(node,encoding='utf-8',xml_declaration=True)
    add_tower_base(files, (112, 20), brim_mm=16, extra_rib_mm=30)
    with ZipFile(output,'w',ZIP_DEFLATED) as dest:
        for name,value_ in files.items():
            dest.writestr(name,value_)
    info.update(layout_sha256=digest(output),extra_objects=[],mode='clear four key sockets')
    release_metadata(info,cfg)
    output.with_suffix('.frame.json').write_text(json.dumps(info,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    compose(args.output,HERE/'exports')
