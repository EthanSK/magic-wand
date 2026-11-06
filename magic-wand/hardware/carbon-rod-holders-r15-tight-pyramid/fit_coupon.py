#!/usr/bin/env python3
"""One central key seat and both full clips, in the final carrier orientation."""
import json,math
import numpy as np,trimesh
import cad
import deliverables
OUT=cad.HERE/'exports/fit-coupon'

def clip_volume():
    return cad.box(-12,12,-20,15,-12,20)

def coupon_shape(diameter=7.9):
    # Compose one exact seat, its load rails, the rear rail/diagonals, both
    # full clip profiles and the same recessed front bumper, ties and spine
    # as the full carrier. Subtracting other coincident seats from the
    # five-key union left tiny disconnected chips. This test does not
    # represent the side keys or their loaded row joints.
    k=cad.P['keys'];z=k['pcb_z'];r=cad.P['structure']['rail_radius']
    rear=cad.carrier_clip_centres()[-1]
    pieces=[cad.key_seat().translate((0,0,z)),cad.rib((-8.2,10.5,z-4.5),(10.3,10.5,z-4.5),r)]
    for sign in [-1,1]:
        pieces.append(cad.rib((sign*3.8,rear,4.1),(sign*7.8,10.5,z+1.1),1.6))
    shape=cad.union(pieces)^cad.box(-30,30,-40,40,-40,z+2.25)
    shape-=cad.cyl(4.2,-40,40).rotate((-90,0,0))
    shape+=cad.ring(rear,diameter)
    shape-=cad.clip_gap(rear)
    shape=cad.recessed_front(shape,[(0,0)],clip_diameter=diameter,bumper_half=9.1)
    return shape.simplify(.0001)

def export(diameter=7.9):
    global OUT
    OUT=cad.HERE/'exports'/('fit-coupon'if diameter==7.9 else f'fit-coupon-{diameter:.1f}')
    OUT.mkdir(exist_ok=True)
    shape=coupon_shape(diameter)
    m=cad.mesh(shape)
    assert m.is_watertight and len(m.split())==1
    m.export(OUT/'Key_Carrier-assembly.stl')
    rot=trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]);normal=m.copy();normal.apply_transform(rot)
    shift=trimesh.transformations.translation_matrix(-normal.bounds[0]);normal.apply_transform(shift)
    # Normalize the exact float32 STL representation, as for the full parts.
    solid=cad.mf.Manifold(cad.mf.Mesh(np.round(normal.vertices,6).astype(np.float32),normal.faces.astype(np.uint32))).simplify(.000001)
    assert solid.status()==cad.mf.Error.NoError and abs(solid.volume()-normal.volume)<.01
    cad.mesh(solid).export(OUT/deliverables.normal_name('Key_Carrier'))
    record={'bounds_mm':m.bounds.tolist(),'volume_mm3':m.volume,'solid_PETG_g':m.volume/1000*cad.P['print']['density_g_cm3'],
            'stl_sha256':cad.sha(OUT/deliverables.normal_name('Key_Carrier')),'print_to_assembly':np.linalg.inv(shift@rot).tolist()}
    report={'revision':cad.P['revision']+'-key-clip-coupon','coupon':True,'clip_diameter_mm':diameter,'key_indices':[1],
            'parts':{'Key_Carrier':record},'source_manifest_sha256':cad.sha(cad.HERE/'exports/manifest.json'),
            'generator_sha256':cad.sha(cad.HERE/'fit_coupon.py'),'physical_fit_verified':False}
    report['construction']='One sourced seat, its load rails, the recessed front bumper/ties/spine and two full clips; no neighbouring seat crops. Upper joints and full-height stability require complete-part trials.'
    for label,part in cad.seated_hardware().items():
        assert (shape^part.translate((0,0,cad.P['keys']['pcb_z']))).volume()<.002,label
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print('One-piece full-orientation key/clip coupon exported.')
if __name__=='__main__':export()
