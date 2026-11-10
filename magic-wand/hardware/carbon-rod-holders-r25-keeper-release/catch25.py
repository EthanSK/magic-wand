#!/usr/bin/env python3
"""R25 XIAO keeper. An insertion ramp and a lift-to-release stop share one ridge."""

import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
R23 = HERE.parent / "carbon-rod-holders-r23-hybrid-centre"
sys.path.insert(0, str(R23))
import holder23 as h
import latch22 as old_latch

OUT = HERE / "exports"
OLD = h.R22 / "exports"
REVISION = HERE.name
HOLDER = "XIAO_Rod_Holder"
KEEPER = "XIAO_Near_Keeper"
RAMP_Y = -1.8
CREST_Y = -.94
STOP_Y = -.64
PATCH_HALF_WIDTH = 2.05
PATCH_FLOOR_Z = 9.45
STOP_TOP_Z = 10.06
STOP_ROOT_Z = 9.78
ROOT_END_Y = .20
TAB_EDGE_Y = 2.45
PROFILE = [(RAMP_Y, PATCH_FLOOR_Z), (CREST_Y, STOP_TOP_Z), (STOP_Y, STOP_TOP_Z),
           (STOP_Y, STOP_ROOT_Z), (ROOT_END_Y, PATCH_FLOOR_Z)]
TOOTH_BACK_Y = old_latch.TOOTH_Y[0]
FREE_PULL_MM = TOOTH_BACK_Y - STOP_Y
TAB_X = (-.45, 1.57)
IDENTITY = [1., 0, 0, 0, 0, 1., 0, 0, 0, 0, 1., 0]


def solids():
    body = h.h22.read(OLD / f"{HOLDER}-assembly.stl")
    keeper = h.h22.read(OLD / f"{KEEPER}-assembly.stl")
    prism = h.h22.h18.prism_yz
    # The tooth enters toward +Y. The added material supports that ramp.
    # The inboard (+Y) side drops away vertically into the released spring seat.
    patch = h.box(-PATCH_HALF_WIDTH, PATCH_HALF_WIDTH, -2., .6,
                  PATCH_FLOOR_Z, old_latch.CREST_Z + .05)
    # Back most of the stop with a gradual root. Only the short catch face
    # remains vertical, so it needs less unsupported material in the slice.
    ridge = prism([(RAMP_Y, PATCH_FLOOR_Z - .36), *PROFILE,
                   (ROOT_END_Y, PATCH_FLOOR_Z - .56)], -PATCH_HALF_WIDTH, PATCH_HALF_WIDTH)
    revised_body = (body - patch + ridge).simplify(.0001)

    # Ethan's "tab": a nail edge on the spring, with a ramp underneath it.
    # The face that prints on the bed stays flush with the old keeper.
    z0 = old_latch.TG["thin_from_z_mm"]
    z1 = old_latch.RET["plate_z_mm"][1]
    lip = prism([(1.02, z0), (TAB_EDGE_Y, z0 + .40),
                 (TAB_EDGE_Y, z1), (1.02, z1)], *TAB_X)
    corners = mf.CrossSection.square((TAB_X[1] - TAB_X[0], TAB_EDGE_Y - .96))
    corners = corners.offset(-.21, mf.JoinType.Round).offset(.21, mf.JoinType.Round)
    clip = mf.Manifold.extrude(corners, z1 - z0 + .2).translate((TAB_X[0], .96, z0 - .1))
    revised_keeper = (keeper + (lip ^ clip)).simplify(.0001)
    return body, keeper, revised_body, revised_keeper


def lift(points):
    offsets = old_latch.lift(points)
    x, y, _ = np.asarray(points).T
    lip = ((x >= TAB_X[0] - .001) & (x <= TAB_X[1] + .001)
           & (y > old_latch.TY1 + .001) & (y <= TAB_EDGE_Y + .001))
    offsets[lip, 2] = old_latch.DELTA_A * old_latch._shape(x[lip] - old_latch.ROOT_X)
    return offsets


def needed_blend(dy):
    lo, hi = (y + dy for y in old_latch.TOOTH_Y)
    if hi < RAMP_Y or lo >= STOP_Y:
        return 0.
    top = np.interp(min(CREST_Y, hi), [RAMP_Y, CREST_Y], [PATCH_FLOOR_Z, STOP_TOP_Z])
    rise = top - old_latch.TOOTH_Z0
    return 0. if rise <= 0 else min(1., (rise + old_latch.CLEAR) / old_latch.FULL)


def motions():
    travel = old_latch.route()
    touch = STOP_Y - TOOTH_BACK_Y
    critical = [CREST_Y - old_latch.TOOTH_Y[1], touch - .001, touch, touch + .001]
    push = sorted(set(np.round(np.r_[np.linspace(-travel, 0., 81), critical], 6)))
    start_release = touch + .01
    outward = np.linspace(start_release, -travel, 81)
    return {
        "insert": [(float(y), needed_blend(y)) for y in push],
        "pull_to_stop": [(float(y), 0.) for y in np.linspace(0., start_release, 9)],
        "lift": [(start_release, float(a)) for a in np.linspace(0., 1., 21)],
        "remove": [(float(y), 1.) for y in outward],
        "relax": [(-travel, float(a)) for a in np.linspace(1., 0., 21)],
    }


