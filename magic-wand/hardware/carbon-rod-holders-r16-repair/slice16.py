#!/usr/bin/env python3
"""Audit the actual sliced R16 project, part by part, from its G-code.

Every bead type in every working space, actual previous-bead backing of every layer start,
no support/brim/skirt, ring and lead-in skirt sections with surviving tracks, fixed load-path
sections, bridge and floating-shell locations, and layer views bound to the exact project.
Numerical guards are not manufacturing tolerances; nothing here is a physical print result.
"""
import argparse, importlib.util, json, math, zipfile, xml.etree.ElementTree as E
from pathlib import Path
import numpy as np, trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import holder16 as h
import spaces16

OUT = h.HERE / 'exports'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


q = load('existing_path_auditor', h.HERE.parent / 'printed-loop-wand/shard-tube-r2/check_sliced_paths.py')
start_audit = load('r15_start_audit', h.R15 / 'start_audit.py')
N = {'m': q.NS}
STEP = .15


def read_project(project):
    with zipfile.ZipFile(project) as z:
        assert z.testzip() is None
        cfg = E.fromstring(z.read('Metadata/model_settings.config'))
        model = E.fromstring(z.read('3D/3dmodel.model')); cache = {'3D/3dmodel.model': model}
        roots = {o.get('id'): o for o in model.findall('m:resources/m:object', N)}
        builds = {i.get('objectid'): q.transform(i.get('transform')) for i in model.findall('m:build/m:item', N)}
        settings = json.loads(z.read('Metadata/project_settings.config'))
        gcode_text = z.read('Metadata/plate_1.gcode').decode(); config_text = z.read('Metadata/model_settings.config').decode()
        data, features, stats = q.extrusion_points(gcode_text, STEP)
        offset = np.array([float(x) for x in settings.get('extruder_offset', ['0x0'])[0].split('x')] + [0])
        parts = {}
        for obj in cfg.findall('object'):
            name = q.metadata(obj)['name']
            part = next(p for p in obj.findall('part') if q.metadata(p).get('name') == name)
            comp = next(c for c in roots[obj.get('id')].findall('m:components/m:component', N) if c.get('objectid') == part.get('id'))
            path = next((v.lstrip('/') for k, v in comp.attrib.items() if k.endswith('}path')), '3D/3dmodel.model')
            if path not in cache: cache[path] = E.fromstring(z.read(path))
            child = next(o for o in cache[path].findall('m:resources/m:object', N) if o.get('id') == part.get('id'))
            vv = np.array([[float(v.get(k)) for k in 'xyz'] for v in child.findall('m:mesh/m:vertices/m:vertex', N)])
            tt = np.array([[int(v.get(k)) for k in ['v1', 'v2', 'v3']] for v in child.findall('m:mesh/m:triangles/m:triangle', N)])
            vv = q.points(q.points(vv, q.transform(comp.get('transform'))), builds[obj.get('id')])
            parts[name] = {'vertices': vv, 'faces': tt, 'settings': {m.get('key'): m.get('value') for m in obj.findall('metadata')}}
    return data, features, stats, settings, offset, parts, gcode_text, config_text


def polar_tracks(points, widths, centre_y, inner=3.95, outer=5.7, angles=(-55, 90, 235)):
    """Actual radial bead-centre clusters at the ring midplane layer (assembly frame)."""
    nearest = float(points[np.argmin(abs(points[:, 1] - centre_y)), 1]); p = points[abs(points[:, 1] - nearest) < .01]
    theta = np.degrees(np.arctan2(p[:, 2], p[:, 0])); radius = np.linalg.norm(p[:, [0, 2]], axis=1); tracks = {}
    for angle in angles:
        delta = abs((theta - angle + 180) % 360 - 180); r = np.sort(radius[(delta < 3) & (radius > inner) & (radius < outer)])
        clusters = []
        for value in r:
            if not clusters or value - clusters[-1][-1] > .17: clusters.append([float(value)])
            else: clusters[-1].append(float(value))
        tracks[str(angle)] = [round(float(np.median(c)), 3) for c in clusters]
    return nearest, tracks


def ray_section(solid, origin, direction):
    c = np.array(origin, dtype=float); d = np.array(direction, dtype=float); d /= np.linalg.norm(d)
    hits = sorted(solid.ray_cast(c - d * 60, c + d * 60), key=lambda t: t.distance)
    for a, b in zip(hits[::2], hits[1::2]):
        if a.distance < .5 < b.distance:  # ray_cast distance is the segment parameter 0..1
            return float(np.linalg.norm(np.array(b.position) - np.array(a.position))), np.array(a.position), np.array(b.position)
    raise AssertionError(('Probe is not in material', origin, direction))


def radial_section(solid, y, angle_deg):
    """Ring wall thickness along an outward radial ray from the rod axis (first entry to first exit)."""
    a = math.radians(angle_deg); hits = sorted(solid.ray_cast((0, y, 0), (15 * math.cos(a), y, 15 * math.sin(a))), key=lambda t: t.distance)
    assert len(hits) >= 2, (y, angle_deg, 'missing ring section')
    return float(np.linalg.norm(np.array(hits[1].position) - np.array(hits[0].position)))


def tracks_on_ray(points, widths, centre, direction, a, b, tol=.09, detail=None):
    """Bead-centre clusters along a ray in the layer nearest the probe (assembly frame, Y layer axis)."""
    c = np.array(centre, dtype=float); d = np.array(direction, dtype=float); d /= np.linalg.norm(d)
    nearest = float(points[np.argmin(abs(points[:, 1] - c[1])), 1]); assert abs(nearest - c[1]) < .12, (centre, nearest)
    c[1] = nearest; row = points[abs(points[:, 1] - nearest) < .01]; rel = row - c
    transverse = np.array([-d[2], 0, d[0]]); along = rel @ d
    lo, hi = float((a - c) @ d), float((b - c) @ d)
    on = (abs(rel @ transverse) < tol) & (along >= min(lo, hi) - .05) & (along <= max(lo, hi) + .05)
    values = np.sort(along[on]); clusters = []
    for v in values:
        if not clusters or v - clusters[-1][-1] > .17: clusters.append([float(v)])
        else: clusters[-1].append(float(v))
    if detail is not None:
        sel = np.flatnonzero(abs(points[:, 1] - nearest) < .01)[on]
        detail['widths'] = [round(float(w), 3) for w in widths[sel]]; detail['along'] = [round(float(v), 3) for v in values]
    return nearest, [round(float(np.median(cl)), 3) for cl in clusters]


