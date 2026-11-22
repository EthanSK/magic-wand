"""Check physical extrusion paths, using the established kit gauges and base witnesses."""
import argparse
import json
from pathlib import Path

import numpy as np
from design60 import BOTTOM, BED, INNER, OUT, OUTER, PREVIOUS, START, THICK, WIDTH, b, old, pouch
from plate60 import LABELS, MINIMA, parts
import verify59 as v


def gauges():
    geometry = v.gauges(v.read(PREVIOUS / 'exports/carrier.json'))
    holder = geometry['Key_Carrier']
    for name in ('right_guard_slides_onto_its_rails', 'left_guard_slides_onto_its_rails'):
        del holder[name]
    # The bought pack deflects a single compliant wall; its opposite wall, floor,
    # roof and loading path are rigid. Gauge the full pack minus the side shoe's
    # fixed working strip at every position, not the whole battery bay minus the wall.
    pack = pouch()
    bounds = pack.bounding_box()
    free_core = b.box(bounds[0]+.25,bounds[3]-.03,bounds[1],bounds[4],bounds[2]+.03,bounds[5]-.03)
    # A 0.40 mm swept window behind the leaf must print clear, including
    # where it runs alongside the upper rail. Also scan its gap to the floor.
    holder['side_leaf_can_flex']=[b.box(OUTER-2.33,OUTER-1.93,21.5,BED-5.9,BOTTOM+.66,BOTTOM+THICK-.65)]
    holder['leaf_is_free_of_floor']=[b.box(OUTER-1.54,OUTER-.9,START+2.7,BED-5.9,BOTTOM+.10,BOTTOM+.30)]
    holder['battery_seated']=[free_core]
    holder['battery_slides_in_from_the_rear']=[free_core.translate((0,float(t),0)) for t in np.arange(0,31)]
    for side, sign in [('Left',-1),('Right',1)]:
        tool=b.load(old.R58/'exports'/f'Socket_Backer_{side}-assembly.stl')
        holder['backing_strip_'+side]=[tool.translate((sign*float(dx),0,0)) for dx in np.arange(0,27)]
    return geometry


def spring_opening(points, position):
    """Measure opposing deposited surfaces halfway up the pack at its contact pad."""
    assert np.allclose(position[:3,:3],[[1,0,0],[0,0,1],[0,-1,0]])
    x0,y0,z0=position[:3,3]
    probe_y=y0+BOTTOM+THICK/2
    center=points[(points[:,0]>x0+OUTER-3) & (points[:,0]<x0+INNER+3)
                  & (abs(points[:,1]-probe_y)<points[:,3]/2)]
    rows=[]
    for depth in (START+6,START+7,START+8):
        line=center[abs(z0-center[:,2]-depth)<.11]
        dx=np.sqrt(np.maximum(0,(line[:,3]/2)**2-(line[:,1]-probe_y)**2))
        on_spring=line[:,0]<x0+(OUTER+INNER)/2
        assert on_spring.any() and (~on_spring).any()
        opening=float((line[~on_spring,0]-dx[~on_spring]).min()-(line[on_spring,0]+dx[on_spring]).max())
        rows.append(dict(depth_mm=round(depth,2), opening_mm=round(opening,3),
                         nominal_pack_interference_mm=round(WIDTH-opening,3)))
    assert all(0<r['nominal_pack_interference_mm']<.35 for r in rows),rows
    return rows


def audit(folder):
    archive=folder/v.ARCHIVE
    frame=v.read(folder/'layout.frame.json')
    sha=v.digest(archive)
    native=v.read(folder/'OP1-hinge.gcode.native.json')
    assert native['return_code']==0 and native['archive_sha256']==sha and len(native['plates'])==1
    assert 'got warnings:' not in (folder/'native/slice.log').read_text()
    assert frame['layout_sha256']==v.digest(folder/'layout.3mf') and set(frame['parts'])==set(LABELS)
    for row in parts():
        assert v.digest(row['source'])==frame['parts'][row['name']]['source_sha256']
    v.audit(archive,folder/'layout.3mf',folder/'separation-and-machine.json',set(LABELS))
    adhesion=v.bases(archive)
    v.verify(adhesion,minimum_base_mm2=MINIMA)
    v.write(folder/'wide-bases.json',adhesion)
    points,labels=v.read_native(archive)
    fit={part:v.check_routes(routes,np.asarray(frame['parts'][part]['assembly_to_machine']),points,labels)
         for part,routes in gauges().items()}
    # A successful insertion route can be entirely empty, even in the 1 mm
    # search envelope. Prove placement by lowering the same fitted strip
    # into the printed fingertip beams and requiring actual interference.
    controls = {side:[b.load(old.R58/'exports'/f'Socket_Backer_{side}-assembly.stl').translate((0,0,-3.5))]
                for side in ('Left','Right')}
    witnesses = v.check_routes(controls,np.asarray(frame['parts']['Key_Carrier']['assembly_to_machine']),points,labels)
    assert all(row['obstructed_poses'] for row in witnesses.values()),witnesses
    v.write(folder/'fit.json',dict(archive_sha256=sha,frame_sha256=v.digest(folder/'layout.frame.json'),
                                   parts=fit,lowered_backer_positive_controls=witnesses,
                                   side_spring_midheight=spring_opening(points,np.asarray(frame['parts']['Key_Carrier']['assembly_to_machine']))))
    blocked=[(part,name,row['obstructed_poses']) for part,rows in fit.items() for name,row in rows.items() if row['obstructed_poses']]
    near=[fit['Key_Carrier'][k]['nearby_samples'] for k in ('battery_seated','side_leaf_can_flex','leaf_is_free_of_floor','pin_go_gauge_through_left_cheek','pin_go_gauge_through_right_cheek')]
    assert min(near)>25,near
    layers=v.inspect(archive)
    v.write(folder/'layers.json',layers)
    starts={p:r['completely_unsupported_starts'] for p,r in layers['parts'].items() if r['completely_unsupported_starts']}
    carrier=frame['parts']['Key_Carrier']
    body=v.load_solid(OUT/carrier['source'])
    position=np.asarray(carrier['assembly_to_machine'])
    oriented=position[:3].copy()
    oriented[:2,3]=0
    panel=carrier['adhesion_panel']
    bed=body.transform(oriented)
    base,_,_=v.base54(bed,v.settings(panel))
    placed=base.translate((*position[:2,3],0))
    joint=v.seam(archive,frame,body,regions={'hinge_bay':v.BAY},regional_base=placed)
    v.write(folder/'joint.json',dict(archive_sha256=sha,current=joint))
    fin=v.report55(bed,panel)
    v.write(folder/'fin-design.json',dict(archive_sha256=sha,**fin))
    v.write(folder/'rod.json',v.rod_bore(archive,position))
    area=joint['vertical_joint_area_mm2']
    print(json.dumps(dict(blocked=blocked, unsupported_starts=starts, seam=area,
         hinge_bay=joint['regional_joint_area_mm2'], warnings=native['plates'][0]['warning_message'])),flush=True)
    ref=v.read(v.R57_LAYOUT/'joint.json')['current']['vertical_joint_area_mm2']
    assert not blocked and not starts and not layers['native_support_moves']
    assert .80*ref<=area<=ref and joint['regional_joint_area_mm2']['hinge_bay']<.25
    assert fin['hinge_bay_open_to_panel_edge'] and fin['fins_on_hinge']==0 and fin['nearest_base_to_hinge_mm']>=3
    assert len(fin['fins'])==6 and fin['panel_pieces']==1

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('folder',type=Path)
    audit(parser.parse_args().folder)
