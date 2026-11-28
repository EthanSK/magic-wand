"""Trace the changed interfaces along the same fitted paths shown in the assembly guide."""
from functools import lru_cache
import json
import numpy as np

from plate80 import OUT, previous

b = previous.b


def transform(sample, actor):
    pose = np.eye(4)
    pose[:3] = np.asarray(sample[actor]).reshape(3, 4)
    return pose


def routes():
    module = json.loads((OUT / 'assembly-guide.json').read_text())['modules']['pin_hinge']
    files = module['actors']
    steps = {s['title']: s['samples'] for s in module['steps']}

    @lru_cache(maxsize=None)
    def mesh(actor):
        return b.load(OUT / files[actor]['file'])

    def sweep(moving, target, titles, geometry=None):
        matrices = {}
        for title in titles:
            for sample in steps[title]:
                pose = (np.linalg.inv(transform(sample, target)) @ transform(sample, moving))[:3]
                matrices[pose.round(7).tobytes()] = pose
        solid = mesh(moving) if geometry is None else geometry
        return [solid.transform(pose) for pose in matrices.values()]

    from plate80 import parts
    results = {p['name']: {} for p in parts()}
    # The paddle is reused. Its printed post openings are checked in passage80.
    group = results['OP1_Lid_Stop']
    group['moving_paddle_during_retainer_installation'] = sweep('cap','lid',['Fit the OP1 retainer'])
    group['paddle_at_centre_press_and_return'] = sweep('cap','lid',['Press the lower half of the pad'])
    import audit69
    values = json.loads((previous.posts.OUT/'carrier.json').read_text())['hinge']['click_values']['r71']
    legs = mesh('cap') ^ b.box(-12,12,-12,6,11.5,17.6)
    group['paddle_at_rolled_corner_press'] = audit69.far_end_poses(legs,values['case_stop_deg'])
    for actor in ('connector','gravity_plug','sensor_lead'):
        results['DFR_Post_Bar'][actor+'_as_board_is_lowered'] = sweep(actor,'post_bar',['Seat the touch board'])
    for side in ('Left','Right'):
        # The flat clip has a deliberate spring throat. Test its open channel
        # separately from the intentional snap around the neck.
        x = b.HOLE_X if side == 'Right' else -b.HOLE_X
        y, z, profile = b.HOLE_Y, b.BOARD_TOP, previous.posts.m.chain()
        half = profile.CLIP_SLOT/2-.10
        throat = b.box(x-half,x+half,y+.2,y+profile.CLIP_TIP+.15,z-.05,z+1.45)
        bore = previous.posts.mf.Manifold.cylinder(1.50, profile.NECK_R-.1, circular_segments=48)
        group = results['DFR_Clip_'+side]
        group['open_throat_and_seated_neck'] = [throat + bore.translate((x,y,z-.05))]
    return results
