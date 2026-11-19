"""Two integral OP1 eyelet catches and a guided, crowned DFRobot paddle."""
import json
from hashlib import sha256
from pathlib import Path
import sys

import numpy as np
import manifold3d as mf
import trimesh

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / "carbon-rod-holders-r51-guided-hinge"
sys.path.insert(0, str(PREV))
import build51 as old

q, h, r = old.q, old.h, old.r
box, union = old.box, old.union
EXPORT = HERE / "exports"
# Running bands at the ends of the journal. The centre remains relieved.
HALF = 5.92
RUNNING_RADIUS = 1.625
THRUST_HALF = 5.93
GUIDE_LOW = 12.75
GUIDE_HIGH = 22.00
GUIDE_RADIUS = 1.0
BAND = 1.4
DOME_RADIUS = 2.4
SPRING_LENGTH = 15.4
SPRING_WIDTH = 1.1
RELEASE = 1.08
ENTRY_DX = -6.9


def dome():
    """Shallow ellipsoidal crown; same bottom height as the checked R51 foot."""
    z = q.PUSH_Z
    mid = z + 0.78
    bottom = mf.Manifold.sphere(1, 96).scale((DOME_RADIUS, DOME_RADIUS, 0.78))
    bottom = bottom.translate((q.PLUNGER_XY[0], q.PUSH_Y, mid))
    neck = mf.Manifold.cylinder(q.PUSHER_TOP - mid, DOME_RADIUS, DOME_RADIUS, 96)
    return bottom + neck.translate((q.PLUNGER_XY[0], q.PUSH_Y, mid))


def thrust_faces():
    # Capsule rails beside the journal. Their lower/upper ends pick up the
    # opposite fixed cheek faces as the paddle tries to roll sideways.
    lo, hi = THRUST_HALF - 1.40, THRUST_HALF
    low = old.cylinder_x(lo, hi, old.AXIS_Y, GUIDE_LOW, GUIDE_RADIUS)
    high = old.cylinder_x(lo, hi, old.AXIS_Y, GUIDE_HIGH, GUIDE_RADIUS)
    return r.mirrored(mf.Manifold.batch_hull([low, high]))


def cheek_guides():
    lo, hi = old.FORK_INNER, old.FORK_OUTER
    base = old.cylinder_x(lo, hi, old.AXIS_WORLD_Y, 20.0, 1.4)
    end = old.cylinder_x(lo, hi, old.AXIS_WORLD_Y, GUIDE_HIGH, 1.35)
    extension = mf.Manifold.batch_hull([base, end])
    extension -= old.cylinder_x(lo - 0.01, hi + 0.01, old.AXIS_WORLD_Y, old.AXIS_Z, old.FORK_BORE)
    return r.mirrored(extension)


def paddle():
    from unittest.mock import patch

    with patch.object(q, "pusher", dome):
        P = old.paddle()
    for sign in (-1, 1):
        lo, hi = sorted((sign * (HALF - BAND), sign * HALF))
        band = old.cylinder_x(lo, hi, old.AXIS_Y, old.AXIS_Z, 2.68)
        P += band
    P += thrust_faces()
    # A two-sided roof allowance follows the measured native sleeve restriction.
    # The near-vertical radii still constrain paddle roll at the journal ends.
    points = []
    for a in np.linspace(0, 2 * np.pi, 160, endpoint=False):
        extra = 0.105 * np.cos(a - np.radians(23)) ** 4
        radius = RUNNING_RADIUS + extra
        points.append((radius * np.cos(a), radius * np.sin(a)))
    section = mf.CrossSection([points])
    bore = (
        mf.Manifold.extrude(section, 2 * HALF + 0.2)
        .rotate((90, 0, 90))
        .translate((-HALF - 0.1, old.AXIS_Y, old.AXIS_Z))
    )
    P -= bore
    # Join the two tangential seams inherited beneath the rear fan roots.
    for x in (-3.05, 3.05):
        P += box(x - 0.075, x + 0.075, 13.18, 14.92, 16.94, 17.19)
    return P


def local_z(world_z):
    return world_z - q.OP1_DZ


def beam_station(x, y, z, width, thickness):
    """Rectangular working section on a tapered leaf."""
    return box(x - width / 2, x + width / 2, y - 0.09, y + 0.09, z, z + thickness)


def beam_dimensions(t):
    taper=np.maximum(0.,1.-4*t)**2
    return SPRING_WIDTH+.90*taper,1.14+.28*taper


def nominal_bending_strain():
    distance=np.linspace(1.25,SPRING_LENGTH,1001)
    arm=SPRING_LENGTH-distance
    width,thickness=beam_dimensions(distance/SPRING_LENGTH)
    inertia=width*thickness**3/12
    force_over_modulus=RELEASE/np.trapezoid(arm**2/inertia,distance)
    return float(np.max(force_over_modulus*arm*thickness/(2*inertia)))