def feature(solid, points, widths, label, probes, direction, minimum, min_tracks, load, decision, test):
    rows = []
    for centre in probes:
        d = direction(centre) if callable(direction) else direction
        assert abs(float(np.asarray(d, dtype=float)[1])) < 1e-9, (label, 'probe rays must lie in a layer plane')
        thickness, a, b = ray_section(solid, centre, d)
        assert thickness >= minimum - .02, (label, centre, thickness, minimum)
        layer, clusters = tracks_on_ray(points, widths, centre, d, a, b)
        assert len(clusters) >= min_tracks, (label, centre, 'Fewer surviving tracks than required', clusters)
        rows.append({'probe_assembly_mm': list(centre), 'direction': [round(float(v), 4) for v in np.asarray(d, dtype=float)], 'STL_section_mm': round(thickness, 4),
                     'sampled_layer_assembly_y_mm': layer, 'track_centres_relative_mm': clusters})
    return {'feature': label, 'probes': rows, 'minimum_sampled_section_mm': round(min(r['STL_section_mm'] for r in rows), 4),
            'minimum_sampled_track_count': min(len(r['track_centres_relative_mm']) for r in rows), 'screen_mm': minimum, 'screen_tracks': min_tracks,
            'load_case': load, 'decision': decision, 'required_physical_test': test, 'layer_direction': 'Assembly Y is the layer axis for every R16 part.',
            'physical_strength_verified': False}


def layer_section(solid, points, widths, y, window, label, minimum_area, minimum_fraction):
    """Whole mesh section at a print layer against the actual printed bead footprints inside a window.

    The assembly solid is turned so its Y (the layer axis) becomes Z; the section and the bead
    footprints then share (x, -z) coordinates. `window` is (x0, x1, z0, z1) in assembly terms.
    """
    nearest = float(points[np.argmin(abs(points[:, 1] - y)), 1]); assert abs(nearest - y) < .12
    upright = solid.rotate((90, 0, 0))
    # Assembly Y falls as print Z rises: a layer with bead top `nearest` occupies Y nearest..nearest+0.2.
    section = upright.slice(nearest + .1)
    win = q.CrossSection([[[window[0], -window[3]], [window[1], -window[3]], [window[1], -window[2]], [window[0], -window[2]]]])
    sel = abs(points[:, 1] - nearest) < .01
    beads = start_audit.bead_footprints(q, points[sel][:, [0, 2]] * np.array([1, -1]), widths[sel])
    mesh_area = (section ^ win).area(); printed = (beads ^ section ^ win).area()
    assert mesh_area >= minimum_area and printed / mesh_area >= minimum_fraction, (label, mesh_area, printed)
    return {'feature': label, 'layer_assembly_y_mm': nearest, 'mesh_section_area_mm2': round(mesh_area, 3), 'printed_bead_area_mm2': round(printed, 3),
            'printed_fraction': round(printed / mesh_area, 4), 'screen_area_mm2': minimum_area, 'screen_fraction': minimum_fraction,
            'note': 'Interlayer load path: the whole section in this layer plane and the conservative inscribed bead footprints that actually printed. Not a breaking force.'}


def band_start_backing(points, widths, band_y0, band_y1, lead_sign, label, minimum=.9):
    """Regression for the R15 failure: the first printed layer of a ring band must rest on real plastic.

    The R15 sensor holder's far clip face started with about 0.9 percent of its area over actual
    beads (one empty layer above a helper). Here the first true band layer, chosen by its layer
    middle lying inside the band, must have at least 90 percent of its bead footprint directly
    over the previous layer's actual bead footprints inside the ring annulus, with no lateral
    expansion credit.
    """
    assert lead_sign > 0, 'R16 skirts lead toward +Y only'
    face = band_y1
    tops = np.unique(np.round(points[:, 1], 4))
    # A layer with bead top T spans assembly Y T..T+0.2 (Y falls as print Z rises); its middle is T+0.1.
    inside = tops[tops + .1 <= face + 1e-6]
    current_top = float(inside.max()); previous_top = current_top + .2
    assert any(abs(tops - previous_top) < .01), (label, 'no previous layer')
    annulus = q.CrossSection.circle(5.8, 128) - q.CrossSection.circle(3.85, 128)

    def footprint(top):
        sel = abs(points[:, 1] - top) < .01
        return start_audit.bead_footprints(q, points[sel][:, [0, 2]], widths[sel]) ^ annulus
    current = footprint(current_top); previous = footprint(previous_top)
    backed = (current ^ previous).area(); fraction = backed / current.area()
    assert current.area() > 10 and fraction >= minimum, (label, current.area(), fraction)
    return {'feature': label, 'band_face_assembly_y_mm': face, 'first_band_layer_top_assembly_y_mm': current_top,
            'first_band_layer_middle_assembly_y_mm': round(current_top + .1, 4), 'previous_layer_top_assembly_y_mm': previous_top,
            'band_first_layer_bead_area_mm2': round(current.area(), 3), 'directly_backed_fraction': round(fraction, 4),
            'lateral_expansion_mm': 0.0, 'screen_fraction': minimum,
            'reference_failure': 'R15 XIAO far clip face: 0.9 percent directly backed over a separate helper.'}


def path_scan(solid, points, widths, y_range, window, label, minimum_area, minimum_fraction, load, decision):
    """Every printed layer between two assembly Y values: the whole mesh section inside a window
    against the actual bead footprints. Reports the layers with the least mesh and printed area."""
    upright = solid.rotate((90, 0, 0)); lo, hi = sorted(y_range)
    tops = np.unique(np.round(points[:, 1], 4)); tops = tops[(tops + .1 > lo) & (tops + .1 < hi)]
    assert len(tops) >= int((hi - lo) / .2) - 2, (label, 'missing layers', len(tops))
    win = q.CrossSection([[[window[0], -window[3]], [window[1], -window[3]], [window[1], -window[2]], [window[0], -window[2]]]])
    rows = []
    for top in tops:
        section = upright.slice(float(top) + .1) ^ win
        if section.is_empty(): continue
        sel = abs(points[:, 1] - top) < .01
        beads = start_audit.bead_footprints(q, points[sel][:, [0, 2]] * np.array([1, -1]), widths[sel])
        printed = (beads ^ section).area(); area = section.area()
        rows.append((float(top), area, printed))
    assert rows, (label, 'empty scan')
    worst_mesh = min(rows, key=lambda r: r[1]); worst_printed = min(rows, key=lambda r: r[2]); worst_fraction = min(rows, key=lambda r: r[2] / r[1])
    assert worst_mesh[1] >= minimum_area and worst_fraction[2] / worst_fraction[1] >= minimum_fraction, (label, worst_mesh, worst_fraction)
    return {'feature': label, 'assembly_y_range_mm': [lo, hi], 'window_x_z_mm': list(window), 'layers_scanned': len(rows),
            'minimum_mesh_section_mm2': round(worst_mesh[1], 3), 'minimum_mesh_layer_top_mm': worst_mesh[0],
            'minimum_printed_area_mm2': round(worst_printed[2], 3), 'minimum_printed_layer_top_mm': worst_printed[0],
            'minimum_printed_fraction': round(worst_fraction[2] / worst_fraction[1], 4), 'screen_area_mm2': minimum_area,
            'screen_fraction': minimum_fraction, 'load_case': load, 'decision': decision, 'physical_strength_verified': False,
            'note': 'Complete intervening-layer scan: every printed layer in the range, whole mesh section in the window and conservative inscribed bead footprints. Not a breaking force.'}


