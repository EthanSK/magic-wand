"""Add a screw-adjusted OP1 stop to the centred Grove bracket.

Run assembly37.py to regenerate and check the screw travel and Wand parts.
"""

from functools import lru_cache
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
R36 = HERE.parent / "carbon-rod-holders-r36-grove-touch"
sys.path.insert(0, str(R36))
import holder36 as base
from holder36 import (BOARD_Y, BOARD_Z, BOSS_DEPTH, BRACKET, HOLES, PILOT_DEPTH, R35, SERVICE_LIFT,
                      board, boss, box, components, cylinder, electrode, fastener,
                      fasteners, h, housing, lead, old, plug, r, union)

STOP_Y = -6.9
STOP_BOSS_BOTTOM = 13.82
START_TURNS = 2.25
PITCH = .40
EARLY_ANGLE = -1.15
BACKUP_ANGLE = .80
DECK_TOP = 11.35
SWITCH_FREE_REFERENCE = 7.35
SAMPLE_TURNS = tuple(np.linspace(0., START_TURNS, 19))


def stop_stock():
    # Front-down print: slope from the front screw floor into the stop boss.
    return r.d.wedge(-2.25, 2.25, [
        (-10.75, 16.18), (-8.1, STOP_BOSS_BOTTOM), (-4.45, STOP_BOSS_BOTTOM),
        (-4.45, 17.1), (-10.75, 17.1),
    ])


def stop_pilot(radius=.85):
    return cylinder(0., STOP_Y, STOP_BOSS_BOTTOM - .08, STOP_BOSS_BOTTOM + 4.25, radius)


def stop_screw(turns=1.125):
    """ISO 4762 M2×4, 3.8 mm head, 2 mm tall, 0.4 mm pitch."""
    head_top = STOP_BOSS_BOTTOM - turns * PITCH
    return (cylinder(0., STOP_Y, head_top - 2., head_top, 1.9)
            + cylinder(0., STOP_Y, head_top, head_top + 4., 1.))


@lru_cache(maxsize=1)
def bracket():
    # The two outer stops remain as a backup after the screw sets travel.
    heel_relief = r.mirrored(box(8.50, 10.30, -12., -9.85, 12.80, 13.59))
    # The new boss joins the forward Grove seat. Re-cut its pilot
    # after the union so the added backing cannot fill the screw opening.
    shape = base.bracket() + stop_stock() - base.pilot() - stop_pilot() - heel_relief
    return h.H.base.clean(shape, BRACKET)


@lru_cache(maxsize=1)
def carrier():
    # Only the left-hand Grove pocket needs space for the longer press.
    swing = union(r.world(part, angle)
                  for part in (lead(1.57), plug(), housing())
                  for angle in np.linspace(EARLY_ANGLE, .85, 13))
    return h.H.base.clean(base.carrier() - swing, "Key_Carrier")


def motion_limit(screw=None):
    moving = bracket() if screw is None else bracket() + screw
    low, high = EARLY_ANGLE, 1.1
    for _ in range(14):
        angle = (low + high) / 2
        if (r.world(moving, angle) ^ carrier()).volume() > .0002:
            high = angle
        else:
            low = angle
    return low, high


def actuator_travel(angle):
    paddle = r.world(bracket(), angle)
    plunger = h.hardware()["plunger"]
    low, high = 0., 1.
    for _ in range(15):
        travel = (low + high) / 2
        if (paddle ^ plunger.translate((0., 0., -travel))).volume() > .00002:
            low = travel
        else:
            high = travel
    return low


def checks():
    original = base.checks()
    key = carrier()
    paddle = bracket()
    support = base.carrier() - key
    _, working, _, guards = old.geometry()
    protected = {**guards, **{name: solid for name, (solid, _) in old.key_braces().items()},
                 "OP1 supports": h.straighten(h.h32.mount_saddles()), "edge stops": h.stop_posts()}
    removal = {name: (solid ^ support).volume() for name, solid in protected.items()}
    installed = key + working["unloaded_clip_bore"] + union(
        part for name, part in h.hardware().items() if name != "plunger")
    installed += union(working[f"key_{i}_{part}"] for i in (0, 2, 3, 4)
                       for part in ("switch", "maximum_socket", "cap_travel"))
    grove = board() + plug() + housing() + components() + fasteners() + electrode()
    backup, beyond = motion_limit()
    available = []
    for turns in SAMPLE_TURNS:
        screw = stop_screw(turns)
        stop, contact = motion_limit(screw)
        travel = actuator_travel(stop)
        available.append({
            "turns_out": float(turns), "angle_deg": round(stop, 5),
            "nominal_plunger_travel_mm": round(travel, 4),
            "stop_height_above_switch_base_mm": round(SWITCH_FREE_REFERENCE - travel, 4),
            "screw_contacts_deck_mm3": (r.world(screw, contact) ^ key).volume(),
            "plastic_before_screw_contact_mm3": (r.world(paddle, contact) ^ key).volume(),
        })
    steps = np.diff([row["nominal_plunger_travel_mm"] for row in reversed(available)])
    clearance = {
        "complete_grove_and_cable_through_backup_stroke_mm3": r._max(
            (r.world(grove + lead(1.45), a), installed)
            for a in np.linspace(EARLY_ANGLE, backup, 29)),
        "bracket_through_backup_stroke_mm3": r._max(
            (r.world(paddle, a), installed) for a in np.linspace(EARLY_ANGLE, backup, 29)),
        "pinched_bracket_install_mm3": r._max(
            (r.world(r.bent(paddle) + stop_screw(turns)).translate((0., 0., z)), installed)
            for turns in (0., START_TURNS) for z in np.linspace(0., 8., 21)),
        "stop_screw_to_sensor_mm3": max((stop_screw(t) ^ grove).volume() for t in SAMPLE_TURNS),
        "pre_fed_cable_with_stop_boss_mm3": r._max(
            (r.world(lead(1.45, lift=float(z))), installed + r.world(paddle))
            for z in np.linspace(0., SERVICE_LIFT, 25)),
    }
    original.update(
        stop_settings=available,
        max_plunger_change_per_eighth_turn_mm=round(float(max(steps)), 4),
        boss_material_bond_mm3=(stop_stock() ^ base.bracket()).volume(),
        screw_engagement_at_start_mm=4. - START_TURNS * PITCH,
        added_pocket_removed_protected_mm3=removal,
        backup_angle_deg=round(backup, 5),
        backup_nominal_plunger_travel_mm=round(actuator_travel(backup), 4),
        backup_touches_both_stops=all((r.world(paddle, beyond + .01) ^ p).volume() > .001
                                      for p in h.stop_posts().decompose()),
        updated_clearances_mm3=clearance,
    )
    original["passed"] = bool(
        original["passed"] and max(removal.values()) < .005 and max(clearance.values()) < .035
        and len(paddle.decompose()) == len(key.decompose()) == 1
        and original["boss_material_bond_mm3"] > 15. and original["backup_touches_both_stops"]
        and available[0]["stop_height_above_switch_base_mm"] < 6.65
        and available[-1]["stop_height_above_switch_base_mm"] > 7.15
        and min(steps) > 0. and max(steps) < .05
        and all(row["screw_contacts_deck_mm3"] > .00015
                and row["plastic_before_screw_contact_mm3"] < .00015 for row in available)
    )
    return original