def arm_features(y, side, lift=0.0):
    """Above-rim integral leaf and broad reach ending in a down-pointing peg.
    Lift the rounded nose and tilt the plugged board beneath the raised pegs.
    """
    root_y = y + side * SPRING_LENGTH
    rail_x = 6.45 if side == 1 else 8.85
    floor = local_z(11.68)
    thickness = 1.14
    root = box(
        rail_x - 1.02,
        rail_x + 1.02,
        root_y - 1.25,
        root_y + 1.25,
        local_z(10.40),
        floor + thickness,
    )
    stations = []
    for t in np.linspace(0, 1, 13):
        u = t * t * (3 - t) / 2
        stations.append(
            beam_station(
                rail_x,
                root_y - side * SPRING_LENGTH * t,
                floor + lift * u,
                *beam_dimensions(t),
            )
        )
    spine = union(mf.Manifold.batch_hull([a, b]) for a, b in zip(stations, stations[1:]))
    # A short rounded thumb lip lies past the peg, clear of the switch case.
    # Keep the crossbar thin in the longitudinal direction at the front eyelet.
    stations = []

    def pad(x, cy, z, radius, height):
        return h.h32.cylinder_at(x, cy, z, z + height, radius)

    for x, rad in [(rail_x, 0.61), (3.0, 1.18), (0.0, 0.83), (-0.18, 0.90)]:
        stations.append(pad(x, y, floor + lift, rad, thickness))
    nose = union(mf.Manifold.batch_hull([a, b]) for a, b in zip(stations, stations[1:]))
    # Underside pad sits just above the board. Locate the peg in its actual
    # eyelet with a lead taper, without clamping the board under preload.
    top = local_z(q.PCB_TOP)
    x = 0.0
    pad_top = pad(x, y, top + 0.24 + lift, 1.06, floor + thickness - top - 0.24)
    peg = h.h32.cylinder_at(x, y, top - 0.55 + lift, top - 0.20 + lift, 0.74, 1.04)
    peg += h.h32.cylinder_at(x, y, top - 0.20 + lift, top + 0.30 + lift, 1.04)
    return root, spine, nose + pad_top + peg


def lifted_vertices(world_vertices, y, side, lift):
    """Viewer deformation for a released leaf or its tip. The root stays fixed."""
    vs = np.asarray(world_vertices, dtype=float).copy()
    angle = np.radians(q.OP1_YAW)
    bx, by = q.board_point(0, 0)
    ys = -(vs[:, 0] - bx) * np.sin(angle) + (vs[:, 1] - by) * np.cos(angle)
    t = np.clip(side * (y + side * SPRING_LENGTH - ys) / SPRING_LENGTH, 0.0, 1.0)
    # Across the nose use rigid tip travel. Along the strap use cantilever travel.
    xs = (vs[:, 0] - bx) * np.cos(angle) + (vs[:, 1] - by) * np.sin(angle)
    rail = 6.45 if side == 1 else 8.85
    t[(abs(xs - rail) > 1.0) & (abs(ys - y) < 1.4)] = 1.0
    vs[:, 2] += lift * t * t * (3 - t) / 2
    return vs


def arm_clearance_masks():
    """World-space gaps below each leaf. Slicer support must stay out."""
    blockers = []
    for y, side in zip(h.h32.EYELETS, (1, -1)):
        root, spine, nose = arm_features(y, side)
        under = union([(spine + nose).translate((0, 0, -dz)) for dz in (0.2, 0.5, 0.8, 1.1)])
        blockers.append(q.board_frame(under - (root + spine + nose)))
    return union(blockers)


def board_offset(dx, dz):
    angle = np.radians(q.OP1_YAW)
    return (dx * np.cos(angle), dx * np.sin(angle), dz)


def insertion_parts(clear=0):
    # Slot the OP1 PCB with its plugged-in lead before fitting the switch
    # and keys. The three socket barrels and white plug project below the PCB.
    z, top = h.h32.PCB_Z, h.h32.PCB_TOP

    def stock(x, y0, y1, z0, z1):
        return q.board_frame(
            box(-x - clear, x + clear, y0 - clear, y1 + clear, z0 - clear, z1 + clear)
        )

    pcb = stock(h.h32.PCB_HALF_X, *h.h32.PCB_Y, z, top)
    body = stock(h.h32.PLUG_HALF_X, *h.h32.PLUG_Y, h.h32.MATE_TOP, z)
    plug = stock(h.h32.MATE_HALF_X, *h.h32.MATE_Y, z - h.h32.PLUG_DEPTH, h.h32.MATE_TOP)
    sockets = [
        q.board_frame(
            h.h32.cylinder_at(0, y, z - h.h32.SOCKET_DEPTH - clear, z + 0.01, 1.3 + clear)
        )
        for y in [h.h32.ACTUATOR_TO_MIDDLE + i * h.h32.PIN_PITCH for i in (-1, 0, 1)]
    ]
    return [pcb, body, plug, *sockets]


