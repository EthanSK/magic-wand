"""R71 assembly guide: the published R70 guide carried onto the R71 parts.

What changes:

* Meshes: the holder, the paddle, the two-post bar and the two touch-board clips are the
  R71 exports. The three wires and the retainer are R71's byte-for-byte copies of R70's.
* Battery: the pouch model is the same bought cell. Every sampled pose moves with its seat:
  6.2 mm outward, 12.45 mm down the holder and 3.05 mm lower. It still slides in 30 mm
  along the rod, which is the motion battery.json checks against the holder.
* Clips: the R70 guide showed R59's clip in its own guide frame. R71's clips are in the
  assembly frame, so their poses are rebased by the offset between the two R59 meshes.
  Their motion is unchanged. The clip is drawn as exported: frame against the head's
  ledges, arms unbent, so its two feet stand 0.2 mm in the board model. Fitted, the arms
  are bent that much and the heels of the feet rest on the board. While it slides on it is
  pressed flat, 0.2 mm lower, with its arms bent 0.4 mm; the animation does not show that.
* Words: the battery steps, the tape step, the clip step and the module notes.

Every other actor and pose is R70's. The guide is written beside the meshes. Registering it
for the viewer is the caller's decision (--register, --current); nothing here does it by
default.
 — Claude Fable 5.2"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import numpy as np

import design71 as d
import hinge71
import kit71

r70, old, b = d.r70, d.old, d.b
OUT = d.OUT
SOURCE = r70.OUT / 'assembly-guide.json'
COPIED = (d.HOLDER, hinge71.PADDLE, hinge71.WIRES, hinge71.POST_BAR, hinge71.LID)       # same names in both export folders
CLIP_ACTORS = {'clip_left': 'Left', 'clip_right': 'Right'}
BATTERY = 'battery'
BATTERY_SHIFT = np.array([d.PACK_X[0] - old.PACK_X[0], d.PACK_Y0 - old.PACK_Y0, d.PACK_Z[1] - old.PACK_Z[1]])
STATUS = 'R71 design · physical fit untested'
LABEL = 'R71 · Battery inside the holder, spring clips, eased hinge'
CAPTIONS = {
    'Tape Every Socket': ('Lay one strip of polyimide tape across each socket and its wires onto the backplate, as on R16. Press the tape ends onto the '
                          'backplate with a flat tool. Keep pressure off the guard runners. The tape insulates the solder from the rod and holds the socket. '
                          'On the left side keep the wires of both sockets flat against the backplate: the battery slides in under them.'),
    'Slide in the battery': ('Fit the battery last. Slide the wrapped battery in from the rear, between the two rails and on under the upper-left socket, '
                             'until its nose stops against the round guard beam. Its end then lies level with the rear of the holder. Guide the leads '
                             'out behind the holder and leave the connector outside.'),
    'Remove the battery': ('Press a fingertip on the open underside of the battery, in front of the two rails, and slide it back until its end can be '
                           'held. Do not pull it by the leads.'),
    'Slide on the two small clips': ('Press the board down onto the paddle. Lay each clip on the board with its two feet down and its open end toward the '
                                     'post. Press down on the front half of the clip, between its two feet, and slide it on until it snaps round the post '
                                     'neck, then let go: the clip rises against the post head and its two feet hold the board down. Do not press on the '
                                     'rear bar: that leaves the open end raised, and it stops against the post head.'),
    'Remove the two clips': 'Press each clip down between its two feet and slide it back off its post neck. Keep both clips.',
}
MODULE_NOTES = {
    'battery': ('The battery lies inside the outline of the key holder, 3 mm under the keypad base, against three ribs. The rails hold its rear 16 mm. '
                'Its nose runs forward under the upper-left socket to the guard beam. Take it out before changing either left socket.'),
}
MODULE_ADDS = {'key': ' The battery lies under the upper-left socket and is fitted last.'}
CLIP_LABEL = 'Touch-board spring clip, %s'
BAR_LABEL = 'Two-post bar with a third ledge under each head'
OPTIONAL_NOTE = ('Not on the R71 plate. The two flat strips can support a socket while its switch is pressed in, and the second pin is '
                 'slightly snugger. Their files are unchanged and the R69 plate prints them. The flat 1.4 mm touch-board clips of the R70 plate '
                 'also still fit the posts.')


def clip_rebase(side):
    """Offset from R59's guide-frame clip to R59's assembly-frame clip: the same mesh, moved."""
    folder = hinge71.R59_CLIPS[side].parent
    shown, placed = (np.reshape(b.load(folder / f'DFR_Clip_{side}-{frame}.stl').bounding_box(), (2, 3)) for frame in ('guide', 'assembly'))
    assert np.allclose(shown[1] - shown[0], placed[1] - placed[0], atol=1e-4), 'the R59 guide clip is not the R59 clip moved'
    return shown[0] - placed[0]


def write(register=False, current=False):
    guide = json.loads(SOURCE.read_text())
    assert guide['revision'] == 'R70', guide['revision']
    rebase = {actor: clip_rebase(side) for actor, side in CLIP_ACTORS.items()}
    hashes, moved, rebased = {}, 0, 0
    for name, module in guide['modules'].items():
        if name in MODULE_NOTES:
            module['note'] = MODULE_NOTES[name]
        if name in MODULE_ADDS and MODULE_ADDS[name].strip() not in module.get('note', ''):
            module['note'] = module.get('note', '') + MODULE_ADDS[name]
        for step in module['steps']:
            step['caption'] = CAPTIONS.get(step['title'], step.get('caption'))
            for sample in step['samples']:
                if BATTERY in sample:
                    pose = np.asarray(sample[BATTERY], float).reshape(3, 4)
                    assert np.allclose(pose[:, :3], np.eye(3), atol=1e-9), 'the battery is expected to slide without turning'
                    pose[:, 3] += BATTERY_SHIFT
                    sample[BATTERY] = [round(float(v), 6) + 0. for v in pose.ravel()]
                    moved += 1
                for actor in CLIP_ACTORS.keys() & set(sample):
                    pose = np.asarray(sample[actor], float).reshape(3, 4)
                    pose[:, 3] += pose[:, :3] @ rebase[actor]
                    sample[actor] = [round(float(v), 6) + 0. for v in pose.ravel()]
                    rebased += 1
        for actor, spec in module['actors'].items():
            for field in ('file', 'morphFile'):
                if field not in spec:
                    continue
                src = (r70.OUT / spec[field]).resolve(strict=True)
                if src.parent == r70.OUT.resolve() and src.name in COPIED:
                    src = OUT / src.name
                if actor in CLIP_ACTORS and field == 'file':
                    src = OUT / hinge71.CLIPS[CLIP_ACTORS[actor]]
                key = os.path.relpath(src, OUT)
                spec[field] = key
                hashes.setdefault(key, digest(src))
            if actor in CLIP_ACTORS:
                spec['label'] = CLIP_LABEL % CLIP_ACTORS[actor].lower()
            if spec.get('file') == hinge71.POST_BAR:
                spec['label'] = BAR_LABEL
        if 'status' in module:
            module['status'] = STATUS
    assert moved > 0 and rebased > 0 and all(name in hashes for name in COPIED), (moved, rebased, sorted(hashes))
    numbers = d.numbers()
    guide['print_components']['keys'] = sorted(row['name'] for row in kit71.parts())
    guide['optional_components'] = dict(keys=guide['optional_components']['keys'], note=OPTIONAL_NOTE)
    guide['r71_changes'] = dict(
        battery_moved_mm=[round(float(v), 2) for v in BATTERY_SHIFT], battery_poses_moved=moved, battery_behind_the_rear_face_mm=numbers['behind_the_rear_face_mm'],
        battery_slide_mm=30.0, battery_slide_checked_in='battery.json: seat.slide_in_from_the_rear_without_the_spring_mm3',
        clip_thickness_mm=dict(r70=1.4, r71=hinge71.CLIP_T), clip_poses_rebased=rebased,
        clip_spring=dict(arms=2, feet_below_the_frame_when_free_mm=hinge71.FOOT, arms_bent_when_fitted_mm=round(hinge71.PRESS, 2), drawn='arms unbent',
                         arms_bent_while_pressed_flat_mm=hinge71.FOOT, frame_stops_board_lift_at_mm=round(hinge71.LIFT, 2),
                         arm_mm=dict(thickness=round(hinge71.ARM_T, 2), width=round(hinge71.ARM_X[1] - hinge71.ARM_X[0], 2), root_width=round(hinge71.ARM_X[1] - hinge71.ROOT_X, 2),
                                     lever_to_the_heel=round(hinge71.ARM_ROOT + hinge71.FOOT_Y[0], 2)),
                         press='on the front half, between the two feet; not on the rear bar'),
        post_rib_full_section_above_the_seat_mm=dict(r70=hinge71.LAYER, r71=hinge71.RIB_FULL),
        left_guard='top arm re-routed beside and in front of the battery; crown hub %.1f mm nearer the lower row' % (d.r62.CROWN_START[1] - d.HUB[1]),
        hinge_journal_relief_mm=hinge71.JOURNAL_FLAT, steps_reworded=sorted(CAPTIONS))
    guide['revision'] = 'R71'
    guide['physical_fit_verified'] = False
    guide['sources'] = dict(generator_sha256=digest(__file__), upstream_guide_sha256=digest(SOURCE), meshes_sha256=hashes,
                            battery_report_sha256=digest(OUT / 'battery.json'), upstream_sources=guide.get('sources', {}).get('upstream_sources'))
    dest = OUT / 'assembly-guide.json'
    dest.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    if register or current:
        sys.path.insert(0, str(d.HARDWARE / 'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(dest, 'r71', LABEL, group_keys=True, make_current=current)
    return dest


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--register', action='store_true')
    parser.add_argument('--current', action='store_true', help='also make R71 the default revision')
    args = parser.parse_args()
    print(write(args.register, args.current))
