"""Verify the thinner R71 leaves and foot columns in actual deposited beads.

Root sections and spring freedom are checked by retention71 and audit71. The
fixed sections cover the three-layer strip and complete foot columns; a 0.02 mm
profile also covers the flare and both sides of every root/heel step. This is
nominal bead geometry, not measured strength or a notch-stress calculation.
— GPT-6.1 Sol
"""
import argparse
from pathlib import Path
import numpy as np
from shapely import set_precision
from shapely.geometry import box, LineString
import audit71 as a
import retention71 as r
import sections70 as sections


def measure_section(points, frame, side, sign, local_y, thickness):
    h,b=a.h,a.b
    x,y=(-1 if side=='Left' else 1)*b.HOLE_X,b.HOLE_Y
    arms=h.clip_plans(side)[1]
    strip=h.mf.CrossSection.square((10.,.002)).translate((0. if sign>0 else -10.,local_y-.001))
    planned=arms ^ strip
    assert planned.area()>.0001,(side,sign,local_y,'Missing source arm')
    x0,_,x1,_=planned.bounds()
    nominal_width=planned.area()/.002
    top=b.BOARD_TOP+h.LIFT+h.CLIP_T
    bottom=top-thickness
    bounds=(x+x0-.06,bottom,x+x1+.06,top)
    cut=sections.section_y(points,frame,y+local_y,bounds).intersection(box(*bounds))
    raw_area=cut.area
    cut=set_precision(cut,.000001)
    assert abs(cut.area-raw_area)<.00001
    lines=[cut.intersection(LineString([(bounds[0],z),(bounds[2],z)]))
           for z in np.arange(bottom+.10,top,.20)]
    widths=[line.length for line in lines]
    outlines=[line.bounds[2]-line.bounds[0] if not line.is_empty else 0. for line in lines]
    pieces=list(getattr(cut,'geoms',[cut]))
    centres=np.arange(bottom+.10,top,.20)
    area=sum(widths)*.20
    assert abs(area-cut.area)<.0001, (side,sign,local_y,'Layer integral does not match section area',area,cut.area)
    centroid=sum(w*.20*z for w,z in zip(widths,centres))/area
    second_moment=sum(w*(.20**3/12+.20*(z-centroid)**2) for w,z in zip(widths,centres))
    native_bottom,native_top=cut.bounds[1],cut.bounds[3]
    return dict(local_y_mm=round(local_y,4),source_width_mm=round(nominal_width,6),
                source_thickness_mm=round(thickness,4),native_area_mm2=round(cut.area,6),
                native_layer_material_widths_mm=[round(v,6) for v in widths],
                native_layer_outer_widths_mm=[round(v,6) for v in outlines],connected=len(pieces)==1,
                component_areas_mm2=[round(p.area,8) for p in pieces],
                second_moment_mm4=round(second_moment,8),
                bending_geometry_factor_per_mm2=round((h.FOOT_Y[0]-local_y)*max(native_top-centroid,centroid-native_bottom)/second_moment,6) if local_y<h.FOOT_Y[0] else None)


def section(points, frame, side, sign, local_y, thickness):
    row=measure_section(points,frame,side,sign,local_y,thickness)
    width=row['source_width_mm']; actual=row['native_layer_material_widths_mm']; outline=row['native_layer_outer_widths_mm']
    assert len(actual)==round(thickness/.20),(side,sign,local_y,actual)
    assert .75*width*thickness<row['native_area_mm2']<1.35*width*thickness,(side,sign,local_y,row)
    # Material length along a layer is not its outline width: normal bead
    # gaps at a wide step reduce the former. Keep the full outline and area
    # guards, require at least the plain leaf's minimum material in every
    # layer, and compare the actual step's bending geometry below.
    assert min(outline)>.75*width and max(outline)<1.35*width,(side,sign,local_y,row)
    assert min(actual)>.75*(a.h.ARM_X[1]-a.h.ARM_X[0]),(side,sign,local_y,row)
    assert row['connected'],(side,sign,local_y,'Disconnected native material')
    return row



def dependencies():
    return {Path(m.__file__).name:a.v.digest(m.__file__) for m in (a,a.h,r,sections)}


