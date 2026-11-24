"""Short connector-down paddle with open trunnion bearings and a rear-entry centre clip.

The bought PCB, its soldered housing, post bar and the front click geometry stay in
the R63 pose. The lowered pin lies below the wired exit. The two circular barrel
ends ride in upward-open U bearings independently of printed-pin diameter.
"""
from functools import lru_cache
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r63-open-hinge'))
import design63 as previous

b, m, r61 = previous.b, previous.m, previous.r61
OUT = HERE / 'exports'
AXIS = 33.6
KEEPER_Z = 12.7
PIVOT = np.array([0., AXIS, KEEPER_Z])
MOVE = (0., AXIS - previous.AXIS, KEEPER_Z - previous.KEEPER_Z)
BARREL_R = 3.30
JOURNAL_R = 3.00
JOURNAL_OUT = 8.60
RADIAL_GAP = .15
AXIAL_GAP = .16
CLIP_ANGLE = -90.
INNER = m.BARREL_X + AXIAL_GAP
OUTER = m.CHEEK_X[1]
TOP = KEEPER_Z + 3.25
REAR = AXIS + 3.50


def rotate(shape, degrees):
    return shape.translate(-PIVOT).rotate((float(degrees), 0, 0)).translate(PIVOT)


def pin(name='Hinge_Pin'):
    body = b.load(r61.OUT / (name + '-assembly.stl'))
    snug_lift = .1 if name == 'Hinge_Pin_Snug' else 0.
    return body.translate((0, AXIS-r61.AXIS, KEEPER_Z-m.PIN_Z-snug_lift))


def clip():
    return rotate(pin('Pin_Clip'), CLIP_ANGLE)


def disc(radius, x0, x1):
    return mf.Manifold.cylinder(x1-x0, radius, radius, 96).rotate((0,90,0)).translate((x0, AXIS, KEEPER_Z))


def wire_paths():
    """Three distinct 1.3 mm leads rise together out of the plug and turn toward +X.

    The bend radii preserve the spacing of the three separate crimp
    positions. The open rear and right side accommodate the unmodelled slack.
    """
    strands = []
    radii = (5.95, 4.35, 2.75)
    y = r61.SOCKET_FACE + 3.25
    for start_x, radius in zip((-2., 0., 2.), radii):
        centre_x = start_x + radius
        nodes = [(start_x, y, b.SEAT_Z-2.85)]
        for a in np.linspace(0., np.pi/2, 19):
            progress = min(1., (radius*a+.35)/4.2)
            rise = 2.10 * progress**2 * (3.-2.*progress)
            nodes.append((centre_x-radius*math.cos(a), y+.35+radius*math.sin(a), b.SEAT_Z-2.85+rise))
        nodes.append((15.2, nodes[-1][1], nodes[-1][2]))
        strands.append(nodes)
    return strands


@lru_cache(maxsize=1)
def wired_lead():
    return b.union(r61.run(nodes, r61.LEAD_R) for nodes in wire_paths())


def rear_clip_slot():
    # Clearance around the fingers and grip for full insertion along -Y.
    return b.box(-1.00, 1.00, AXIS-3.75, AXIS+8., KEEPER_Z-2.57, KEEPER_Z+2.57)


def paddle():
    old = b.load(previous.OUT / previous.PADDLE)
    front = old ^ b.box(-15,15,-30,20.05,0,40)
    # Centre the barrel and both R63-shaped cheek throats on one axis. The
    # trunnions locate the paddle independently of the pin-hole clearance.
    length = m.BARREL_X
    barrel = disc(BARREL_R, -length, length) + b.mirrored(disc(JOURNAL_R, length-.22, JOURNAL_OUT))
    # Top-down print: a continuous bed-side spine away from the cable joins
    # the barrel to the left rail. The right beam sits below the wired exit.
    left = mf.Manifold.batch_hull([b.box(-10.6,-8.6,19.65,20.05,15.35,b.SEAT_Z),
                                   b.box(-6.80,-4.65,AXIS-.8,AXIS+.7,KEEPER_Z+.4,b.SEAT_Z)])
    right = mf.Manifold.batch_hull([b.box(8.60,10.60,19.65,20.04,15.35,b.SEAT_Z),
                                    b.box(5.0,7.0,AXIS-.7,AXIS+.4,KEEPER_Z-.55,KEEPER_Z+1.2)])
    # The rear spine sits flat on the bed in the top-down print. Its diagonal
    # web backs the first barrel beads across the width below the wire bend.
    web_profile = [(AXIS+.03,KEEPER_Z+.55),(AXIS+.03,KEEPER_Z+BARREL_R+.20),
                   (AXIS+3.26,b.SEAT_Z),(AXIS+3.98,b.SEAT_Z),(AXIS+3.35,KEEPER_Z+1.75)]
    rear_web = b.prism_yz(web_profile,-6.85,6.85) - cable_loading_space()
    rail_relief = b.mirrored(b.box(m.BARREL_X-.08,12., AXIS-4.65,REAR+.1,8.,24.))
    body = front + ((left + right) - rail_relief) + rear_web + barrel
    bore = m.hole(AXIS, KEEPER_Z, m.BARREL_HOLE_R, (0,-1), -JOURNAL_OUT, JOURNAL_OUT)
    return body - bore - rear_clip_slot()


