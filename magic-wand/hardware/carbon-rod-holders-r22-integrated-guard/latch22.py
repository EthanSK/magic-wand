#!/usr/bin/env python3
"""R22 XIAO near-keeper latch: push-to-click, seated and pull-out motion for the assembly guide.

Uses the exported R22 meshes only (XIAO_Near_Keeper and XIAO_Rod_Holder, both byte copies of the
R19/R20 parts) and the R18 keeper/ridge parameters that built them. Nothing here changes a part.

How the keeper works (from holder18.keeper, holder18.sensor_holder and the R17 retainer brief):
- Paws (the two fingers, x 6.8-9.4 mm) lie over the bare near corners of the board and keep it down.
- Ears (the tabs sticking out at each side, x 10.6-13 mm) slide in the holder's rigid side grooves.
  The grooves hold the keeper down and guide it; the closed groove end stops it going too far.
- The tongue is a sprung beam inside the outline, cut free by a 0.6 mm slit, rooted at x -6.6 mm.
  Its tooth hangs 0.35 mm below the crest of a 45-degree ridge on the holder keel. Pushing in, the
  tooth rides up the ridge, the tongue bends up and the tooth drops behind the crest: the click.
  Only that catch stops the keeper sliding back out. The wires play no part.
- Removal (R18 README): pull by the ears. The ridge is 45 degrees on both faces, so the same bend
  lets the tooth ride back over it. No lift tab was designed; lifting the tongue tip clears the
  tooth geometrically (checked below), but finger access through the slit is not verified.

The tongue bend is drawn as a linear point-load cantilever at the tooth centre, for the viewer only.
It is applied as one absolute morph target: vertex + blend * lift(vertex), identical in the viewer
(position interpolation) and in the collision check here.
"""
import sys
sys.dont_write_bytecode = True
import math
import numpy as np, manifold3d as mf, trimesh
import holder22 as h

OUT = h.HERE / 'exports'; GUIDE = OUT / 'guide'
K = h.h18.K; TG = K['tongue']; RD = K['ridge']; RET = h.h18.RET
KEEPER_FILE, HOLDER_FILE = 'XIAO_Near_Keeper-assembly.stl', 'XIAO_Rod_Holder-assembly.stl'
ROOT_X, TIP_X = TG['x_mm']; TY0, TY1 = TG['y_mm']; SLIT = TG['slit_mm']
TOOTH_X, TOOTH_Y, TOOTH_Z0 = TG['tooth_x_mm'], TG['tooth_y_mm'], TG['tooth_bottom_z_mm']
CREST_Y, CREST_Z, RIDGE_BASE = RD['crest_y_mm'], RD['crest_z_mm'], RD['base_z_mm']
HOLDER_Y0 = h.h18.S['y_mm'][0]
TONGUE_T = RET['plate_z_mm'][1] - TG['thin_from_z_mm']          # 1.2 mm beam
CLEAR = .05                                                     # drawn clearance over the crest
FULL = CREST_Z - TOOTH_Z0 + CLEAR                               # lift at the tooth's root-side edge
A = (TOOTH_X[0] + TOOTH_X[1]) / 2 - ROOT_X                      # load point: tooth centre, 6.6 mm
EPS = 1e-3
assert SLIT > 10 * EPS and A > 0


def _shape(xp):
    xp = np.clip(xp, 0, None)
    return np.where(xp <= A, xp ** 2 * (3 * A - xp) / (2 * A ** 3), 1 + 1.5 * (xp - A) / A)


DELTA_A = FULL / float(_shape(np.array([TOOTH_X[0] - ROOT_X]))[0])   # deflection at the tooth centre at blend 1


def lift(points):
    """Absolute Z displacement at blend 1 for every point in the tongue and tooth; zero elsewhere."""
    p = np.asarray(points, float); x, y = p[:, 0], p[:, 1]
    inside = (x >= ROOT_X - EPS) & (x <= TIP_X + EPS) & (y >= TY0 - EPS) & (y <= TY1 + EPS)
    d = np.zeros_like(p); d[:, 2] = DELTA_A * _shape(x - ROOT_X) * inside
    return d


