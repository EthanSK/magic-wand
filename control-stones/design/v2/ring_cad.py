#!/usr/bin/env python3
"""Editable Control Stones V2 concept CAD; run `python ring_cad.py` after requirements.txt.
Component envelopes and finger dimensions come from dimensions.json; shell details
are editable below. All source dimensions are in millimetres. Exports are generated, not
editable sources. This is a mechanical layout study, not a working switch mechanism,
a battery-approved enclosure or a print-ready release. Never contacts hardware.
"""
from __future__ import annotations
import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
import numpy as np
import manifold3d as mf
import trimesh

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / 'dimensions.json').read_text())
OUT = HERE / 'exports'
N = 96

@dataclass
class Part:
    name: str
    solid: mf.Manifold
    color: str
    role: str = 'concept shell'


def box(size: list[float] | tuple[float, ...], center: list[float] | tuple[float, ...]) -> mf.Manifold:
    return mf.Manifold.cube(size, center=True).translate(center)


def rounded_box(w: float, length: float, height: float, radius: float, center: tuple[float, float, float]) -> mf.Manifold:
    section = mf.CrossSection.square((w-2*radius, length-2*radius), center=True).offset(radius, mf.JoinType.Round, circular_segments=32)
    return mf.Manifold.extrude(section, height).translate((center[0], center[1], center[2]-height/2))


def finger_bore(extra: float = 0, length: float = 80) -> mf.Manifold:
    f = CONFIG['finger']
    return mf.Manifold.cylinder(length, 1, circular_segments=N, center=True).scale((f['bore_width']/2+extra, f['bore_height']/2+extra, 1)).rotate((90, 0, 0))


def mesh(solid: mf.Manifold) -> trimesh.Trimesh:
    data = solid.to_mesh()
    return trimesh.Trimesh(np.asarray(data.vert_properties)[:, :3], np.asarray(data.tri_verts), process=False)


def build(hand: str, count: int, family: str = 'Ring') -> list[Part]:
    if family == 'Handheld':
        return build_handheld(hand,count)
    assert family == 'Ring'
    assert hand in ('Left', 'Right') and count in (3, 4)
    f, p, c = CONFIG['finger'], CONFIG['pod'], CONFIG['controls']
    switch_w, switch_l, switch_t = CONFIG['switch']['size']
    w, length, height = p['size']; base = p['bottom']; top = base+height
    # Ethan's OUTER/THUMB-FACING side is normal mouse click. +X denotes that
    # anatomical side on the left-hand model viewed palm-down, fingertips +Y.
    # Mirroring X makes the right-hand model; firmware axes are not changed.
    body = finger_bore(f['wall'], f['band_width']) - finger_bore()
    pod = rounded_box(w, length, height, p['corner_radius'], (0, 0, base+height/2))
    cavity = rounded_box(w-2*p['wall'], length-2*p['wall'], height+2, 2, (0, 0, base+p['wall']+(height+2)/2))
    body = body + (pod-cavity)
    # A separate lower boss keeps the provisional switches outside the skin
    # opening. Its bulk is deliberate and must be tested for palm clearance.
    body += rounded_box(10, 14, 4.8, 2, (0, 0, -13.0))
    caps: list[Part] = []
    switches: list[Part] = []
    for side, y, label, color in [(1, c['thumb_side_y'], 'Thumb_Click', '#f1b84b'), (-1, c['far_side_y'], 'Far_Side', '#a18be3')]:
        z = c['side_z']
        # Guard rims are proud of the caps; these are shape studies, not
        # validated accidental-press protection or switch retention features.
        body += rounded_box(3.0, 9.0, 7.0, 1.1, (side*11.6, y, z))
        body -= box((6, 7.0, 5.0), (side*11.5, y, z))
        cap = rounded_box(1.1, 6.2, 4.2, .35, (side*12.35, y, z))
        # Rounded boxes extrude in Z; the thin side dimension is X.
        caps.append(Part(label+'_Cap', cap, color, 'button position mock-up'))
        switches.append(Part(label+'_Switch_Assumed', box((switch_t, switch_l, switch_w), (side*10.2, y, z)), '#48515c', 'unverified component envelope'))
    under_positions = [0] if count == 3 else c['under_y_four']
    for i, y in enumerate(under_positions):
        cap_length = 8.5 if count == 3 else 4.5
        body -= box((6.6, cap_length+.6, 5.5), (0, y, -14.1))
        cap = rounded_box(5.8, cap_length, 1.0, 1.0, (0, y, -15.5))
        # The second optional underside cap has a transverse ridge, to compare
        # touch identification. No independent ring-finger motion is assumed.
        if i == 1:
            cap += rounded_box(4.0, .9, .6, .3, (0, y, -16.2))
        label = 'Under' if count == 3 else f'Under_{i+1}'
        caps.append(Part(label+'_Cap', cap, '#68c4b5' if i == 0 else '#db8aa3', 'button position mock-up'))
        switches.append(Part(label+'_Switch_Assumed', box((switch_w, switch_l, switch_t), (0, y, -13.2)), '#48515c', 'unverified component envelope'))
    # USB access is an allowance, not a verified plug fit. The antenna end is
    # opposite USB; no metal fastener is added beside the antenna in this study.
    body -= box((11, 5, 5), (0, -length/2, 20.4))
    # Remove any material from the placeholder finger opening after all unions.
    body -= finger_bore()
    lid = rounded_box(w, length, p['lid_thickness'], p['corner_radius'], (0, 0, top+p['lid_gap']+p['lid_thickness']/2))
    parts = [Part('Band_Pod', body, '#237889'), Part('Lift_Off_Lid', lid, '#529dab')] + caps
    for name, color in [('board', '#3e9b58'), ('battery', '#b8c2cc')]:
        spec = CONFIG[name]
        parts.append(Part(name.capitalize()+'_Envelope', box(spec['size'], spec['center']), color, 'unverified component envelope' if name == 'battery' else 'verified XY only; provisional height'))
    parts += switches
    if hand == 'Right':
        parts = [Part(a.name, a.solid.mirror((1, 0, 0)), a.color, a.role) for a in parts]
    return parts