def cradle_scans(X, xs, xw):
    """Surviving printed material of every board cradle: the 0.45 mm of ledge directly under the
    board plane where the board rests (every layer under the board), the near V stop tabs and
    the far stop blocks, each side separately."""
    sn = h.P['sensor']; bz = h.SENSOR['board_z']; bo = sn['board_outline_mm']; yn = sn['board_near_end_y_mm']; yf = yn + bo['length']
    inner = sn['cradle_inner_x_mm']; rail = sn['rail_x_mm'][0]; un, uf = sn['ledge_under_board_mm']
    rows = []
    for sign, side in ((1, '+X'), (-1, '-X')):
        xw_ = (min(sign * inner, sign * rail), max(sign * inner, sign * rail))
        rows.append(path_scan(X, xs, xw, (yn, yn + un), (xw_[0], xw_[1], bz - .45, bz), f'Near {side} ledge, top 0.45 mm under the board plane, every layer under the board', .5, .5,
                              'The board corner rests here; USB plugging presses it down and tape holds it.', f'1.0 mm ledge from the rail to |X| {inner}, led in at 45 degrees; the window is the 0.45 mm the board actually bears on.'))
        rows.append(path_scan(X, xs, xw, (yf - uf, yf), (xw_[0], xw_[1], bz - .45, bz), f'Far {side} ledge, top 0.45 mm under the board plane, every layer under the board', .5, .5,
                              'As the near ledge; this one stands on the bed.', f'1.0 mm ledge from the rail to |X| {inner}, continuous to the bed.'))
        tw = (min(sign * inner, sign * (rail + .1)), max(sign * inner, sign * (rail + .1)))
        rows.append(path_scan(X, xs, xw, (sn['near_tab_y0_mm'], 1.6), (tw[0], tw[1], bz, bz + sn['stop_height_mm']),
                              f'Near {side} V stop tab, every layer from its base to where the 45-degree face reaches |X| 8.5', .8, .5,
                              'The USB-plug push drives the board corner arc into this face.', 'A 1.1 mm tall tab from the rail with a 45-degree plan face tangent to the 0.3 mm-offset corner arc.'))
        rows.append(path_scan(X, xs, xw, (sn['far_stop_y_mm'], sn['y_mm'][1]), (xw_[0], xw_[1], bz, bz + sn['stop_height_mm']), f'Far {side} stop block on the bed, every layer', 1.8, .6,
                              'The unplug pull drives the far corner arcs into these faces.', 'A 1.1 mm tall block from the rail to |X| 7.3 standing on the bed.'))
    return rows


def object_labels(config_text):
    """Map the G-code 'unique label id' to object names through the plate's identify_id entries."""
    import re
    names = {m.group(1): re.search(r'key="name" value="([^"]+)"', m.group(2)).group(1)
             for m in re.finditer(r'<object id="(\d+)">(.*?)</object>', config_text, re.S)}
    labels = {}
    for m in re.finditer(r'<model_instance>(.*?)</model_instance>', config_text, re.S):
        oid = re.search(r'key="object_id" value="(\d+)"', m.group(1)).group(1)
        ident = re.search(r'key="identify_id" value="(\d+)"', m.group(1)).group(1)
        labels[ident] = names[oid]
    return labels


def band_speeds(text, config_text, bands):
    """Actual extrusion speeds (last F on any move), fan (last M106) and extruded path length per
    feature and fan level, in print-height bands. Arc moves (G2/G3) count their chord length."""
    import re, collections
    labels = object_labels(config_text)
    z = None; feature = None; F = None; fan = None; label = None; pos = [None, None]
    out = collections.defaultdict(lambda: collections.defaultdict(set)); fans = collections.defaultdict(set)
    lengths = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(float)))
    for line in text.splitlines():
        if line.startswith('; Z_HEIGHT:'): z = float(line.split(':')[1]); continue
        if line.startswith('; FEATURE:'): feature = line[11:].strip(); continue
        if line.startswith('; start printing object, unique label id:'): label = line.rsplit(':', 1)[1].strip(); continue
        if line.startswith('; stop printing object'): label = None; continue
        if line.startswith('M106'):
            m = re.search(r'S(\d+)', line); fan = int(m.group(1)) if m else 0; continue
        if line.startswith('M107'): fan = 0; continue
        if line.startswith('G92'):
            if ' X' in line or ' Y' in line: pos = [None, None]
            continue
        if line.startswith(('G1 ', 'G0 ', 'G2 ', 'G3 ')):
            m = re.search(r'F(\d*\.?\d+)', line)
            if m: F = float(m.group(1))
            mx = re.search(r' X(-?\d*\.?\d+)', line); my = re.search(r' Y(-?\d*\.?\d+)', line)
            new = [float(mx.group(1)) if mx else pos[0], float(my.group(1)) if my else pos[1]]
            e = re.search(r'E(-?\d*\.?\d+)', line)
            # Printing moves only: retraction/unretraction lines carry E but no X/Y motion.
            if e and float(e.group(1)) > 0 and (mx or my) and z is not None and label in labels and F:
                part = labels[label]
                for lo, hi in bands.get(part, []):
                    # Membership by the layer middle (Z_HEIGHT is the layer top), as the slicer assigns regions.
                    if lo - 1e-6 <= z - .1 <= hi + 1e-6:
                        key = (part, round(z, 2))
                        out[key][feature].add(round(F / 60, 1)); fans[key].add(fan)
                        if pos[0] is not None and pos[1] is not None and new[0] is not None and new[1] is not None:
                            lengths[key][feature][str(fan)] += math.hypot(new[0] - pos[0], new[1] - pos[1])
            pos = new
    result = {}
    for (part, zz) in sorted(out):
        result.setdefault(part, {})[str(zz)] = {'features_mm_s': {k: sorted(v) for k, v in out[(part, zz)].items()},
                                                'fan_M106_0_255': sorted(x for x in fans[(part, zz)] if x is not None),
                                                'feature_length_mm_by_fan': {k: {fan_: round(v, 1) for fan_, v in d.items()} for k, d in lengths[(part, zz)].items()}}
    return result


def band_fan_summary(actual_bands):
    """Total extruded length per feature at each fan level over all band layers of each part."""
    import collections
    summary = {}
    for part, layers in actual_bands.items():
        totals = collections.defaultdict(lambda: collections.defaultdict(float))
        for row in layers.values():
            for feat, by_fan in row.get('feature_length_mm_by_fan', {}).items():
                for fan, mm in by_fan.items(): totals[feat][fan] += mm
        summary[part] = {feat: {fan: round(mm, 1) for fan, mm in d.items()} for feat, d in totals.items()}
    return summary


