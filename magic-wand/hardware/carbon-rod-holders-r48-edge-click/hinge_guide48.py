"""Show the wider printed hinge spring visibly changing between its three poses."""
from pathlib import Path
import shutil
from unittest.mock import patch

import numpy as np

import hinge48 as spring


def export_printed(g, stage, scratch, out, manifest):
    """The printer gets the relaxed bracket. The assembly scene retains seated references."""
    label=g.d.BRACKET
    seated_file=out/(label+'-assembly.stl')
    free_source=stage/'R47-DFRobot_Hole_Bracket-cap.stl'
    model=g.A.trimesh.load_mesh(seated_file,process=False)
    vertices=model.vertices.copy()
    expansion=spring.FREE_SHOULDER-spring.SEATED_SHOULDER
    relaxed=out/'guide/dfrobot-bracket-free.stl'
    g.A.trimesh.Trimesh(vertices+spring.displacement(g.h,vertices,expansion,expansion),
                        model.faces,process=False).export(relaxed)
    squeeze=spring.PINCHED_SHOULDER-spring.SEATED_SHOULDER
    expected=vertices+spring.displacement(g.h,vertices,squeeze,squeeze)
    pinched=out/'guide/dfrobot-bracket-pinched.stl'
    g.A.trimesh.Trimesh(expected,model.faces,process=False).export(pinched)
    written=g.A.trimesh.load_mesh(pinched,process=False)
    assert np.allclose(written.vertices,expected,atol=.00001) and np.array_equal(written.faces,model.faces)
    native=g.b.load(free_source)
    free=g.b.load(relaxed)
    delta=(free-native).volume()+(native-free).volume()
    assert abs(delta)<.01, ('Displayed free bracket differs from native input',delta)
    assembly=g.b.load(seated_file)
    settled=g.b.load(stage/'R48-DFRobot_Hole_Bracket-seated.stl')
    drift=(assembly-settled).volume()+(settled-assembly).volume()
    assert abs(drift)<.01, ('Displayed seated bracket differs from checked installed pose',drift)
    # The generic STL links in exports are also regenerated in the unloaded shape.
    cache=scratch/'guide-print-frame'
    cache.mkdir(exist_ok=True)
    with patch.object(g.H,'OUT',cache):
        free_part=g.H.export_part(label,native,label)
    printed=label+'-SOURCE-REQUIRES-PREPARATION.stl'
    shutil.copyfile(cache/printed,out/printed)
    installed=manifest['parts'][label]
    installed.update(volume_mm3=free_part['volume_mm3'],solid_PETG_g=free_part['solid_PETG_g'],
                     installed_volume_mm3=round(float(assembly.volume()),3),
                     stl_sha256=g.H.sha(out/printed),print_to_assembly=free_part['print_to_assembly'],
                     print_height_mm=free_part['print_height_mm'],free_stl_sha256=g.H.sha(relaxed),
                     installed_assembly_sha256=g.H.sha(seated_file),native_free_sha256=g.H.sha(free_source),
                     print_to_assembly_scope='Maps the STL into the unloaded spring frame. In the assembled bracket each side bends inward.')
    return {'free_file':relaxed.relative_to(out).as_posix(),'spring_neutral_to_native_mm3':round(delta,6),
            'spring_seated_to_checked_mm3':round(drift,6)}


def animate(guide,g,free_path):
    # A single morph interpolates between physical endpoints: as printed and
    # fully pinched. The installed spring lies partway between the two.
    rest=(spring.FREE_SHOULDER-spring.SEATED_SHOULDER)/(spring.FREE_SHOULDER-spring.PINCHED_SHOULDER)
    r=g.h.r
    pivot=np.array([0.,r.AXIS_Y,r.AXIS_Z,1.])
    fixed=(np.asarray(r.placement())@pivot)[2]
    for name in ('dfr','snap_hinge'):
        module=guide['modules'][name]
        module['actors']['cap']['file']=free_path
        for step in module['steps']:
            if step['title'] in ('Pinch the Bracket Arms','Pinch to Release the Tabs'):
                step['caption']='Pinch the two pads on the empty orange bracket just enough for both round tabs to clear the fixed supports.'
            if step['title'] in ('Let the Tabs Snap Into the Holes','Let the Tabs Snap Back In'):
                step['caption']='Let go with the outer guides either side of the fixed supports. Check that both round tabs are in their holes. Lift the bracket gently to check it stays seated before fitting the touch board.'
            for sample in step['samples']:
                matrix=np.asarray(sample['cap']).reshape(3,4)
                axis_height=(matrix@pivot)[2]
                previously=float(sample.get('morphs',{}).get('cap',0.))
                # The tabs are fully squeezed while passing the ear tops.
                # Out of the ears a released arm takes its as-printed shape.
                sitting=abs(axis_height-fixed)<.02
                base=rest if sitting else 0.
                sample.setdefault('morphs',{})['cap']=base+(1.-base)*previously
        weights=[sample['morphs']['cap'] for step in module['steps'] for sample in step['samples']]
        assert min(weights)<1e-6 and max(weights)==1. and abs(weights[-1]-rest)<1e-6
    return rest