def entry_transform(t):
    """From seated (0) to raised approach (1); tilt about the incoming long edge."""
    side = np.sign(ENTRY_DX)
    angle = -side * np.radians(62 * t ** 2.5)
    c, s = np.cos(angle), np.sin(angle)
    yaw = np.radians(q.OP1_YAW)
    zrot = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
    rot = zrot @ np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]) @ zrot.T
    pivot = np.array([*q.board_point(-side * 4.1, 0), q.PCB_TOP])
    dx = ENTRY_DX * t
    disp = np.asarray(board_offset(dx, 0.35 * t))
    return np.column_stack([rot, pivot - rot @ pivot + disp]).tolist()


def board_entry_relief():
    cutters = []
    for i, component in enumerate(insertion_parts(0.28)):
        # Clearance below the PCB at home stops above the seated floor.
        # The already open, nominal fitted pocket owns that final surface.
        stations = [component.transform(entry_transform(t)) for t in np.linspace(0.04, 1, 13)]
        path = union(mf.Manifold.batch_hull([a, b]) for a, b in zip(stations, stations[1:]))
        path += mf.Manifold.batch_hull([stations[-1], stations[-1].translate((0, 0, 16))])
        if i == 0:
            path ^= box(-40, 40, -50, 50, q.PCB_Z + 0.002, 60)
        cutters.append(path)
    return union(cutters)


def support_keepouts(carrier_mesh):
    """Assembly-space support blockers without any installed printed material."""
    return (arm_clearance_masks() + board_entry_relief()) - carrier_mesh


def carrier(include_arms=True):
    C = old.baseline.b.load(PREV / "exports/Key_Carrier-assembly.stl")
    C += cheek_guides()
    C -= board_entry_relief()
    arms = []
    for y, side in zip(h.h32.EYELETS, (1, -1)):
        # Fill the original tiny screw pilot and trim the old locator flush.
        plug = h.h32.cylinder_at(
            0, y + (-0.85 if side == 1 else 0), local_z(7.31), local_z(q.PCB_Z), 0.80
        )
        clear = h.h32.cylinder_at(0, y, local_z(q.PCB_Z), local_z(q.PCB_TOP + 2), 2.5)
        root, leaf, tip = arm_features(y, side)
        arm = q.board_frame(root + leaf + tip)
        C = (C + q.board_frame(plug)) - q.board_frame(clear)
        # An uninterrupted air slit isolates the working length from the rim.
        # The fixed root is the only intended attachment.
        root_y = y + side * SPRING_LENGTH
        lo, hi = sorted((root_y - side * 1.32, y - side * 2.7))
        window = box(-25, 25, lo, hi, local_z(10.0), local_z(16.5))
        poses = [0, RELEASE / 2, RELEASE]
        relief = []
        for lift in poses:
            _, b, t = arm_features(y, side, lift)
            relief.append(
                mf.Manifold.batch_hull(
                    [
                        b.translate((dx, dy, dz))
                        for dx in (-0.72, 0.72)
                        for dy in (-0.52, 0.52)
                        for dz in (-0.68, 0.62)
                    ]
                )
            )
            relief.append(
                mf.Manifold.batch_hull(
                    [
                        t.translate((dx, dy, dz))
                        for dx in (-0.72, 0.72)
                        for dy in (-0.52, 0.52)
                        for dz in (-0.62, 0.62)
                    ]
                )
            )
        C -= q.board_frame(union(relief) ^ window)
        arms.append(arm)
    return C + union(arms) if include_arms else C


def click_stops():
    """Fixed pads outside the OP1 insertion path; the new left pad meets the rigid paddle underside."""
    right=box(9.92,10.35,-7.94,-7.30,11.62,13.08)+box(9.60,10.35,-7.95,-7.68,11.62,13.08)
    footprint=box(-7.68,-6.36,9.08,15.80,10.90,11.48)
    # The slope supports the boss in rear-down printing and carries the load to the rim.
    cap=box(-7.62,-6.45,9.15,9.98,16.68,16.97)
    return right+mf.Manifold.batch_hull([footprint,cap])


