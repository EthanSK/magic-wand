"""Interchangeable coarse-thread battery caps for Shard Tube R2.

Geometry is built in assembled wand coordinates (butt at Z=0, tip +Z).
The male cap screws into an integral female thread in the grip. The weighted
variant adds a closed, infilled extension below the butt; it has no loose
ballast pocket and shares exactly the light cap's upper interface.

This is a PETG fit candidate. CAD clearance does not establish printed fit,
tightening torque, fatigue life or impact strength. Print the matching gauge
before a complete grip. The nominal cell is still provisional.
"""
from __future__ import annotations

from functools import lru_cache
import math
import numpy as np

PITCH = 3.4
CORE_RADIUS = 12.2
MALE_ROOT_RADIUS = 11.9
THREAD_ROOT_RADIUS = 11.75
THREAD_CREST_RADIUS = 12.75
RADIAL_GAP = .30
AXIAL_GAP = .25  # per flank, not total diametral clearance
THREAD_ROOT_HALF_WIDTH = 1.15
THREAD_CREST_HALF_WIDTH = .15
SOCKET_OUTER_RADIUS = 14.5
THREAD_Z = (3.0, 9.3)
WEIGHTED_EXTENSION = 18.0


@lru_cache(None)
def _helix(c, female=False):
    """Closed swept trapezoid, subsequently clipped to the useful Z range.

    The 1 mm radial rise over 1 mm axial flank is 45 degrees. The female
    clearance is modelled on the real helical profile, rather than replacing
    the thread with annular rings or relying on slicer negative volumes.
    """
    rg = RADIAL_GAP if female else 0.
    ag = AXIAL_GAP if female else 0.
    section = [
        (THREAD_ROOT_RADIUS + rg, -THREAD_ROOT_HALF_WIDTH - ag),
        (THREAD_CREST_RADIUS + rg, -THREAD_CREST_HALF_WIDTH - ag),
        (THREAD_CREST_RADIUS + rg, THREAD_CREST_HALF_WIDTH + ag),
        (THREAD_ROOT_RADIUS + rg, THREAD_ROOT_HALF_WIDTH + ag),
    ]
    verts, faces = [], []
    # Extra turns outside the final useful band give both parts a continuous
    # screw lead. Three-degree facets are under 0.005 mm chord error.
    angles = np.linspace(-360., 1440., 601)
    for angle in angles:
        a = math.radians(float(angle))
        zc = PITCH * float(angle) / 360.
        verts.extend((r * math.cos(a), r * math.sin(a), zc + dz)
                     for r, dz in section)
    for i in range(len(angles) - 1):
        a, b = 4 * i, 4 * (i + 1)
        for k in range(4):
            j = (k + 1) % 4
            faces.extend(((a + k, b + k, b + j), (a + k, b + j, a + j)))
    faces.extend(((0, 1, 2), (0, 2, 3)))
    q = 4 * (len(angles) - 1)
    faces.extend(((q, q + 2, q + 1), (q, q + 3, q + 2)))
    return c.b.closed_mesh(verts, faces, 'coarse helical battery-cap thread')


@lru_cache(None)
def female_socket_void(c):
    """Final subtraction for the grip, including an unobstructed mouth.

    Root must apply this after all integral grip reinforcements. A separate
    cell/sled sweep must continue from this open socket through the battery
    chamber; this function deliberately stops below the lower loop mount.
    """
    thread = _helix(c, True) ^ c.cyl(13.1, 2.6, 10.2)
    mouth = c.cyl(CORE_RADIUS + .30, -3., 3.2, CORE_RADIUS)
    core = c.cyl(CORE_RADIUS, 3.0, 11.4)
    return c.union([thread, mouth, core])


def _grip_scallops(c, z0, z1):
    # Rounded shallow fingertip scallops, not teeth or sharp knurling.
    return c.union([
        c.cyl(1.1, z0, z1, x=15.15 * math.cos(a), y=15.15 * math.sin(a))
        for a in np.linspace(0., 2. * math.pi, 16, endpoint=False)
    ])


@lru_cache(None)
def male_interface(c):
    core = c.cyl(MALE_ROOT_RADIUS, 2.5, 8.5)
    core += c.cyl(MALE_ROOT_RADIUS, 8.5, THREAD_Z[1], 11.55)
    lead = c.cyl(THREAD_CREST_RADIUS, 2.8, 8.1)
    lead += c.cyl(THREAD_CREST_RADIUS, 8.1, THREAD_Z[1], 11.55)
    thread = _helix(c) ^ lead ^ c.cyl(13.0, *THREAD_Z)
    # This is a closed floor, not a cap with a hole into its ballast region.
    # The cell bottom is above Z13, leaving >3.7 mm headroom above the cap.
    return (core + thread) - c.cyl(10.4, 3.0, 10.0)


@lru_cache(None)
def light_cap(c):
    flange = c.cyl(13.5, 0., .8, SOCKET_OUTER_RADIUS)
    flange += c.cyl(SOCKET_OUTER_RADIUS, .8, 3.)
    return (flange + male_interface(c)) - _grip_scallops(c, .8, 2.4)


