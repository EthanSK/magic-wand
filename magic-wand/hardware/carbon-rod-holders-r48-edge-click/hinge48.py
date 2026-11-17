"""Two outward-set PETG spring arms and rigid guides for the DFRobot bracket.

The free bracket is the print. A pair of rigid outriggers rests just outside the
receivers to stop the entire bracket drifting to one side during installation.
The bought board, pin diameter, fixed through holes and axle stay in place.
"""
from functools import lru_cache

import manifold3d as mf
import numpy as np


SEATED_SHOULDER = 3.40  # inner receiver face, positive half of assembled span
FREE_SHOULDER = 3.67
PINCHED_SHOULDER = 2.00
PIN_LENGTH = 1.12
PIN_TAPER = .22
GUIDE_INNER = 5.78   # clears the 5.50 receiver even for two +0.10 mm faces
ARM_WIDTH = 1.20
ROOT_OFFSET = .90
TIP_BACK = 3.0
PAD_CENTRE_BEHIND_AXIS = 2.15


def displacement(h, points, left, right):
    """Lateral set of the flexible blades only. Pin and fingertip move together."""
    p = np.asarray(points, float)
    x, y, z = p.T
    root = h.r.ARM_ROOT_Y + ROOT_OFFSET
    # Straight journal ends stay parallel to X in all the guide's poses.
    run = h.r.AXIS_Y - .78 - root
    t = np.clip((y - root) / run, 0., 1.)
    weight = t*t*(3. - t)/2.
    chosen = (y >= root - .001) & (np.abs(x) >= 1.5) & (np.abs(x) < 5.15) & (z > 16.95)
    return np.column_stack((np.sign(x)*np.where(x < 0., left, right)*weight*chosen,
                            np.zeros_like(x), np.zeros_like(x)))


def pose_arms(h, seated, left, right):
    return seated.warp_batch(lambda p: p + displacement(h, p, left, right))


def free_bracket(h):
    set_each = FREE_SHOULDER - SEATED_SHOULDER
    return pose_arms(h, h.p.bracket(), set_each, set_each)


def replace_arms(h, source):
    r, box = h.r, h.box
    axis, z = r.AXIS_Y, r.AXIS_Z
    root = r.ARM_ROOT_Y + ROOT_OFFSET
    # Keep the original filleted roots, the centre anti-crush prong and its bridge.
    cut = r.mirrored(box(1.72, 5.24, root, axis + 3.2, 16.92, 20.15))
    sections = []
    for y in np.linspace(root-.13, axis-.78, 23):
        t = np.clip((y-root)/(axis-.78-root), 0., 1.)
        edge = 3.05 + (SEATED_SHOULDER-3.05)*t*t*(3.-t)/2.
        sections.append(box(edge-ARM_WIDTH, edge, y-.012, y+.012, 17., 19.))
    sections.append(box(SEATED_SHOULDER-ARM_WIDTH, SEATED_SHOULDER, axis-.78,
                        axis+TIP_BACK, 17., 19.))
    arm = h.union(mf.Manifold.batch_hull([a,b]) for a,b in zip(sections, sections[1:]))
    # Pinch from above at the end beyond the ears: a longer moment arm than
    # squeezing the blades beside their roots. Ramps avoid flat islands.
    pad1 = box(SEATED_SHOULDER-ARM_WIDTH, SEATED_SHOULDER, axis+.32,axis+.42,18.98,19.12)
    pad2 = box(SEATED_SHOULDER-ARM_WIDTH, SEATED_SHOULDER, axis+1.45,axis+2.6,18.98,20.)
    pad3 = box(SEATED_SHOULDER-ARM_WIDTH, SEATED_SHOULDER, axis+2.87,axis+3.,18.98,19.65)
    pads = mf.Manifold.batch_hull([pad1,pad2]) + mf.Manifold.batch_hull([pad2,pad3])
    tip = SEATED_SHOULDER + PIN_LENGTH
    journal = r.d.axis_oval(axis, z, r.h29.TAB_R, SEATED_SHOULDER-.10, tip-PIN_TAPER)
    cone = mf.Manifold.cylinder(PIN_TAPER, r.h29.TAB_R, r.h29.TAB_R-PIN_TAPER, 48)
    cone = cone.rotate((0,90,0)).translate((tip-PIN_TAPER,axis,z))
    # The guides straddle the outsides of the fixed ears, below the pinch tabs.
    # Their sloped lead-ins centre the bracket during the last part of the drop.
    stations = [(8.55,9.95,14.0,18.55,19.18), (7.8,9.65,16.5,17.55,18.95),
                (6.5,8.0,21.0,15.85,17.25),(GUIDE_INNER,7.12,axis-1.8,15.62,17.12),
                (GUIDE_INNER,7.12,axis+1.15,15.62,17.12)]
    faces = [box(a,b,y-.06,y+.06,lo,hi) for a,b,y,lo,hi in stations]
    guide = h.union(mf.Manifold.batch_hull([a,b]) for a,b in zip(faces,faces[1:]))
    # Relieve the lower inside corner of each shoe to form a vertical-entry funnel.
    guide -= h.p._xz_prism([(GUIDE_INNER-.1, 15.5), (GUIDE_INNER+.55, 15.5),
                            (GUIDE_INNER, 16.25), (GUIDE_INNER-.1, 16.25)],
                           axis-3.8, axis+1.3)
    return (source-cut) + r.mirrored(arm+pads+journal+cone+guide)


