"""Compose checked native subprojects into the complete Wand plate; never print.

Keep each key/helper group rigid. Preserve each subproject's per-object recipe
and map height ranges by build identity. The caller must supply a freshly
checked bracket project; this utility does not certify its supports or fit.
"""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree as E
from zipfile import ZipFile, ZIP_DEFLATED

MODEL = '3D/3dmodel.model'
SETTINGS = 'Metadata/model_settings.config'
PROJECT = 'Metadata/project_settings.config'
RANGES = 'Metadata/layer_config_ranges.xml'
NAMESPACE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
E.register_namespace('', NAMESPACE)
FUNCTIONAL = {'Key_Carrier','DFRobot_Hole_Bracket','DFR0030_Post_Clip','DFR0030_Post_Clip_2',
              'XIAO_Rod_Holder','XIAO_Near_Keeper','Battery_Holder','Battery_End_Door','Cable_Clip_12_Wire'}
LOCAL_CONFIG = {'bridge_angle','is_infill_first','min_bead_width','wall_distribution_count','wall_generator'}

def fields(element):
    return {m.get('key'):m.get('value') for m in element.findall('metadata')}

def set_fields(element, values):
    for key,value in values.items():
        entry=element.find(f"metadata[@key='{key}']")
        if entry is None: entry=E.SubElement(element,'metadata',key=key)
        entry.set('value',str(value))

def read(path):
    with ZipFile(path) as z: files={name:z.read(name) for name in z.namelist()}
    model=E.fromstring(files[MODEL]); settings=E.fromstring(files[SETTINGS])
    resources={obj.get('id'):obj for obj in model.find('./{*}resources')}
    objects={obj.get('id'):obj for obj in settings.findall('object')}
    build=list(model.find('./{*}build'))
    names={identifier:fields(obj)['name'] for identifier,obj in objects.items()}
    return dict(files=files,model=model,settings=settings,resources=resources,objects=objects,
                build=build,names=names,config=json.loads(files[PROJECT]),
                ranges=E.fromstring(files.get(RANGES,b'<objects/>')))

def reachable(resources, roots):
    ids=set(roots); pending=list(ids)
    while pending:
        obj=resources[pending.pop()]
        for ref in obj.findall('./{*}components/{*}component'):
            identifier=ref.get('objectid')
            if identifier not in ids: ids.add(identifier); pending.append(identifier)
    return ids

def build_ranges(project, selected):
    order=[project['names'][b.get('objectid')] for b in project['build']]
    rows=[]
    for row in project['ranges']:
        name=order[int(row.get('id'))-1]
        if name in selected: rows.append((name,deepcopy(row)))
    return rows

