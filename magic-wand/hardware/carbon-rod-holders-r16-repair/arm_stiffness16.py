#!/usr/bin/env python3
"""Reproducible curved-beam screen of the clip-arm stiffness change caused by the lead-in skirt.

Stated assumptions: each arm is a curved cantilever on the R7 wall profile (1.0 mm tip to the
root wall, 7.9 mm bore), clamped where the crown leaves the saddle (the bonded angle measured in
slice-clearances.json), loaded radially at the tip, elastic and linear. The skirt adds width
k*s along the arm (s = arc distance to the tip, k = 1/tan(lead angle)) with its radial thickness
tapering linearly from the wall to the skin. Castigliano tip compliance; Young's modulus cancels.
This is a relative screening ratio, not a measured force, fatigue life or slide feel.
"""
import json
import math
from pathlib import Path
import numpy as np
import holder16 as h

OUT = h.HERE / 'exports'


def compliance(width, root_wall, bonded_deg, k, skin, n=4000):
    inner, gap, thickness = h.ring_profile(width, root_wall)
    tip = -math.pi / 2 + gap / 2; root = math.radians(bonded_deg)
    a = np.linspace(tip, root, n)
    t = np.array([thickness(x) for x in a]); rm = inner + t / 2
    ds = np.r_[0., np.diff(a)] * rm; s = np.cumsum(ds)
    if k > 0:
        # Skirt width along the arc with a thickness tapering toward the skin at its leading edge.
        extra = k * s; frac = np.where(extra > 0, 0.5, 0.)  # average taper position
        t_skirt = t - (t - skin) * frac
        I = width * t ** 3 / 12 + extra * t_skirt ** 3 / 12
    else:
        I = width * t ** 3 / 12
    x = rm * np.cos(a); z = rm * np.sin(a)
    fx, fz = math.cos(a[0]), math.sin(a[0])          # unit radial force at the tip
    M = (x[0] - x) * fz - (z[0] - z) * fx
    return float(np.trapezoid(M ** 2 / I, s)), float(s[-1])


def main():
    a = h.P['arrow_ring']; k = 1 / math.tan(math.radians(a['lead_angle_degrees']))
    audit = json.loads((OUT / 'slice-clearances.json').read_text())
    rows = {}
    for part, rings in audit['strength']['rings'].items():
        width = h.P['sensor']['clip_width_mm'] if part == 'XIAO_Rod_Holder' else h.ROD['ring_width']
        root_wall = h.ROD['sensor_clip_root_wall'] if part == 'XIAO_Rod_Holder' else h.ROD['clip_root_wall']
        for label, ring in rings.items():
            bonded = ring['arm_bonding']['crown_bonded_down_to_degrees_above_equator']
            plain, arc = compliance(width, root_wall, bonded, 0., a['skin_thickness_mm'])
            skirted, _ = compliance(width, root_wall, bonded, k, a['skin_thickness_mm'])
            r15_like, _ = compliance(width, root_wall, 47., 0., a['skin_thickness_mm'])
            rows[f'{part}:{label}'] = {'bonded_degrees_above_equator': bonded, 'free_arc_mm': round(arc, 2), 'skirted': 'lead_in_skirt' in ring,
                                       'stiffness_ratio_vs_plain_arm_same_root': round(plain / skirted, 3) if 'lead_in_skirt' in ring else 1.0,
                                       'stiffness_ratio_vs_r15_like_arm_bonded_at_47_degrees': round(r15_like / (skirted if 'lead_in_skirt' in ring else plain), 3)}
    report = {'generator_sha256': h.sha(h.HERE / 'arm_stiffness16.py'), 'slice_audit_sha256': h.sha(OUT / 'slice-clearances.json'),
              'assumptions': __doc__.strip(), 'lead_angle_degrees': a['lead_angle_degrees'], 'skin_mm': a['skin_thickness_mm'], 'rings': rows,
              'physical_force_verified': False}
    (OUT / 'arm-stiffness-screen.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(rows, indent=1))


if __name__ == '__main__':
    main()
