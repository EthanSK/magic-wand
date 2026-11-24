"""Compare the printed D-flat shafts directly with the printed hinge passage.

Each extruded segment projects to an interval across the pin axis and a slab
through the complete printed layer. Work in each part's actual print frame,
then compare in common assembly YZ. This keeps the flat and the independent
layer staircases of the two bores. Fitting a single circle to the pin loses both.
"""
from collections import defaultdict
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import sys
from xml.etree.ElementTree import fromstring
from zipfile import ZipFile

import numpy as np

import hinge64 as h
from openings53 import paths as native
from verify59 import ARCHIVE


NAMES = ('Hinge_Pin','Hinge_Pin_Snug','Touch_Paddle','Key_Carrier')
ARC_ERROR = .002


def intervals(pieces):
    merged = []
    for lo, hi in sorted(pieces):
        if merged and lo <= merged[-1][1] + 1e-7:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo,hi])
    return merged


def sample_chords(start, end, words, cmd):
    if cmd not in ('G2','G3'):
        return [(start,end)],0.
    centre,r,angle,sweep = native._arc(np.array(start),np.array(end),words,cmd=='G2')
    steps = max(1,math.ceil(abs(sweep)/(2*math.acos(max(-1.,1.-ARC_ERROR/r)))))
    angles = angle+sweep*np.linspace(0,1,steps+1)
    nodes = np.column_stack((centre[0]+r*np.cos(angles),centre[1]+r*np.sin(angles),np.linspace(start[2],end[2],steps+1)))
    return zip(nodes,nodes[1:]),ARC_ERROR


def interval_for_segment(a,b,axis,cross,axial,allowed,outer):
    # Clip by the axial slab plus bead radius. Expanding the retained lateral
    # extremes by the full radius is conservative at both axial boundaries.
    low,high=axial[0]-outer,axial[1]+outer
    first,last=a[axis],b[axis]
    if min(first,last)>high or max(first,last)<low:
        return None
    if abs(last-first)>1e-10:
        t0,t1=sorted(((low-first)/(last-first),(high-first)/(last-first)))
        t0,t1=max(0.,t0),min(1.,t1)
    else:
        t0,t1=0.,1.
    u,v=a[cross],b[cross]-a[cross]
    lo,hi=sorted((u+t0*v,u+t1*v))
    lo,hi=max(allowed[0],lo-outer),min(allowed[1],hi+outer)
    return (lo,hi) if hi>=lo else None