def compose(base_path, key_path, bracket_path, output, battery_path=None):
    base,key,bracket=map(read,(base_path,key_path,bracket_path))
    assert {base['names'][b.get('objectid')] for b in base['build']}==FUNCTIONAL
    assert 'Key_Carrier' in key['names'].values()
    bracket_names={'DFRobot_Hole_Bracket','DFR0030_Post_Clip','DFR0030_Post_Clip_2'}
    assert bracket_names <= set(bracket['names'].values()), 'Bracket project must include both matching post clips'
    battery_names={'Battery_Holder','Battery_End_Door'} if battery_path else set()
    replace={'Key_Carrier'} | bracket_names | battery_names
    model=base['model']; settings=base['settings']
    resource_root=model.find('./{*}resources'); build_root=model.find('./{*}build')
    plate=settings.find('plate'); assemble=settings.find('assemble')
    keep=[b.get('objectid') for b in base['build'] if base['names'][b.get('objectid')] not in replace]
    kept_resources=reachable(base['resources'],keep)
    for obj in list(resource_root):
        if obj.get('id') not in kept_resources:resource_root.remove(obj)
    for obj in list(settings.findall('object')):
        if obj.get('id') not in keep:settings.remove(obj)
    for obj in list(plate.findall('model_instance')):
        if fields(obj)['object_id'] not in keep:plate.remove(obj)
    if assemble is not None:
        for obj in list(assemble):
            if obj.get('object_id') not in keep:assemble.remove(obj)
    old_positions={base['names'][b.get('objectid')]:deepcopy(b) for b in base['build']}
    groups={}; next_id=max(map(int,base['resources']))+1
    ranges=build_ranges(base,FUNCTIONAL-replace)
    config_differences={}
    sources=[('key',key,set(key['names'].values()),'Key_Carrier'),
             ('bracket',bracket,bracket_names,'DFRobot_Hole_Bracket')]
    if battery_path:
        battery=read(battery_path)
        assert set(battery['names'].values())==battery_names
        sources.append(('battery',battery,battery_names,'Battery_Holder'))
    for label,source,selected,anchor in sources:
        root_ids=[b.get('objectid') for b in source['build'] if source['names'][b.get('objectid')] in selected]
        assert root_ids and len(root_ids)==len(selected)
        chosen=reachable(source['resources'],root_ids)
        mapping={old:str(next_id+i) for i,old in enumerate(sorted(chosen,key=int))};next_id+=len(chosen)
        for identifier in sorted(chosen,key=int):
            obj=deepcopy(source['resources'][identifier]);obj.set('id',mapping[identifier])
            for ref in obj.findall('./{*}components/{*}component'):ref.set('objectid',mapping[ref.get('objectid')])
            resource_root.append(obj)
        differences={k:v for k,v in source['config'].items() if base['config'].get(k)!=v}
        assert set(differences)<=LOCAL_CONFIG, ('Review unhandled global setting changes',label,sorted(differences))
        config_differences[label]=differences
        anchor_item=next(b for b in source['build'] if source['names'][b.get('objectid')]==anchor)
        old_transform=list(map(float,old_positions[anchor].get('transform').split()))
        anchor_transform=list(map(float,anchor_item.get('transform').split()))
        assert old_transform[:9]==anchor_transform[:9], 'Rotation belongs in the checked project, not this compositor'
        if label=='battery':
            # R42's later battery repair widened its anchors and moved the
            # body right. Keep that checked placement rather than reverting
            # to the older complete-plate footprint.
            old_transform[9:12]=[30.,63.,0.]
        delta=[old_transform[i]-anchor_transform[i] for i in (9,10,11)]
        group=[]
        for b in source['build']:
            identifier=b.get('objectid')
            if identifier not in root_ids:continue
            new=deepcopy(b);new.set('objectid',mapping[identifier]);values=list(map(float,b.get('transform').split()))
            for i,d in zip((9,10,11),delta):values[i]+=d
            new.set('transform',' '.join(f'{v:.12g}' for v in values));group.append(new)
            obj=deepcopy(source['objects'][identifier]);obj.set('id',mapping[identifier])
            for part in obj.findall('part'):part.set('id',mapping[part.get('id')])
            set_fields(obj,differences);settings.insert(0,obj)
            instance=E.SubElement(plate,'model_instance')
            set_fields(instance,{'object_id':mapping[identifier],'instance_id':'0','identify_id':mapping[identifier]})
        ranges.extend(build_ranges(source,selected));groups[label]=group
    for b in list(build_root):build_root.remove(b)
    for b in base['build']:
        name=base['names'][b.get('objectid')]
        if name=='Key_Carrier':build_root.extend(groups['key'])
        elif name=='DFRobot_Hole_Bracket':build_root.extend(groups['bracket'])
        elif name=='Battery_Holder' and battery_path:build_root.extend(groups['battery'])
        elif name not in replace:build_root.append(b)
    if battery_path:
        # The same widened-anchor recipe stages this cable at X=90 to leave
        # the battery pads clear. The final slice must recheck every bead.
        cable=next(b for b in build_root if base['names'].get(b.get('objectid'))=='Cable_Clip_12_Wire')
        values=list(map(float,cable.get('transform').split()));values[9:12]=[90.,56.,0.]
        cable.set('transform',' '.join(f'{v:.12g}' for v in values))
    names={o.get('id'):fields(o)['name'] for o in settings.findall('object')}
    order=[names[b.get('objectid')] for b in build_root]
    assert len(order)==len(set(order)) and FUNCTIONAL <= set(order), order
    ranges_root=E.Element('objects')
    for name,row in ranges:row.set('id',str(order.index(name)+1));ranges_root.append(row)
    set_fields(plate,{'plater_name':'Magic Wand R47 complete assembly - A1 mini PETG'})
    files=base['files'];files[MODEL]=E.tostring(model,encoding='utf-8',xml_declaration=True)
    files[SETTINGS]=E.tostring(settings,encoding='utf-8',xml_declaration=True)
    files[RANGES]=E.tostring(ranges_root,encoding='utf-8',xml_declaration=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)
    source_paths=[('complete_template',base_path),('key',key_path),('bracket',bracket_path)]
    if battery_path:source_paths.append(('battery',battery_path))
    receipt={'schema':1,'state':'composed_not_slice_checked','functional_parts':sorted(FUNCTIONAL),'build_order':order,
             'local_config_differences':config_differences,
             'source_sha256':{k:sha256(v.read_bytes()).hexdigest() for k,v in source_paths},
             'layout_sha256':sha256(output.read_bytes()).hexdigest(),'physical_ready_for_send':False}
    output.with_suffix('.composition.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base',type=Path);p.add_argument('key',type=Path);p.add_argument('bracket',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--battery-layout',type=Path)
    a=p.parse_args();compose(a.base,a.key,a.bracket,a.output,a.battery_layout)
