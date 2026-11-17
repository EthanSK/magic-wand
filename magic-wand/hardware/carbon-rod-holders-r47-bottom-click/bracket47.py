"""Prepare the revised bracket and its two matching clips; never send a job.

The bought-board/hinge geometry comes from Opus's checked R47 cap export.
The unchanged normalized frame preserves R42's narrow external anchor ties
and manual foot-support selections. Final native backing/removal checks are
still required; this script does not certify that a slice will print.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys
from xml.etree import ElementTree as E
from zipfile import ZipFile, ZIP_DEFLATED

import compose47 as c
NAMES={'DFRobot_Hole_Bracket','DFR0030_Post_Clip','DFR0030_Post_Clip_2'}

def prepare(base, cap, checks, output):
    geometry=json.loads(checks.read_text())['r47']
    required=('bracket_one_piece','stop_boss','pusher_to_floor','pusher_root_to_floor',
              'pusher_to_root','edge_stops','dfr_posts','backup_stops_both_sides',
              'tab_engagement_0.6','squeezed_tab_clear_0.2','straight_lift_retention',
              'capture_contacts','pin_gaps_0.2','pin_relief_ahead_of_arm_root')
    assert all(geometry['inherited_gates'][name] for name in required), 'Bracket geometry gate failed'
    project=c.read(base);model=project['model'];settings=project['settings']
    raw=cap.read_bytes();count,=struct.unpack_from('<I',raw,80)
    assert len(raw)==84+50*count, 'Expected the CAD exporter binary STL'
    triangles=[]
    for i in range(count):
        row=struct.unpack_from('<12fH',raw,84+50*i)
        triangles.append([tuple(row[j:j+3]) for j in (3,6,9)])
    low=[min(v[k] for tri in triangles for v in tri) for k in range(3)]
    high=[max(v[k] for tri in triangles for v in tri) for k in range(3)]
    # The existing front-down frame is assembly XYZ=(-10.6, -11.835,22.7)
    # plus print (X,Z,-Y). A changed bound must trigger a new anchor screen.
    frame=[low[0],low[1],high[2]]
    expected=[-10.6,-11.835,22.7]
    assert all(abs(a-b)<.001 for a,b in zip(frame,expected)),('Re-screen bracket anchors and foot selections',frame)
    points=[];faces=[];indices={}
    for tri in triangles:
        face=[]
        for x,y,z in tri:
            point=(x-low[0],high[2]-z,y-low[1])
            if point not in indices:indices[point]=len(points);points.append(point)
            face.append(indices[point])
        faces.append(face)
    resources=model.find('./{*}resources');body=resources.find("./{*}object[@id='3']")
    old=body.find('./{*}mesh');body.remove(old)
    mesh=E.SubElement(body,'{'+c.NAMESPACE+'}mesh')
    vv=E.SubElement(mesh,'{'+c.NAMESPACE+'}vertices');tt=E.SubElement(mesh,'{'+c.NAMESPACE+'}triangles')
    for point in points:E.SubElement(vv,'{'+c.NAMESPACE+'}vertex',**{k:f'{v:.12g}' for k,v in zip('xyz',point)})
    for face in faces:E.SubElement(tt,'{'+c.NAMESPACE+'}triangle',**{k:str(v) for k,v in zip(('v1','v2','v3'),face)})
    chosen={i for i,n in project['names'].items() if n in NAMES}
    build=model.find('./{*}build')
    for item in list(build):
        if item.get('objectid') not in chosen:build.remove(item)
    for obj in list(settings.findall('object')):
        if obj.get('id') not in chosen:settings.remove(obj)
    plate=settings.find('plate')
    for inst in list(plate.findall('model_instance')):
        if c.fields(inst)['object_id'] not in chosen:plate.remove(inst)
    assemble=settings.find('assemble')
    if assemble is not None:
        for item in list(assemble):
            if item.get('object_id') not in chosen:assemble.remove(item)
    keep=c.reachable(project['resources'],chosen)
    for obj in list(resources):
        if obj.get('id') not in keep:resources.remove(obj)
    ranges=E.Element('objects');order=[project['names'][i.get('objectid')] for i in build]
    for name,row in c.build_ranges(project,NAMES):row.set('id',str(order.index(name)+1));ranges.append(row)
    c.set_fields(plate,{'plater_name':'Magic Wand R47 bracket and clips - A1 mini PETG'})
    files=project['files']
    for name,root in [(c.MODEL,model),(c.SETTINGS,settings),(c.RANGES,ranges)]:files[name]=E.tostring(root,encoding='utf-8',xml_declaration=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)
    receipt={'state':'prepared_geometry_only_not_sliced','parts':order,'cap_sha256':sha256(raw).hexdigest(),
             'complete_geometry_check_passed':geometry['passed'],
             'remaining_geometry_check_scope':'The carrier is independently checked before any combined job is sent.',
             'source_layout_sha256':sha256(base.read_bytes()).hexdigest(),'geometry_checks_sha256':sha256(checks.read_bytes()).hexdigest(),
             'layout_sha256':sha256(output.read_bytes()).hexdigest(),'cap_assembly_bounds_mm':[low,high],
             'print_to_assembly':[[1,0,0,low[0]],[0,0,1,low[1]],[0,-1,0,high[2]],[0,0,0,1]],
             'anchor_and_manual_foot_selectors':'R42 normalized frame unchanged; final deposited attachment/backing/removal audit pending'}
    output.with_suffix('.preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':prepare(*map(Path,sys.argv[1:]))