def build_handheld(hand: str, count: int) -> list[Part]:
    """Ethan's leading V2: very short and light, picked up and put down.
    No extra shaft: the actual electronics envelope sets the starting size.
    The same gyro rotation does not establish the same comfort or control feel.
    """
    assert hand in ('Left','Right') and count in (3,4)
    p,c=CONFIG['handheld'],CONFIG['controls']
    sw,sl,st=CONFIG['switch']['size']
    w,length,height=p['size'];wall=p['wall']
    # A hollow rounded capsule removes the ring and unused rod length. A
    # modest end taper softens its silhouette without reducing board clearance.
    bottom=rounded_box(w-2,length-2,.02,p['corner_radius']-1,(0,0,.01))
    middle=rounded_box(w,length,height-2, p['corner_radius'],(0,0,height/2))
    outer=mf.Manifold.batch_hull([bottom,middle])
    cavity=rounded_box(w-2*wall,length-2*wall,height+2,p['corner_radius']-wall,(0,0,wall+(height+2)/2))
    body=outer-cavity
    caps=[];references=[]
    for side,y,label,color in [(1,c['thumb_side_y'],'Thumb_Click','#f1b84b'),(-1,c['far_side_y'],'Far_Side','#a18be3')]:
        z=p['side_z']
        body+=rounded_box(2.5,9,7,1,(side*11.95,y,z))
        body-=box((6,7,5),(side*12,y,z))
        caps.append(Part(label+'_Cap',rounded_box(1,6.2,4.2,.35,(side*12.5,y,z)),color,'button position mock-up'))
        references.append(Part(label+'_Switch_Assumed',box((st,sl,sw),(side*10.5,y,z)),'#48515c','unverified component envelope'))
    body+=rounded_box(10,14,3.4,2,(0,0,-.5))
    for i,y in enumerate([0] if count==3 else c['under_y_four']):
        cap_length=8.5 if count==3 else 4.5
        body-=box((6.6,cap_length+.6,5),(0,y,-.5))
        cap=rounded_box(5.8,cap_length,.8,1,(0,y,-2.3))
        if i==1:cap+=rounded_box(4,.9,.5,.3,(0,y,-2.85))
        label='Under' if count==3 else f'Under_{i+1}'
        caps.append(Part(label+'_Cap',cap,'#68c4b5' if i==0 else '#db8aa3','button position mock-up'))
        references.append(Part(label+'_Switch_Assumed',box((sw,sl,st),(0,y,p['under_switch_z'])),'#48515c','unverified component envelope'))
    # Provisional soft-tie bridge in the gutter beyond the board: one place
    # to capture leads without pulling on solder pads. Real wire/tie sizing,
    # strain tests and cell retention remain unverified.
    anchor=box((6,1.6,3),(0,12.2,2.4))-box((3,4,1),(0,12.2,2.2))
    body+=anchor
    body-=box((11,5,5),(0,-length/2,10))
    lid=rounded_box(w,length,p['lid_thickness'],p['corner_radius'],(0,0,height-1+p['lid_gap']+p['lid_thickness']/2))
    parts=[Part('Handheld_Shell',body,'#237889'),Part('Lift_Off_Lid',lid,'#529dab')]+caps
    for component,color in [('board','#3e9b58'),('battery','#b8c2cc')]:
        parts.append(Part(component.capitalize()+'_Envelope',box(CONFIG[component]['size'],p[component+'_center']),color,'unverified component envelope' if component=='battery' else 'verified XY only; provisional height'))
    parts+=references
    if hand=='Right':parts=[Part(a.name,a.solid.mirror((1,0,0)),a.color,a.role) for a in parts]
    return parts