def needed_blend(dy):
    """Smallest drawn blend whose tooth clears the 45-degree ridge with the keeper moved by dy along Y."""
    lo, hi = TOOTH_Y[0] + dy, TOOTH_Y[1] + dy
    lo = max(lo, HOLDER_Y0)
    if hi < lo: return 0.
    dist = 0. if lo <= CREST_Y <= hi else min(abs(CREST_Y - lo), abs(CREST_Y - hi))
    ridge = max(RIDGE_BASE, CREST_Z - dist)
    need = ridge - TOOTH_Z0
    return 0. if need <= 0 else min(1., (need + CLEAR) / FULL)


def route():
    return float(RET['route_travel_mm']) if 'route_travel_mm' in RET else 12.


def push_path(n=61):
    """(dy, blend) from the start of the slide to seated. Critical ridge contacts are included exactly."""
    r = route(); crit = [CREST_Y - TOOTH_Y[1], CREST_Y - TOOTH_Y[0], CREST_Y - TOOTH_Y[1] - (CREST_Z - TOOTH_Z0), CREST_Y - TOOTH_Y[0] + (CREST_Z - TOOTH_Z0)]
    dys = sorted(set(np.round(np.r_[np.linspace(-r, 0, n), [c for c in crit if -r < c < 0]], 6)))
    return [(float(d), needed_blend(d)) for d in dys]


def deflected(base_mesh, blend):
    v = np.asarray(base_mesh.vertices, float) + blend * lift(base_mesh.vertices)
    m = mf.Manifold(mf.Mesh(np.asarray(v, np.float32), np.asarray(base_mesh.faces, np.uint32)))
    assert m.status() == mf.Error.NoError, m.status()
    return m


def write_pair(name, solid=None, source=None):
    """Base STL plus its morph target, same triangle order. Returns relative guide paths."""
    GUIDE.mkdir(parents=True, exist_ok=True)
    if solid is not None:
        base_path = GUIDE / f'{name}.stl'; h.mesh(solid).export(base_path); rel = 'guide/' + base_path.name
    else:
        base_path = OUT / source; rel = source
    soup = trimesh.load_mesh(base_path, process=False)
    target = trimesh.Trimesh(np.asarray(soup.vertices, float) + lift(soup.vertices), soup.faces, process=False)
    tpath = GUIDE / f'{name}-tongue-lifted.stl'; target.export(tpath)
    back = trimesh.load_mesh(tpath, process=False)
    assert len(back.vertices) == len(soup.vertices) and len(back.faces) == len(soup.faces), name
    return rel, 'guide/' + tpath.name


