"""Print the bought Micron cradle with its open tray face on the bed and a pull-out rail."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

from tower52 import add_tower_base
from plate52 import MODEL, SETTINGS, decode, tag, value, resource
import manifold3d as mf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'carbon-rod-holders-r48-edge-click'))
import battery48 as b


def oriented(body):
    # Rotate about assembly Y. Both open tray rims become first-layer rails.
    return body.rotate((0,180,0)).translate((90,90,12.8))


def build(out):
    with ZipFile(HERE/'exports/print-accessories/Clips-and-holders.3mf') as z:
        files={k:z.read(k) for k in z.namelist()}
    model=ET.fromstring(files[MODEL])
    cfg=ET.fromstring(files[SETTINGS])
    ET.register_namespace('',model.tag[1:].split('}')[0])
    res=model.find(tag('resources'))
    build=model.find(tag('build'))
    plate=cfg.find('plate')
    for node in list(res):res.remove(node)
    for node in list(build):build.remove(node)
    for node in cfg.findall('object'):cfg.remove(node)
    for node in plate.findall('model_instance'):plate.remove(node)
    source=HERE.parent/'carbon-rod-holders-r48-edge-click/exports/Battery_Holder-assembly.stl'
    solid=b.read(source)
    # A 0.20-mm air gap keeps the centre rail separate from the tray floor.
    # Its wide front tab stays clear of the cell sides and lid grooves.
    pieces=[b.box(-1,1,-18.8,13.82,6.55,12.8),b.box(-3,3,-22.5,-18,11.8,12.8)]
    # Three runners back transverse bridge lines across the cell floor. Each
    # auxiliary runner joins only the front pull handle, clear of the lid.
    for x in (-3.65,3.65):
        pieces.extend([b.box(x-.65,x+.65,-18.8,13.82,6.55,12.8),
                       b.box(min(0,x)-.65,max(0,x)+.65,-19.4,-18.4,12.2,12.8)])
    # Support the front of the ring keel where it extends beyond the tray floor.
    pieces.append(b.box(-1.60,1.60,-17.85,-15.30,5.99,12.8))
    # A pair of low shoulders backs the first extrusion above each lid groove.
    # The shoulders and centre runner slide out of the unobstructed front together.
    for sign in [-1,1]:
        stem=b.box(5.3,6.17,-18.8,13.82,10.86,12.8)
        shelf=mf.Manifold.batch_hull([
            b.box(5.3,6.16,-15.25,13.82,11.80,11.90),
            b.box(5.3,7.15,-15.25,13.82,10.68,10.82)])
        handle=b.box(-.5,6.17,-19.5,-18.4,12.20,12.8)
        pieces.extend(s if sign==1 else s.mirror((1,0,0)) for s in (stem,shelf,handle))
    # A separate wide base steadies the pull-out fork. It travels out with
    # the fork, entirely beyond the open end of the tray.
    pieces.append(b.box(-46,46,-56,-25,12.4,12.8))
    for x in (-1.75,1.75):
        pieces.append(b.box(x-.9,x+.9,-25.8,-21,12.4,12.8))
    rail=b.union(pieces)
    # Brim only on the outside of the two long rigid rails, with six short cut ties.
    pads=[]
    for sign in [-1,1]:
        wing=b.box(9.0,50.0,-18,18,12.4,12.8)
        ties=[b.box(8.25,10.0,y-1.1,y+1.1,12.4,12.8) for y in (-10,0,10)]
        side=b.union([wing,*ties])
        pads.append(side if sign==1 else side.mirror((1,0,0)))
    bodies=[('Battery_Holder',solid),('REMOVE - centre pull rail',rail),('REMOVE - outside feet',b.union(pads))]
    owner=ET.Element('object',id='4')
    cfg.insert(0,owner)
    for k,v in dict(name='Battery_Holder',extruder=1,enable_support=0,wall_loops=4,brim_type='no_brim',
                    wall_generator='arachne',bridge_angle=180,bridge_speed=16,outer_wall_speed=35,
                    inner_wall_speed=55,outer_wall_acceleration=500).items():value(owner,k,v)
    for i,(name,body) in enumerate(bodies,1):
        resource(res,tag,i,name,oriented(body).translate((-90,-90,0)))
        value(ET.SubElement(owner,'part',id=str(i),subtype='normal_part'),'name',name)
    obj=ET.SubElement(res,tag('object'),id='4',type='model')
    components=ET.SubElement(obj,tag('components'))
    for i in (1,2,3):ET.SubElement(components,tag('component'),objectid=str(i))
    ET.SubElement(build,tag('item'),objectid='4',transform='1 0 0 0 1 0 0 0 1 90 90 0',printable='1')
    instance=ET.SubElement(plate,'model_instance')
    for k,v in [('object_id',4),('instance_id',0),('identify_id',4)]:value(instance,k,v)
    value(plate,'plater_name','Battery cradle recovery')
    for key,el in [(MODEL,model),(SETTINGS,cfg),('Metadata/layer_config_ranges.xml',ET.Element('objects'))]:
        files[key]=ET.tostring(el,encoding='utf-8',xml_declaration=True)
    add_tower_base(files, (118, 140), brim_mm=27)
    out.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(out,'w',ZIP_DEFLATED) as z:
        for k,v in files.items():z.writestr(k,v)

    # The whole straight extraction is outside all permanent faces.
    # Nonconvex fork: sweep its cross-section exactly as each shelf is drawn out.
    sweep=b.union([mf.Manifold.batch_hull([s,s.translate((0,-40,0))]) for s in pieces])
    assert (sweep^solid).volume()<1e-6
    print('CAD height, permanent first-layer area, helper first-layer area, rail extraction overlap:',
          oriented(solid).bounding_box()[-1], oriented(solid).slice(.1).area(),
          sum(oriented(s).slice(.1).area() for _,s in bodies[1:]),(sweep^solid).volume())


if __name__=='__main__':build(Path(sys.argv[1]))
