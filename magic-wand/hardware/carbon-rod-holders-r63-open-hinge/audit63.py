"""Check both replacement bodies in the same assembled frame against actual PETG toolpaths."""
from pathlib import Path
import argparse
import json

from kit63 import OUT, R62, PRINT_POSES, kit62, parts
import audit61
import fit61
import passage63

v = audit61.v
r61 = passage63.r61


def turn_key(index, solid):
    if index == 0:
        return solid.translate((21, 0, 0)).rotate((0, 0, 90)).translate((-21, 0, 0))
    return solid


def key_routes(routes=None):
    """Rotate the installed socket while retaining the outside approach and vertical lift."""
    if routes is None:
        routes = audit61.gauges()
    holder = routes["Key_Carrier"]
    for key, poses in holder.items():
        if not key.startswith("key_0_"):
            continue
        if key.endswith("_soldered_socket_slide"):
            offsets = r61.k.h.d.r22.slide_poses(0)
            assert len(poses) == len(offsets) and tuple(offsets[-1]) == (0,0,0)
            seated = turn_key(0, poses[-1])
            holder[key] = [seated.translate(offset) for offset in offsets]
        else:
            holder[key] = [turn_key(0, pose) for pose in poses]
    return {name: routes[name] for name in ("Key_Carrier", "Touch_Paddle")}


def mechanism_check():
    from design63 import KEEPER_Z
    paddle = OUT / "Touch_Paddle-assembly.stl"
    fit61.main(OUT, paddle_file=paddle, key_pose=turn_key, pin_height_shift=KEEPER_Z-r61.m.PIN_Z)
    file = OUT / "click-fit.json"
    result = json.loads(file.read_text())
    result["geometry_sha256"] = {part: v.digest(OUT / f"{part}-assembly.stl") for part in PRINT_POSES}
    v.write(file, result)


def audit(folder):
    from cradle_checks63 import deposited_routes, spring_opening
    import design63 as d
    def routes():
        geometry = key_routes()
        geometry["Key_Carrier"].update(deposited_routes())
        clip = d.b.load(d.r61.OUT / "Pin_Clip-assembly.stl").translate((0,0,d.KEEPER_Z-d.m.PIN_Z))
        geometry["Touch_Paddle"]["centre_clip_approach"] = [clip.translate((0,0,i/2)) for i in range(1,17)]
        geometry["Touch_Paddle"]["centre_clip_seated"] = [clip]
        return geometry
    passages = passage63.inspect(folder, r61.AXIS)
    reused = passage63.shaft_envelopes(R62 / "exports/print-mechanisms")
    passages["reused_pins"] = reused
    shafts = reused["straight_shaft_envelope_diameter_mm"]
    passages["clearance_over_standard_shaft_envelope_mm"] = round(passages["assembled_clear_diameter_mm"] - shafts["Hinge_Pin"], 3)
    passages["clearance_over_snug_shaft_envelope_mm"] = round(passages["assembled_clear_diameter_mm"] - shafts["Hinge_Pin_Snug"], 3)
    v.write(folder / "passages.json", passages)
    assert passages["rod_min_clear_diameter_mm"] >= 8.2 and passages["rod_layers_under_8mm"] == 0, passages
    assert passages["assembled_clear_diameter_mm"] >= 3.30, passages
    assert passages["clearance_over_standard_shaft_envelope_mm"] > .10, passages
    backers={"Left": OUT/"Socket_Backer_Left-assembly.stl",
             "Right": audit61.old.R58/"exports/Socket_Backer_Right-assembly.stl"}
    audit61.audit(folder, parts, OUT, expected_names=PRINT_POSES, route_builder=routes,
                  spring_probe=spring_opening, backer_rows=backers,
                  base_minima=dict(audit61.MINIMA, Rod_Collet=150))


def release(primary, reopened):
    fit = v.read(OUT / "click-fit.json")
    assert fit["geometry_sha256"] == {part: v.digest(OUT / f"{part}-assembly.stl") for part in PRINT_POSES}
    receipts = (*kit62.release61.REPORTS, "passages.json")
    kit62.release61.release(primary, reopened, OUT, parts,
                             "R63-Replacement-Key-Holder-A1-mini-PETG-print-only.3mf", reports=receipts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fit")
    commands.add_parser("audit").add_argument("plate", type=Path)
    pack = commands.add_parser("release")
    pack.add_argument("primary", type=Path)
    pack.add_argument("reopened", type=Path)
    args = parser.parse_args()
    if args.command == "fit":
        mechanism_check()
    elif args.command == "audit":
        audit(args.plate)
    else:
        release(args.primary, args.reopened)
