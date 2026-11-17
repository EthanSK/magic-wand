"""Back the short return on the right finger-rest roof using its existing bed prop."""
from pathlib import Path
from shelf45 import band, box
from native48 import write, digest
import manifold3d as mf
import numpy as np
import trimesh
from io import BytesIO

def shape(cradle,carrier):
    # Relative to the standing print frame; the bend on the following carrier
    # layer is at X42.05–43.25, Y5.74–6.61. Its centre had ~0.7 mm of open
    # air even after widening the side-withdrawing shelf. The adjacent
    # exterior rib is rooted below and withdraws in -Z after cooling.
    window=box(41.45,5.08,2.68,2.14)
    sections=[]
    prev=cradle.slice(20.1)
    for k in range(102,109):
        top=round(k*.2,3)
        under=carrier.trim_by_plane((0,0,-1),-top-.011).project()
        # Exact full-height shadow for the downward peel. At the lip, keep
        # the next native slicing plane (top +0.10) clear. The prospective
        # carrier roof first prints at 22.0, leaving the 21.8 layer empty.
        # The independent complete-bead audit checks the true layer envelopes.
        allowed=window-under.offset(.49)-band(carrier,top-.21,top+.105)
        stock=cradle.slice(top-.1)
        part=allowed ^ prev.offset(.22) ^ stock.offset(1.3)
        # Anything grown away from the original stock must remain rooted in
        # deposited prior layers. Each layer projects no more than .22 mm.
        section=part.extrude(.201).translate((0,0,top-.201))
        sections.append(section)
        prev=stock + part
    extra=mf.Manifold.batch_boolean(sections,mf.OpType.Add)
    result=cradle + extra
    def exported_pieces(shape):
        # Compare topology at the actual STL vertex precision. In the CAD
        # generator adjacent 0.2-mm layer faces can differ by machine epsilon.
        # This is the same binary export and reader used for the delivered part.
        raw=shape.to_mesh()
        packed=trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts,process=False).export(file_type='stl')
        mesh=trimesh.load_mesh(BytesIO(packed),file_type='stl')
        physical=mf.Manifold(mf.Mesh64(mesh.vertices,np.asarray(mesh.faces,np.uint64)))
        assert physical.status()==mf.Error.NoError
        return [p for p in physical.decompose() if p.volume()>.001]
    old=exported_pieces(cradle)
    new=exported_pieces(result)
    def grounded(parts):return [piece for piece in parts if piece.bounding_box()[2]<.01]
    touched=[part for part in old if (part^extra).volume()>.0001]
    # The little 0.52-mm³ cap already sat on this same strip. Fuse it to the
    # underlying 395-mm³ strip; keep every independently held bed foot separate.
    assert result.status()==mf.Error.NoError and len(grounded(new))==len(grounded(old))
    assert len(grounded(touched))==1 and all(p.volume()<1. for p in touched if p.bounding_box()[2]>=.01)
    add=(result-cradle).volume()
    assert .6<add<6.,add
    target=box(41.94,5.6,1.4,1.1)
    evidence={'volume_added_mm3':add,
              'covered_target_before_mm2':(cradle.slice(21.5)^target).area(),
              'covered_target_after_mm2':(result.slice(21.5)^target).area(),
              'old_cradle_parts':len(old),'new_cradle_parts':len(new),
              'grounded_strips_before_and_after':[len(grounded(old)),len(grounded(new))],
              'existing_merged_cap_volumes_mm3':[p.volume() for p in touched if p.bounding_box()[2]>=.01],
              'highest_sacrificial_layer_mm':21.6,'permanent_roof_first_top_mm':22.,'sha256':digest(Path(__file__))}
    stations=[(42.05,6.6),(42.05,6.22),(42.05,5.84),(42.4,6.33),(42.85,5.735)]
    for key,part in [('before',cradle),('after',result)]:
        evidence[key+'_path_stations']=[]
        for xy in stations:
            spot=mf.CrossSection.circle(.18,24).translate(xy)
            evidence[key+'_path_stations'].append((spot^part.slice(21.5)).area()/spot.area())
    assert min(evidence['after_path_stations'])>=.95 and evidence['covered_target_after_mm2']>1.25,evidence
    return result,evidence
