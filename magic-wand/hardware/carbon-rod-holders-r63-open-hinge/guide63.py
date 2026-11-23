"""Show the replacement parts with the surviving R62 hardware and the 500 mm rod."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import design63

HERE = Path(__file__).resolve().parent
OUT = HERE / "exports"
PREVIOUS = HERE.parent / "carbon-rod-holders-r62-compact-guard" / "exports"
CHANGED = {"Key_Carrier-assembly.stl", "Touch_Paddle-assembly.stl", "Battery_Pack-assembly.stl"}


def face_outside(matrix):
    """Turn the key clockwise looking at the underside, retaining its world insertion path."""
    result = list(matrix)
    for i in (0, 4, 8):
        result[i], result[i + 1] = matrix[i + 1], -matrix[i]
    return result


def animate_backer(keys):
    """Show how the flat strip braces the rotated socket while the switch goes in."""
    actor="left_backer"
    keys["stagedActors"]=True
    keys["frameBounds"]=[[-70,-32,-9],[50,61,45]]
    keys["actors"][actor]={"file":design63.BACKER,"label":"Left socket backing strip","color":"#9d4139","frame":False}
    i=next(i for i,step in enumerate(keys["steps"]) if step["title"]=="Press In the Switches")
    press=keys["steps"][i]
    def shift(x):
        return [1,0,0,x,0,1,0,0,0,0,1,0]
    def movement(title,caption,base,offsets):
        return dict(title=title,caption=caption,duration=1.8,
                    samples=[dict(base,left_backer=shift(x)) for x in offsets])
    into=movement("Support the outside-facing socket",
                  "Slide the left backing strip under the black socket from the open edge. Hold the strip while pressing the switch.",
                  press["samples"][0],range(-26,1))
    out=movement("Pull the backing strip out",
                 "Once the switch is seated, slide the strip back out through the same edge. Keep it for the next assembly.",
                 press["samples"][-1],range(0,-27,-1))
    for sample in press["samples"]:
        sample[actor]=shift(0)
    keys["steps"][i:i+1]=[into,press,out]


def relocate_pin(sample):
    dz=design63.KEEPER_Z-design63.m.PIN_Z
    for name in ("hinge_pin","pin_clip"):
        if name in sample:
            sample[name][11]+=dz
    cap=sample.get("cap")
    if cap and abs(cap[9])>1e-8:
        # A rotation about the new pivot adds (I-R) times the change of origin.
        delta=(-cap[2]*dz,-cap[6]*dz,(1-cap[10])*dz)
        for name in ("cap","post_bar","clip_left","clip_right","sensor","electrode",
                     "connector","sensor_lead","gravity_plug","flat_electrode"):
            for column,extra in zip((3,7,11),delta):
                sample[name][column]+=extra


def rod_grip(guide, keys):
    """The grip clips on from +X, then slides towards the holder along -Y."""
    actor = "rod_collet"
    keys["actors"][actor] = dict(file=design63.COLLET_FILE, label="Removable rod grip",
                                 color="#b04939", frame=False)
    final = keys["steps"][-1]["samples"][-1]
    steps = []
    for title,caption,travel in [
        ("Clip the grip onto the carbon rod",
         "With the holder on the rod, fit the open side of the small grip around the rod behind the holder.",
         [(16-i,9) for i in range(17)]),
        ("Seat the rod grip",
         "Push the tapered end into the round opening until the holder stays put. Pull the flange back to release it.",
         [(0,9-i/2) for i in range(21)]),
    ]:
        samples = [dict(final, **{actor:[1,0,0,x,0,1,0,y,0,0,1,0]}) for x,y in travel]
        steps.append(dict(title=title,caption=caption,duration=1.7,samples=samples))
    keys["steps"].extend(steps)
    mount = next(m for m in guide["modules"]["whole"]["rodMounts"] if m["id"]=="keys")
    mount["afterSlide"] = dict(actor=actor, steps=[s["title"] for s in steps])


def write_guide(register=False):
    source = PREVIOUS / "assembly-guide.json"
    guide = json.loads(source.read_text())
    hashes = {}
    seen = set()
    for module in guide["modules"].values():
        for actor in module["actors"].values():
            for field in ("file", "morphFile"):
                if field not in actor:
                    continue
                path = (PREVIOUS / actor[field]).resolve(strict=True)
                if path.name in CHANGED:
                    path = (OUT / path.name).resolve(strict=True)
                    seen.add(path.name)
                relative = os.path.relpath(path, OUT)
                actor[field] = relative
                if relative not in hashes:
                    hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        for step in module["steps"]:
            for sample in step["samples"]:
                relocate_pin(sample)
                for key in ("switch_0", "socket_0"):
                    if key in sample:
                        sample[key] = face_outside(sample[key])
    assert seen == CHANGED, seen
    keys = guide["modules"]["key"]
    animate_backer(keys)
    hashes[design63.BACKER]=hashlib.sha256((OUT/design63.BACKER).read_bytes()).hexdigest()
    rod_grip(guide, keys)
    hashes[design63.COLLET_FILE] = hashlib.sha256((OUT/design63.COLLET_FILE).read_bytes()).hexdigest()
    outside = next(s for s in keys["steps"] if s["title"] == "Slide In the Lower-Left Socket")
    outside["caption"] = ("Face both switch contacts toward the outside edge. Slide the wired socket in "
                         "from that edge below its seat, then lift it straight onto the contacts.")
    assert keys["steps"][-1]["samples"][-1]["socket_0"] == [0,-1,0,-21,1,0,0,0,0,0,1,8.87]
    for module in (keys, guide["modules"]["battery"]):
        insertion = next(s for s in module["steps"] if s["title"] == "Slide in the battery")
        insertion["caption"] = ("Slide the wrapped battery lengthwise against the underside of the key holder. "
                               "Guide the leads out through the open end and leave the connector outside.")
    batteries = guide["modules"]["battery"]
    batteries["note"] = "The broad face of the battery rests against the keypad base. Pull the exposed end of the pack to remove it."
    all_parts = guide["print_components"]["keys"]
    guide["print_components"]["keys"] = ["Key_Carrier", "Touch_Paddle", "Socket_Backer_Left", "Rod_Collet"]
    guide["reuse_components"] = {"keys": [part for part in all_parts if part not in guide["print_components"]["keys"]],
                                "note": "Use the standard pin, centre clip, board clips, post bar, OP1 retainer and right backing strip from R62."}
    guide.update(revision="R63", physical_fit_verified=False, sources={
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "upstream_guide_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "meshes_sha256": hashes,
    })
    path = OUT / "assembly-guide.json"
    path.write_text(json.dumps(guide, separators=(",", ":"), allow_nan=False)+"\n")
    if register:
        sys.path.insert(0, str(HERE.parent / "carbon-rod-holders/assembly"))
        from register_assembly import register_assembly
        register_assembly(path, "r63", "R63 trial · Open hinge, rod and flush battery seat", group_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", action="store_true")
    write_guide(parser.parse_args().register)
