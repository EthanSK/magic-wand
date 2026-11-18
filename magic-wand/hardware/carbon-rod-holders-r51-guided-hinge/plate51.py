"""Compose two changed R51 parts for comparative native slicing with the verified A1 mini PETG recipe."""
import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from orient51 import digest, load_solid, oriented
from clearance51 import blockers

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "carbon-rod-holders-r50-targeted-feet/exports/R50-layout.3mf"
MODEL = "3D/3dmodel.model"
SETTINGS = "Metadata/model_settings.config"
PROJECT = "Metadata/project_settings.config"
NAMES = ("Key_Carrier", "DFRobot_Hole_Bracket")
CENTER = ((53., 89.), (133., 91.))


def value(node, key, val):
    meta = node.find(f"metadata[@key='{key}']")
    if meta is None:
        meta = ET.SubElement(node, "metadata", key=key)
    meta.set("value", str(val))


def resource(resources, tag, idx, name, body):
    obj = ET.SubElement(resources, tag("object"), id=str(idx), type="model", name=name)
    mesh = ET.SubElement(obj, tag("mesh"))
    raw = body.to_mesh()
    vertices = ET.SubElement(mesh, tag("vertices"))
    for pt in raw.vert_properties[:, :3]:
        ET.SubElement(vertices, tag("vertex"), {axis: format(float(v), ".9g") for axis,v in zip("xyz", pt)})
    triangles = ET.SubElement(mesh, tag("triangles"))
    for face in raw.tri_verts:
        ET.SubElement(triangles, tag("triangle"), {axis: str(v) for axis,v in zip(("v1","v2","v3"),face)})


