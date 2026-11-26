"""Compare R70's real deposited joints with fitted R69 and draw critical native layers.

Run after audit70: sections70.py SLICE_DIRECTORY. Nominal bead footprints measure
material and continuity, not breaking force, adhesion, sag or physical fit.
— GPT-6.1 Sol
"""
import argparse
import json
from pathlib import Path

import numpy as np
from shapely.geometry import box,Point
from shapely.ops import unary_union
from shapely import minimum_bounding_radius

import audit70 as a


def run(folder: Path) -> dict:
    """Record all parts, changed load paths and native visual witnesses. — GPT-6.1 Sol"""
    current=measure(folder, render=True)
    reference=measure(a.d.r69.OUT/'print-mechanisms')
    compared={name:dict(r69=reference['sections'][name],r70=row,
                       minimum_ratio=round(row['minimum_mm2']/reference['sections'][name]['minimum_mm2'],4))
              for name,row in current['sections'].items()}
    report=dict(archive_sha256=a.v.digest(folder/a.v.ARCHIVE),frame_sha256=a.v.digest(folder/'layout.frame.json'),
                checker_sha256=a.v.digest(__file__),parts=current['parts'],sections=compared,
                post_fit=dict(r69=reference['post_fit'],r70=current['post_fit']),
                post_neck_root=dict(r69=reference['post_neck_root'],r70=current['post_neck_root']),
                images=current.get('images'),physical_strength_and_fit_verified=False,
                method='Union of sampled native bead footprints without width inflation; complete layer slabs. Every 0.1 mm section on each stated interval. No force prediction.')
    report['passes']=bool(set(current['parts'])==kit_names() and all(
        3.04<rows[0]['smallest_enclosing_diameter_mm']<3.3 and rows[-1]['smallest_enclosing_diameter_mm']<3.05
        for rows in current['post_fit'].values()))
    (folder/'mechanical-sections.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['passes'],current['post_fit']
    return report


def kit_names() -> set:
    """The assembly inventory is owned by kit70, including the spare clip. — GPT-6.1 Sol"""
    return set(a.kit70.COMPLETE)


def measure(folder: Path, render: bool=False) -> dict:
    """Work through each archive independently to avoid retaining both point clouds. — GPT-6.1 Sol"""
    points,_=a.v.read_native(folder/a.v.ARCHIVE)
    frames=a.v.read(folder/'layout.frame.json')['parts']
    regions={
        'left_paddle_joint':('Touch_Paddle',27.9,33.0,(-10.8,10.0,-2.9,20.0)),
        'right_paddle_joint':('Touch_Paddle',27.9,33.0,(2.9,10.0,10.8,20.0)),
        'right_guard_root':('Key_Carrier',19.2,22.4,(12.5,5.8,14.2,11.2)),
        'left_guard_root':('Key_Carrier',19.2,22.4,(-14.2,5.8,-12.5,11.2)),
    }
    fitted = frames['Key_Carrier']['source_sha256'] == a.d.R69_SHA256
    shift = 0. if fitted else -a.d.KEY_SHIFT
    regions['aligned_right_latch_path'] = ('Key_Carrier',22.+shift,25.15+shift,(12.5,5.8,14.2,11.2))
    measured={}
    for name,(part,start,end,bounds) in regions.items():
        frame=np.asarray(frames[part]['assembly_to_machine'])
        rows=[]
        for y in np.arange(start,end+.001,.1):
            section=section_y(points,frame,float(y),bounds).intersection(box(*bounds))
            rows.append(dict(y_mm=round(float(y),3),area_mm2=round(section.area,4),pieces=len(getattr(section,'geoms',[section]))))
        assert all(row['area_mm2']>.1 for row in rows),(name,rows)
        measured[name]=dict(minimum_mm2=min(row['area_mm2'] for row in rows),bounds_xz_mm=bounds,rows=rows)
    post_frame=np.asarray(frames['DFR_Post_Bar']['assembly_to_machine'])
    result=dict(sections=measured,parts={n:dict(source_sha256=r['source_sha256'],pose=r['assembly_to_machine']) for n,r in frames.items()},
                post_fit={side:post_sections(points,post_frame,sign*a.b.HOLE_X) for side,sign in (('left',-1),('right',1))},
                post_neck_root={side:post_sections(points,post_frame,sign*a.b.HOLE_X,
                    planes=(a.b.PLATE_Z+.1,a.b.BOARD_TOP+.1,a.b.BOARD_TOP+a.hinge70.m.NECK-.1))
                    for side,sign in (('left',-1),('right',1))})
    if render:
        path=draw_layers(folder,points,frames)
        result['images']={path.name:a.v.digest(path)}
    return result


def post_sections(points: np.ndarray, frame: np.ndarray, x: float, planes=None) -> list:
    """Measure the smallest hole enclosing actual post bead outlines inside the PCB.

    Horizontal post prints use complete layer slabs; upright prints use nominal
    XY bead footprints at the selected interior planes. These are deposited-path
    measurements, not physical force or a measurement of the real board holes.
    — GPT-6.1 Sol
    """
    inv=np.linalg.inv(frame);axis=int(np.argmax(abs(frame[:3,2])))
    rows=[]
    for z in planes or (a.b.SEAT_Z+.10,(a.b.SEAT_Z+a.b.BOARD_TOP)/2,a.b.BOARD_TOP-.10):
        centre=(frame@[0,0,z,1])[axis]
        mask=((points[:,2]>=centre)&(points[:,2]-points[:,4]<centre) if axis==2
              else abs(points[:,axis]-centre)<points[:,3]/2)
        q=points[mask];local=q[:,:3]@inv[:3,:3].T+inv[:3,3]
        # Installed posts are inside +/-1.33 X and +1.47 Y in the paddle.
        # Nearby small-part pad beads are disposable, not part of the shaft.
        # Keep every post centreline (with extra room) while excluding that pad.
        keep=(abs(local[:,0]-x)<1.45)&(abs(local[:,1]-a.b.HOLE_Y)<1.6)
        q,local=q[keep],local[keep];assert len(q)>25,(x,z,len(q))
        if axis==2:
            shape=unary_union([Point(float(px),float(py)).buffer(float(w/2),resolution=16) for px,py,w in zip(local[:,0],local[:,1],q[:,3])])
        else:
            half=np.sqrt(np.maximum(0,(q[:,3]/2)**2-(q[:,axis]-centre)**2))
            opposite=local[:,1]-inv[1,2]*q[:,4]
            shape=unary_union([box(float(px-w),float(min(py,t)),float(px+w),float(max(py,t))) for px,py,t,w in zip(local[:,0],local[:,1],opposite,half) if w>1e-7])
        diameter=2*float(minimum_bounding_radius(shape))
        rows.append(dict(board_plane_z_mm=round(z,3),smallest_enclosing_diameter_mm=round(diameter,4),
                         nominal_3mm_hole_interference_on_diameter_mm=round(diameter-3.,4),
                         nominal_3_2mm_hole_clearance_on_diameter_mm=round(3.2-diameter,4),
                         deposited_section_area_mm2=round(shape.area,4)))
    return rows


def section_y(points: np.ndarray, frame: np.ndarray, y: float, bounds: tuple):
    """Cut nominal bead envelopes normal to assembly Y, in assembly X/Z. — GPT-6.1 Sol"""
    inv=np.linalg.inv(frame)
    axis=int(np.argmax(abs(frame[:3,1])))
    assert abs(frame[axis,1])>.999
    centre=(frame@[0,y,0,1])[axis]
    if axis==2:
        # Standing carrier: an assembly-Y cut is a horizontal printed-layer
        # footprint, rather than a vertical slab through a flat printed paddle.
        # Found and fixed by GPT-6.1 Sol.
        q=points[(points[:,2]>=centre)&(points[:,2]-points[:,4]<=centre)]
        local=q[:,:3]@inv[:3,:3].T+inv[:3,3];radius=q[:,3]/2
        keep=(local[:,0]+radius>bounds[0])&(local[:,0]-radius<bounds[2])&(local[:,2]+radius>bounds[1])&(local[:,2]-radius<bounds[3])
        return unary_union([Point(float(x),float(z)).buffer(float(r),resolution=12) for x,z,r in zip(local[keep,0],local[keep,2],radius[keep])])
    assert abs(inv[2,2])>.999
    take=abs(points[:,axis]-centre)<points[:,3]/2
    q=points[take]
    local=q[:,:3]@inv[:3,:3].T+inv[:3,3]
    half=np.sqrt(np.maximum(0,(q[:,3]/2)**2-(q[:,axis]-centre)**2))
    other=local[:,2]-inv[2,2]*q[:,4]
    return unary_union([box(float(x-w),float(min(z,t)),float(x+w),float(max(z,t)))
                        for x,z,t,w in zip(local[:,0],local[:,2],other,half) if w>1e-7])


def draw_layers(folder: Path, points: np.ndarray, frames: dict) -> Path:
    """Show first layers, key roofs, the post ribs and both paddle roots. — GPT-6.1 Sol"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import EllipseCollection
    fig,axes=plt.subplots(4,3,figsize=(14,15),layout='constrained')
    probes=[('Key_Carrier',[0,a.d.BED,6],[39,18]),
            ('Key_Carrier',[-21,12.7,10.3],[10,4]),
            ('Touch_Paddle',[0,31.8,16.0],[10,8]),
            ('DFR_Post_Bar',[a.b.HOLE_X,a.b.HOLE_Y,a.b.SEAT_Z+.3],[4,4])]
    for row,(part,point,span) in enumerate(probes):
        frame=np.asarray(frames[part]['assembly_to_machine']); centre=frame@[*point,1]
        base=max(.2,float(np.ceil((centre[2]-.001)/.2)*.2))
        for col,top in enumerate(base+np.array([0,.2,.4])):
            ax=axes[row,col]
            for offset,color in ((-.2,'#777b83'),(0,'#df7865')):
                mask=(abs(points[:,2]-top-offset)<.01)&(abs(points[:,0]-centre[0])<span[0])&(abs(points[:,1]-centre[1])<span[1])
                q=points[mask]
                if offset==0:
                    assert len(q)>0,(part,top,offset)
                ax.add_collection(EllipseCollection(q[:,3],q[:,3],np.zeros(len(q)),units='xy',offsets=q[:,:2]-centre[:2],transOffset=ax.transData,facecolors=color,edgecolors='none',alpha=.8))
            ax.set(xlim=(-span[0],span[0]),ylim=(-span[1],span[1]),aspect='equal',title=f'{part}: layer top {top:.2f} mm')
    fig.suptitle('Actual native bead widths: current coral, previous grey. Physical bonding and sag untested.')
    path=folder/'critical-native-layers.png';fig.savefig(path,dpi=140);plt.close(fig)
    return path


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path)
    report=run(parser.parse_args().folder)
    print(json.dumps({name:row['minimum_ratio'] for name,row in report['sections'].items()}),flush=True)