def show_independent_arms(guide, g, out, rest):
    """Partition one physical mesh without cutting new surfaces, so each arm can flex alone."""
    from copy import deepcopy
    detail=guide['modules']['snap_hinge']
    cap=detail['actors']['cap']
    mesh=g.A.trimesh.load_mesh(out/(g.d.BRACKET+'-assembly.stl'),process=False)
    vertices=mesh.vertices
    free=spring.displacement(g.h,vertices,spring.FREE_SHOULDER-spring.SEATED_SHOULDER,
                             spring.FREE_SHOULDER-spring.SEATED_SHOULDER)
    pinch=spring.displacement(g.h,vertices,spring.PINCHED_SHOULDER-spring.SEATED_SHOULDER,
                              spring.PINCHED_SHOULDER-spring.SEATED_SHOULDER)
    moved=free[mesh.faces,0]
    left=(moved < -1e-8).any(axis=1)
    right=(moved > 1e-8).any(axis=1)
    assert not (left & right).any()
    masks={'cap':~(left|right),'left_arm':left,'right_arm':right}
    assert all(mask.any() for mask in masks.values()) and sum(mask.sum() for mask in masks.values())==len(mesh.faces)
    for actor,mask in masks.items():
        source=f'guide/hinge-detail-{actor}.stl'
        target=f'guide/hinge-detail-{actor}-pinched.stl'
        faces=mesh.faces[mask]
        g.A.trimesh.Trimesh(vertices+free,faces,process=False).export(out/source)
        record=dict(cap,file=source)
        record.pop('morphFile',None)
        if actor!='cap':
            g.A.trimesh.Trimesh(vertices+pinch,faces,process=False).export(out/target)
            record.update(morphFile=target,label='Left spring arm' if actor=='left_arm' else 'Right spring arm')
        else:
            record['label']='Touch bracket with rigid centring guides and centre squeeze stop'
        detail['actors'][actor]=record
    # A single rigid transform still moves the bracket. Only the flex weights differ.
    for step in detail['steps']:
        for sample in step['samples']:
            weight=sample['morphs'].pop('cap')
            for arm in ('left_arm','right_arm'):
                sample[arm]=list(sample['cap'])
                sample['morphs'][arm]=weight
    replacements={}
    sequence=[]
    for step in detail['steps']:
        refit=step['title']=='Let the Tabs Snap Back In'
        if not refit and step['title']!='Let the Tabs Snap Into the Holes':
            sequence.append(step)
            continue
        first,second=('right','left') if refit else ('left','right')
        titles=[]
        for active,waiting,waiting_weight in [(first,second,1.),(second,first,rest)]:
            title=f'Seat the {active} tab' if not refit else f'Refit the {active} tab'
            caption=(f'Release the {active} pad into its hole. '
                     +(f'Keep the {waiting} pad pinched.' if waiting_weight==1. else 'Check that both pins are inside their holes. Give the bracket a gentle lift to check it stays seated.'))
            samples=deepcopy(step['samples'])
            for sample in samples:
                sample['morphs'][waiting+'_arm']=waiting_weight
            sequence.append(dict(step,title=title,caption=caption,samples=samples))
            titles.append(title)
        replacements[step['title']]=titles[-1]
    detail['steps']=sequence
    for mark in detail['annotations']:
        if mark['actor']=='cap':
            mark['actor']='left_arm'
        mark['step']=replacements.get(mark['step'],mark['step'])
    assert any(abs(s['morphs']['left_arm']-s['morphs']['right_arm'])>.7 for step in sequence for s in step['samples'])


def render_fit_states(module, out):
    """Draw the free and two release states from the same meshes and transforms as the animation."""
    from compare46 import render, triangles
    from PIL import Image, ImageDraw, ImageFont
    by_title = {step['title']:step['samples'] for step in module['steps']}
    free = next((frame for step in module['steps'] for frame in step['samples']
                 if frame['morphs']['left_arm'] == frame['morphs']['right_arm'] == 0.), None)
    assert free is not None
    states = (('As printed',free,False),('Left tab seated',by_title['Seat the left tab'][-1],True),
              ('Both tabs seated',by_title['Seat the right tab'][-1],True))
    by_actor = {}
    for name,actor in module['actors'].items():
        if name not in ('cap','left_arm','right_arm','carrier'):
            continue
        base = triangles(out/actor['file'])
        delta = triangles(out/actor['morphFile'])-base if 'morphFile' in actor else 0.
        color = bytes.fromhex(actor['color'].strip('#'))
        by_actor[name]=base,delta,list(color)
    size=(380,295)
    overview=Image.new('RGB',(3*size[0],size[1]+36),(24,31,37))
    draw=ImageDraw.Draw(overview)
    try:
        font=ImageFont.truetype('Arial.ttf',18)
    except OSError:
        font=ImageFont.load_default(size=18)
    for index,(label,frame,with_carrier) in enumerate(states):
        items=[]
        for name,(base,delta,rgb) in by_actor.items():
            if name=='carrier' and not with_carrier:
                continue
            mat=np.asarray(frame[name]).reshape(3,4)
            verts=base+delta*frame.get('morphs',{}).get(name,0.)
            items.append((verts@mat[:,:3].T+mat[:,3],rgb))
        # Centre on the axle. Each panel keeps the same angle and magnification.
        mat=np.asarray(frame['cap']).reshape(3,4)
        import build48
        h=build48.h
        pivot=mat@np.array([0.,h.r.AXIS_Y,h.r.AXIS_Z,1.])
        overview.paste(render(items,(0.,.64,1.),19.,size,pivot),(index*size[0],36))
        draw.text((index*size[0]+16,8),label,fill='#f4f4f4',font=font)
    overview.save(out/'R48-hinge-fit.png')