def compose(sources, poses, mode, output, lid=None, negative=None, props=None):
    names = list(NAMES); centers = list(CENTER)
    if lid is not None:
        names.append("Battery_End_Door"); centers.append((64., 42.))
        sources=(*sources,lid); poses=(*poses,"bottom_down")
    with ZipFile(BASE) as z:
        original_ranges=ET.fromstring(z.read('Metadata/layer_config_ranges.xml'))
        files = {k: z.read(k) for k in z.namelist() if k != "Metadata/layer_config_ranges.xml"}
    model = ET.fromstring(files[MODEL])
    namespace = model.tag.split("}")[0][1:]
    ET.register_namespace("",namespace)
    def tag(name): return "{"+namespace+"}"+name
    resources = model.find(tag("resources"));resources.clear()
    build = model.find(tag("build"));original_order=[b.get("objectid") for b in build];build.clear()
    old = ET.fromstring(files[SETTINGS])
    settings = ET.Element("config")
    plate = ET.Element("plate")
    value(plate, "plater_id", 1); value(plate, "plater_name", "R51 changed key carrier and guided hinge")
    metrics = {}
    for i,(name,source,pose,center) in enumerate(zip(names,sources,poses,centers)):
        body, frame = oriented(load_solid(source), pose)
        (x,y,_,x2,y2,h) = body.bounding_box()
        off = (center[0]-(x+x2)/2, center[1]-(y+y2)/2)
        baseline = next(o for o in old.findall("object") if o.find("metadata[@key='name']").get("value")==name)
        part_id, owner = 2*i+1, 2*i+2
        node = ET.SubElement(settings,"object",id=str(owner))
        for meta in baseline.findall("metadata"):node.append(meta)
        # A single process across each part keeps perimeter strands continuous through narrow frame members.
        fields = dict(wall_loops=5,wall_generator="arachne",inner_wall_line_width=.34,outer_wall_line_width=.34,
                      internal_solid_infill_line_width=.34,inner_wall_speed=55,outer_wall_speed=35,
                      is_infill_first=0, enable_support=int(mode!="none"),support_type="tree(auto)",
                      support_style="tree_slim",support_threshold_angle=28, support_critical_regions_only=1,
                      support_on_build_plate_only=1,support_top_z_distance=.24,support_bottom_z_distance=.24,
                      support_object_xy_distance=.45,support_interface_top_layers=1,support_interface_spacing=.6,
                      tree_support_wall_count=1,brim_type="outer_only",brim_width=5 if i==0 else 10,
                      brim_object_gap=.05,bridge_no_support=1,max_bridge_length=10)
        if mode in ('spots','clear','routed') and name in NAMES:
            fields.update(support_type="normal(manual)",support_style="snug",
                          support_base_pattern_spacing=3.0,support_interface_spacing=.38,
                          support_interface_top_layers=2,support_critical_regions_only=0)
        if name=='Battery_End_Door':
            fields={m.get('key'):m.get('value') for m in baseline.findall('metadata')}
            selected=ET.Element(original_ranges.tag)
            lid_index=original_order.index(baseline.get('id'))+1
            for entry in original_ranges:
                if int(entry.get('id'))==lid_index:
                    entry.set('id',str(i+1));selected.append(entry)
            if len(selected):
                files['Metadata/layer_config_ranges.xml']=ET.tostring(selected,encoding='utf-8',xml_declaration=True)
        else:
            for k,v in fields.items(): value(node,k,v)
        res_title = name
        resource(resources,tag,part_id,res_title,body)
        compound = ET.SubElement(resources,tag("object"),id=str(owner),type="model",name=name)
        components = ET.SubElement(compound,tag("components"))
        ET.SubElement(components,tag("component"),objectid=str(part_id))
        value(ET.SubElement(node,"part",id=str(part_id),subtype="normal_part"),"name",name)
        if mode in ('spots','clear','routed') and name in NAMES:
            from spots51 import enforcers
            for index,(label,solid) in enumerate(enforcers(negative,name,digest(source),off).items()):
                if mode in ('clear','routed') and name=='Key_Carrier':
                    # Snug/manual Bambu supports grow downward through voids. Remove
                    # the whole XY projection of each sensitive route from the paint
                    # so no higher roof can seed a column through it.
                    from manifold3d import CrossSection, OpType
                    keepouts=[]
                    for label,v in blockers(name,contact_only=mode=='routed').items():
                        margin=.20 if mode=='routed' and label.startswith('finger') else .9
                        keepouts.append(v.transform(frame[:3]).project().offset(margin))
                    shadow=CrossSection.batch_boolean(keepouts,OpType.Add)
                    solid-=shadow.extrude(h+2).translate((0,0,-1))
                ident=66+i*8+index
                resource(resources,tag,ident,label,solid)
                ET.SubElement(components,tag("component"),objectid=str(ident))
                value(ET.SubElement(node,"part",id=str(ident),subtype="support_enforcer"),"name",label)
        if mode in ('protected','spots','clear','routed') and name in NAMES:
            for index,(label,solid) in enumerate(blockers(name,contact_only=mode=='routed').items()):
                ident=101+i*32+index
                resource(resources,tag,ident,label,solid.transform(frame[:3]))
                ET.SubElement(components,tag("component"),objectid=str(ident))
                value(ET.SubElement(node,"part",id=str(ident),subtype="support_blocker"),"name",label)
        ET.SubElement(build,tag("item"),objectid=str(owner),printable="1",transform=f"1 0 0 0 1 0 0 0 1 {off[0]:.9g} {off[1]:.9g} 0")
        instance = ET.SubElement(plate,"model_instance")
        for key,val in (("object_id",owner),("instance_id",0),("identify_id",owner)):value(instance,key,val)
        frame[:2,3] += off
        metrics[name] = dict(assembly_stl=source.name,source_sha256=digest(source),orientation=pose,
                             assembly_to_machine=frame.tolist(),height_mm=round(h,4),
                             model_volume_mm3=round(body.volume(),3),owner=owner,settings=fields)
    if props:
        import manifold3d as mf
        import numpy as np
        members=[load_solid(p) for p in sorted(props.glob("prop-*.stl"))]
        if not members:raise ValueError("Empty removable prop group")
        prop=mf.Manifold.batch_boolean(members,mf.OpType.Add)
        ident,owner=97,98
        title="External_peel_support"
        resource(resources,tag,ident,title,prop)
        key_id=metrics['Key_Carrier']['owner']
        key_object=resources.find(tag("object")+f"[@id='{key_id}']")
        ET.SubElement(key_object.find(tag('components')),tag("component"),objectid=str(ident))
        key_node=settings.find(f"object[@id='{key_id}']")
        part=ET.SubElement(key_node,"part",id=str(ident),subtype="normal_part")
        value(part,"name",title)
        for k,v in dict(wall_loops=3,outer_wall_speed=28,inner_wall_speed=35).items():value(part,k,v)
        metrics['Key_Carrier']['peel_support']=dict(part_id=ident,name=title,pieces=len(members),source_sha256=digest(props/'props.json'),
            parts_sha256={p.name:digest(p) for p in sorted(props.glob("prop-*.stl"))})
    settings.append(plate);ET.SubElement(settings,"assemble")
    files[MODEL]=ET.tostring(model,encoding="utf-8",xml_declaration=True)
    files[SETTINGS]=ET.tostring(settings,encoding="utf-8",xml_declaration=True)
    with ZipFile(output,"w",ZIP_DEFLATED) as z:
        for key,data in files.items():z.writestr(key,data)
    output.with_suffix(".frame.json").write_text(json.dumps(dict(parts=metrics,mode=mode,layout_sha256=digest(output)),indent=2)+"\n")
    print(output.name,mode,[m["height_mm"] for m in metrics.values()],flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("key",type=Path);p.add_argument("bracket",type=Path);p.add_argument("output",type=Path)
    p.add_argument("--key-face",default="rear_down");p.add_argument("--bracket-face",default="front_down")
    p.add_argument("--mode",choices=("none","selective","protected","spots","clear","routed"),required=True)
    p.add_argument("--lid",type=Path,help="Preoriented revised lid for a three-part plate")
    p.add_argument("--negative",type=Path,help="Frozen no-support deposition report for local enforcers")
    p.add_argument("--props",type=Path,help="Measured external prop STLs and extraction directions")
    a=p.parse_args();compose((a.key,a.bracket),(a.key_face,a.bracket_face),a.mode,a.output,a.lid,a.negative,a.props)
