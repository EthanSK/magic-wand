#!/usr/bin/env python3
"""Build R14 from exact final STLs with limited, labelled exterior support sources.

Explicit CAD breakaway walls replace algorithmic supports. The actual resulting G-code,
including support/interface/brim footprints, must pass verify_slice.py.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess,zipfile,xml.etree.ElementTree as E
import numpy as np,trimesh
import cad
import deliverables
import working_spaces
HERE=cad.HERE
BUILDER=HERE.parent/'printed-loop-wand/shard-tube-r2'

LAYER=.2
SIDE_GAP=.9


def helper_top(face,bed,direction=1):
    """Geometry top that leaves exactly one empty actual layer below a face.

    Bambu samples layer middles. A face on a sampling plane starts on the
    following layer; the exported paths, not this prediction, verify the gap.
    """
    height=direction*(face-bed)
    first=(int(np.floor((height+LAYER/2+1e-6)/LAYER))+1)*LAYER
    last=first-2*LAYER
    return bed+direction*(last-LAYER/4)


def clip_wall(bed,face,direction=1):
    end=helper_top(face,bed,direction);height=direction*(end-bed);cap=2.
    outer=cad.cyl(7.1,0,height)
    inside=cad.cyl(6.3,0,height-cap)+cad.mf.Manifold.cylinder(cap,6.3,4.3,96).translate((0,0,height-cap))
    wall=(outer-inside).rotate((-90*direction,0,0)).translate((0,bed,0))
    base=cad.tube_y(6.2,8.5,min(bed,bed+direction),max(bed,bed+direction))
    # Split through both ends: each half can leave outward, rather than
    # being trapped axially between two nearly closed spring rings.
    return (wall+base)-cad.box(-.8,.8,-80,100,-12,12)


def bonded_tabs(name):
    """Deliberate cut-away ties on fixed outer rails, never on spring tips."""
    if name=='XIAO_Rod_Holder':
        return [cad.box(sign*10.6-.4,sign*10.6+.4,.6,1.25,8.,8.8)for sign in [-1,1]]
    if name!='Key_Carrier':return []
    z=cad.P['keys']['pcb_z']+1.4
    return [cad.box(sign*26.2-.4,sign*26.2+.4,-10.55,-9.9,z-.4,z+.4)for sign in [-1,1]]

def clip_contact(shape,centre,width):
    # Classify the exported clip with a generously containing volume.
    # Subtracting a nearly identical analytical ring from a float32 STL
    # leaves microscopic films; their offset wrongly erased the real cap.
    volume=cad.cyl(6.05,centre-width/2-.02,centre+width/2+.02).rotate((-90,0,0))
    return shape^volume


def layered_helper(raw,ordinary,contacts,functional,keepout,name,bed):
    """Continuous XY offsets on the actual 0.2 mm print layer grid.

    Unioned translated 3D copies are not a continuous dilation and left
    tiny trapped chips. Layer sections also make the contact grid explicit.
    The resulting G-code is still independently audited, not inferred here.
    """
    angle=-90 if name=='Battery_Holder'else 90
    rot=trimesh.transformations.rotation_matrix(np.deg2rad(angle),[1,0,0])
    rot[2,3]=(bed if angle<0 else -bed)
    objects=[s.transform(rot[:3,:])for s in [raw,ordinary,functional,keepout]]
    raw,ordinary,functional,keepout=objects
    contacts=[(s.transform(rot[:3,:]),stop)for s,stop in contacts]
    cs_union=lambda values:cad.mf.CrossSection.batch_boolean(values,cad.mf.OpType.Add)
    count=int(np.ceil(raw.bounding_box()[5]/LAYER));pieces=[];normal_cache={};contact_cache={};previous=cad.mf.CrossSection()
    for i in range(count):
        mid=(i+.5)*LAYER;section=raw.slice(mid)
        if section.is_empty():previous=cad.mf.CrossSection();continue
        for j in range(max(0,i-5),i+6):
            if j not in normal_cache:
                # Coincident float32 contact cuts can leave micron-thin
                # films. Expanding one by 0.9 mm erased a valid front cap.
                # Remove only sub-printable numerical films before the
                # clearance offset; actual bead side gaps remain audited.
                normal_cache[j]=ordinary.slice((j+.5)*LAYER).offset(-.01).offset(.01).offset(SIDE_GAP)
        full_clearance=[normal_cache[j]for j in range(max(0,i-5),i+6)];close_contacts=[]
        for index,(target,stop)in enumerate(contacts):
            if mid<=stop+.001:
                close_contacts += [target.slice(mid+d)for d in [-.15,0,.15]]
            else:
                # The narrow release gap applies only BELOW its named
                # first face. A different wall passing above that contact
                # must regain the ordinary full clearance, never fuse to it.
                for j in range(max(0,i-5),i+6):
                    key=(index,j)
                    if key not in contact_cache:contact_cache[key]=target.slice((j+.5)*LAYER).offset(SIDE_GAP)
                    full_clearance.append(contact_cache[key])
        general=cs_union(full_clearance)
        contact=cs_union(close_contacts).offset(SIDE_GAP)
        functional_halo=cs_union([functional.slice(mid+d)for d in [-.3,0,.3]]).offset(.3)
        clear=section-general-contact-functional_halo-keepout.slice(mid)
        # Strip sub-nozzle chips and reject starts hanging from a later
        # connection. A connected 3D wall can still start as an air island.
        clear=clear.offset(-.22).offset(.22)
        natural=previous.offset(.25)
        if i:clear^=natural
        clear=cs_union([s for s in clear.decompose()if s.area()>.15 and
                        (i==0 or (s^natural).area()>.01)]).simplify(.005)
        # A 5-micron modelling overlap joins neighbouring solids robustly.
        # It does not add a sliced layer; real backing gaps are remeasured.
        if not clear.is_empty():pieces.append(cad.mf.Manifold.extrude(clear,LAYER+.005).translate((0,0,i*LAYER)))
        previous=clear
    result=cad.union(pieces).simplify(.005)
    # Every surviving wall grows from the bed. A crop or a keepout must not
    # leave a detached chip above a spring. Fixed-rail cut tabs are separate.
    result=cad.union([s for s in result.decompose()if s.volume()>.05 and abs(s.bounding_box()[2])<.02])
    inverse=np.linalg.inv(rot)
    return result.transform(inverse[:3,:])


def print_helpers(name,normal_shape=None,diameter=None,key_indices=None):
    """Split outward-removable aids; one actual empty layer at named contacts."""
    z=cad.P['keys']['pcb_z'];shape=cad.part_shapes()[name]if normal_shape is None else normal_shape;bb=shape.bounding_box()
    diameter=diameter or cad.P['rod']['clip_diameter'];pieces=[];ties=[];contacts=[]
    def add_contact(region,top):contacts.append((region,abs(top-bed)-LAYER/4))
    if name=='Key_Carrier':
        bed=bb[1]
        if key_indices is None:
            # Back the deep front webs as well as the thin front lip. Their
            # first section was a broad cantilever below that lip.
            # The first full web infill is at 4.0 mm; the preceding layer
            # prints only its border. Back the interior one empty layer
            # below 4.0, keeping earlier border paths at ordinary clearance.
            face=-10.1;top=helper_top(face+.17,bed)
            for sign in [-1,1]:
                xs=(7.,18.5)if sign>0 else(-18.5,-7.)
                pieces.append(cad.box(*xs,bed,top,z-4.5,z+2.05))
                add_contact(shape^cad.box(xs[0]+1,xs[1]-1,face-.02,face+1.5,z-3.5,z+1.05),top)
        for index,(x,y)in enumerate(cad.key_positions()):
            if key_indices is not None and index not in key_indices:continue
            # The slicer omits the tiny leading sliver of the lower front
            # diagonals. Back their first actual bead, not that absent mesh.
            face=y-10.53;leg_top=helper_top(face,bed)
            for sign in [-1,1]:
                xx=x+sign*7.9
                target=shape^cad.box(xx-1.4,xx+1.4,face-.6,face+1.5,z-5.6,z-1.5)
                if target.volume()>.1:
                    pieces.append(cad.box(xx-1,xx+1,bed,leg_top,z-5.6,z-3.2))
                    pieces.append(cad.box(xx-1.5,xx+1.5,bed,bed+.6,z-5.9,z-2.9))
                    add_contact(target,leg_top)
            xs=(x-7.7,x+7.7)if y==0 else ((x+7.6,x+9.2)if x>0 else(x-9.2,x-7.6))
            face=y-9.4-cad.P['structure']['rail_radius'];top=helper_top(face,bed)
            pieces.append(cad.box(*xs,bed,top,z+.8,z+2.05))
            add_contact(shape^cad.box(xs[0]-1,xs[1]+1,face,face+1.7,z-.2,z+3.1),top)
            face=y-.5;top=helper_top(face,bed)
            add_contact(shape^cad.box(x-6,x+11,face,face+1.7,z-5.8,z-2.4),top)
            if y:
                # Route the tall upper-floor aids below the lower key floors.
                # A gradual ramp rises only after those floors have ended.
                ramp=top-3.6
                pieces.append(cad.box(x-5,x+10,bed,ramp,z-8.57,z-6.57))
                a=cad.box(x-5,x+10,ramp-.15,ramp,z-8.57,z-6.57)
                b=cad.box(x-5,x+10,top-.15,top,z-4.8,z-3.77)
                pieces.append(cad.mf.Manifold.batch_hull([a,b]))
                xx=x+(8.4 if x>0 else -8.4);anchor=x+(9 if x>0 else -4)
                pieces.append(cad.rib((anchor,bed+3,z-7.57),(xx,bed+12,z+1.4),.7))
            elif x==0:
                # Bed-grown side wings taper inward above the first ring.
                # This avoids resting a long helper on that spring's end face.
                for lo,hi,inner in [(-8.5,-6.8,-.8),(6.8,10.5,.8)]:
                    pieces.append(cad.box(lo,hi,bed,top,z-4.8,z-3.77))
                    start=bed+5.8
                    aa=cad.box(lo,hi,start-.15,start,z-4.8,z-3.77)
                    bbx=(lo,inner)if lo<0 else(inner,hi)
                    bbshape=cad.box(*bbx,top-.15,top,z-4.8,z-3.77)
                    pieces.append(cad.mf.Manifold.batch_hull([aa,bbshape]))
            else:pieces.append(cad.box(x-5,x+10,bed,top,z-4.8,z-3.77))
            pieces.append(cad.box(x-6,x+11,bed,bed+1,z-9.57,z+2.4))
        cy=cad.carrier_clip_centres()[-1];width=cad.P['rod']['ring_width']
        pieces.append(clip_wall(bed,cy-width/2))
        add_contact(clip_contact(shape,cy,width),helper_top(cy-width/2,bed))
        for sign in [-1,1]:
            xx=sign*26.2;pieces.append(cad.box(xx-.8,xx+.8,bed,-10.55,z+.6,z+2.2))
        ties=bonded_tabs(name);keepout=cad.wire_bus(-80,100)
    elif name=='Battery_Holder':
        bed=bb[4];cy=cad.battery_clip_centres()[0];width=cad.P['rod']['ring_width']
        pieces=[clip_wall(bed,cy+width/2,-1),cad.box(-17,17,bed-1,bed,-8.5,15)]
        add_contact(clip_contact(shape,cy,width),helper_top(cy+width/2,bed,-1))
        b=cad.P['battery'];floor=b['floor_z']+cad.P['assembly']['battery_floor_raise_mm']
        keepout=cad.box(-11.9,11.9,-80,16.9,floor-.25,floor+b['reserve_thickness']+.25)
        keepout+=cad.wire_bus(-80,100)+cad.wire_bus(-80,100).mirror((1,0,0))
    elif name=='XIAO_Rod_Holder':
        bed=bb[1];cy=22.2;width=cad.P['rod']['sensor_clip_width']
        pieces=[clip_wall(bed,cy-width/2),cad.box(-12.5,12.5,bed,bed+1,-8.5,11)]
        add_contact(clip_contact(shape,cy,width),helper_top(cy-width/2,bed))
        # The late fixed diagonals begin before the C face. Back their
        # complete first face rather than asking a V-shaped 18 mm path to
        # bridge from the PCB rails to a crown that is not printed yet.
        diagonal=shape^cad.box(-12,12,20.7,22.3,3.,9.)
        top=helper_top(20.75,bed)
        projection=diagonal.rotate((90,0,0)).project().offset(.15)
        wall=cad.mf.Manifold.extrude(projection,top-bed).rotate((-90,0,0)).translate((0,bed,0))
        pieces.append(wall);add_contact(diagonal,top)
        for sign in [-1,1]:
            xx=sign*10.2
            pieces.append(cad.box(xx-.7,xx+.7,bed,helper_top(1.,bed),7.25,9.75))
            add_contact(shape^cad.box(xx-1.5,xx+1.5,1.,2.7,6.8,10.5),helper_top(1.,bed))
        keepout=cad.external_wire_route();ties=bonded_tabs(name)
    else:return None
    targets=cad.union([s for s,stop in contacts]);ordinary=shape-targets
    functional=cad.union(list(working_spaces.regions(name,diameter,key_indices).values()))
    raw=cad.union(pieces)-cad.cyl(4.3,-80,100).rotate((-90,0,0))
    raw-=cad.clip_gap(0).scale((1,100,1))
    raw-=cad.box(-.8,.8,-80,100,-12,20)
    result=layered_helper(raw,ordinary,contacts,functional,keepout,name,bed)
    return (result+cad.union(ties)if ties else result).simplify(.005)

def helper(model,config,obj,shape,transform,ident,subtype,title):
    ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';tag=lambda s:'{'+ns+'}'+s
    resources=model.find(tag('resources'));m=cad.mesh(shape)
    inverse=np.linalg.inv(transform);vv=m.vertices@inverse[:3,:3].T+inverse[:3,3]
    child=E.SubElement(resources,tag('object'),id=str(ident),type='model',name=title)
    mesh=E.SubElement(child,tag('mesh'));vertices=E.SubElement(mesh,tag('vertices'));faces=E.SubElement(mesh,tag('triangles'))
    for v in vv:E.SubElement(vertices,tag('vertex'),**{k:format(float(t),'.9g')for k,t in zip('xyz',v)})
    for f in m.faces:E.SubElement(faces,tag('triangle'),v1=str(f[0]),v2=str(f[1]),v3=str(f[2]))
    parent=next(o for o in resources.findall(tag('object'))if o.get('id')==obj.get('id'))
    E.SubElement(parent.find(tag('components')),tag('component'),objectid=str(ident))
    part=E.SubElement(obj,'part',id=str(ident),subtype=subtype)
    E.SubElement(part,'metadata',key='name',value=title)

def build(scratch,do_slice,coupon=False,only=None,bore=7.9):
    assert coupon or bore==7.9,'Bore brackets are test coupons, not a new default fit'
    builder=cad.load('print_projects',BUILDER);settings=builder.settings()
    overrides=dict(enable_support='0',brim_type='no_brim',layer_height='0.2',
                   wall_loops='3',sparse_infill_density='20%',bridge_no_support='1',max_bridge_length='12')
    settings.update(overrides)
    diff=settings.get('different_settings_to_system',['','',''])
    diff[0]=';'.join(sorted(set(filter(None,diff[0].split(';')))|set(overrides)))
    settings['different_settings_to_system']=diff;builder.settings=lambda:settings
    out=HERE/'exports'
    if coupon:
        import fit_coupon
        fit_coupon.export(bore);out=fit_coupon.OUT
    manifest=json.loads((out/'manifest.json').read_text())
    if only:
        assert not coupon,'Choose a coupon or a complete-part trial, not both'
        trial=out/('trial-'+'-'.join(only));trial.mkdir(exist_ok=True)
        manifest={**manifest,'parts':{n:manifest['parts'][n]for n in only},'subset_test':True,'source_manifest_sha256':cad.sha(out/'manifest.json')}
        for n in only:
            for filename in [deliverables.normal_name(n),n+'-assembly.stl']:shutil.copyfile(out/filename,trial/filename)
        out=trial;(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    parts=[]
    for name,record in manifest['parts'].items():
        mesh=trimesh.load_mesh(out/deliverables.normal_name(name));mesh.apply_transform(np.array(record['print_to_assembly']))
        parts.append(dict(name=name,**record,assembly_vertices=mesh.vertices.tolist(),assembly_faces=mesh.faces.tolist()))
    layout=out/'Holder-R14-layout.3mf';layout.unlink(missing_ok=True)
    builder.make(list(manifest['parts']),[(30,90),(115,100),(170,130),(210,170)],layout,{'parts':parts})
    with zipfile.ZipFile(layout)as z:files={n:z.read(n)for n in z.namelist()}
    model=E.fromstring(files['3D/3dmodel.model']);config=E.fromstring(files['Metadata/model_settings.config'])
    for index,obj in enumerate(config.findall('object')):
        meta={m.get('key'):m for m in obj.findall('metadata')};name=meta['name'].get('value')
        meta['enable_support'].set('value','0')
        for k,v in overrides.items():
            if k!='enable_support':E.SubElement(obj,'metadata',key=k,value=v)
        mm=trimesh.load_mesh(out/(name+'-assembly.stl'))
        normal_shape=cad.mf.Manifold(cad.mf.Mesh(mm.vertices.astype(np.float32),mm.faces.astype(np.uint32)))
        shape=print_helpers(name,normal_shape,manifest.get('clip_diameter_mm'),tuple(manifest['key_indices'])if coupon else None)
        if coupon and shape is not None:shape^=fit_coupon.clip_volume()
        if shape is not None and not shape.is_empty():
            cad.mesh(shape).export(out/(name+'-PRINT-HELPER-assembly.stl'))
            helper(model,config,obj,shape,np.array(manifest['parts'][name]['print_to_assembly']),100+index,
                   'normal_part','REMOVE AFTER PRINT - exterior breakaway wall')
    for plate in config.findall('plate'):
        for item in plate.findall('metadata'):
            if item.get('key')=='plater_name':item.set('value','Magic Wand R14 - print trial')
    files['3D/3dmodel.model']=E.tostring(model,encoding='utf-8',xml_declaration=True)
    files['Metadata/model_settings.config']=E.tostring(config)
    with zipfile.ZipFile(layout,'w',zipfile.ZIP_DEFLATED)as z:
        for n,d in files.items():z.writestr(n,d)
    report={'layout_sha256':cad.sha(layout),'generator_sha256':cad.sha(Path(__file__)),
            'builder_sha256':cad.sha(BUILDER/'print_projects.py'),'parts':list(manifest['parts']),'helper_sha256':{p.name:cad.sha(p)for p in out.glob('*-PRINT-HELPER-assembly.stl')},
            'support_policy':'Automatic supports off; labelled exterior CAD breakaway walls; actual beads require separate audit.',
            'physical_print_verified':False}
    if do_slice:
        scratch=scratch.resolve();scratch.mkdir(parents=True,exist_ok=True);(scratch/'tmp').mkdir(exist_ok=True)
        cfg=BUILDER/'print-settings';process=json.loads((cfg/'process.json').read_text());process.update(overrides)
        process_path=scratch/'process.json';process_path.write_text(json.dumps(process,indent=2)+'\n')
        target=deliverables.project_name(out)
        cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--datadir',str(scratch/'bambu-data'),'--debug','2',
             '--load-settings',str(cfg/'machine.json')+';'+str(process_path),'--load-filaments',str(cfg/'filament.json'),
             '--orient','0','--arrange','0','--slice','0','--export-3mf',target,'--outputdir',str(scratch),str(layout)]
        with (scratch/'slice.log').open('w')as log:
            subprocess.run(cmd,cwd=scratch,stdout=log,stderr=subprocess.STDOUT,check=True,env={**os.environ,'TMPDIR':str(scratch/'tmp')})
        result=json.loads((scratch/'result.json').read_text());assert result['return_code']==0
        report['slice']=result;report['warnings']=[p['warning_message']for p in result['sliced_plates']if p.get('warning_message')]
        (out/target).write_bytes((scratch/target).read_bytes())
        report['delivered_settings_registration']=restore_registration(out/target,settings)
        report['sliced_project_filename']=target
        report['sliced_project_sha256']=cad.sha(out/target)
    (out/'print-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(report.get('warnings',[]),flush=True)

def restore_registration(path,expected):
    """CLI export drops registration. Restore metadata, never invent values."""
    with zipfile.ZipFile(path)as z:files={i.filename:(i,z.read(i))for i in z.infolist()}
    key='Metadata/project_settings.config';config=json.loads(files[key][1])
    required=set(filter(None,expected['different_settings_to_system'][0].split(';')))
    for name in required:
        assert config.get(name)==expected.get(name),(name,'Sliced value differs from prepared recipe')
    before=set(filter(None,config.get('different_settings_to_system',[''])[0].split(';')))
    slots=config.get('different_settings_to_system',['','','']);slots[0]=';'.join(sorted(before|required))
    config['different_settings_to_system']=slots
    files[key]=(files[key][0],json.dumps(config,indent=2).encode())
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)as z:
        for info,data in files.values():z.writestr(info,data)
    return {'required_keys':sorted(required),'registered_keys':sorted(before|required),
            'cli_dropped_keys':sorted(required-before),'values_unchanged':True}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scratch',type=Path,required=True);p.add_argument('--slice',action='store_true');p.add_argument('--coupon',action='store_true');p.add_argument('--bore',type=float,choices=[7.9,8.,8.1],default=7.9);p.add_argument('--only',nargs='+',choices=list(cad.part_shapes()));a=p.parse_args();build(a.scratch,a.slice,a.coupon,a.only,a.bore)
