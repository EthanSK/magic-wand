#!/usr/bin/env python3
"""One definition of functional spaces for helper generation and bead checks."""
from functools import lru_cache
import numpy as np
import cad

@lru_cache(maxsize=1)
def maximum_socket():
    # The maximum sourced socket envelope is retained from R12's independent
    # geometry checker, including its pocket-bottom datum.
    socket=cad.seated_hardware()['socket'];bounds=np.array(socket.bounding_box());centre=(bounds[:3]+bounds[3:])/2
    return socket.translate((-centre[0],-centre[1],-bounds[2])).scale((13.55/13.15,6.95/6.85,3.25/3.05)).translate((centre[0],centre[1],cad.P['keys']['socket_pocket_bottom']))

@lru_cache(maxsize=1)
def socket_route():
    """The sampled hot-swap socket loading route, as offsets from its seat.

    115 vertical, 61 diagonal and 13 final vertical poses. verify_geometry.py
    keeps its own independent copy and requires it to stay identical.
    """
    route=[(-2.5,-4.824,dz)for dz in np.linspace(12,.6,115)]
    route += [(-2.5*(1-t),-4.824*(1-t),.6)for t in np.linspace(0,1,61)]
    route += [(0,0,dz)for dz in np.linspace(.6,0,13)]
    route=np.array(route,dtype=float);assert route.shape==(189,3)
    route.setflags(write=False)
    return route

class Swept:
    """The exact union of rigid translates of one solid, kept as its poses.

    A 3D union of the 189 sampled socket poses materialises the swept
    envelope everywhere, mostly in empty space, and exceeded the 2 GiB
    geometry guard. Every consumer needs that union only against existing
    material (CAD carving) or on a print layer (helper halos and actual bead
    checks). Subtraction and slicing both distribute exactly over a union,
    so each is evaluated pose by pose. Every pose is used whole: no pose,
    sample step, tolerance or hardware change, and nothing is cropped.
    """
    def __init__(self,solid,offsets):
        offsets=np.array(offsets,dtype=float).reshape(-1,3)
        assert len(offsets) and np.isfinite(offsets).all(),'Swept space needs finite poses'
        self.solid,self.offsets,self._box=solid,offsets,None

    def __len__(self):
        return len(self.offsets)

    def base_box(self):
        if self._box is None:self._box=np.asarray(self.solid.bounding_box(),dtype=float)
        return self._box

    def poses(self):
        # Generate each pose on demand: holding all evaluated poses costs memory.
        for t in self.offsets:yield self.solid.translate(tuple(float(v)for v in t))

    def translate(self,v):
        return Swept(self.solid,self.offsets+np.asarray(v,dtype=float))

    def transform(self,m):
        # m(S+t) = m(S) + (linear part of m) t, for an affine 3x4 matrix m.
        m=np.asarray(m,dtype=float)[:3,:]
        moved=Swept(self.solid.transform(m),self.offsets@m[:,:3].T)
        check_transform(self,moved,m)
        return moved

    def bounding_box(self):
        # The box of a union of translates is the union of their boxes.
        b=self.base_box()
        return tuple(float(v)for v in np.r_[b[:3]+self.offsets.min(0),b[3:]+self.offsets.max(0)])

    def slice(self,z):
        # A pose's section at z is the base section at z-dz moved by (dx,dy).
        b=self.base_box();z=float(z);sections={};pieces=[]
        for dx,dy,dz in self.offsets:
            h=z-float(dz)
            if h<b[2] or h>b[5]:continue
            if h not in sections:sections[h]=self.solid.slice(h)
            if not sections[h].is_empty():pieces.append(sections[h].translate((float(dx),float(dy))))
        return cad.mf.CrossSection.batch_boolean(pieces,cad.mf.OpType.Add)if pieces else cad.mf.CrossSection()

    def subtract_from(self,shape):
        """Exactly shape minus every pose, without a union of the poses.

        Only poses meeting remaining material can change the shape. Each pose
        is tested whole against the material inside a box containing every
        pose, then subtracted. Each step is evaluated: left lazy, Manifold
        would batch the chain into one union of all poses, the swept
        envelope this avoids. The result is that of subtracting the union.
        """
        b=self.bounding_box();lo=np.array(b[:3])-1;hi=np.array(b[3:])+1
        shape.num_tri()
        crop=shape^cad.box(float(lo[0]),float(hi[0]),float(lo[1]),float(hi[1]),float(lo[2]),float(hi[2]));crop.num_tri()
        met=0
        for pose in self.poses():
            if crop.is_empty():break
            if (crop^pose).is_empty():continue
            shape=shape-pose;shape.num_tri()
            crop=crop-pose;crop.num_tri();met+=1
        assert shape.status()==cad.mf.Error.NoError,shape.status()
        return shape,met

