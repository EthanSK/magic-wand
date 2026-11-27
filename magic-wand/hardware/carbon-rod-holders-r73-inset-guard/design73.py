"""R73 corrects the battery-side finger guard on the finished R72 carrier.

The other three tips are the shape reference. Keep R72's battery, symmetric
upper outline, open OP1 route and complete nine-piece kit. — GPT-6.2 Astra
"""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'carbon-rod-holders-r72-inboard-battery'))
import design72 as prior
import checks71

OUT=HERE/'exports'
HOLDER=prior.HOLDER
SOURCE_SHA='b366e7da2a673765712714a6939640419b6cea05efe7554d7d26bbc095bc56ee'
b, design, fit = prior.b, prior.prev, prior.r64
RADIUS=1.35
SOCKET_MARGIN=.18


def centres():
    # Ethan wants all four tips to come *in* like the three he likes. Copy
    # their actual side curve, including the almost tangent entry at the
    # rounded rim. Keep the two battery-side roots 14 mm apart for his grip.
    profile=fit.smooth_return(28.2)
    points=[]
    def ease(t):
        return t*t*(3.-2.*t)
    for t in np.linspace(0.,1.,29):
        _, y, z=fit.bezier(profile,t)
        # The prewired black socket slides across this bank from outside.
        # Bend sideways under it, then meet the finger rest at the same tip.
        # Moving the joint towards the bottom edge instead caused R72's lip.
        if t<.40:
            x=28.2+(19.3-28.2)*ease(t/.40)
        else:
            x=19.3+(22.1-19.3)*ease((t-.40)/.60)
        points.append((-x,y,z))
    return points


@lru_cache(maxsize=1)
def socket_clearance():
    design.old.k.old.configure_new_op1()
    spaces=checks71.c70.placed_spaces()
    local=b.box(-31.,-16.,-10.,7.,-2.,10.)
    keep=b.union([shape for name,poses in spaces.items() if name.startswith('key_0') for shape in poses]) ^ local
    margin=SOCKET_MARGIN
    offsets=[(0.,0.,0.),(margin,0.,0.),(-margin,0.,0.),(0.,margin,0.),
             (0.,-margin,0.),(0.,0.,margin),(0.,0.,-margin)]
    return b.union(keep.translate(v) for v in offsets)


def branch():
    return design.r61.run(centres(),RADIUS)-socket_clearance()


def carrier():
    path=prior.OUT/HOLDER
    if sha256(path.read_bytes()).hexdigest()!=SOURCE_SHA:
        raise ValueError('R72 carrier differs from the checked export')
    body=b.load(path)
    original=b.load(design.OUT/HOLDER)
    old=prior.fork_support()
    # Cut just the previous branch. Restore any shell or shared finger-rest
    # material also present in R71, so its rounded edge and PCB seats survive.
    directions=[(0.,0.,0.),(.03,0.,0.),(-.03,0.,0.),(0.,.03,0.),(0.,-.03,0.),(0.,0.,.03),(0.,0.,-.03)]
    cutter=b.union(old.translate(v) for v in directions)
    stock=(body-cutter)+(original ^ (body ^ cutter))
    pieces=sorted((stock+branch()).decompose(),key=lambda part:part.volume(),reverse=True)
    # The former branch crossed R71's old return. Tiny isolated flecks where
    # the two rounded skins grazed do not belong on Ethan's finger surface.
    for fleck in pieces[1:]:
        if fleck.volume()>1e-5:
            outside=(fleck-cutter).volume()
            if fleck.volume()>.10 or outside>1e-5:
                raise ValueError(('unexpected detached material',fleck.volume(),outside,fleck.bounding_box()))
    return pieces[0]


def export():
    OUT.mkdir(exist_ok=True)
    path=OUT/HOLDER
    shape=carrier()
    for _ in range(3):
        b.save_closed(path,shape)
        mesh=b.load(path)
        if mesh.status()==mf.Error.NoError and len(mesh.decompose())==1:
            return
        shape=design.old.one_piece(mesh,'float32 seam',limit=.00001)
    raise ValueError('R73 must export as one watertight solid')


if __name__=='__main__':
    export()