def arm_bonding(solid, yc, width, root_wall):
    """Lowest angle above the equator (degrees) at which the ring wall is still bonded to fixed material.

    Radial sections from the rod axis at the band centre; where the section exceeds the ring wall
    by more than 0.15 mm the crown is embedded in the saddle. Below that angle the arm is free.
    """
    inner, gap, thickness = h.ring_profile(width, root_wall)
    bonded_until = 90.
    for deg in range(90, -76, -1):
        a = math.radians(deg)
        hits = sorted(solid.ray_cast((0, yc, 0), (15 * math.cos(a), yc, 15 * math.sin(a))), key=lambda t: t.distance)
        if len(hits) < 2: continue
        section = float(np.linalg.norm(np.array(hits[1].position) - np.array(hits[0].position)))
        if section > thickness(a) + .15: bonded_until = deg
        else: break
    return {'crown_bonded_down_to_degrees_above_equator': bonded_until, 'free_arm_arc_degrees': bonded_until + 75,
            'method': 'Radial exported-mesh sections every degree at the band centre; bonded where the section exceeds the R7 wall profile by more than 0.15 mm.'}


def skirt_scan(solid, points, widths, band_y0, band_y1, width, root_wall, skin):
    """Walk each lead-in skirt: STL radial section and actual tracks on rays through the skirt."""
    a = h.P['arrow_ring']; k = 1 / math.tan(math.radians(a['lead_angle_degrees']))
    inner, gap, thickness = h.ring_profile(width, root_wall)
    tip = -math.pi / 2 + gap / 2; root = math.radians(a['root_phi_degrees_above_equator'])
    angles = np.linspace(tip, root, 97); mids = np.array([inner + thickness(x) / 2 for x in angles])
    s = np.concatenate([[0.], np.cumsum(np.diff(angles) * (mids[1:] + mids[:-1]) / 2)]); lead = k * s
    rows = []; worst_section = 9; worst_tracks = 9
    for y in np.arange(band_y1 + .3, band_y1 + lead[-1] - .3, 1.0):
        # Angles whose lead-in began at least 1 mm below this layer: inside the wall loop's
        # turnaround at the sloped edge, so both arm walls cross the radial ray.
        ok = angles[lead >= (y - band_y1) + 1.0]
        if not len(ok): continue
        for phi in np.linspace(ok[0], ok[-1], 4):
            for sign in (1, -1):
                origin = (sign * 4.4 * math.cos(phi), y, 4.4 * math.sin(phi)); direction = (sign * math.cos(phi), 0, math.sin(phi))
                thickness_mm, pa, pb = ray_section(solid, origin, direction)
                detail = {}
                layer, clusters = tracks_on_ray(points, widths, origin, direction, pa, pb, detail=detail)
                worst_section = min(worst_section, thickness_mm); worst_tracks = min(worst_tracks, len(clusters))
                rows.append({'assembly_y_mm': round(float(y), 3), 'phi_degrees': round(math.degrees(phi), 1), 'side': sign, 'STL_radial_mm': round(thickness_mm, 3), 'tracks': clusters, 'layer_top_mm': layer, **detail})
    thin = [r for r in rows if len(r['tracks']) < 2]
    if thin:
        print('SKIRT single-track rays:', json.dumps(thin[:8]), flush=True)
    assert worst_section >= skin - .05 and worst_tracks >= 2, (worst_section, worst_tracks)
    return {'rays': len(rows), 'minimum_STL_radial_section_mm': round(worst_section, 3), 'minimum_track_count': worst_tracks, 'samples': rows[:400],
            'skin_mm': skin, 'method': 'Native ray sections of the exported assembly STL through the skirt on 4 angles per 1 mm layer step, at least 1 mm inside the sloped leading edge, with actual bead-centre clusters on each ray.'}


def reach_guess(sn):
    return sn['bar_rail_mm'][0] - sn['bar_crown_mm'][0]