def stop_parts(carrier_shape,paddle_shape):
    """Gauge the actual exposed carrier stops against the original heel and rigid left underside."""
    feet=carrier_shape^(box(-11,11,-10,-5,12.2,13.22)+box(-7.9,-6.15,8.9,10.3,16.35,17.20))
    local_strip=box(-7.95,-6.15,9.05-r.CLICK_SHIFT,10.20-r.CLICK_SHIFT,15,19)
    heels=paddle_shape^(box(-11,11,-12.5,-8,13.1,15)+local_strip)
    return feet,heels


def production_carrier(control_frame):
    from relief52 import relieve
    mechanical=carrier()
    control=json.loads((HERE/'control-starts52.json').read_text())
    shape,report=relieve(mechanical,control_frame,control)
    pieces=sorted(shape.decompose(), key=lambda s:-s.volume())
    # A trim in the obsolete lower floor can split off small remnants.
    # Only the largest connected carrier is printed. Check all omitted pieces.
    discarded=[abs(s.volume()) for s in pieces[1:]]
    if max(discarded,default=0.)>.11 or sum(discarded)>.5:
        raise ValueError(f"Detached carrier remnants (mm3): {sorted(discarded, reverse=True)[:10]} total {sum(discarded)}")
    report['discarded_skin_mm3']=round(sum(discarded),6)
    from relief52 import back_fixed_starts, trim_fixed_fringes
    reinforced,report["fixed_start_backing_mm3"]=back_fixed_starts(pieces[0],control_frame)
    return trim_fixed_fringes(reinforced,control_frame)+click_stops(),report


def main(output=None):
    from clearance51 import patches
    patches()
    output=Path(output) if output is not None else EXPORT
    framefile=PREV/'exports/print/trial.frame.json'
    report=json.loads(framefile.read_text())
    frame=np.asarray(report['parts']['Key_Carrier']['assembly_to_machine'])
    physical,relief=production_carrier(frame)
    from relief52 import key_entry_bevel
    physical,key_entry=key_entry_bevel(physical,frame)
    connected=sorted(physical.decompose(),key=lambda part:-part.volume())
    key_entry["detached_skin_mm3"]=round(sum(abs(part.volume()) for part in connected[1:]),6)
    if key_entry["detached_skin_mm3"]>.25:
        raise ValueError("Unexpected disconnected material at a key opening")
    physical=connected[0]

    output.mkdir(exist_ok=True)
    records = {}
    for name, shape in [("DFRobot_Hole_Bracket", paddle()), ("Key_Carrier", physical)]:
        path = output / (name + "-assembly.stl")
        pieces = sorted(shape.decompose(), key=lambda s: -s.volume())
        print(
            name,
            "pieces",
            [(round(s.volume(), 5), old.xyz_bounds(s)) for s in pieces[:5]],
            flush=True,
        )
        if any(abs(s.volume()) > 0.015 for s in pieces[1:]):
            raise ValueError("Detached geometry")
        accuracy=.004 if name=="Key_Carrier" else .002
        final=(shape if name=="Key_Carrier" else pieces[0]).simplify(accuracy)
        old.baseline.b.save(path, final)
        mesh = trimesh.load_mesh(path)
        if name=="Key_Carrier" or not mesh.is_watertight:
            # STL writes coordinates as float32 and omits vertex indices. At
            # coincident R51 skin edges this collapses distinct mesh nodes.
            # Give only duplicated nodes a deterministic sub-micron offset.
            indexed = final.to_mesh()
            vertices = np.array(indexed.vert_properties[:, :3], dtype=np.float64)
            _, groups, counts = np.unique(vertices, axis=0, return_inverse=True, return_counts=True)
            coincident = counts[groups] > 1
            rng = np.random.default_rng(52)
            vertices[coincident] += rng.uniform(-0.00018, 0.00018, (coincident.sum(), 3))
            trimesh.Trimesh(vertices, indexed.tri_verts, process=False).export(path)
            mesh = trimesh.load_mesh(path)
        print(name, mesh.is_watertight, mesh.is_volume, flush=True)
        if not mesh.is_volume:
            raise ValueError("Invalid export")
        records[name] = dict(sha256=sha256(path.read_bytes()).hexdigest(), volume_mm3=mesh.volume)
    (output / "dimensions.json").write_text(
        json.dumps(
            dict(
                meshes=records,
                lower_floor_relief=relief,
                key_entry_bevel=key_entry,
                eyelet_pitch_mm=17.9,
                peg_diameter_mm=2.08,
                release_travel_mm=RELEASE,
                crown_diameter_mm=DOME_RADIUS * 2,
                plunger_reference_mm=[2.9, 1.2],
                bearing_span_mm=2 * HALF,
                bearing_band_mm=BAND,
                running_diameter_mm=2 * RUNNING_RADIUS,
                sleeve_mm=[3, 2.1, 12],
                axle_mm=[2, 20],
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv)>1 else None)
