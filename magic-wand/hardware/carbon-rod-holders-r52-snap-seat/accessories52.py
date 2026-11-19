"""Slice the two DFRobot clips and all other reusable printed parts as separate objects."""
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET
from zipfile import ZipFile,ZIP_DEFLATED
from plate52 import append_extras,OLD_PLATE,MODEL,SETTINGS,tag,value


def build(destination):
    with ZipFile(OLD_PLATE) as z:
        files={k:z.read(k) for k in z.namelist()}
    model=ET.fromstring(files[MODEL])
    cfg=ET.fromstring(files[SETTINGS])
    ET.register_namespace('',model.tag[1:].split('}')[0])
    resources=model.find(tag('resources'))
    build=model.find(tag('build'))
    lid=next(o for o in cfg.findall('object') if o.find("metadata[@key='name']").get('value')=='Battery_End_Door')
    ident=lid.get('id')
    retained={ident,*(p.get('id') for p in lid.findall('part'))}
    for obj in list(resources):
        if obj.get('id') not in retained:resources.remove(obj)
    for obj in list(build):
        if obj.get('objectid')!=ident:build.remove(obj)
    for obj in cfg.findall('object'):
        if obj is not lid:cfg.remove(obj)
    plate=cfg.find('plate')
    for instance in plate.findall('model_instance'):
        if instance.find("metadata[@key='object_id']").get('value')!=ident:plate.remove(instance)
    value(plate,'plater_name','R52 clips and holders')
    ranges=ET.fromstring(files['Metadata/layer_config_ranges.xml'])
    assert all(o.get('id')=='3' for o in ranges)
    for o in ranges:o.set('id','1')
    append_extras(resources,model,cfg,ranges)
    for n,v in [(MODEL,model),(SETTINGS,cfg),('Metadata/layer_config_ranges.xml',ranges)]:
        files[n]=ET.tostring(v,encoding='utf-8',xml_declaration=True)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(destination,'w',ZIP_DEFLATED) as output:
        for k,v in files.items():output.writestr(k,v)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('layout',type=Path)
    build(p.parse_args().layout)
