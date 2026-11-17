"""Use the checked Micron cassette for both battery views and the full rod animation."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import shutil

import numpy as np

import battery48 as cad
from battery_print48 import inputs
from native48 import digest, read, write


def translated(vector):
    matrix = np.eye(4)
    matrix[:3, 3] = vector
    return matrix[:3].ravel().tolist()


def export(out, scratch, manifest, g):
    directory, rows = inputs(scratch)
    receipt=read(directory/'manifest.json')
    checks=read(directory/receipt['checks'])
    assert checks['passed'] and digest(directory/receipt['checks'])==receipt['checks_sha256']
    assert receipt['source_sha256']==digest(Path(cad.__file__))
    layout=checks['layout']
    anchors = {}
    for name, row in rows.items():
        assembly = out / (name + '-assembly.stl')
        source = out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')
        shutil.copyfile(directory / row['assembly_stl'], assembly)
        shutil.copyfile(directory / row['print_stl'], source)
        model = g.A.trimesh.load_mesh(assembly)
        native = g.A.trimesh.load_mesh(source)
        manifest['parts'][name] = dict(
            source='Micron 72217 cassette from the selected plate',
            stl_sha256=digest(source), assembly_stl_sha256=digest(assembly),
            print_to_assembly=row['print_to_assembly'], assembly_bounds_mm=model.bounds.round(4).tolist(),
            volume_mm3=round(float(model.volume), 3), solid_PETG_g=round(float(model.volume)*.00127, 3),
            print_height_mm=round(float(native.extents[2]), 3))
        pad = out / (name+'-ANCHOR-REMOVE-AFTER-PRINT.stl')
        if row.get('pad_stl'):
            shutil.copyfile(directory/row['pad_stl'], pad)
            anchors[name] = {**row['anchors'],'file': pad.name, 'stl_sha256': digest(pad),
                             'source': 'Removable anchors from the Micron cassette on this plate.'}
        elif pad.exists():
            pad.unlink()  # R47's export writer stages an older, differently shaped anchor.
    write(out/'anchors.json', {'parts': anchors})
    # The inherited writer stages these old end-gate cutaways first. Only the
    # Micron panel and its release pose are part of this revision's guide.
    for filename in ('battery-catch-door-released.stl','battery-catch-door.stl',
                     'battery-catch-holder.stl','battery-door-released.stl'):
        (out/'guide'/filename).unlink(missing_ok=True)
    views=receipt['review_assets']
    assets = {'cell':'battery-cell','positive':'battery-positive','negative':'battery-negative',
              'tab-pressed':'released_panel'}
    for name, target in assets.items():
        source=directory/views[target]['file']
        assert digest(source)==views[target]['sha256']
        shutil.copyfile(source, out/f'guide/micron-{name}.stl')
    geometry=read(out/'geometry-checks.json')
    geometry['checks']['battery_door']=checks
    write(out/'geometry-checks.json',geometry)
    return {'battery_manifest_sha256': digest(directory/'manifest.json'), 'cad_checks_sha256':receipt['checks_sha256'],
            'panel_removal_mm':layout['open_panel_displacement_mm'], 'cell_load_from_mm':layout['load_displacement_mm'],
            'cell_size_LWH_mm':layout['cell_dimensions_LWH_mm'], 'anchors':anchors,
            'panel_spring_mesh':'guide/micron-tab-pressed.stl'}



def compose(guide, report):
    modules=guide['modules']
    assembly=modules['battery']
    actors=assembly['actors']
    actors['cell'].update(label='Micron 72217 · 100 mAh cell', file='guide/micron-cell.stl')
    actors['door'].update(label='Patterned sliding lid', file=cad.PANEL+'-assembly.stl',
                          morphFile=report['panel_spring_mesh'])
    actors['holder'].update(label='Micron battery cradle',file=cad.BODY+'-assembly.stl')
    for name in ('positive','negative'):
        actors[name].update(label=name.capitalize()+' battery lead',file=f'guide/micron-{name}.stl')
    rod = np.asarray(assembly['steps'][-1]['samples'][-1]['rod']).reshape(3,4)[:,3]
    load, pull = np.asarray(report['cell_load_from_mm']), np.asarray(report['panel_removal_mm'])
    # Compute the inward motion needed for the detent to cam past the rail at
    # each position. Pulling the solid end of the lid supplies this deflection.
    tray,lid=cad.body(),cad.panel()
    @lru_cache(maxsize=17)
    def sprung(level):
        return lid if level==0 else lid.warp_batch(lambda v:v+cad.deflect(v,level/16))
    @lru_cache(maxsize=134)
    def displacement(fraction):
        offset=tuple(pull*fraction)
        def blocked(level):
            return (tray ^ sprung(level).translate(offset)).volume()>.00003
        if not blocked(0):
            return 0.
        assert not blocked(16)
        low,high=0,16
        while high-low>1:
            mid=(high+low)//2
            if blocked(mid):low=mid
            else:high=mid
        return high/16
    def sample(lift, withdraw, rod_offset):
        frame={k:translated(load*lift) for k in ('cell','positive','negative')}
        frame.update(holder=translated((0.,0.,0.)),door=translated(pull*withdraw),
                     rod=translated(rod*rod_offset),morphs={'door':displacement(round(float(withdraw),7))})
        return frame
    # State = cell lift, lid withdrawal, rod offset.
    instructions=[
        ('Remove the cradle’s print tabs', f"Snip the {report['anchors'][cad.BODY]['pad_count']} narrow ties at the base once cool. The lid enters the grooves from the open wire end.", (1,1,1)),
        ('Lower the cell into the cradle', 'Lay the cell onto the floor. Its two wires leave through the open end. Its fitted connector stays outside.', (0,1,1)),
        ('Slide the patterned lid into place', 'Guide both edges into the grooves. Push the solid end of the lid towards the far wall until the small catch slips into its pocket. Keep both wires between the shoulders at the open end.', (0,0,1)),
        ('Fit the holder onto the rod', 'Slide the two rings over the free end of the rod.', (0,0,0)),
        ('Slide the lid out', 'Hold the cradle and grip the solid end of the patterned lid. Pull the lid towards the wire end so the catch rides out of its pocket. Keep your grip clear of the wires.', (0,1,0)),
        ('Lift out the cell', 'Lift the cell straight out with both leads free.', (1,1,0))]
    steps=[]
    previous=np.array(instructions[0][2])
    for title,caption,end in instructions:
        end=np.array(end)
        sliding=end[1]!=previous[1]
        count=133 if sliding else 1 if np.array_equal(end,previous) else 19
        samples=[sample(*v) for v in np.linspace(previous,end,count)]
        if sliding:
            weights=[row['morphs']['door'] for row in samples]
            assert weights[0]==weights[-1]==0. and max(weights)>0.
        steps.append(dict(title=title,caption=caption,samples=samples,duration=4 if sliding else 3,reveal=True))
        previous=end
    assembly.update(label='Micron battery holder',frameEachStep=True,
                    note='The cradle takes one 100 mAh cell. The removable patterned lid slides in from the wire end.',
                    actors=actors,steps=steps)
    latch=modules['battery_latch']
    detail=[]
    for i in (2,4):
        source=steps[i]
        detail.append(dict(source,samples=[{name:row[name] for name in ('holder','door','morphs')}
                                          for row in source['samples']]))
    latch.update(label='Sliding lid and catch', note='The rounded catch flexes into the side of the cradle as the lid slides. Grip the solid end of the lid to pull it out.',
                 rotation=[.55,0.,-.3],actors={n:deepcopy(actors[n]) for n in ('holder','door')},steps=detail,
                 annotations=[dict(actor='door',title='Catch flexes as the lid slides',
                                   point=[cad.SLOT_X,-9.24,11.70],step=detail[0]['title'])])
    whole=modules['whole']
    for name,actor in actors.items():
        if name!='rod':
            key='battery_'+name
            whole['actors'][key]=deepcopy(actor)
            for step in whole['steps']:
                for frame in step['samples']:
                    frame[key]=list(frame['battery_holder'])
                    frame.get('morphs',{}).pop(key,None)
    guide['sources']['micron_battery']=report
    return len(steps)