def check_transform(original,moved,m,levels=3):
    """Bounded equivalence probe of the pose bookkeeping under a transform.

    Four individual poses only: each is transformed directly by Manifold and
    compared with the moved representation, by bounds and three sections.
    """
    n=len(original)
    for i in sorted({0,n//3,(2*n)//3,n-1}):
        direct=original.solid.translate(tuple(float(v)for v in original.offsets[i])).transform(m)
        single=Swept(moved.solid,moved.offsets[i:i+1])
        a=np.asarray(direct.bounding_box(),dtype=float);b=np.asarray(single.bounding_box(),dtype=float)
        assert np.allclose(a,b,atol=1e-6),('Swept pose bounds changed under transform',i,a,b)
        for z in np.linspace(a[2],a[5],levels+2)[1:-1]:
            x=direct.slice(float(z));y=single.slice(float(z))
            assert (x-y).area()+(y-x).area()<1e-6,('Swept pose section changed under transform',i,float(z))

class Spaces:
    """The union of working spaces for print-layer sections."""
    def __init__(self,spaces=(),solid=None,swept=None):
        if solid is None:
            spaces=list(spaces)
            solid=cad.union([s for s in spaces if not isinstance(s,Swept)]);swept=[s for s in spaces if isinstance(s,Swept)]
        self.solid,self.swept=solid,list(swept)

    def transform(self,m):
        return Spaces(solid=self.solid.transform(m),swept=[s.transform(m)for s in self.swept])

    def slice(self,z):
        z=float(z);parts=[self.solid.slice(z)]
        for s in self.swept:
            b=s.bounding_box()
            if b[2]<=z<=b[5]:parts.append(s.slice(z))
        return cad.mf.CrossSection.batch_boolean(parts,cad.mf.OpType.Add)

CARVE_LOG={}

def carve(shape,spaces,label):
    """Exactly shape minus the union of the named spaces; no swept 3D union."""
    solids=[s for s in spaces.values()if not isinstance(s,Swept)]
    if solids:shape=shape-cad.union(solids)
    log={}
    for name,space in spaces.items():
        if isinstance(space,Swept):
            shape,met=space.subtract_from(shape)
            log[name]={'poses':len(space),'poses_meeting_material':met}
    CARVE_LOG[label]=log
    return shape

@lru_cache(maxsize=32)
def regions(name,diameter=None,key_indices=None):
    diameter=diameter or cad.P['rod']['clip_diameter']
    result={'unloaded_clip_bore':cad.cyl(diameter/2,-40,100).rotate((-90,0,0))}
    if name in ['Key_Carrier','Battery_Holder']:result['external_wire_bus']=cad.wire_bus(-80,100)
    if name=='Battery_Holder':result['reverse_wire_bus']=cad.wire_bus(-80,100).mirror((1,0,0))
    if name!='Battery_End_Gate':
        centres=cad.carrier_clip_centres()if name=='Key_Carrier'else cad.battery_clip_centres()if name=='Battery_Holder'else[-3.8,22.2]
        for i,y in enumerate(centres):
            width=cad.P['rod']['sensor_clip_width']if name=='XIAO_Rod_Holder'else cad.P['rod']['ring_width']
            result[f'clip_gap_{i}']=cad.clip_gap(y,width)
    if name=='Key_Carrier':
        k=cad.P['keys'];z=k['pcb_z'];hw=cad.seated_hardware();route=socket_route()
        for i,(x,y)in enumerate(cad.key_positions()):
            if key_indices is not None and i not in key_indices:continue
            for label,shape in {**hw,'maximum_socket':maximum_socket()}.items():result[f'key_{i}_{label}']=shape.translate((x,y,z))
            for label,socket in [('socket_loading',hw['socket']),('maximum_socket_loading',maximum_socket())]:
                # All 189 sampled poses, exactly as before, kept as poses.
                result[f'key_{i}_{label}']=Swept(socket,route+np.array([x,y,z],dtype=float))
            result[f'key_{i}_mount_opening']=cad.rr(14.1,14.1,.2,z+k['plate_bottom'],z+k['plate_bottom']+1.2).translate((x,y,0))
        if key_indices is None:
            expected=2+len(cad.carrier_clip_centres())+6*len(cad.key_positions())
            assert len(result)==expected,('Missing Key_Carrier working spaces',len(result),expected)
    elif name=='Battery_Holder':
        floor=cad.P['battery']['floor_z']+cad.P['assembly']['battery_floor_raise_mm']
        result['battery_reserve']=cad.battery_shape(True)
        result['battery_loading']=cad.box(-11,11,-55,15,floor,floor+6)
        # The same 61 sampled gate poses, kept as poses rather than a 3D union.
        result['gate_removal_route']=Swept(cad.battery_gate(True),[(0,0,dz)for dz in np.linspace(0,15,61)])
        for sign in [-1,1]:
            x=sign*13.4;result[f'gate_slot_{sign}']=cad.box(x-.75,x+.75,-17.25,-15.35,floor+.45,floor+7.9)
    elif name=='XIAO_Rod_Holder':
        refs=cad.references();result.update(board=refs['pcb'],usb=refs['usb'],wire_route=cad.external_wire_route())
    return result