def seated_arm_estimate(h):
    # The upstream report applies an additional conservative 1.5 mm root
    # deduction, so give it the unshortened span and the unshortened estimate.
    L = h.r.AXIS_Y - h.r.ARM_ROOT_Y
    a = L + PAD_CENTRE_BEHIND_AXIS
    delta = FREE_SHOULDER - PINCHED_SHOULDER
    E = h.r.h29.E_PETG
    inertia = 2.*ARM_WIDTH**3/12.
    force = 6.*E*inertia*delta/(L**2*(3*a-L))
    strain = force*a*ARM_WIDTH/(2*E*inertia)
    return dict(arm_thickness_mm=ARM_WIDTH,arm_height_mm=2.,root_to_tab_mm=round(L,3),
                root_to_pinch_pad_mm=round(a,3),tab_squeeze_mm=delta,
                pad_squeeze_mm=round(force*a**3/(3*E*inertia),3),
                pinch_force_each_N_estimate=round(force,2),root_strain_percent_estimate=round(100*strain,2),
                assumed_PETG_modulus_MPa=E,assumed_PETG_yield_strain_percent=100*h.r.h29.YIELD_STRAIN)


def install(h):
    source = h.p.bracket_before_pin_relief
    @lru_cache(maxsize=1)
    def repaired():
        return replace_arms(h, source())
    h.p.bracket_before_pin_relief = h.q.bracket_before_pin_relief = repaired
    h.r.arm_bend = lambda points, amount=1.: displacement(
        h, points, amount*(PINCHED_SHOULDER-SEATED_SHOULDER), amount*(PINCHED_SHOULDER-SEATED_SHOULDER))
    h.r.h29.arm_estimate = lambda: seated_arm_estimate(h)


def native_targets(h):
    """Actual load-bearing sections on the free printed bracket, in its CAD frame."""
    printed = free_bracket(h)
    r, box = h.r, h.box
    zones = {}
    for side, name in [(-1,'left'),(1,'right')]:
        def at(x0,x1,y0,y1,z0,z1):
            lo,hi=sorted([side*x0,side*x1])
            return printed ^ box(lo,hi,y0,y1,z0,z1)
        zones[name+' spring root and beam'] = at(1.7,3.5,r.ARM_ROOT_Y+.92,r.ARM_ROOT_Y+2.,17.04,18.96)
        # Includes real journal and adjacent blade across the loaded seam.
        zones[name+' hinge axle and blade joint'] = at(FREE_SHOULDER-.53,FREE_SHOULDER+.79,
                                                        r.AXIS_Y-.47,r.AXIS_Y+.47,18.10,18.90)
        zones[name+' outer guide shoe'] = at(GUIDE_INNER+.12,7.05,r.AXIS_Y-1.1,r.AXIS_Y+.65,16.31,17.02)
    return zones


