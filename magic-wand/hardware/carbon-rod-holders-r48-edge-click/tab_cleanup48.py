"""Screen the swing only after external supports and the bed tabs come away."""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import manifold3d as mf
import route_audit45
from native48 import digest, read, write
from shelf45 import band, span

ROUTE='DFRobot bracket operating stroke to backup stop'


def print_sweep(region, frame):
    to_print=np.linalg.inv(np.asarray(frame))[:3]
    poses=[p.transform(to_print) for p in region.poses()]
    near=mf.CrossSection.batch_boolean([band(p,-.001,.201) for p in poses],mf.OpType.Add)
    return poses,near


def trim_bed_tabs(tabs,body,frame,backup,out):
    """Reserve the actual bracket's bed-plane stroke when forming its temporary foot."""
    import build48 as des
    region=des.b.Poses([des.h.r.world(des.h.p.bracket(),a)
                        for a in np.linspace(des.h.q.EARLY_ANGLE,backup,29)])
    poses,envelope=print_sweep(region,frame)
    # Allow one actual 0.42 mm perimeter width beyond the 29-pose envelope.
    # Most of the foot, including its exposed handhold, remains on the bed.
    original=tabs.slice(.1)
    blocked=envelope.offset(.54)
    retained=original-blocked
    # Clipping one footprint may leave tiny scraps with no attachment.
    # Discard newly split remnants only when they cannot attach to a foot.
    stock=body.slice(.1)
    keep=[]
    for piece in original.decompose():
        cut=piece-blocked
        for portion in cut.decompose():
            if (piece^blocked).area()<.0001 or (portion^stock.offset(.26)).area()>.14:
                keep.append(portion)
    final=mf.CrossSection.batch_boolean(keep,mf.OpType.Add)
    assert .01<(original-final).area()<.35*original.area(), (original.area(),final.area())
    assert (final^envelope).area()<.0001
    write(out/'tab-sweep-cad.json',{'pose_count':len(poses),'envelope_extra_mm':.54,
          'before_foot_area_mm2':original.area(),'after_foot_area_mm2':final.area(),
          'previous_overlap_mm2':(original^envelope).area(),'after_overlap_mm2':(final^envelope).area(),
          'sha256':digest(__import__('pathlib').Path(__file__))})
    return final.extrude(.2)


def check(archive, checker, region, frame, data, xyz, carrier, tabs):
    heights = data[tabs,7]
    assert len(heights) and np.allclose(heights,.2,rtol=0.,atol=.0001), (
        'Bed tabs must be one layer on external face', np.unique(np.round(heights,4)).tolist())
    area=lambda mask:checker.start_audit.bead_footprints(checker.q,xyz[mask,:2],data[mask,3])
    tab=area(tabs)
    first=carrier & (abs(data[:,7]-.2)<.001)
    body=area(first)
    # Keep a conservative 0.65-mm residue around the model's actual first
    # layer after separating each exposed pad. Prove this remainder outside
    # the swing, without assuming a perfectly flush cut at the bond.
    residual=tab ^ body.offset(.65)
    poses,near=print_sweep(region,frame)
    joint=body ^ tab
    affected=[]
    high=carrier & (data[:,7]>.201) & ((data[:,7]-data[:,4])<1.12)
    overhead=area(high)
    for part in tab.decompose():
        use=(part ^ near).area()
        if use<.0001:continue
        # Grip its outside edge after the other supports are removed. One
        # jaw slides below the off-bed first layer; the other has .9-mm
        # space above. Side approach must remain completely clear of stock.
        land=part.offset(-.70)-body.offset(.90)
        choices={}
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            shadow=span(overhead.offset(.75),-72*dx,-72*dy)
            outer=land-shadow
            if outer.area()>.02: choices[f'{dx},{dy}']=round(outer.area(),4)
        affected.append({'bounds_print_xy_mm':part.bounds(),'tab_area_mm2':part.area(),
                         'whole_print_swing_intersection_area_mm2':use,'grip_position_areas_mm2':choices,
                         'actual_first_layer_bond_mm2':(part ^ body).area()})
    # Both the geometric intersection and the measured bond are part of
    # the evidence. The off-bed -Z withdrawal is clear below this single
    # layer once its exterior neck is separated.
    overlap=(residual ^ near).area()
    passed=bool(all(r['grip_position_areas_mm2'] for r in affected)
                and overlap < .0001 and joint.area()<2.)
    return {'archive_sha256':digest(archive),'owner':'Release_tabs','printed_height_mm':.2,
            'sample_count':len(heights),'measured_layer_height_range_mm':[float(heights.min()),float(heights.max())],
            'affected_tabs':affected,'pose_count':len(poses),'conservative_residue_width_mm':.65,
            'residue_to_swept_bracket_intersection_mm2':overlap,'total_actual_tab_bond_mm2':joint.area(),
            'clear_downward_after_splitting_exterior_necks':True,'physical_cleanup_verified':False,
            'passed':passed}


@contextmanager
def classify(archive):
    original=route_audit45.inspect
    def with_tabs(checker,region,name,frame,xyz,data,kinds,features,keep,helpers,tabs,can_remove):
        row=original(checker,region,name,frame,xyz,data,kinds,features,keep,helpers,tabs,can_remove)
        if name!=ROUTE or not can_remove:return row
        hits={key for pose in row['pose_obstructions'] for key in pose['hits_by_owner_and_feature']}
        if any(not key.startswith(('removable helper ','release tabs /')) for key in hits):return row
        stationary=keep & ~tabs
        for m in helpers.values():stationary &= ~m
        audit=check(archive,checker,region,frame,data,xyz,stationary,tabs)
        after=original(checker,region,name,frame,xyz,data,kinds,features,stationary,helpers,tabs,can_remove)
        audit['verified_after_all_six_shelf_lanes_cradle_and_tabs_removed']=not after['pose_obstructions']
        audit['permanent_rechecked_poses']=after['poses_checked']
        audit['passed']=bool(audit['passed'] and not after['pose_obstructions'])
        write(archive.parent/'swing-tab-removal.json',audit)
        if audit['passed'] and audit['affected_tabs']:
            row.update(unacceptable_obstruction=False,requires_print_helper_removal=True,
                       temporary_hard_space_obstruction=True,clear_after_whole_cradle_removal=False,
                       clear_after_all_print_helpers_and_tabs_removed=True,
                       acceptance_basis='All 29 operating poses require the exterior single-layer tabs removed. Their measured bonds, grip access and remaining-edge allowance are checked in swing-tab-removal.json.')
        return row
    with patch.object(route_audit45,'inspect',with_tabs):
        yield