def profile_rows(folder):
    layout_bytes=(folder/'layout.frame.json').read_bytes()
    frames=json.loads(layout_bytes)['parts']
    archive=(folder/ARCHIVE).read_bytes()
    target={}
    with ZipFile(BytesIO(archive)) as data:
        root=fromstring(data.read('Metadata/model_settings.config'))
        tags=lambda n:{v.get('key'):v.get('value') for v in n.findall('metadata')}
        names={o.get('id'):tags(o).get('name') for o in root.findall('object')}
        for entry in root.find('plate').findall('model_instance'):
            item=tags(entry);name=names[item['object_id']]
            if name in NAMES:
                target[int(item['identify_id'])]=name
        assert set(target.values())==set(NAMES)
        settings=json.loads(data.read('Metadata/project_settings.config'))
        off=np.fromstring(settings['extruder_offset'][0],sep='x')
        assert np.allclose(off,[0,0]),off
        windows={}
        for name in NAMES:
            frame=np.asarray(frames[name]['assembly_to_machine'])
            pin=name.startswith('Hinge_Pin')
            # R58 prints the snug shaft 0.10 mm higher in its assembly source.
            centre=frame @ ([0,h.r61.AXIS,h.m.PIN_Z+(.1 if name=='Hinge_Pin_Snug' else 0),1] if pin else [0,h.AXIS,h.KEEPER_Z,1])
            axis=int(np.argmax(abs(frame[:2,0])))
            cross=1-axis
            length=h.m.PIN_HALF if pin else 34.
            span = 2.1 if pin else 3.6
            windows[name]=(axis,cross,(centre[axis]-length,centre[axis]+length),(centre[cross]-span,centre[cross]+span),centre,frame)
        # Only allocate projected intervals for the four fitted pieces. Track
        # positioning and extrusion mode over the complete original G-code.
        pin_windows=(9., h.m.PIN_HALF-.50)
        rows={n:defaultdict(list) for n in NAMES}
        for name in NAMES[:2]:
            rows.update({(name,w):defaultdict(list) for w in pin_windows})
        feature=''; marked=None; pos=(0.,0.,0.); last_e=0.; relative_e=True; relative_xyz=False; width=.42; height=.2
        for raw in BytesIO(data.read('Metadata/plate_1.gcode')):
            if raw.startswith(b';'):
                if raw.startswith(b'; FEATURE:'):feature=raw[10:].strip().decode()
                elif raw.startswith(b'; LINE_WIDTH:'):width=float(raw.partition(b':')[2])
                elif raw.startswith(b'; LAYER_HEIGHT:'):height=float(raw.partition(b':')[2])
                elif raw.startswith(b'; start printing object, unique label id:'):marked=target.get(int(raw.rsplit(b':',1)[1]))
                elif raw.startswith(b'; stop printing object, unique label id:'):marked=None
                continue
            line=raw.partition(b';')[0].decode().split()
            if not line:continue
            cmd=line[0]
            if cmd=='M82':relative_e=False
            elif cmd=='M83':relative_e=True
            elif cmd=='G90':relative_xyz=False
            elif cmd=='G91':relative_xyz=True
            if cmd not in ('G0','G1','G2','G3','G92'):continue
            words={s[0]:float(s[1:]) for s in line[1:] if len(s)>1 and s[0] in 'XYZEIJR'}
            if cmd=='G92':
                last_e=words.get('E',last_e)
                pos=tuple(words.get(key,pos[i]) for i,key in enumerate('XYZ'))
                continue
            start=pos
            pos=tuple(start[i]+words.get(k,0.) if relative_xyz else words.get(k,start[i]) for i,k in enumerate('XYZ'))
            e=words.get('E',0.) if relative_e else words.get('E',last_e)-last_e
            if not relative_e:last_e=words.get('E',last_e)
            if not marked or e<=0 or feature in ('','Custom','Flush') or start==pos:continue
            axis,cross,axial,allowed,centre,_=windows[marked]
            if abs(pos[2]-centre[2])>4.4:continue
            assert abs(start[2]-pos[2])<1e-6,(marked,cmd,start,pos)
            chords,error=sample_chords(start,pos,words,cmd)
            for a,b in chords:
                pair=interval_for_segment(a,b,axis,cross,axial,allowed,width/2+error)
                if pair is not None:
                    layer=(pos[2]-height,pos[2])
                    rows[marked][layer].append(pair)
                    if marked.startswith('Hinge_Pin'):
                        for w in pin_windows:
                            inner=(centre[axis]-w,centre[axis]+w)
                            sub=interval_for_segment(a,b,axis,cross,inner,allowed,width/2+error)
                            if sub is not None:rows[(marked,w)][layer].append(sub)
    # Convert each merged machine-layer slab to an axis-aligned rectangle
    # relative to its own (corrected) assembly pin axis.
    result={}
    for name,layers in rows.items():
        _,c,_,_,centre,frame=windows[name if isinstance(name,str) else name[0]]
        rectangles=[]
        for (bottom,top),pieces in layers.items():
            for low,high in intervals(pieces):
                hc=np.array([low-centre[c],high-centre[c]])
                z=np.array([bottom-centre[2],top-centre[2]])
                yb=np.sort(frame[c,1]*hc+frame[2,1]*z)
                zb=np.sort(frame[c,2]*hc+frame[2,2]*z)
                rectangles.append([yb[0],yb[1],zb[0],zb[1]])
        result[name]=np.array(rectangles)
        assert len(rectangles)>8,(name,len(rectangles))
    identity=dict(archive_sha256=sha256(archive).hexdigest(),layout_sha256=sha256(layout_bytes).hexdigest(),
                  source_sha256={n:frames[n]['source_sha256'] for n in NAMES},
                  tab_width_mm={n:frames[n]['adhesion_panel']['tie_width'] for n in NAMES[:2]})
    return result,identity


