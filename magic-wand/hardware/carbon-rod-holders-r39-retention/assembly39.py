"""Export the R39 review candidate and its complete assembly/removal guide.

No print file is emitted here. Reuses unchanged bought-part routes from R38;
rechecks repaired solids and drives the battery drawing with its checked bend.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import math
import numpy as np
import holder39 as d
import assembly38 as old

HERE=Path(__file__).resolve().parent
OUT=HERE/'exports'
I=old.IDENTITY
H=d.previous.H
A=old.a31


def pose(x=0.,y=0.,z=0.):
    return [1.,0.,0.,float(x),0.,1.,0.,float(y),0.,0.,1.,float(z)]


def stage(title,caption,frames,duration=3):
    return {'title':title,'caption':caption,'samples':frames,'duration':duration,'reveal':True}


def battery_guide(module,body,door):
    module['label']='Battery holder · lower click-in door'
    module['frameEachStep']=True
    module['note']='The existing LP402025 envelope is shown. A replacement cell must be checked before use.'
    module['actors']['holder']['file']='Battery_Holder-assembly.stl'
    module['actors']['door'].update(file='Battery_End_Door-assembly.stl',morphFile='guide/battery-door-released.stl',label='Battery end door · press tab to release')
    mesh=A.trimesh.load_mesh(OUT/'Battery_End_Door-assembly.stl',process=False)
    target=A.trimesh.Trimesh(mesh.vertices+d.door_displacement(mesh.vertices),mesh.faces,process=False)
    target.export(OUT/'guide/battery-door-released.stl')
    state=deepcopy(module['steps'][0]['samples'][0]);state['morphs']={'door':0.}
    steps=[stage('Clear the Print Pads','Snip the narrow pad ties once cool. Clear the two door slots; the battery door is the wide plate with one central spring tab.',[deepcopy(state)])]
    def move(title,caption,changes,blend=None):
        start=deepcopy(state);frames=[]
        for t in np.linspace(0.,1.,41):
            f=deepcopy(start)
            for name,end in changes.items():f[name]=old.lerp(start[name],end,float(t))
            if blend is not None:f['morphs']={'door':start['morphs']['door']+(blend-start['morphs']['door'])*float(t)}
            frames.append(f)
        state.update(deepcopy(frames[-1]));steps.append(stage(title,caption,frames))
    leads=('cell','positive','negative')
    move('Slide the Battery In','Slide the non-wire end in first. Keep both wires through the middle opening; never force or squeeze the pouch.',{n:I for n in leads})
    move('Press the Door Tab','Press the rounded central tab away from the battery. This bends only its spring, clearing the catch.',{},1.)
    move('Slide Down Both Door Edges','Keep the tab pressed and lower both side edges through the two grooves until the door reaches its bottom stop.',{'door':I})
    move('Let the Catch Engage','Release the tab. Its tooth moves under the holder lip. Check that the door stays down with a gentle lift.',{},0.)
    move('Slide Onto the Rod','Slide the assembled holder onto an accessible rod end.',{'rod':I})
    steps.append(stage('Battery Held in Place','The sides guide the door; the middle tooth keeps it from lifting. This is a CAD fit trial, not measured retention force.',[deepcopy(state)],2))
    move('Release the Battery Door','Press the small tab away from the battery to clear the lip. Do not pull hard on a latched door.',{},1.)
    move('Lift the Door Out','Hold the tab pressed and lift the wide door straight up its side grooves.',{'door':pose(z=15)})
    move('Release the Tab','Once out of the grooves, let the spring return to its flat shape.',{},0.)
    move('Remove the Battery','Withdraw the battery by its body, keeping the wires clear of the opening.',{n:pose(y=-37.5) for n in leads})
    move('Slide the Holder Off','With an accessible rod end, slide the empty holder off.',{'rod':pose(y=80)})
    module['steps']=steps
    # Identical checked path with the side wall cut away to expose the tooth.
    cut=d.box(-2.5,2.5,-19,-11,8.5,15)
    A.guide_mesh('battery-catch-holder',body ^ cut)
    cutdoor=door ^ cut
    A.guide_mesh('battery-catch-door',cutdoor)
    m=A.trimesh.load_mesh(OUT/'guide/battery-catch-door.stl',process=False)
    A.trimesh.Trimesh(m.vertices+d.door_displacement(m.vertices),m.faces,process=False).export(OUT/'guide/battery-catch-door-released.stl')
    return {'label':'Battery door catch · cutaway','rotation':[math.pi/2,0,0],
        'note':'A section of the same door and holder. The spring continues outside this cutaway.',
        'actors':{'holder':{'label':'Holder lip','file':'guide/battery-catch-holder.stl','color':'#29a5b7'},
                  'door':{'label':'Door tooth','file':'guide/battery-catch-door.stl','morphFile':'guide/battery-catch-door-released.stl','color':'#d9822b'}},
        'steps':[{**deepcopy(s),'samples':[{k:v for k,v in f.items() if k in ('holder','door','morphs')} for f in s['samples']]} for s in steps if s['title'] in ('Press the Door Tab','Slide Down Both Door Edges','Let the Catch Engage','Release the Battery Door','Lift the Door Out','Release the Tab')]}


def battery_checks(body,door):
    released=door.warp_batch(lambda p:p+d.door_displacement(p))
    zs=np.linspace(0,15,121)
    maximum=max(float((body ^ released.translate((0,0,float(z)))).volume()) for z in zs)
    retained=max(float((body ^ door.translate((0,0,float(z)))).volume()) for z in np.linspace(0,1.5,31))
    cell=d.BATTERY.base.cell_shape()
    cell_hit=float((cell ^ door).volume())
    length=abs(d.DOOR['tongue_root_x_mm'])-d.DOOR['tooth_half_x_mm']
    tooth_shift=abs(d.door_displacement(np.array([[-d.DOOR['tooth_half_x_mm'],-13.25,11.0]]))[0,1])
    report={'released_slide_max_overlap_mm3':round(maximum,6),'unreleased_lift_contact_mm3':round(retained,6),
        'seated_overlap_mm3':round(float((body ^ door).volume()),6),'cell_overlap_mm3':round(cell_hit,6),
        'whole_height_mm':round(d.DOOR['z_mm'][1]-d.DOOR['z_mm'][0],3),'height_reduction_mm':1.3,
        'nominal_tooth_engagement_mm':.55,'nominal_slot_clearance_total_mm':.2,
        'release_tip_deflection_mm':d.RELEASE_MM,'tooth_deflection_mm':round(tooth_shift,3),
        'bending_strain_estimate_percent':round(100*3*tooth_shift*1.9/(2*length*length),2),
        'physical_force_fatigue_and_fit_verified':False}
    report['passed']=maximum<.002 and retained>.05 and cell_hit<.002 and len(door.decompose())==1
    assert report['passed'],report
    return report


def cable_guide(module):
    data=json.loads((HERE/'cable-routes.json').read_text())
    original=module['steps'];state=deepcopy(original[1]['samples'][-1]);steps=deepcopy(original[:2])
    # Each wire starts outside; none teleports into the packed position.
    start=data['routes'][str(data['order'][0])][0]
    for i in range(12):state[f'wire_{i}']=pose(start[0]+i*1.7,8.)
    steps[0]['samples']=[deepcopy(state)]
    state['clip']=pose(z=24)
    for f in steps[0]['samples']:f['clip']=pose(z=24)
    steps[1]['samples']=[{**deepcopy(state),'clip':pose(z=24*(1-float(t)))} for t in np.linspace(0,1,33)]
    state=deepcopy(steps[1]['samples'][-1])
    for i in data['order']:
        path=data['routes'][str(i)];frames=[]
        source=np.array([state[f'wire_{i}'][3],state[f'wire_{i}'][7]])
        # Approach outside the ring first, then follow the checked entry path.
        approach=[(source[0],float(y)) for y in np.linspace(source[1],0,13)]
        approach += [(float(x),0.) for x in np.linspace(source[0],start[0],13)]
        for x,y in approach+path:
            state[f'wire_{i}']=pose(x,y);frames.append(deepcopy(state))
        steps.append(stage(f'Feed Wire {i+1}','Feed one flexible wire through the side slit, then move it inside the loop to leave room for the next. Wire colours identify positions, not an electrical wiring plan.',frames,2))
    steps.append(stage('All Twelve Wires Seated','This checks twelve wires at 1.5 mm outside diameter. The clip guides the bundle; it does not grip the solder joints.',[deepcopy(state)],2))
    for i in reversed(data['order']):
        frames=[]
        for x,y in reversed(data['routes'][str(i)]):
            state[f'wire_{i}']=pose(x,y);frames.append(deepcopy(state))

        for t in np.linspace(0,1,17):
            state[f'wire_{i}']=pose(start[0]+i*1.7*float(t),0.);frames.append(deepcopy(state))
        for t in np.linspace(0,1,17):
            state[f'wire_{i}']=pose(start[0]+i*1.7,8.*float(t));frames.append(deepcopy(state))
        steps.append(stage(f'Remove Wire {i+1}','Bring this wire to the side slit and ease it out. Move the other wires aside; do not pull on their solder joints.',frames,1.5))
    frames=[]
    for t in np.linspace(0,1,33):
        state['clip']=pose(z=24*float(t));frames.append(deepcopy(state))
    steps.append(stage('Slide the Clip Off','Use an accessible rod end to slide the empty clip off.',frames))
    module.update(steps=steps,note='Each 1.5 mm wire follows a separate collision-checked path into the unchanged 7 mm loop. Flexible wire routes outside this short clip are illustrative.')


def overview(modules):
    """Arrange the already assembled units along one rod; no rewiring implied."""
    groups={}
    for group,step_index in [('keys',13),('battery',6),('xiao',4),('cable',14)]:
        m=modules['dfr' if group=='keys' else group]
        # Use the seated frame before any release step.
        if group=='xiao':
            step_index=next((i for i,v in enumerate(m['steps']) if 'check' in v['title'].lower()),4)
        if group=='cable':step_index=next(i for i,v in enumerate(m['steps']) if v['title']=='All Twelve Wires Seated')
        groups[group]=(m,deepcopy(m['steps'][step_index]['samples'][-1]))
    actors={};final={};ids={}
    placements={
        'keys':np.eye(4),'battery':A.trimesh.transformations.rotation_matrix(math.pi,[0,0,1]),
        'cable':A.trimesh.transformations.rotation_matrix(-math.pi/2,[1,0,0]),'xiao':np.eye(4)}
    placements['battery'][1,3]=62.;placements['cable'][1,3]=91.;placements['xiao'][1,3]=128.
    for group,(m,frame) in groups.items():
        ids[group]=[]
        for name,a in m['actors'].items():
            if name=='rod' or (group=='keys' and name.startswith('switch_')):continue
            id=group+'_'+name
            actors[id]=deepcopy(a);ids[group].append(id)
            matrix=np.eye(4);matrix[:3,:]=np.asarray(frame[name]).reshape(3,4)
            final[id]=(placements[group]@matrix)[:3,:].ravel().tolist()
    key_guide=modules['key']
    key_pose=key_guide['steps'][-1]['samples'][-1]
    for name,a in key_guide['actors'].items():
        if not name.startswith(('switch_','socket_')):continue
        id='keys_'+name;actors[id]=deepcopy(a);ids['keys'].append(id);final[id]=deepcopy(key_pose[name])
    rod=d.BATTERY.cyl(4.,-30.,175.).rotate((-90,0,0))
    actors['rod']={'label':'8 mm carbon rod','file':A.guide_mesh('whole-rod',rod),'color':'#35383e','frame':True}
    final['rod']=I
    state=deepcopy(final)
    for group in groups:
        for id in ids[group]:state[id]=A.move(final[id],(0,260,0))
    steps=[stage('Assemble Each Holder First','Use each component view to fit its board, door or keeper. This view shows their order on a bare rod; wire lengths are illustrative.',[deepcopy(state)])]
    for group,label in [('keys','keys'),('battery','battery holder'),('cable','cable clip'),('xiao','XIAO holder')]:
        begin=deepcopy(state);frames=[]
        for t in np.linspace(0,1,41):
            f=deepcopy(begin)
            for id in ids[group]:f[id]=A.move(final[id],(0,260*(1-float(t)),0))
            frames.append(f)
        state=deepcopy(frames[-1]);steps.append(stage('Slide On the '+label.title(),'Slide the '+label+' from the free rod end. Keep the end open until all holders are in place.',frames))
    steps.append(stage('Check the Complete Arrangement','Leave clear space between the holders and spare wire at both ends of the cable clip. These positions are adjustable along the rod.',[deepcopy(state)]))
    for group in ('xiao','cable','battery','keys'):
        begin=deepcopy(state);frames=[]
        for t in np.linspace(0,1,33):
            f=deepcopy(begin)
            for id in ids[group]:f[id]=A.move(final[id],(0,260*float(t),0))
            frames.append(f)
        state=deepcopy(frames[-1]);steps.append(stage('Remove the '+group.title(),'Disconnect the wiring first, then slide this unit off the free end. Follow its own component view for releasing the board or catch.',frames))
    return {'label':'Complete rod assembly','frameEachStep':True,'frameBounds':[[-35,-35,-8],[35,190,32]],'note':'Same R39 parts, grouped on one rod. Adjustable spacing; external wiring lengths are not dimensioned.','rotation':[1.1,0.,-.6],'actors':actors,'steps':steps}


def write_guide(checks,battery,door):
    source=d.R38/'exports'
    guide=old.read(source/'assembly-guide.json')
    for module in guide['modules'].values():
        module['actors']={name:A.relative_actor(actor,source,OUT) for name,actor in module['actors'].items()}
    modules=guide['modules'];modules.pop('battery_easy',None)
    for name in ('key','dfr'):modules[name]['actors']['carrier']['file']='Key_Carrier-assembly.stl'
    morph,_=A.pinched('Grove_Touch_Bracket-assembly.stl','guide/grove-bracket-pinched.stl')
    for name in ('dfr','snap_hinge'):modules[name]['actors']['cap'].update(file='Grove_Touch_Bracket-assembly.stl',morphFile=morph)
    pivot=d.r.AXIS_Y+d.r.CLICK_SHIFT
    detail=d.carrier() ^ d.box(-7.6,7.6,pivot-3.1,pivot+9.,10.9,21.)
    modules['snap_hinge']['actors']['carrier']['file']=A.guide_mesh('grove-hinge-detail',detail)
    modules['dfr'].update(label='Grove touch board and centred OP1 click',status='Fit-trial candidate · not physically tested',note='Uses the Grove Touch Sensor and its two M2 mounting screws. DFRobot DFR0030 uses the separate R35 assembly; its holes and connector are different. R39 adds curved arm roots and a squeeze stop without moving the boards.')
    modules['battery_latch']=battery_guide(modules['battery'],battery,door)
    cable_guide(modules['cable'])
    modules['whole']=overview(modules)
    # An underside view identifies the real rounded contact surfaces without
    # pretending to model the dimensions or force of a particular finger.
    modules['finger_rest']={
        'label':'Finger rest underside','rotation':[-1.2,0.,-.55],
        'note':'The six rounded beams protect the contacts. The front deck edge has a 0.5 mm curved relief; physical comfort still needs a trial.',
        'actors':{'carrier':deepcopy(modules['key']['actors']['carrier'])},
        'steps':[stage('Inspect the Rounded Finger Rest','Curl your finger against the smooth beams below the keys. Remove any support strands first. The square switch openings remain unchanged.',[{'carrier':I}])],
        'annotations':[{'side':'left','actor':'carrier','point':[0.,d.h28.BOTTOM_EDGE,d.DECK_TOP-.25],'title':'Rounded front edge'},
                       {'side':'right','actor':'carrier','point':[13.2,3.45,1.25],'title':'Rounded protective beam'}]}

    guide.setdefault('defaultViews',{})['battery']='battery'
    modules['key']['note']='Choc V1 openings retain their 14.1 mm square seats with 0.2 mm corner rounding. The outer shoulders are deliberately curved; the openings must not narrow after printing.'
    modules['xiao']['note'] += ' Keep the USB-C socket, reset button and antenna end accessible. The keeper belongs to this XIAO holder, not the battery.'
    guide['print_components']={name:group['parts'] for name,group in old.read(HERE/'complete-assembly.json')['groups'].items()}
    files={a[k] for m in modules.values() for a in m['actors'].values() for k in ('file','morphFile') if k in a}
    guide.update(revision=HERE.name,physical_fit_verified=False,sources={
        'r38_guide_sha256':H.sha(source/'assembly-guide.json'),'generator_sha256':H.sha(__file__),
        'manifest_sha256':H.sha(OUT/'manifest.json'),'meshes_sha256':{name:H.sha(OUT/name) for name in sorted(files)}})
    A.write_json(OUT/'assembly-guide.json',guide)


def export():
    (OUT/'guide').mkdir(parents=True,exist_ok=True)
    A.OUT=H.OUT=OUT
    d.install_checks()
    checks=d.checks()
    assert checks['passed']
    H.PRINT_ROT[d.previous.BRACKET]=A.trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0])
    H.PRINT_ROT['Battery_End_Door']=A.trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0])
    parts={name:H.export_part(name,shape,name) for name,shape in ((d.previous.CARRIER,d.carrier()),(d.previous.BRACKET,d.bracket()),('Battery_End_Door',d.battery_door()))}
    parts['Battery_Holder']=d.BATTERY.copy_part('Battery_Holder',d.BATTERY.HERE,OUT,anchored=True)
    A.write_json(OUT/'anchors.json',{'parts':{'Battery_Holder':old.read(d.BATTERY.HERE/'exports/anchors.json')['parts']['Battery_Holder']}})
    battery= d.BATTERY.read(OUT/'Battery_Holder-assembly.stl')
    door=d.BATTERY.read(OUT/'Battery_End_Door-assembly.stl')
    checks['battery_door']=battery_checks(battery,door)
    A.write_json(OUT/'geometry-checks.json',{'revision':HERE.name,'physical_fit_verified':False,'sliced':False,'checks':checks})
    A.write_json(OUT/'manifest.json',{'revision':HERE.name,'units':'mm','parts':parts,'physical_fit_verified':False,'print_cleared':False,
        'source_sha256':{p.name:H.sha(p) for p in (HERE/'holder39.py',Path(__file__),HERE/'complete-assembly.json',HERE/'cable-routes.json')}})
    write_guide(checks,battery,door)
    print(json.dumps({'checks_passed':True,'battery':checks['battery_door'],'parts':list(parts),'modules':{n:len(m['steps']) for n,m in old.read(OUT/'assembly-guide.json')['modules'].items()}},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--register',action='store_true');p.add_argument('--guide-only',action='store_true');a=p.parse_args()
    if a.register:A.register_assembly(OUT/'assembly-guide.json','r39','R39 Stronger hinge and lower battery door',make_current=True,group_keys=True)
    elif a.guide_only:
        d.install_checks()
        A.OUT=H.OUT=OUT
        write_guide(old.read(OUT/'geometry-checks.json')['checks'],d.BATTERY.read(OUT/'Battery_Holder-assembly.stl'),d.BATTERY.read(OUT/'Battery_End_Door-assembly.stl'))
    else:export()
