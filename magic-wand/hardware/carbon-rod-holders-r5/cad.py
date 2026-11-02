#!/usr/bin/env python3
"""Five bought Choc switches on a close, closed-ring carbon-tube carrier.

Ethan's 'bottom plug bit' is the Choc hot-swap socket. Its flat underside
gets a supported flat seat, not the R1/R3 annular locating pads. PCB Z=0 in
the purchased-part reference; the mounting lip is 1.05..2.25 mm above it.
"""
from pathlib import Path
import importlib.util
import json
import math
import sys
from functools import lru_cache
import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent
P = json.loads((HERE / 'parameters.json').read_text())

def load(name, folder):
    spec = importlib.util.spec_from_file_location('r5_' + name, folder / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

r2 = load('cad', HERE.parent / 'carbon-rod-holders-r2')
base = r2.base
for name in ['box', 'rr', 'rib', 'cyl', 'tube_y', 'union', 'mesh', 'sha']:
    globals()[name] = getattr(base, name)

OPTIONS = {'front': 'Battery above middle key', 'rear': 'Battery behind rod', 'lower': 'Battery below keys'}

def key_positions():
    # Ethan wants less thumb travel: retain five full-size keys and the centre gap.
    k = P['keys']
    return [(-k['pitch'], 0), (0, 0), (k['pitch'], 0),
            (-k['upper_half_spacing'], k['row_spacing']), (k['upper_half_spacing'], k['row_spacing'])]

@lru_cache(maxsize=1)
def source_hardware():
    result = {}
    for name in ['switch', 'socket']:
        data = json.loads((HERE / 'references' / (name + '.json')).read_text())
        result[name] = mf.Manifold(mf.Mesh(np.array(data['vertices'], dtype=np.float32), np.array(data['faces'], dtype=np.uint32)))
        assert result[name].status() == mf.Error.NoError, name
    return result

def seated_hardware():
    raw = source_hardware()
    socket = raw['socket']
    # The carrier has no PCB: its floor, not the boss face, locates the socket.
    dz = P['keys']['socket_pocket_bottom'] - socket.bounding_box()[2]
    return {'switch': raw['switch'], 'socket': socket.translate((0,0,dz))}

def key_seat(opening=None, outer_side=0):
    k = P['keys']
    hole = opening or k['opening']
    bottom = k['plate_bottom']
    face = rr(16.4, 18.2, 1.1, bottom, bottom + k['plate_thickness'])
    face -= rr(hole, hole, .2, bottom - .1, bottom + k['plate_thickness'] + .1)
    # Keep the flange-bearing surface flat; a wide top chamfer removed its
    # narrow support land. Clean first-layer squish on the physical coupon.
    # Broad flat-backed socket floor, with low rigid side stops. The solder
    # tabs are outside the body and remain accessible through the open sides.
    floor = rr(15.6, 12, 1.1, k['socket_floor_bottom'], k['socket_floor_top']).translate((2.5, 5.5, 0))
    # A shallow convex outline recess locates the flat socket back. Unlike R4's
    # initial raised guide posts, the connected rim prints deck-down without
    # starting isolated posts in mid-air. The .3mm outline allowance also
    # accommodates the newer documented socket revision; test the coupon.
    pocket = source_hardware()['socket'].project().hull().offset(.3)
    floor -= mf.Manifold.extrude(pocket, 1).translate((0, 0, k['socket_pocket_bottom']))
    pieces = [face, floor,
              box(7.85, 9.2, 5.3, 7.5, k['socket_floor_bottom'], bottom + .65),
              box(-1.5, 1.5, 8.45, 10.1, k['socket_floor_bottom'], bottom + .65)]
    for side in [-1, 1]:
        x = side * 7.9
        for y in [-9.7, 9.7]:
            if y < 0 and side == outer_side:
                continue  # No free-ended outer leg against the index finger.
            pieces.append(rib((x, y, -4.5), (x, math.copysign(8.0, y), bottom + .55), 1.05))
        if side == 1:
            pieces.append(rib((x, 9.7, -4.5), (side * 6.7, 6.8, k['socket_floor_bottom'] + .7), .95))
        # The left spur ended short of the floor; the rear arm/wall carries
        # that side. Omit the unused tip rather than leaving a finger poke.
    pieces.append(rib((-8.4, 10.5, -4.5), (9.0, 10.5, -4.5), 1.25))
    # This small rear arm joins the floor to the left load rail without a
    # narrow isolated post. Hardware clearance is verified after final union.
    pieces.append(rib((-7.9, 9.7, -4.5), (-2.5, 8.8, -4.5), 1.1))
    for x in [-7.9, 7.9]:
        pieces.append(box(x - .7, x + .7, 8.8, 10.4, -4.5, bottom + .6))
    return union(pieces)

def wire_bus(y0=-20, y1=57):
    s = P['structure']
    return cyl(s['wire_bus_diameter'] / 2, y0, y1).rotate((-90, 0, 0)).translate((s['wire_bus_x'], 0, s['wire_bus_z']))

def ring(y, diameter=None):
    # Ethan's "brace area that attaches to the rod" is this sliding bearing,
    # distinct from the thumb brace above the middle key. One inner liner sets drag.
    p = P['rod']
    inner = (diameter or p['diameter'] + p['diametral_clearance']) / 2
    shape = tube_y(inner, inner + p['ring_wall'], y - p['ring_width'] / 2, y + p['ring_width'] / 2)
    # Lead-in at both ends, without changing the cylindrical bearing bore.
    for sign in [-1, 1]:
        edge = y + sign * p['ring_width'] / 2
        chamfer = mf.Manifold.cylinder(.35, inner, inner + .35, 64).rotate((-90 * sign, 0, 0)).translate((0, edge - sign * .35, 0))
        shape -= chamfer
    return shape

def battery_pose(option):
    b = P['battery']
    if option == 'lower':
        return -52.0, b['floor_z'], 1
    return b['start_y'], b['floor_z'], -1 if option == 'rear' else 1

def battery_shape(option, reserve=False):
    b = P['battery']; y, z, side = battery_pose(option)
    w = b['reserve_width'] if reserve else b['nominal_width']
    length = b['reserve_length'] if reserve else b['nominal_length']
    thick = b['reserve_thickness'] if reserve else b['nominal_thickness']
    # The reserve includes cell wrapping and lead allowance, not measured tape.
    y += b['clearance_per_side'] + (b['reserve_length'] - length) / 2
    shape = box(-w / 2, w / 2, y, y + length, z, z + thick)
    return shape if side == 1 else shape.mirror((0, 0, 1))

def battery_cradle(option):
    b = P['battery']; y0, z, side = battery_pose(option)
    w = b['reserve_width'] + 2 * b['clearance_per_side']
    length = b['reserve_length'] + 2 * b['clearance_per_side']
    y1 = y0 + length
    parts = []
    for sign in [-1, 1]:
        x = sign * (w / 2 + .7)
        parts.append(box(x - .7, x + .7, y0 - 1, y1 + 1, z - b['floor_thickness'], z + 2.0))
        # Local corner flare closes the rail/diagonal junction as the deck
        # is lowered; it avoids tiny enclosed Boolean seam cavities.
        parts.append(rib((x,y0-.85,z+.9),(x,y0-.85,z+1.1),.7))
        for y in [y1 - 10, y1 - 2]:
            ear = rr(5.4, 5.5, 1.1, z - 1.3, z + .2) - rr(2.6, 3.2, .6, z - 1.5, z + .4)
            parts.append(ear.translate((x + sign * 2.3, y, 0)))
    for y in [y0 - .5, y0 + length / 3, y0 + length * 2 / 3, y1 + .5]:
        parts.append(rib((-w / 2, y, z - .7), (w / 2, y, z - .7), .7))
    for y in [y0 - .5, y1 + .5]:
        for sign in [-1, 1]:
            parts.append(box(sign * (w / 2 - 1.3) - 1.4, sign * (w / 2 - 1.3) + 1.4, y - .7, y + .7, z - .7, z + 2.0))
    # Symmetric triangular roots feed the cradle into complete rings. This
    # avoids R3's single long strut at the battery end.
    anchors = [-55, -18] if option == 'lower' else [11.5, 48.5]
    for anchor, y in zip(anchors, [y0 - 1, y1 + 1]):
        parts.append(ring(anchor))
        for sign in [-1, 1]:
            parts.append(rib((sign * 3.8, anchor, 4.1), (sign * (w / 2 + .7), y, z - .2), 1.35))
    shape = union(parts)
    return shape if side == 1 else shape.mirror((0, 0, 1))

def carrier(option='front'):
    k = P['keys']; z = k['pcb_z']; r = P['structure']['rail_radius']
    pieces = [key_seat(outer_side=1 if x > 0 else -1 if x < 0 else 0).translate((x, y, z)) for x, y in key_positions()]
    for row, half in [(0, k['pitch']), (k['row_spacing'], k['upper_half_spacing'])]:
        # Two separated load rails make a shallow truss, rather than relying
        # on one thin rod. The upper centre stays open for Ethan's thumb.
        spans = [(-half - 8.2, half + 8.2)] if row == 0 else [(-half - 8.2, -half + 8.2), (half - 8.2, half + 8.2)]
        for x0, x1 in spans:
            pieces.append(rib((x0, row - 9.4, z + 1.4), (x1, row - 9.4, z + 1.4), r))
            pieces.append(rib((x0, row + 10.5, z - 4.5), (x1, row + 10.5, z - 4.5), r))
    # Deck bridges under the gaps provide a second direct load path between
    # neighbouring seats. Their top shares the mounting plane, below caps.
    for sign in [-1, 1]:
        for yy in [-4, 7.3]:
            pieces.append(box(min(sign*7.8, sign*(k['pitch']-7.8)), max(sign*7.8, sign*(k['pitch']-7.8)), yy-1.5, yy+1.5, z+k['plate_bottom'], z+2.25))
        for dx in [-7.5, 7.5]:
            a=rr(2.5,2.5,.6,z+k['plate_bottom'],z+2.25).translate((sign*(k['pitch']+dx),8.8,0))
            b=rr(2.5,2.5,.6,z+k['plate_bottom'],z+2.25).translate((sign*(k['upper_half_spacing']+dx),k['row_spacing']-8.8,0))
            pieces.append(mf.Manifold.batch_hull([a,b]))
        # Deep, thin webs beside the central ring resist bending/twist. Round
        # rails alone looked connected but left outer seats on a long lever.
        for yy in [-9.4,10.5]:
            pieces.append(box(min(sign*7,sign*k['pitch']),max(sign*7,sign*k['pitch']),yy-.7,yy+.7,z-4.5,z+2.25))
    for sign in [-1, 1]:
        # Outer and inner diagonals connect each top key to the lower row.
        for dx in [-7.8, 7.8]:
            pieces.append(rib((sign * (k['pitch'] + dx), 9.7, z - 4.5),
                              (sign * (k['upper_half_spacing'] + dx), k['row_spacing'] - 8, z + 1.5), 1.2))
        # The inner rear braces sit below the sockets as the upper keys move
        # inward. Keep their centre clear of the battery reserve.
        path = [(sign * 7.8, 10.5, z + 1.0), (sign * 13.6, 14, z - 5.2),
                (sign * 13.6, k['row_spacing'] + 11.5, z - 5.2),
                (sign * (k['upper_half_spacing'] - 8.2), k['row_spacing'] + 11.5, z - 5.2),
                (sign * (k['upper_half_spacing'] - 7.8), k['row_spacing'] + 10.5, z - 5.2)]
        pieces.extend(rib(a, b, 1.2) for a, b in zip(path[:-1], path[1:]))
    for y in [-12, 11.5]:
        pieces.append(ring(y))
        for sign in [-1, 1]:
            target_y = -10.5 if y == -12 else 10.5 if y == 11.5 else 43
            target_x = 7.8 if y != 48.5 else 12.4
            pieces.append(rib((sign * 3.8, y, 4.1), (sign * target_x, target_y, z + 1.1 if y != 48.5 else 5), 1.6))
    # The front thumb brace remains even with the battery behind/below. Its
    # load goes to the ring/frame, never through the LiPo pouch.
    pieces.append(rib((-7.8, 11.5, z + 1.35), (7.8, 11.5, z + 1.35), 1.3))
    pieces.append(battery_cradle(option))
    if option == 'lower':
        for sign in [-1, 1]:
            pieces.append(rib((sign * 5.1, -55, 0), (sign * 5.1, -12, 0), 1.1))
    shape = union(pieces)
    # A flat common print face keeps every mounting lip on the bed.
    shape ^= box(-80,80,-90,90,-40,z+2.25)
    rod = P['rod']
    shape -= cyl((rod['diameter'] + rod['diametral_clearance']) / 2, -80, 80).rotate((-90, 0, 0))
    return shape - wire_bus(-80, 80)

def sensor_holder():
    return r2.sensor_holder()

def references(option='front'):
    z = P['keys']['pcb_z']; hardware = seated_hardware()
    refs = {'battery': battery_shape(option), 'rod': tube_y(3.5, 4, -64 if option == 'lower' else -21, 60)}
    for i, (x, y) in enumerate(key_positions()):
        for name, shape in hardware.items():
            refs[f'key_{i}_{name}'] = shape.translate((x, y, z))
        refs[f'key_{i}_cap'] = rr(16.6, 17.5, 1.4, z + 6.1, z + 9.1).translate((x, y, 0))
    old = r2.references()
    for name in ['pcb', 'usb']:
        refs[name] = old[name]
    refs['wire'] = r2.wire_route()
    return refs

def export():
    out = HERE / 'exports'; out.mkdir(exist_ok=True)
    record = {}
    models = {**{'Carrier_' + option: carrier(option) for option in OPTIONS}, 'XIAO_Rod_Holder': sensor_holder()}
    for name, solid in models.items():
        if name != 'XIAO_Rod_Holder':
            solid = solid.simplify(.0001)
        assert solid.status() == mf.Error.NoError, (name, solid.status())
        m = mesh(solid)
        assert m.is_watertight and m.is_winding_consistent and len(m.split()) == 1, (name, len(m.split()))
        m.export(out / (name + '-assembly.stl'))
        oriented = m.copy(); rot = trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]); oriented.apply_transform(rot)
        shift = trimesh.transformations.translation_matrix(-oriented.bounds[0]); oriented.apply_transform(shift)
        normalisation = 0.0
        if name != 'XIAO_Rod_Holder':
            # Binary STL rounds vertices to float32. Normalise after that
            # rounding so collapsed seam triangles cannot leave open edges.
            rounded = mf.Manifold(mf.Mesh(np.asarray(oriented.vertices,dtype=np.float32),np.asarray(oriented.faces,dtype=np.uint32)))
            assert rounded.status() == mf.Error.NoError
            normalisation = abs(rounded.volume() - oriented.volume)
            assert normalisation < .01, normalisation
            oriented = mesh(rounded)
        oriented.export(out / (name + '.stl'))
        final = trimesh.load_mesh(out / (name + '.stl'))
        assert final.is_watertight and len(final.split()) == 1, name
        record[name] = {'bounds_mm': m.bounds.tolist(), 'volume_mm3': m.volume, 'solid_PETG_g': m.volume / 1000 * P['print']['density_g_cm3'], 'stl_float32_volume_change_mm3': normalisation, 'body_count': 1, 'watertight': True, 'stl_sha256': sha(out / (name + '.stl')), 'print_to_assembly': np.linalg.inv(shift @ rot).tolist()}
    sources = [HERE / 'cad.py', HERE / 'parameters.json', HERE / 'reference_models.py', HERE.parent / 'carbon-rod-holders-r2/cad.py', HERE.parent / 'carbon-rod-holders-r2/parameters.json', HERE.parent / 'carbon-rod-holders/cad.py', HERE.parent / 'carbon-rod-holders/parameters.json']
    sources += sorted((HERE / 'references').glob('*.json')) + sorted((HERE / 'references').glob('*.stp'))
    manifest = {'revision': P['revision'], 'source_sha256': {str(p.relative_to(HERE)) if p.is_relative_to(HERE) else str(Path('..') / p.relative_to(HERE.parent)): sha(p) for p in sources}, 'parts': record, 'physical_fit_verified': False, 'physical_strength_verified': False}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print({name: round(r['solid_PETG_g'], 3) for name, r in record.items()}, flush=True)

if __name__ == '__main__':
    export()