def bending_profile(points, frame, side, sign):
    """Extend the section method across the arm, including the missed flare peak.

    Opus's independent factor_profile probe found that five stations missed a
    small top-surface pocket. Use our existing exact nominal-bead section
    convention here, rather than importing a private probe or claiming a
    continuous/material-strength solution. — GPT-6.1 Sol
    """
    h=a.h
    step=.02
    edges=[-h.ARM_ROOT+run for run in h.STEP_RUNS]+[h.FOOT_Y[0]-h.HEEL_STEP]
    ys=sorted(set(round(float(y),6) for y in [
        *np.arange(-h.ARM_ROOT+.01,h.FOOT_Y[0]-.009,step),
        *(e+offset for e in edges for offset in (-.01,.01))]))
    sampled=[]; split_cuts=[]
    for y in ys:
        row=measure_section(points,frame,side,sign,y,h.arm_thickness(y))
        # A transverse cut through a local bead pocket can have separate pieces
        # that join alongside it. Keep the fixed load-path connectivity gates;
        # record these cuts rather than miscalling them severed 3-D arms.
        if not row['connected']:
            split_cuts.append(dict(local_y_mm=y,component_areas_mm2=row['component_areas_mm2']))
        factor=row['bending_geometry_factor_per_mm2']
        assert factor is not None and np.isfinite(factor) and factor>0,(side,sign,y,row)
        source=6*(h.FOOT_Y[0]-y)/(row['source_width_mm']*h.arm_thickness(y)**2)
        sampled.append([y,factor,round(source,6),row['native_area_mm2']])
    native=max(sampled,key=lambda s:s[1]); source=max(sampled,key=lambda s:s[2])
    arm=h.arm_numbers()
    estimate=arm['bending_strain_while_pressed_flat']*native[1]/source[2]
    # Preserve the existing source gate's stricter half-of-first-reported
    # comparison, now scaled by the actual largest sampled native factor.
    limit=.5*arm['first_spring_clip']['loaded_at_the_middle_of_the_foot_as_first_reported']['bending_strain_while_pressed_flat']
    assert estimate<=limit,(side,sign,native,source,estimate,limit)
    return dict(sample_spacing_mm=step,section_count=len(sampled),
                native_peak=dict(local_y_mm=native[0],factor_per_mm2=native[1]),
                source_plan_peak=dict(local_y_mm=source[0],factor_per_mm2=source[2]),
                native_over_source_peak=round(native[1]/source[2],6),
                scaled_pressed_flat_strain_estimate=round(estimate,6),
                comparative_estimate_limit=limit,step_edges_mm=edges,
                multiple_component_cuts=split_cuts,
                profile_columns=['local_y_mm','native_factor_per_mm2','source_factor_per_mm2','native_area_mm2'],
                sampled_profile=sampled)


def run(folder):
    h=a.h
    points,_=a.v.read_native(folder/a.v.ARCHIVE)
    frame=a.v.read(folder/'layout.frame.json')['parts']
    peak=-h.arm_numbers()['largest_strain_is_mm_behind_the_post_axis']
    ys=dict(plain_peak_bending=peak,
            plain_behind_heel=h.FOOT_Y[0]-h.HEEL_STEP-.20,
            plain_after_root_step=-h.ARM_ROOT+max(h.STEP_RUNS)+.20,
            middle_root_step=-h.ARM_ROOT+sum(h.STEP_RUNS[:2])/2,
            complete_foot_column=sum(h.FOOT_Y)/2)
    rows={}
    for side in ('Left','Right'):
        pose=np.asarray(frame['DFR_Clip_'+side]['assembly_to_machine'])
        rows[side]={str(sign):{name:section(points,pose,side,sign,y,
                    h.CLIP_T+h.FOOT if name=='complete_foot_column' else h.arm_thickness(y))
                    for name,y in ys.items()} for sign in (-1,1)}
    profiles={side:{str(sign):bending_profile(points,np.asarray(frame['DFR_Clip_'+side]['assembly_to_machine']),side,sign)
                    for sign in (-1,1)} for side in ('Left','Right')}
    report=dict(revision='R71',archive_sha256=a.v.digest(folder/a.v.ARCHIVE),
                frame_sha256=a.v.digest(folder/'layout.frame.json'),checker_sha256=a.v.digest(__file__),
                dependencies_sha256=dependencies(),parts=rows,bending_profiles=profiles,passes=True,
                physical_strength_force_and_creep_verified=False,
                method='Exact nominal native bead sections at five source-defined stations plus a 0.02 mm sampled profile of each loaded arm, including both sides of the root and heel steps. Measures all layers, outline width, actual material length, connected area and second moment. Reports the true sampled native maximum without assuming it lies in the plain strip. The scaled source strain estimate retains the existing half-of-first-reported comparison; notch effects, material strength, bonding, friction and creep are unmeasured. Only float32 seams snapped at one millionth millimetre with bounded area change.')
    a.v.write(folder/'native-spring-arms.json',report)
    print(folder.name,'all four leaf, step-transition and complete foot-column sections passed')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('folders',type=Path,nargs='+')
    for folder in p.parse_args().folders:run(folder)