@lru_cache(None)
def weighted_cap(c):
    # The CAD bulk is closed material. The prepared project must assign this
    # one object 45% gyroid, 3 walls and 5 top/bottom layers, not 100% infill.
    lower = c.cyl(13.5, -WEIGHTED_EXTENSION, -WEIGHTED_EXTENSION + .8,
                  SOCKET_OUTER_RADIUS)
    lower += c.cyl(SOCKET_OUTER_RADIUS, -WEIGHTED_EXTENSION + .8, 3.)
    lower -= _grip_scallops(c, -WEIGHTED_EXTENSION + 1.6, 2.4)
    return lower + male_interface(c)


@lru_cache(None)
def socket_coupon(c):
    """A complete female-thread ring; use with the actual light cap."""
    return c.cyl(SOCKET_OUTER_RADIUS, 3.2, 11.4) - female_socket_void(c)


def screw_pose(part, turns_out):
    """Unscrew downwards; clockwise viewed from tip is removal."""
    return part.rotate((0., 0., -360. * turns_out)).translate(
        (0., 0., -PITCH * turns_out))


def specs():
    return {
        'interface': 'single-start helical screw; no bayonet lugs',
        'thread_pitch_mm': PITCH,
        'thread_engagement_height_mm': THREAD_Z[1] - THREAD_Z[0],
        'thread_major_diameter_mm': 2. * THREAD_CREST_RADIUS,
        'female_groove_major_diameter_mm': 2. * (THREAD_CREST_RADIUS + RADIAL_GAP),
        'female_clear_core_diameter_mm': 2. * CORE_RADIUS,
        'nominal_radial_clearance_mm': RADIAL_GAP,
        'nominal_axial_clearance_per_flank_mm': AXIAL_GAP,
        'female_nominal_outer_wall_at_thread_crest_mm':
            SOCKET_OUTER_RADIUS - THREAD_CREST_RADIUS - RADIAL_GAP,
        'flank_angle_deg': 45.,
        'light_visible_flange_z_mm': [0., 3.],
        'weighted_cap_extension_below_butt_mm': WEIGHTED_EXTENSION,
        'weight_recipe': {'infill_pattern': 'gyroid', 'infill_percent': 45,
                          'walls': 3, 'top_layers': 5, 'bottom_layers': 5},
        'print_orientation': 'cap closed underside on bed; open threaded neck upwards',
        'cap_thread_hand': 'tighten anticlockwise viewed from tip; remove clockwise',
        'battery_status': '20 x 6 x 40 mm nominal envelope remains provisional',
        'physical_acceptance': 'unverified; print matching complete thread gauge first',
    }


def check_design(c):
    """Independent full screw sweep, capture and cell-mouth checks.

    Root additionally checks these caps against both final handed stems, the
    repaired loop insertion path, the complete sled sweep, and actual slices.
    """
    caps = {'light': light_cap(c), 'weighted': weighted_cap(c)}
    ring = socket_coupon(c)
    checks = {}
    # Sample every 3 degrees through over two complete turns: beyond the neck
    # being entirely below the body. No insert-then-teleport placement test.
    turns = np.linspace(0., 2.8, 337)
    for name, cap in caps.items():
        components = cap.decompose()
        assert len(components) == 1, (name, [p.volume() for p in components])
        overlaps = [(screw_pose(cap, float(t)) ^ ring).volume() for t in turns]
        assert max(overlaps) < .01, (name, max(overlaps))
        straight = (cap.translate((0., 0., -.9)) ^ ring).volume()
        assert straight > 1., (name, straight)
        checks[name] = {'volume_mm3': round(cap.volume(), 6),
                        'bounds_mm': list(cap.bounding_box()),
                        'screw_motion_samples': len(turns),
                        'maximum_ring_collision_mm3': round(max(overlaps), 8),
                        'locked_straight_withdrawal_collision_mm3': round(straight, 6)}
    # Sled's 20.6 x 8.2 mm conservative rectangle, not just bare battery size.
    cell = c.box(-10., 10., -3., 3., -10., 40.)
    sled_envelope = c.box(-10.3, 10.3, -4.1, 4.1, -10., 40.)
    mouth_obstacle = c.cyl(14.5, -1., 11.4) - c.cyl(CORE_RADIUS, -2., 12.)
    assert (cell ^ mouth_obstacle).volume() < .001
    assert (sled_envelope ^ mouth_obstacle).volume() < .001
    # Interchangeability is exactly the same upper solid, not approximate.
    upper = c.box(-20., 20., -20., 20., 0., 12.)
    difference = ((caps['light'] ^ upper) - (caps['weighted'] ^ upper)).volume()
    difference += ((caps['weighted'] ^ upper) - (caps['light'] ^ upper)).volume()
    # The weighted flange retains the same scallops for the common Z0.8..2.4
    # band, but fills below the light flange's underside bevel; compare the
    # entire functional interface above Z0.8 instead of decorative undersides.
    functional = c.box(-20., 20., -20., 20., .8, 12.)
    a, b = caps['light'] ^ functional, caps['weighted'] ^ functional
    functional_difference = (a - b).volume() + (b - a).volume()
    assert functional_difference < .001, functional_difference
    checks['socket_coupon'] = {'volume_mm3': round(ring.volume(), 6),
                               'bounds_mm': list(ring.bounding_box())}
    checks['mouth'] = {'core_diameter_mm': 2. * CORE_RADIUS,
                       'cell_section_mm': [20., 6.],
                       'conservative_sled_section_mm': [20.6, 8.2],
                       'required_circle_diameter_mm': round(math.hypot(20.6, 8.2), 6),
                       'functional_cap_difference_mm3': round(functional_difference, 8)}
    return {'specs': specs(), 'checks': checks}
