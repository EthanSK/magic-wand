#!/usr/bin/env python3
"""Functional working spaces for R16: one definition for CAD carving and actual-bead checks.

Reuses R15's exact pose-by-pose `Swept` representation and maximum-socket envelope so no
hundreds-of-poses 3D union is ever built.
"""
from functools import lru_cache
import numpy as np
import holder16 as h

Swept = h.r15_spaces.Swept
Spaces = h.r15_spaces.Spaces
CARVE_LOG = {}


def socket_route_below():
    """Straight insertion from below the backplate: 31 poses from 6 mm below to seated."""
    return np.array([(0., 0., -dz) for dz in np.linspace(6., 0., 31)], dtype=float)


@lru_cache(maxsize=1)
def maximum_socket():
    return h.r15_spaces.maximum_socket().translate((0, 0, h.P['bay']['socket_body_top_shift_mm']))


def carve(shape, spaces, label):
    solids = [s for s in spaces.values() if not isinstance(s, Swept)]
    if solids: shape = shape - h.union(solids)
    log = {}
    for name, space in spaces.items():
        if isinstance(space, Swept):
            shape, met = space.subtract_from(shape)
            log[name] = {'poses': len(space), 'poses_meeting_material': met}
    CARVE_LOG[label] = log
    return shape


@lru_cache(maxsize=8)
def regions(name):
    rod = h.ROD
    result = {'unloaded_clip_bore': h.cyl(rod['clip_diameter'] / 2, -40, 100).rotate((-90, 0, 0))}
    if name == 'Key_Carrier':
        c = h.P['carrier_rings']
        result['clip_gap_mid'] = h.gap_cut(*c['mid_band_y_mm'])
        result['clip_gap_rear'] = h.gap_cut(*c['rear_band_y_mm'])
        result['external_wire_bus'] = h.wire_bus(-80, 100)
        hw = h.seated_hardware(); socket = h.seated_socket(); route = socket_route_below()
        b = h.P['bay']; cap = h.P['cap_clearance_screen']
        for i, ((x, y), rot) in enumerate(zip(h.key_positions(), h.key_rotations())):
            sw = hw['switch'].rotate((0, 0, rot)); so = socket.rotate((0, 0, rot)); mx = maximum_socket().rotate((0, 0, rot))
            result[f'key_{i}_switch'] = sw.translate((x, y, h.PCB_Z))
            result[f'key_{i}_socket'] = so.translate((x, y, h.PCB_Z))
            result[f'key_{i}_maximum_socket'] = mx.translate((x, y, h.PCB_Z))
            result[f'key_{i}_socket_loading'] = Swept(so, route + np.array([x, y, h.PCB_Z]))
            result[f'key_{i}_maximum_socket_loading'] = Swept(mx, route + np.array([x, y, h.PCB_Z]))
            sb = so.bounding_box()
            # Tape zone: 0.4 mm of clear space under the socket body and its legs for the required tape.
            result[f'key_{i}_socket_tape_zone'] = h.box(sb[0] - 1.0, sb[3] + 1.0, sb[1] - .5, sb[4] + .5, sb[2] - .4, sb[2] + .01).translate((x, y, h.PCB_Z))
            result[f'key_{i}_mount_opening'] = h.rr(b['plate_opening_mm'], b['plate_opening_mm'], .2, h.PCB_Z + b['plate_bottom_mm'], h.plate_top() + .2).translate((x, y, 0))
            result[f'key_{i}_clip_relief'] = h.rr(2 * b['clip_relief_half_x_mm'], 2 * b['clip_relief_half_y_mm'], .5, h.PCB_Z, h.PCB_Z + b['plate_bottom_mm']).translate((x, y, 0))
            m = cap['lateral_allowance_per_cap_side_mm']
            result[f'key_{i}_cap_travel'] = h.rr(cap['reference_width_mm'] + 2 * m, cap['reference_length_mm'] + 2 * m, 1.4, h.PCB_Z + 6.1 - cap['stroke_mm'], h.PCB_Z + 9.1).translate((x, y, 0))
    elif name == 'Battery_Holder':
        c = h.P['cage']; lv = h.cage_levels()
        result['clip_gap_near'] = h.gap_cut(*c['near_band_y_mm'])
        result['clip_gap_far'] = h.gap_cut(*c['far_band_y_mm'])
        result['external_wire_bus'] = h.wire_bus(-80, 100)
        result['reverse_wire_bus'] = h.wire_bus(-80, 100).mirror((1, 0, 0))
        result['cell_reserve'] = h.cell_shape(True)
        result['cell_loading'] = h.box(-lv['half_w'], lv['half_w'], -45, lv['half_l'], lv['floor_top'], lv['roof_bottom'])
        result['gate_removal_route'] = Swept(h.battery_gate(True), [(0, 0, dz) for dz in np.linspace(0, 15, 61)])
        sx = c['slot_x_centre_mm']; sw = c['slot_width_mm']; sy0, sy1 = c['gate_slot_y_mm']
        for sign in (1, -1):
            result[f'gate_slot_{sign:+d}'] = h.box(min(sign * (sx - sw / 2), sign * (sx + sw / 2)), max(sign * (sx - sw / 2), sign * (sx + sw / 2)), sy0, sy1, lv['floor_top'] + .45, lv['roof_top'] + .5)
        w = c['wire_exit_clear_x_mm']
        result['lead_exit'] = h.box(-w, w, c['near_band_y_mm'][0] - 1, -13.1, lv['floor_top'], lv['roof_bottom'] - .5)
    elif name == 'XIAO_Rod_Holder':
        s = h.P['sensor']; refs = h.references()
        result['clip_gap_near'] = h.gap_cut(*s['near_band_y_mm'])
        result['clip_gap_far'] = h.gap_cut(*s['far_band_y_mm'])
        result.update(board=refs['pcb'], usb=refs['usb'], wire_route=refs['wire'], usb_plug_body=refs['usb_plug_body'], pad_access_top=refs['pad_access_top'])
        # Every reachable board pose (official rounded outline) 0.1 mm inside the rails and stops.
        result['board_travel'] = h.union([h.board_outline(dx, dy) for dx, dy in h.board_travel_poses(margin=.1, n_lateral=3, n_axial=3)])
        # Stated clearance band under the board centre for unknown underside parts; not a measured component height.
        result['board_underside_centre'] = h.box(-4.0, 4.0, 3.5, 20.0, h.SENSOR['board_z'] - s['board_underside_clear_mm'], h.SENSOR['board_z'])
    return result