@lru_cache(maxsize=1)
def cable_loading_space():
    # Sweep a 0.38 mm clearance envelope from the three cable paths upwards.
    # A shadow taken at a single Z would remove the diagonal print support
    # below the higher, bent portion of the wires as well.
    ball = mf.Manifold.sphere(r61.LEAD_R+.38, 24)
    cuts = []
    for path in wire_paths():
        columns = [mf.Manifold.batch_hull([ball.translate(p), ball.translate((p[0],p[1],24.))])
                   for p in path]
        cuts.extend(mf.Manifold.batch_hull([a,z]) for a,z in zip(columns,columns[1:]))
    return b.union(cuts)


def cheeks():
    # Rear-down print: this uninterrupted sloping root grows from the old
    # tongue onto each loaded cheek. The broad pivot stop is closer to the
    # board. The ramp merges into the existing rod/battery bed plane.
    bottom = 8.65
    profile = [(AXIS-4.40,bottom),(AXIS-4.40,TOP-.85),(AXIS-3.55,TOP),
               (REAR-.45,TOP),(REAR+.05,TOP-.50),(previous.BED,9.40),
               (previous.BED,bottom)]
    cheek = b.prism_yz(profile, INNER, OUTER)
    shifted_section = previous.bore_section().translate((MOVE[1], MOVE[2]))
    cut = m.along_x(shifted_section, INNER-.3, OUTER+.1)
    cut += previous.lead_in(shifted_section, OUTER, -1)
    cut += previous.lead_in(shifted_section, JOURNAL_OUT+AXIAL_GAP, 1)
    # U sockets can drop straight over the journals. Long, upright flanks
    # continue guiding even when the user's press lifts the side of the hinge.
    socket_r = JOURNAL_R + RADIAL_GAP
    end = JOURNAL_OUT + AXIAL_GAP
    socket = disc(socket_r, INNER-.02, end).translate((0,0,-KEEPER_Z)).scale(
        (1,1,(JOURNAL_R+.035)/socket_r)).translate((0,0,KEEPER_Z))
    socket += b.box(INNER-.02, end, AXIS-socket_r, AXIS+socket_r, KEEPER_Z, TOP+.1)
    return b.mirrored(cheek - cut - socket)


def carrier(body):
    # Remove the old rear-down hinge above the keypad deck; preserve the
    # battery roof land (top 8.47), rod socket, and wire-bus cross-section.
    body -= b.box(-11.65,11.65,28.0,previous.BED+.1,10.95,32.)
    # Nest the lowered barrel. Its entire central channel remains open above
    # for removal with the PCB and cable still attached.
    body -= b.box(-INNER,INNER,AXIS-4.65,AXIS+4.20,KEEPER_Z-BARREL_R-.45,32.)
    body -= b.mirrored(b.box(INNER-.01,OUTER+.01,AXIS-4.5,REAR+.06,8.8,32.))
    body -= b.box(-.96,.96, AXIS+2.,previous.BED+.1,KEEPER_Z-3.62,20.)
    # The deck corners beyond both outer cheeks skim the round insertion
    # line even though the D-flat pins fit nominally. Give the approaching
    # leading end an open trough, above the rear rod and pouch roof.
    approach = disc(2.38,OUTER-.01,35.) + b.box(OUTER-.01,35.,AXIS-2.38,AXIS+2.38,KEEPER_Z,24.)
    return (body - b.mirrored(approach)) + cheeks()


def save_parts():
    OUT.mkdir(exist_ok=True)
    for name, shape in [('Touch_Paddle',paddle()), ('Gravity_Wires',wired_lead())]:
        if name == 'Touch_Paddle':
            shape = previous.one_piece(shape, name)
        b.save_closed(OUT / (name+'-assembly.stl'),shape)


if __name__ == '__main__':
    save_parts()