def collision_checks(body, board=None):
    """Real triangle-mesh overlaps at every sampled pose, with the viewer's interpolation."""
    keeper_mesh = trimesh.load_mesh(OUT / KEEPER_FILE)    # merged copy of the exported keeper
    path = push_path(); rows = []
    rest = deflected(keeper_mesh, 0.)
    lifted = deflected(keeper_mesh, 1.)
    for dy, b in path:
        k = deflected(keeper_mesh, b).translate((0, dy, 0))
        rows.append((dy, b, float((body ^ k).volume()), float((body ^ rest.translate((0, dy, 0))).volume())))
    flexed_route = max(float((body ^ lifted.translate((0, dy, 0))).volume()) for dy, _ in path)
    worst = max(rows, key=lambda r: r[2])
    out = {'samples': len(rows), 'max_overlap_with_drawn_bend_mm3': round(worst[2], 5), 'at_dy_mm': round(worst[0], 3), 'at_blend': round(worst[1], 3),
           'max_rigid_overlap_mm3': round(max(r[3] for r in rows), 5), 'seated_overlap_mm3': round(rows[-1][2], 5),
           'full_route_with_tongue_lifted_overlap_mm3': round(flexed_route, 5),
           'nondeflecting_collision_found': worst[2] > .002,
           'tongue': {'beam_mm': [round(TIP_X - ROOT_X, 3), round(TY1 - TY0, 3), round(TONGUE_T, 3)], 'tooth_catch_mm': round(CREST_Z - TOOTH_Z0, 3),
                      'drawn_deflection_at_tooth_mm': round(DELTA_A, 3),
                      'linear_beam_peak_root_strain': round(3 * DELTA_A * TONGUE_T / (2 * A ** 2), 4),
                      'strain_note': 'Momentary, during the click only; zero when seated. Linear point-load estimate from CAD sizes, layers along the beam (keeper prints flat). Not a measured PETG strain limit, creep or fatigue result.'},
           'removal': {'documented': 'Pull by the ears (R18 README). The 45-degree ridge face lifts the tongue on the way out.',
                       'tongue_lift_option': 'Geometrically sufficient (full-route overlap above). No lift tab exists; access through the 0.6 mm slit and force are unverified.'}}
    if board is not None:
        out['seated_keeper_board_overlap_mm3'] = round(float((board ^ rest).volume()), 5)
    if out['nondeflecting_collision_found'] or out['seated_overlap_mm3'] > .002 or out['max_rigid_overlap_mm3'] < .05:
        raise ValueError(f"Keeper route or catch geometry needs review: {out}")
    return out


def keeper_samples(state, sample, path, actor='keeper'):
    """Sample list for a path of (dy, blend). Mutates state[actor] like the other guide steps."""
    out = []
    for dy, b in path:
        state[actor] = [1., 0, 0, 0, 0, 1., 0, float(dy), 0, 0, 1., 0]
        s = sample(); s['morphs'] = {actor: float(b)}; out.append(s)
    return out


def cutaway_module(step, checks):
    """Use a strip through the middle of both exported parts to expose the catch."""
    body = h.read(OUT / HOLDER_FILE); keeper = h.read(OUT / KEEPER_FILE)
    centre = h.h18.box(-.45, .45, -7.5, 3.5, 8., 13.5)
    holder_file = _write('latch_cut_holder_centre', body ^ centre)
    keeper_file, target = write_pair('latch_cut_keeper_centre', keeper ^ centre)
    actors = {
        'holder': {'label': 'Holder ridge', 'file': 'guide/' + holder_file, 'color': '#29a5b7'},
        'keeper': {'label': 'Keeper and spring tab', 'file': keeper_file, 'morphFile': target, 'color': '#f19a49'},
    }
    I = [1., 0, 0, 0, 0, 1., 0, 0, 0, 0, 1., 0]
    path = [pose for pose in push_path() if pose[0] >= -3.5]
    state = {'holder': I, 'keeper': I}
    def frames(poses):
        return keeper_samples(state, state.copy, poses)
    steps = [
        step('Find the Tooth', 'The orange tooth hangs from the spring tab. The blue ridge is part of the holder.', frames(path[:1]), duration=3),
        step('Push Until It Clicks', 'Push along the side grooves. The orange tab bends up as its tooth rides over the blue ridge.', frames(path), checks, duration=4),
        step('Check the Catch', 'The tooth drops behind the ridge. Check for a little resistance when you pull back gently.', frames(path[-1:]), duration=3),
        step('Pull Out by the Ears', 'Pull evenly on the two side ears. The tooth rides back over the ridge and the tab springs flat.', frames(path[::-1]), duration=4),
    ]
    return {'label': 'XIAO keeper latch · cutaway',
            'note': 'Side section of the R22 keeper and holder. The side grooves are outside this slice. The bend is an illustration from the CAD.',
            'rotation': [math.pi / 2, math.pi / 2, 0.], 'actors': actors, 'steps': steps}


def _write(name, solid):
    GUIDE.mkdir(parents=True, exist_ok=True); path = GUIDE / (name + '.stl'); h.mesh(solid).export(path); return path.name