def clearance_map(pin,parts,ys,zs):
    # The complete projected shaft travels through each axial station.
    # Keeping the complete union for each owner bounds the whole insertion.
    space={}
    for owner,wall in parts.items():
        box=pin[:,None,:]
        left=wall[:,0]-box[:,:,1];right=box[:,:,0]-wall[:,1]
        below=wall[:,2]-box[:,:,3];above=box[:,:,2]-wall[:,3]
        values=[]
        for y in ys:
            dy=np.maximum(left-y,right+y)
            for z in zs:
                dz=np.maximum(below-z,above+z)
                # Euclidean gap for disjoint boxes; least penetration depth
                # for intersecting boxes lets us identify an obstructed fit.
                delta=np.hypot(dy.clip(0),dz.clip(0))+np.minimum(np.maximum(dy,dz),0)
                values.append(float(delta.min()))
        space[owner]=np.array(values)
    return space


def check(folder):
    """Inspect one original or reopened native slice and return hash-bound evidence."""
    rows,identity=profile_rows(Path(folder))
    walls={n:rows[n] for n in ('Touch_Paddle','Key_Carrier')}
    steps=np.linspace(-.18,.18,37)
    result={}
    for name in ('Hinge_Pin','Hinge_Pin_Snug'):
        spans=(('bearing_portions',9.),('through_start_of_taper',h.m.PIN_HALF-.50),('through_nominal_tips',h.m.PIN_HALF))
        regions={}
        for region,half_length in spans:
            # The first two checks distinguish the working round body from any
            # disposable stock in the end tapers. The full check keeps ALL printed
            # material within the original shaft length, including the flat tie stubs.
            profile=rows[name] if region=='through_nominal_tips' else rows[(name,half_length)]
            nominal=clearance_map(profile,walls,[0.],[0.])
            regions[region]=dict(axial_range_mm=[-half_length,half_length],
                clearance_at_nominal_line_mm=round(min(s[0] for s in nominal.values()),4),
                owner_clearances_at_nominal_line_mm={n:round(s[0],4) for n,s in nominal.items()})
        pin=rows[name]
        clear=clearance_map(pin,walls,steps,steps)
        both=np.minimum(*clear.values())
        i=int(np.argmax(both))
        y,z=steps[i//len(steps)],steps[i%len(steps)]
        result[name]=dict(stations=regions,
            best_tested_whole_pin_clearance_mm=round(both[i],4),
            best_tested_whole_pin_axis_yz_mm=np.round([h.AXIS+y,h.KEEPER_Z+z],3).tolist(),
            shaft_bounds_yz_mm=np.round([pin[:,0].min(),pin[:,1].max(),pin[:,2].min(),pin[:,3].max()],3).tolist())
    std,snug=(result[n]['stations']['through_nominal_tips']['clearance_at_nominal_line_mm'] for n in NAMES[:2])
    return dict(**identity,pose='Flat on the pin faces down in the assembled carrier; the same straight line passes through both cheeks and the barrel.',
                nominal_axis_yz_mm=[h.AXIS,h.KEEPER_Z],arc_chord_error_bound_mm=ARC_ERROR,axis_grid_step_mm=.01,
                removal='Cut both disposable pad ties flush with the nominal pin ends. Through-nominal-tips includes all first-layer stubs within those ends.',
                method='All positive model extrusion widths and full layer slabs for the four named parts. Project the complete selected shaft and bore-owner material across the insertion direction. Positive distances are conservative one-sided gaps. Each circular G-code chord is expanded by its sag bound.',
                physical_fit_verified=False,parts=result,
                passes=bool(std>snug>0))


if __name__=='__main__':
    report=check(Path(sys.argv[1]))
    print(json.dumps(report,indent=2))
    if not report['passes']:
        raise SystemExit('As-sliced pin with both tip remnants must clear at the nominal axis.')
