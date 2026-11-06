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
        k=cad.P['keys'];z=k['pcb_z'];hw=cad.seated_hardware()
        route=[(-2.5,-4.824,dz)for dz in np.linspace(12,.6,115)]
        route += [(-2.5*(1-t),-4.824*(1-t),.6)for t in np.linspace(0,1,61)]
        route += [(0,0,dz)for dz in np.linspace(.6,0,13)]
        for i,(x,y)in enumerate(cad.key_positions()):
            if key_indices is not None and i not in key_indices:continue
            for label,shape in {**hw,'maximum_socket':maximum_socket()}.items():result[f'key_{i}_{label}']=shape.translate((x,y,z))
            for label,socket in [('socket_loading',hw['socket']),('maximum_socket_loading',maximum_socket())]:
                result[f'key_{i}_{label}']=cad.union([socket.translate((x+px,y+py,z+pz))for px,py,pz in route])
            result[f'key_{i}_mount_opening']=cad.rr(14.1,14.1,.2,z+k['plate_bottom'],z+k['plate_bottom']+1.2).translate((x,y,0))
    elif name=='Battery_Holder':
        floor=cad.P['battery']['floor_z']+cad.P['assembly']['battery_floor_raise_mm']
        result['battery_reserve']=cad.battery_shape(True)
        result['battery_loading']=cad.box(-11,11,-55,15,floor,floor+6)
        result['gate_removal_route']=cad.union([cad.battery_gate(True).translate((0,0,dz))for dz in np.linspace(0,15,61)])
        for sign in [-1,1]:
            x=sign*13.4;result[f'gate_slot_{sign}']=cad.box(x-.75,x+.75,-17.25,-15.35,floor+.45,floor+7.9)
    elif name=='XIAO_Rod_Holder':
        refs=cad.references();result.update(board=refs['pcb'],usb=refs['usb'],wire_route=cad.external_wire_route())
    return result