def classify(name, part_rows, to_assembly, actual=None):
    """Attach a snapshot-specific decision class to every broad partially unbacked row."""
    out = []
    cr = h.P['carrier_rings']; cg = h.P['cage']; sn = h.P['sensor']; s = h.P['slab']
    for row in part_rows:
        b = row['print_xy_bounds_mm']; top = row['layer_top_mm']
        # layer middle in the print frame -> assembly point of the patch centre
        centre = q.points(np.array([[(b[0] + b[2]) / 2, (b[1] + b[3]) / 2, top - .1]]), to_assembly)[0]
        x, y, z = [float(v) for v in centre]; r = math.hypot(x, z)
        cls = None
        interior = False
        if actual is not None:
            section = actual.slice(top - .1); patch = q.CrossSection([[[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]])
            interior = (patch - section.offset(-.5, q.JoinType.Round)).area() < .05
        if interior:
            cls = 'internal shell transition: solid shell layer over one sparse-infill layer inside a solid region (slicer behaviour, enclosed by walls)'
        elif name == 'Key_Carrier':
            roof = any(abs(x - kx) < 8.0 and -7.5 < (y - ky) < -6.8 for kx, ky in h.key_positions()) and z > h.PCB_Z - .1
            if roof: cls = 'bay roof span: 14.1 mm opening and 15.6 mm clip relief printed across air at the front edge of the bay; local slow-speed band applied, actual speeds and fan recorded in band_recipe_actual'
            elif cr['mid_band_y_mm'][0] - .3 <= y <= cr['saddle_y_mm'][1] and r < 6.2 and z < 4.3: cls = 'ring lead-in skirt: 45-degree arc rule, each layer rests on the previous arm layer'
            elif y < -7.6: cls = 'rounded finger nose: convex top rounds shrink layer by layer'
            elif abs(x) > s['upper_half_x_mm'] - .5 and y > s['lower_rear_y_mm'] - .5: cls = '45-degree shoulder face between the lower row and the narrower upper row'
            elif any(abs(x - (kx + (1 if rot else -1) * 5.4)) < 2.0 and (y - ky) * (1 if rot else -1) > 0 and abs(y - ky) < 7.5 for (kx, ky), rot in zip(h.key_positions(), h.key_rotations())) and z < h.PCB_Z + .1: cls = 'lightening window roof: 3.2 mm flat bridge at the window edge, or the 45-degree peak'
            elif abs(y - 17.8) < 7.3 and z > h.PCB_Z - .5: cls = 'upper bay walls above the inter-row strip'
            elif abs(y) < 7.3 and z > h.PCB_Z - .5: cls = 'lower bay roof: switch opening and clip relief roofs bridged across each bay'
            elif z < h.slab_bottom() + .1: cls = 'saddle flank or ring crown growing from the slab underside at 45 degrees or less'
        elif name == 'Battery_Holder':
            if r < 6.2 and z < 4.3 and y > cg['near_band_y_mm'][1] - .3: cls = 'ring lead-in skirt: 45-degree arc rule'
            elif abs(x) > cg['side_rail_x_mm'][0] - .3 and cg['gate_slot_y_mm'][0] - .3 < y < cg['gate_slot_y_mm'][0] + .3: cls = 'gate guide end cap closing over the slot: about 2.4 x 6.2 mm patch held by the outer wall and bottom ledge, inner top corner chamfered, local slow band applied'
            elif abs(x) > cg['side_rail_x_mm'][0] - .3 and y < cg['guide_y_mm'][1] + 2.6: cls = 'gate guide led in at 45 degrees from the side rail'
            elif abs(x) > cg['side_rail_x_mm'][0] - .3: cls = 'side zigzag strut at 45 degrees'
            else: cls = 'chevron lattice bar at 45 degrees to the bed'
        elif name == 'XIAO_Rod_Holder':
            if r < 6.2 and z < 4.3 and y > sn['near_band_y_mm'][1] - .3: cls = 'ring lead-in skirt: 45-degree arc rule'
            elif y < sn['near_band_y_mm'][1] + reach_guess(sn) + .3 and abs(x) > 1.0: cls = 'near end gusset bar growing at 45 degrees from the rail toward the saddle'
            elif abs(x) > 7.0 and y < 4.6: cls = 'near board cradle: ledge led in at 45 degrees from the rail and the 45-degree V stop face'
            elif r < 6.2: cls = 'saddle flank over the rod at 45 degrees'
        elif name == 'Battery_End_Gate':
            cls = 'flat gate on its broad face'
        out.append({**row, 'assembly_centre_mm': [round(x, 3), round(y, 3), round(z, 3)], 'decision_class': cls or 'UNCLASSIFIED - review'})
    return out


def views(name, actual, samples, widths, layers, rows, to_assembly, images, out_dir=None, tag=''):
    out_dir = Path(out_dir) if out_dir else OUT
    levels = sorted({r['layer_top_mm'] for r in rows})
    levels = sorted(set([.2] + levels))[:15]
    count = int(np.ceil(len(levels) / 3)); fig, axes = plt.subplots(count, 3, figsize=(15, 3.6 * count), squeeze=False)
    fig.suptitle(name + ' | first layer and every broad-overhang layer; actual sliced beads in print coordinates')
    for ax, top in zip(axes.flat, levels):
        prior = abs(layers - (top - .2)) < .001; ids = abs(layers - top) < .001
        ax.scatter(samples[prior, 0], samples[prior, 1], s=.8, c='#8a5cb7'); ax.scatter(samples[ids, 0], samples[ids, 1], s=.7, c='#007aa5')
        for level, colour, ls in [(top - .1, 'black', '-'), (top - .3, '#999999', '--')]:
            for poly in actual.slice(level).to_polygons():
                pp = np.array(poly); pp = np.vstack([pp, pp[:1]]); ax.plot(pp[:, 0], pp[:, 1], c=colour, lw=.65, ls=ls)
        bb = actual.bounding_box(); ax.set(xlim=(bb[0] - 1, bb[3] + 1), ylim=(bb[1] - 1, bb[4] + 1)); ax.set_aspect('equal'); ax.set_title(f'Layer top {top:g} mm'); ax.grid(alpha=.2)
    for ax in list(axes.flat)[len(levels):]: ax.set_visible(False)
    fig.text(.5, .005, 'Blue: current paths. Purple: previous actual paths. Black: current mesh section. Grey dashed: previous mesh section (not backing). Physical result unverified.', ha='center', fontsize=9)
    fig.tight_layout(rect=[0, .015, 1, .97]); target = out_dir / (name + tag + '-layer-views.png'); fig.savefig(target, dpi=120); plt.close(fig)
    images[target.name] = h.sha(target)


def inspect(project_name, out_dir=None, tag=''):
    """Audit a sliced project against the registered R16 meshes. `out_dir`/`tag` let the same
    audit run on a re-sliced copy (roundtrip16.py) without touching the delivered receipts."""
    out_dir = Path(out_dir) if out_dir else OUT
    project = Path(project_name) if Path(project_name).is_absolute() else OUT / project_name
    manifest = json.loads((OUT / 'manifest.json').read_text())
    data, features, stats, settings, offset, parts, gcode_text, config_text = read_project(project)
    assert not any(f.startswith(('Support', 'Brim', 'Skirt')) for f in features), features
    report = {'project_sha256': h.sha(project), 'manifest_sha256': h.sha(OUT / 'manifest.json'), 'checker_sha256': h.sha(Path(__file__)),
              'parser_sha256': h.sha(Path(q.__file__)), 'start_auditor_sha256': h.sha(h.R15 / 'start_audit.py'), 'spaces_sha256': h.sha(h.HERE / 'spaces16.py'),
              'features': features, 'parser_stats': stats, 'path_sample_step_mm': STEP,
              'settings': {k: settings.get(k) for k in ['printer_settings_id', 'print_settings_id', 'filament_settings_id', 'layer_height', 'wall_loops', 'sparse_infill_density', 'enable_support', 'brim_type', 'nozzle_temperature', 'textured_plate_temp', 'initial_layer_speed', 'elefant_foot_compensation', 'bridge_speed', 'overhang_1_4_speed', 'slow_down_for_layer_cooling', 'slow_down_min_speed', 'slow_down_layer_time', 'overhang_fan_speed', 'overhang_fan_threshold', 'enable_overhang_bridge_fan', 'fan_max_speed', 'fan_min_speed', 'enable_overhang_speed']},
              'xy_guard_mm': q.XY_GUARD, 'z_guard_mm': q.Z_GUARD, 'support_policy': 'No support, brim or CAD helper beads exist; model beads must still clear every functional region.',
              'parts': {}, 'physical_print_verified': False}
    images = {}
    for name, record in manifest['parts'].items():
        info = parts[name]; expected = trimesh.load_mesh(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl'))
        place = (info['vertices'].min(0) + info['vertices'].max(0) - expected.bounds.sum(0)) / 2
        assert np.max(abs(np.array([info['vertices'].min(0), info['vertices'].max(0)]) - place - expected.bounds)) < .03, (name, 'placement')
        local = data[:, :3] + offset - place; mask = np.all(local >= expected.bounds[0] - .4, 1) & np.all(local <= expected.bounds[1] + .4, 1)
        samples = local[mask]; w = data[mask, 3]; hh = data[mask, 4]; f = data[mask, 5].astype(int); tops = data[mask, 7]
        actual = q.solid(expected.vertices, expected.faces)
        project_solid = q.solid(info['vertices'] - place, info['faces'])
        difference = abs((actual - project_solid).volume()) + abs((project_solid - actual).volume()); assert difference < .05, (name, difference)
        assert len(samples) > 1000, (name, 'no paths')
        pa = np.array(record['print_to_assembly']); to_print = np.linalg.inv(pa)
        assembly = q.points(samples, pa)
        # Working spaces: every bead type.
        checks = {}; swept = {}
        for label, region in spaces16.regions(name).items():
            if isinstance(region, spaces16.Swept):
                worst = None
                for pose in region.poses():
                    res = q.inspect_region(pose.transform(to_print[:3, :]), samples, w, hh, f, features, pa, limit=4)
                    if worst is None or sum(res['violations'].values()) > sum(worst['violations'].values()): worst = res
                checks[label] = {**worst, 'poses': len(region)}; swept[label] = len(region)
            else:
                checks[label] = q.inspect_region(region.transform(to_print[:3, :]), samples, w, hh, f, features, pa, limit=4)
        # Layer starts against actual previous beads.
        starts = start_audit.inspect(q, actual, samples, hh, f, features, tops, pa, w)
        rows = classify(name, starts['partial_overhangs'], pa, actual)
        for row in rows:
            bb = row['print_xy_bounds_mm']; sel = (abs(tops - row['layer_top_mm']) < .001) & (samples[:, 0] >= bb[0] - .3) & (samples[:, 0] <= bb[2] + .3) & (samples[:, 1] >= bb[1] - .3) & (samples[:, 1] <= bb[3] + .3)
            hist = {}
            for fid in np.unique(f[sel]): hist[features[int(fid)]] = int((f[sel] == fid).sum())
            row['actual_features_in_patch'] = hist
        unclassified = [r for r in rows if r['decision_class'].startswith('UNCLASSIFIED')]
        # Bridges and floating shells by location.
        special = {}
        for key in ['Bridge', 'Floating vertical shell', 'Overhang wall']:
            if key in features:
                fid = features.index(key); sel = f == fid
                if sel.any():
                    pts = assembly[sel]; layer_set = sorted({round(float(t), 2) for t in tops[sel]})
                    special[key] = {'samples': int(sel.sum()), 'assembly_bounds_mm': [np.round(pts.min(0), 2).tolist(), np.round(pts.max(0), 2).tolist()], 'layers': layer_set[:40], 'layer_count': len(layer_set)}
        views(name, actual, samples, w, tops, starts['partial_overhangs'], pa, images, out_dir, tag)
        report['parts'][name] = {'normal_mesh_difference_mm3': difference, 'path_samples': int(mask.sum()), 'checks': checks, 'swept_space_poses': swept,
                                 'layer_starts': {k: v for k, v in starts.items() if k != 'partial_overhangs'}, 'partial_overhangs': rows,
                                 'unclassified_overhangs': unclassified, 'special_features': special, 'effective_settings': info['settings']}
        print(name, 'violations:', {k: v['violations'] for k, v in checks.items() if v['violations']}, 'floating:', len(starts['floating_components']), 'missing:', len(starts['missing_printed_components']), 'partial rows:', len(rows), 'unclassified:', len(unclassified), flush=True)
        for r in unclassified: print('   UNCLASSIFIED', json.dumps({k: r[k] for k in ['layer_top_mm', 'unbacked_mesh_area_mm2', 'print_xy_bounds_mm', 'direct_backed_fraction', 'assembly_centre_mm']}), flush=True)
    # Local recipe: actual speeds and fan in the slow bands versus a reference band of each part.
    recipe = h.P['print']['local_recipe']
    bands = {n: recipe.get(n + '_bands_mm', []) for n in manifest['parts']}
    actual_bands = band_speeds(gcode_text, config_text, bands)
    reference = band_speeds(gcode_text, config_text, {n: [[5.0, 6.0]] for n in manifest['parts'] if bands[n]})
    limits = {'Outer wall': 'outer_wall_speed', 'Inner wall': 'inner_wall_speed', 'Gap infill': 'gap_infill_speed',
              'Overhang wall': 'overhang_1_4_speed', 'Bridge': 'bridge_speed', 'Internal solid infill': 'internal_solid_infill_speed',
              'Sparse infill': 'sparse_infill_speed', 'Top surface': 'top_surface_speed'}
    too_fast = []
    for part, layers in actual_bands.items():
        for zz, row in layers.items():
            for feat, speeds in row['features_mm_s'].items():
                key = limits.get(feat)
                if key and max(speeds) > recipe['speeds_mm_s'][key] + .5: too_fast.append((part, zz, feat, speeds))
    assert actual_bands and all(part in actual_bands for part in bands if bands[part]), ('No extrusion found in a recipe band', list(actual_bands))
    report['band_recipe_actual'] = {'bands_mm': bands, 'requested_speeds_mm_s': recipe['speeds_mm_s'], 'band_wall_loops': recipe.get('band_wall_loops'),
                                    'actual_in_bands': actual_bands, 'band_feature_length_mm_by_fan': band_fan_summary(actual_bands),
                                    'reference_layers_5_to_6_mm': reference, 'features_faster_than_requested': too_fast,
                                    'note': 'Speeds are the last F before each extruding move; fan values are the last M106 S (0-255, 102 = 40 %, 229 = 90 %); lengths are extruded XY path lengths (arc chords). Fan follows the filament profile, not the band: only overhang-wall and bridge paths get the 90 % overhang/bridge fan.'}
    assert not too_fast, ('A band feature printed faster than the local recipe allows', too_fast[:4])
    # Strength screens in the assembly frame.
    strength = {}
    solids = {}
    for name in manifest['parts']:
        m = trimesh.load_mesh(OUT / (name + '-assembly.stl')); solids[name] = q.solid(m.vertices, m.faces)
    rows_by_part = {}
    for name, record in manifest['parts'].items():
        info = parts[name]; expected = trimesh.load_mesh(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl'))
        place = (info['vertices'].min(0) + info['vertices'].max(0) - expected.bounds.sum(0)) / 2
        local = data[:, :3] + offset - place; mask = np.all(local >= expected.bounds[0] - .4, 1) & np.all(local <= expected.bounds[1] + .4, 1)
        rows_by_part[name] = (q.points(local[mask], np.array(record['print_to_assembly'])), data[mask, 3])
    a = h.P['arrow_ring']
    ring_table = {}
    for name, bands, width, root_wall in [('Key_Carrier', [('mid', h.P['carrier_rings']['mid_band_y_mm'], True), ('rear', h.P['carrier_rings']['rear_band_y_mm'], False)], h.ROD['ring_width'], h.ROD['clip_root_wall']),
                                          ('Battery_Holder', [('near', h.P['cage']['near_band_y_mm'], True), ('far', h.P['cage']['far_band_y_mm'], False)], h.ROD['ring_width'], h.ROD['clip_root_wall']),
                                          ('XIAO_Rod_Holder', [('near', h.P['sensor']['near_band_y_mm'], True), ('far', h.P['sensor']['far_band_y_mm'], False)], h.P['sensor']['clip_width_mm'], h.ROD['sensor_clip_root_wall'])]:
        solid = solids[name]; pts, wd = rows_by_part[name]; entries = {}
        for label, (y0, y1), skirted in bands:
            yc = (y0 + y1) / 2
            sections = {}
            for ang in [-70, -55, 0, 90, 180, 235, 250]:
                sections[str(ang)] = round(radial_section(solid, yc, ang), 4)
            assert min(sections.values()) > .95, (name, label, sections)
            layer, tracks = polar_tracks(pts, wd, yc)
            assert all(len(v) >= 2 for v in tracks.values()), (name, label, tracks)
            entry = {'band_y_mm': [y0, y1], 'radial_STL_sections_mm': sections, 'sampled_layer_assembly_y_mm': layer, 'radial_track_centres_mm': tracks,
                     'arm_bonding': arm_bonding(solid, yc, width, root_wall)}
            if skirted:
                entry['lead_in_skirt'] = skirt_scan(solid, pts, wd, y0, y1, width, root_wall, a['skin_thickness_mm'])
                entry['band_start_backing'] = band_start_backing(pts, wd, y0, y1, +1, f'{name} {label} band first layer')
            entries[label] = entry
        ring_table[name] = entries
    strength['rings'] = ring_table
    table = {}
    ks, kw = rows_by_part['Key_Carrier']; bs, bw = rows_by_part['Battery_Holder']; xs, xw = rows_by_part['XIAO_Rod_Holder']; gs, gw = rows_by_part['Battery_End_Gate']
    K = solids['Key_Carrier']; B = solids['Battery_Holder']; X = solids['XIAO_Rod_Holder']; G = solids['Battery_End_Gate']
    z0 = h.PCB_Z; sb = h.slab_bottom()
    table['Key_Carrier'] = [
        feature(K, ks, kw, 'Saddle neck under the slab', [(0.013, 14.013, sb + .23), (0.013, 20.013, sb + .23), (0.013, 25.013, sb + .23)], (1, 0, 0), 3.6, 4,
                'Key presses and rod loads pass from the slab into both rings through this neck.', 'A 3 mm wide neck flaring at 45 degrees into a 7.6 mm tombstone saddle; the rear ring is on the bed.', 'Press every key while the carrier is on a rod; inspect the saddle for splits.'),
        layer_section(K, ks, kw, 8.9, (-18.4, 18.4, sb - .1, z0 + 2.3), 'Inter-row strip section at Y 8.9 (whole upper-row-to-lower-row interlayer load path)', 90., .6),
        layer_section(K, ks, kw, 9.7, (-18.4, 18.4, sb - .1, z0 + 2.3), 'Inter-row strip section at Y 9.7', 90., .6),
        feature(K, ks, kw, 'Plate lip over the clip relief', [(x, y + 7.4, z0 + 1.65) for x, y in h.key_positions()], (0, 0, 1), 1.15, 2,
                'Switch clips snap under this 0.75 mm lip; pulling a switch loads it.', 'Standard 1.2 mm plate thickness; the lip is backed by the solid wall behind the relief.', 'Insert and remove a switch twice; inspect the lip for cracks.'),
        feature(K, ks, kw, 'Outer bay wall', [(-27.1, 0.0, z0 + .5), (27.1, 0.0, z0 + .5)], (1, 0, 0), 1.15, 2,
                'The outer lower keys are pushed sideways against this wall by sideways cap play.', 'A 1.2 mm wall outside the clip relief, continuous into the plate and backplate.', 'Press the outer keys with sideways bias.'),
        feature(K, ks, kw, 'Thinned backplate', [(-24.7, -5.0, z0 - .5), (6.0, -5.0, z0 - .5), (-9.35 + 3.0, 17.8 + 5.0, z0 - .5), (9.35 - 3.0, 17.8 - 5.0, z0 - .5)], (0, 0, 1), 1.15, 2,
                'The switch housing bears on this plate; the socket pads stay 1.6 mm.', 'Backplate 1.2 mm away from the socket zone, 1.6 mm under the socket bosses.', 'Push a switch home and remove it; look for backplate cracks at the holes.'),
        layer_section(K, ks, kw, 12.0, (18.3, 27.8, sb - .1, z0 + 2.3), 'Right shoulder section at Y 12.0 (outer lower bay hangs from the upper slab here)', 15., .6),
        layer_section(K, ks, kw, 12.0, (-27.8, -18.3, sb - .1, z0 + 2.3), 'Left shoulder section at Y 12.0', 15., .6)]
    lv = h.cage_levels(); cg = h.P['cage']
    table['Battery_Holder'] = [
        feature(B, bs, bw, 'Side rail bottom chord', [(11.4, 5.0, lv['floor_bottom'] + .8), (-11.4, 5.0, lv['floor_bottom'] + .8)], (1, 0, 0), 1.55, 3,
                'Cell weight and handling load the chords and zigzag struts.', '1.6 mm chords joined by 45-degree struts; the far end plate sits on the bed.', 'Flex the cage gently by hand after printing.'),
        feature(B, bs, bw, 'Floor spine', [(0, 5.0, lv['floor_bottom'] + .8), (0, -8.0, lv['floor_bottom'] + .8)], (1, 0, 0), 1.75, 3,
                'Every floor chevron lands on the spine and the spine carries both rings.', '1.8 mm spine widening to 7.6 mm saddles at both rings.', 'Load the cell and slide the module on the rod; inspect the spine.'),
        feature(B, bs, bw, 'Gate guide slot wall beside the gate (outside the slot Y range)', [(11.0, -12.9, lv['floor_top'] + 3.0), (-11.0, -12.9, lv['floor_top'] + 3.0)], (1, 0, 0), 1.55, 3,
                'The gate bears in Y against these guide faces; as in R15 the slot is open toward the cage so the bar can pass, and only the outer wall takes the wedge interference.', 'Guide block 2.25 mm thick each side of the 2.1 mm slot in Y, led in at 45 degrees from the side rail.', 'Fit the gate gently; stop if the guide whitens.'),
        feature(B, bs, bw, 'Gate guide outer wall', [(13.8, -14.9, lv['floor_top'] + 3.0), (-13.8, -14.9, lv['floor_top'] + 3.0)], (1, 0, 0), 1.55, 3,
                'Wedge interference loads the outer wall across its layers.', '1.6 mm outer wall.', 'Fit and remove the gate three times.'),
        feature(B, bs, bw, 'Floor chevron bar', [(5.3, -11.8, lv['floor_bottom'] + .8)], (1, 0, 1), 1.5, 3,
                'The cell rests on the chevron bars.', '1.6 mm bars at 45 degrees to the bed and to the side rails.', 'Inspect the bars under the loaded cell.')]
    table['Battery_End_Gate'] = [
        feature(G, gs, gw, 'Wedge neck', [(12.2, -14.9, lv['floor_top'] + 4.5), (-12.2, -14.9, lv['floor_top'] + 4.5)], (1, 0, 0), 1.15, 2,
                'Gate insertion and removal flex the wedge necks.', 'R15 wedge profile retained; the gate prints flat.', 'Cycle the gate without a cell first.'),
        feature(G, gs, gw, 'Top grab bar', [(0, -14.9, lv['roof_bottom'] + .4)], (0, 0, 1), 1.75, 4,
                'The bar is pulled to remove the gate.', '1.9 mm deep bar above the cell, with two stubs at the cell end corners.', 'Pull the gate out by its bar only.'),
        feature(G, gs, gw, 'Cell stub', [(7.75, -14.9, lv['floor_top'] + 2.0), (-7.75, -14.9, lv['floor_top'] + 2.0)], (1, 0, 0), 2.4, 5,
                'The stubs stop the cell at its end corners away from the lead end.', '2.5 mm wide stubs, 1.6 mm thick, open centre for the leads.', 'Check the leads pass between the stubs without being pinched.')]
    sn = h.P['sensor']; bz = h.SENSOR['board_z']
    table['XIAO_Rod_Holder'] = [
        feature(X, xs, xw, 'Board rail', [(10.2, 10.0, 8.6), (-10.2, 10.0, 8.6)], (1, 0, 0), 1.95, 4,
                'Board insertion, USB plugging and lead snags load the rails.', '2.0 x 2.8 mm rails running end to end, bonded to both ring planes.', 'Insert the board and plug USB; check the rails.'),
        feature(X, xs, xw, 'Keel over the rod', [(0, 12.0, 5.2), (0, 18.0, 5.2)], (1, 0, 0), 2.9, 4,
                'The keel joins both crowns and backs the near ring saddle.', '3 mm keel from end to end.', 'Slide the holder onto the rod; inspect the keel.'),
        feature(X, xs, xw, 'End bars', [(6.0, 22.2, 6.65), (-6.0, 22.2, 6.65), (6.0, -3.8, 6.65), (-6.0, -3.8, 6.65)], lambda c: (-.37 * np.sign(c[0]), 0, 1.0), 2.0, 4,
                'Board loads pass from the rails through the bars into the ring crowns.', '2.2 mm flat bars in the ring planes; the far pair prints on the bed, the near pair bridges 6 mm onto the saddle.', 'Press the board down gently; inspect the bar roots.'),
        feature(X, xs, xw, 'Board ledge root into the rail', [(8.9, 1.7, bz - .2), (-8.9, 1.7, bz - .2), (8.9, 21.8, bz - .2), (-8.9, 21.8, bz - .2)], (1, 0, 0), 2.0, 3,
                'The board edges rest on the ledges; the ledge gusset roots into the rail.', '45-degree gussets from the rails at the header-free short ends, measured through the gusset into the rail.', 'Seat the board and press on it lightly.')]
    strength['fixed_features'] = table
    # Complete intervening-layer scans through every loaded-to-anchor path.
    cr = h.P['carrier_rings']
    scans = {'Key_Carrier': [
        path_scan(K, ks, kw, (cr['saddle_y_mm'][0], cr['rear_band_y_mm'][1] - .3), (-6.5, 6.5, 2.5, sb + .05), 'Slab-to-ring saddle and crown, full length',
                  12., .6, 'Every key press and rod load passes through this saddle into the two rings.', 'Saddle neck 3 mm at the slab flaring to a 7.6 mm tombstone; the scan covers every layer from the mid ring to the bed.'),
        path_scan(K, ks, kw, (7.2, 10.6), (-18.5, 18.5, sb - .05, z0 + 2.3), 'Inter-row strip, every layer between the lower reliefs (Y 7.15) and the upper reliefs (Y 10.65)',
                  90., .6, 'The upper row hangs from this strip.', 'Solid strip 3.5 mm thick over the full upper-slab width.'),
        path_scan(K, ks, kw, (9.1, 16.5), (18.3, 27.8, sb - .05, z0 + 2.3), 'Right shoulder root region, every layer (Y 9.1-16.5; the 45-degree taper narrows to a point at Y 18.45 against the upper slab wall by design)', 6., .6,
                  'The lower-right bay hangs from the upper slab through this shoulder while printing and in use.', 'Solid 45-degree shoulder, 3.85 mm thick, at least 1.9 mm wide over the scanned span.'),
        path_scan(K, ks, kw, (9.1, 16.5), (-27.8, -18.3, sb - .05, z0 + 2.3), 'Left shoulder root region, every layer (Y 9.1-16.5)', 6., .6,
                  'As the right shoulder.', 'As the right shoulder.'),
        path_scan(K, ks, kw, (-7.0, 8.2), (-28, 28, sb - .05, z0 + 2.3), 'Lower row, every layer through the bays', 60., .5,
                  'Lower key presses and the finger load the lower row around its five openings and the backplate ligaments.', 'Bay walls, lips and the thinned backplate; ligaments beside the windows are 1.2 mm.')],
        'XIAO_Rod_Holder': [
        path_scan(X, xs, xw, (-2.6, 21.0), (-11.5, 11.5, -1, 11), 'Rails, keel, struts and saddle between the ring planes, every layer', 15., .6,
                  'The board and USB loads pass along the rails into both ring planes; this is the former 21 mm free-column region.', 'Two 2 x 2.8 mm rails, a 3 mm keel, a 7.6 mm saddle and two diagonal struts tie the columns mid-height.')]
        + cradle_scans(X, xs, xw),
        'Battery_Holder': [
        path_scan(B, bs, bw, (-12.6, 15.7), (-15, 15, 3.0, 12.5), 'Cage lattice between the gate guides and the end plate, every layer', 20., .6,
                  'Cell weight, handling and rod loads pass through the chords, chevrons, spine and struts.', '1.6 mm chords and bars at 45 degrees; the spine carries both rings.')]}
    strength['path_scans'] = scans
    report['strength'] = strength
    report['passed'] = all(not c['violations'] for p in report['parts'].values() for c in p['checks'].values()) \
        and all(not p['layer_starts']['floating_components'] and not p['layer_starts']['missing_printed_components'] and not p['unclassified_overhangs'] for p in report['parts'].values())
    report['images_sha256'] = images
    target = out_dir / f'slice-clearances{tag}.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    assert report['passed'], f'See {target.name}'
    print('Actual beads clear every working space; every layer start is backed; all overhang rows classified; sections and tracks passed.')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--project', default='R16-A1-mini-PETG.gcode.3mf'); a = p.parse_args(); inspect(a.project)