def check_hinge(h, seated, free, carrier):
    """Test the physical failure mode where one pin seats and the other misses."""
    r = h.r
    y,z = r.AXIS_Y,r.AXIS_Z
    box=h.box
    # Isolate the actual assembled receiver, including nearby deck and shoulders.
    local = carrier ^ box(-12.,12., y+r.CLICK_SHIFT-13.,y+r.CLICK_SHIFT+3.5,13.,21.5)
    receiver_half = r.h29.SUPPORT_X[0]
    outside = r.h29.SUPPORT_X[1]
    tol = .10  # challenge each printed surface independently per axis, not a measurement
    gap = GUIDE_INNER - outside
    preload = FREE_SHOULDER - receiver_half
    worst_offset = gap+2*tol
    snap = SEATED_SHOULDER+PIN_LENGTH-receiver_half
    worst_far = FREE_SHOULDER+PIN_LENGTH-tol - worst_offset - (receiver_half+tol)
    # In the actual geometry the end of an eccentric fit is limited by the
    # fixed guide contacting its ear, independent of whether either spring flexes.
    guide_clear = []
    for side in (-1,1):
        shoe = r.world(seated ^ box(*sorted([side*5.6,side*7.25]),y-1.4,y+.88,16.30,17.05))
        ear = local ^ box(*sorted([side*3.4,side*5.5]),y+r.CLICK_SHIFT-1.4,y+r.CLICK_SHIFT+.8,16.32,17.02)
        guide_clear.append(round(shoe.min_gap(ear,1.),4))
    tip_box = box(2.4,5.15,y-.51,y+.51,z-.4,z+.4)
    side_report=[]
    for side in (-1,1):
        local_tip = tip_box if side>0 else tip_box.mirror((1.,0.,0.))
        ends=[]
        for solid in (free,seated,r.bent(seated)):
            bounds=(solid ^ local_tip).bounding_box()
            ends.append(round(max(abs(bounds[0]),abs(bounds[3])),4))
        side_report.append(dict(side=side,free_tip_x_mm=ends[0],seated_tip_x_mm=ends[1],
                                pinched_tip_x_mm=ends[2],seated_depth_mm=round(ends[1]-receiver_half,4)))
    contact = []
    for offset in (-gap,0.,gap):
        right=min(preload,-offset)
        left=min(preload,offset)
        for first in (-1,1):
            travel=[]
            for t in np.linspace(0.,1.,9):
                a=(1.-t)*(PINCHED_SHOULDER-SEATED_SHOULDER)
                l=left if first<0 else a+t*left
                rr=right if first>0 else a+t*right
                assembly=r.world(pose_arms(h,seated,l,rr)).translate((offset,0.,0.))
                travel.append(max((assembly ^ local).volume(),0.))
            contact.append(dict(assembly_offset_mm=round(offset,3),first_tab='left' if first<0 else 'right',
                                worst_collision_mm3=round(max(travel),5)))
    # Remove either finger independently from the pinched, seated bracket. The
    # spring stop itself must not intersect the moving blades at full squeeze.
    root=r.ARM_ROOT_Y+ROOT_OFFSET
    squeezed=r.bent(seated)
    positive=box(.7,5.2,root+.4,y+3.2,16.95,20.05)
    prong=box(-.66,.66,root+.4,y+3.2,16.95,20.05)^seated
    arm=squeezed ^ positive
    stop_gap=arm.min_gap(prong,2.)
    root_area=[]
    for side in (-1,1):
        blade=seated ^ box(*sorted([side*1.72,side*3.7]),root+.18,root+.38,17.,19.)
        root_area.append(round(blade.volume()/.20,3))
    assert h.r.h29.TAB_R == .7 and h.r.h29.BORE_R == .9
    # Opposed presses act beyond the pivot, at the exposed pads. Compute the
    # conservative strain for a cantilever loaded there; adding guide stock
    # to the outer rigid rails has no effect on the compliant blade section.
    L=y-root
    a=L+PAD_CENTRE_BEHIND_AXIS
    delta=FREE_SHOULDER-PINCHED_SHOULDER
    I=2.*ARM_WIDTH**3/12.
    force=6.*r.h29.E_PETG*I*delta/(L*L*(3*a-L))
    strain=force*a*ARM_WIDTH/(2*r.h29.E_PETG*I)
    data=dict(physical_fit_verified=False, journal_and_bore_diameters_mm=[1.4,1.8],
              free_shoulder_span_mm=round(2*FREE_SHOULDER,3), old_free_shoulder_span_mm=6.10,
              ear_to_ear_mm=2*receiver_half, spring_preload_each_mm=round(preload,3),
              minimum_preload_each_for_surface_tolerance_mm=round(preload-2*tol,3),
              toleranced_surface_error_mm=tol, guide_clearance_each_mm=guide_clear,
              min_guide_clearance_at_tolerance_mm=round(gap-2*tol,3),
              worn_or_eccentric_offset_challenge_mm=round(worst_offset,3),
              min_far_tip_engagement_at_tolerance_mm=round(worst_far,3),
              min_full_diameter_engagement_at_tolerance_mm=round(worst_far-PIN_TAPER,3),
              nominal_engagement_each_mm=round(snap,3),pin_tip_measurements=side_report,
              either_order_release_checks=contact,arm_contact_area_mm2=root_area,
              centre_stop_clearance_at_full_pinch_mm=round(stop_gap,4),
              effective_span_for_strain_mm=round(L,3),estimated_peak_pinch_strain_percent=round(100*strain,3),
              estimated_pinch_force_per_arm_N=round(force,3),
              pad_surface_beyond_board_mm=round(y+PAD_CENTRE_BEHIND_AXIS-(r.board_front_y()+r.BOARD_LENGTH),3),
              bracket_to_bought_board_and_lead_mm3=round(max((seated^r.sensor()).volume(),(seated^r.gravity_lead()).volume(),0.),5))
    data['gates']={
        'both_printed_tabs_match_free_and_seated_dimensions': all(
            abs(t['free_tip_x_mm']-(FREE_SHOULDER+PIN_LENGTH))<.003
            and abs(t['seated_depth_mm']-snap)<.003 and receiver_half-t['pinched_tip_x_mm']>.20 for t in side_report),
        'positive_preload_after_printed_tolerance':preload-2*tol>=.06,
        'both_fixed_guides_limit_one_sided_seating': all(abs(d-gap)<.02 for d in guide_clear)
            and gap-2*tol>=.07 and worst_far-PIN_TAPER>=.45,
        'either_arm_can_seat_first_at_both_guide_limits': all(t['worst_collision_mm3']<.002 for t in contact),
        'squeeze_stop_and_roots_clear': stop_gap>.10 and min(root_area)>=2.36,
        'conservative_elastic_estimate_and_finger_access': strain<.034 and data['pad_surface_beyond_board_mm']>5.
            and data['bracket_to_bought_board_and_lead_mm3']<.002,
        'seated_free_and_pinched_each_single_solid': all(
            s.status()==mf.Error.NoError and len(s.decompose())==1 for s in (free,seated,squeezed)),
    }
    return data
