"""Prepare the revised battery lid on its flat face using the R50 PETG settings."""
import argparse
from pathlib import Path
import sys

from lid51 import HERE, old
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r47-bottom-click'))
import compose47 as c
from battery_print48 import install_mesh, write_project

BASE = HERE.parent / 'carbon-rod-holders-r50-targeted-feet/exports/R50-layout.3mf'


def make(output):
    project = c.read(BASE)
    [item] = [node for node in project['build'] if project['names'][node.get('objectid')] == old.PANEL]
    ident = item.get('objectid')
    keep = c.reachable(project['resources'], [ident])
    ranges = c.build_ranges(project, {old.PANEL})
    model, settings = project['model'], project['settings']
    for node in list(model.find('{*}resources')):
        if node.get('id') not in keep:
            model.find('{*}resources').remove(node)
    for node in project['build']:
        if node is not item:
            model.find('{*}build').remove(node)
    for key, node in project['objects'].items():
        if key != ident:
            settings.remove(node)
    plate = settings.find('plate')
    for node in plate.findall('model_instance'):
        if c.fields(node)['object_id'] != ident:
            plate.remove(node)
    for node in settings.findall('assemble/assemble_item'):
        if node.get('object_id') != ident:
            settings.find('assemble').remove(node)
    project['ranges'].clear()
    for _, node in ranges:
        node.set('id','1')
        project['ranges'].append(node)
    c.set_fields(plate, {'plater_name': 'R51 feather-pattern battery lid'})
    obj = project['objects'][ident]
    normal, = obj.findall("part[@subtype='normal_part']")
    install_mesh(project['resources'][normal.get('id')], HERE/'exports/Battery_End_Door-print.stl')
    # Retain the bed-facing orientation and outer brim of the printed R48 lid.
    write_project(project, output)


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    make(p.parse_args().output)