def export_3mf(parts: list[Part], path: Path) -> None:
    """Standard millimetre 3MF assembly for inspection, with named objects.
    No printer profile, filament, supports, slicing or print instructions implied.
    """
    ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
    root=Element('model', {'unit':'millimeter','xml:lang':'en-US','xmlns':ns})
    SubElement(root,'metadata',{'name':'Title'}).text='Control Stones V2 — concept only'
    resources=SubElement(root,'resources'); build_node=SubElement(root,'build')
    materials=SubElement(resources,'basematerials',{'id':'1'})
    for part in parts:
        SubElement(materials,'base',{'name':part.name,'displaycolor':part.color.upper()+'FF'})
    for index, part in enumerate(parts):
        obj=SubElement(resources,'object',{'id':str(index+2),'type':'model','name':part.name,'pid':'1','pindex':str(index)})
        m=mesh(part.solid); node=SubElement(obj,'mesh'); vertices=SubElement(node,'vertices'); triangles=SubElement(node,'triangles')
        for v in m.vertices: SubElement(vertices,'vertex',dict(zip(('x','y','z'),(f'{a:.6f}' for a in v))))
        for face in m.faces: SubElement(triangles,'triangle',dict(zip(('v1','v2','v3'),map(str,face))))
    assembly_id=str(len(parts)+2)
    assembly=SubElement(resources,'object',{'id':assembly_id,'type':'model','name':'Control Stones V2 CONCEPT'})
    components=SubElement(assembly,'components')
    for index in range(len(parts)):
        SubElement(components,'component',{'objectid':str(index+2)})
    SubElement(build_node,'item',{'objectid':assembly_id})
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',tostring(root,encoding='utf-8',xml_declaration=True))


def main() -> None:
    OUT.mkdir(exist_ok=True)
    manifest: dict = {'units':'mm','status':CONFIG['status'],'source_sha256':hashlib.sha256((HERE/'dimensions.json').read_bytes()+(HERE/'ring_cad.py').read_bytes()).hexdigest(),'assumptions':CONFIG,'variants':[]}
    from itertools import product
    for family,hand,count in product(('Ring','Handheld'),('Left','Right'),(3,4)):
            parts=build(hand,count,family); name=('Handheld_' if family=='Handheld' else '')+f'{hand}_{count}Button'; folder=OUT/name; folder.mkdir(exist_ok=True)
            scene=trimesh.Scene(); entries=[]
            for part in parts:
                m=mesh(part.solid); m.visual.vertex_colors=np.tile(trimesh.visual.color.hex_to_rgba(part.color), (len(m.vertices), 1))
                assert part.solid.status()==mf.Error.NoError and m.is_watertight and m.volume>0, part.name
                m.export(folder/(part.name+'.stl'))
                gltf_mesh=m.copy()
                gltf_mesh.apply_scale(.001)  # glTF uses metres; STL and 3MF remain millimetres.
                gltf_mesh.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2, (1, 0, 0)))
                scene.add_geometry(gltf_mesh,geom_name=part.name,node_name=part.name)
                entries.append({'name':part.name,'role':part.role,'color':part.color,'bounds_mm':m.bounds.tolist(),'volume_mm3':float(m.volume),'watertight':bool(m.is_watertight),'vertices':m.vertices.tolist(),'faces':m.faces.tolist()})
            scene.export(OUT/(name+'.glb'))
            export_3mf(parts,OUT/(name+'_CONCEPT.3mf'))
            manifest['variants'].append({'name':name,'family':family,'hand':hand,'buttons':count,'parts':entries})
    (OUT/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    print('Generated eight ring/handheld concept assemblies; no physical fit or printability claim.')

if __name__=='__main__': main()