def deformed(mesh, blend, displacement):
    positions = np.asarray(mesh.vertices) + blend * displacement(mesh.vertices)
    solid = mf.Manifold(mf.Mesh(np.asarray(positions, np.float32), np.asarray(mesh.faces, np.uint32)))
    assert solid.status() == mf.Error.NoError, solid.status()
    return solid


def compare_routes(body, keeper, paths, displacement):
    mesh = h.mesh(keeper)
    max_overlap = {}
    for name, poses in paths.items():
        max_overlap[name] = round(max(h.vol(body ^ deformed(mesh, blend, displacement).translate((0., y, 0.)))
                                      for y, blend in poses), 6)
    return max_overlap


def verify(old_body, old_keeper, body, keeper):
    same_bounds = lambda a, b: np.allclose(a.bounding_box(), b.bounding_box(), atol=.0002, rtol=0)
    assert same_bounds(body, old_body) and same_bounds(keeper, old_keeper)
    assert len(body.decompose()) == len(keeper.decompose()) == 1
    tongue = old_latch.TG
    tooth = h.box(*tongue["tooth_x_mm"], *tongue["tooth_y_mm"],
                  tongue["tooth_bottom_z_mm"] - .1, tongue["thin_from_z_mm"] + .05)
    assert h.vol(tooth ^ (keeper - old_keeper)) < .002
    assert h.vol(old_keeper - keeper) < .002
    board = h.h22.h19.board_outline()
    paths = motions()
    checks = compare_routes(body, keeper, paths, lift)
    assert max(checks.values()) < .002, checks
    blocked = h.vol(body ^ keeper.translate((0., -FREE_PULL_MM - .14, 0.)))
    assert blocked > .08, blocked
    assert h.vol(body ^ keeper) < .002 and h.vol(board ^ keeper) < .002

    board_source = h.h22.h18.h17
    extra = keeper - old_keeper
    bare_clearance = {}
    for label, solid in {"PCB": board, **{k: board_source.component_box(k) for k in board_source.XO["components"]}}.items():
        bare_clearance[label] = round(h.vol(extra ^ solid), 6)
    assert max(bare_clearance.values()) < .002, bare_clearance
    board_route = max(h.vol((body - old_body) ^ board.transform(np.asarray(p)[:3, :4]))
                      for p in board_source.insertion_poses())
    assert board_route < .002, board_route

    compatible = {
        "R25_keeper_R22_holder": compare_routes(old_body, keeper, {"insert": old_latch.push_path()}, lift)["insert"],
        "R22_keeper_R25_holder": compare_routes(body, old_keeper, paths, old_latch.lift),
    }
    assert compatible["R25_keeper_R22_holder"] < .002
    assert max(compatible["R22_keeper_R25_holder"].values()) < .002, compatible
    return {
        "stop_face_deg_from_horizontal": 90.,
        "tooth_height_below_crest_mm": round(STOP_TOP_Z - old_latch.TOOTH_Z0, 3),
        "travel_to_stop_mm": round(FREE_PULL_MM, 3),
        "drawn_lift_at_nearest_tooth_edge_mm": round(old_latch.FULL, 3),
        "drawn_lift_at_free_tip_mm": round(float(lift([[TAB_X[1], TAB_EDGE_Y, 11.95]])[0, 2]), 3),
        "blocked_straight_pull_overlap_mm3": round(blocked, 6),
        "matched_path_overlap_mm3": checks,
        "added_lip_component_overlap_mm3": bare_clearance,
        "added_ridge_board_path_overlap_mm3": round(board_route, 6),
        "compatible_path_overlap_mm3": compatible,
        "physical_fit_and_retention_verified": False,
    }


def export():
    baseline_body, baseline_keeper, body, keeper = solids()
    parts = {name: h.h22.export_new(name, shape, OUT)
             for name, shape in ((HOLDER, body), (KEEPER, keeper))}
    checks = verify(baseline_body, baseline_keeper, *(
        h.h22.read(OUT / f"{name}-assembly.stl") for name in (HOLDER, KEEPER)))
    anchors = json.loads((OLD / "anchors.json").read_text())
    old_pad = OLD / f"{HOLDER}-ANCHOR-REMOVE-AFTER-PRINT.stl"
    pad = OUT / old_pad.name
    pad.write_bytes(old_pad.read_bytes())
    assert h.sha(pad) == anchors["parts"][HOLDER]["stl_sha256"]
    old_manifest = json.loads((OLD / "manifest.json").read_text())
    assert np.allclose(parts[HOLDER]["print_to_assembly"], old_manifest["parts"][HOLDER]["print_to_assembly"], atol=.0002, rtol=0)
    print_body = h.h22.read(OUT / f"{HOLDER}-SOURCE-REQUIRES-PREPARATION.stl")
    old_print = h.h22.read(OLD / f"{HOLDER}-SOURCE-REQUIRES-PREPARATION.stl")
    bed = h.box(-1., 60., -2., 60., -.05, .401)
    assert h.vol((print_body ^ bed) - old_print) + h.vol((old_print ^ bed) - print_body) < .02
    (OUT / "anchors.json").write_text(json.dumps({"parts": {HOLDER: anchors["parts"][HOLDER]}}, indent=2) + "\n")
    manifest = {"revision": REVISION, "plate_parts": [HOLDER, KEEPER], "anchored_parts": [HOLDER],
                "parts": parts, "geometry_checks": checks, "generator_sha256": h.sha(__file__),
                "base_r22_manifest_sha256": h.sha(OLD / "manifest.json"), "physical_fit_verified": False}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(checks), flush=True)


if __name__ == "__main__":
    export()
