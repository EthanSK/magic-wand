"""Prepare three independent R42 jobs after the R41 physical toppling failure.

The complete assembly remains the component source of truth. This filters
its build list and remaps height ranges by name, preserving each selected
object's orientation, native support exclusions and bought-part geometry.
Battery helpers keep six outward, two-layer cuttable ties, widened to 2 mm.
Their outward extension grows from 6 to 8 mm. A native outer brim was rejected
because its actual paths entered the open rod bore and clip mouth.
No printer commands are sent by this module.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np

import plate42 as p
import audit42 as audit

HERE = Path(__file__).resolve().parent
JOBS = {
    'keys': ('Key_Carrier', 'DFRobot_Hole_Bracket', 'DFR0030_Post_Clip', 'DFR0030_Post_Clip_2'),
    'battery': ('Battery_Holder', 'Battery_End_Door'),
    'xiao': ('XIAO_Rod_Holder', 'XIAO_Near_Keeper', 'Cable_Clip_12_Wire'),
}
BATTERY_PAD_EXTENSION_MM = 8.
TIE_MM = 2.
BASE_STAGE = p.stage_parts


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def battery_stage(selected, exports, holder, anchors20, manifold):
    extensions = {**p.previous.pads.PAD_EXTENSION, 'Battery_Holder':BATTERY_PAD_EXTENSION_MM}
    with patch.object(p.previous.pads, 'PAD_EXTENSION', extensions):
        manifest, anchors = BASE_STAGE(selected, exports, holder, anchors20, manifold)
    name = 'Battery_Holder'
    body = holder.read(exports/f'{name}{p.plate.SOURCE_SUFFIX}')
    original = holder.read(exports/f'{name}{p.plate.PAD_SUFFIX}')
    section = body.slice(.1)
    rod_x = anchors[name]['rod_axis_print_xy'][0]
    old_plan = anchors20.plan(name, section, rod_x)
    with patch.object(anchors20, 'A', {**anchors20.A, 'tie_width_mm':TIE_MM}):
        plan = anchors20.plan(name, section, rod_x)
    assert len(plan['necks']) == len(old_plan['necks']) == 6
    added = manifold.CrossSection.batch_boolean(plan['necks'], manifold.OpType.Add)
    new = original + manifold.Manifold.extrude(added, .4)
    old_contacts = [(neck ^ section).area() for neck in old_plan['necks']]
    contacts = [(neck ^ section).area() for neck in plan['necks']]
    assert all(new > old*1.9 for new, old in zip(contacts, old_contacts)), (contacts, old_contacts)
    assert len(new.decompose()) == len(original.decompose()) == 6
    # Widen only the accessible cuttable necks; preserve the rod bore.
    rod = anchors[name]['rod_axis_print_xy']
    bore = manifold.CrossSection.circle(4.3, 96).translate(rod)
    assert (new.slice(.1)^bore).area() < 1e-6
    sites = anchors20.anchors19.tie_sites_report(name, body, section, plan)
    assert all(row['part_volume_in_cutter_corridor_mm3'] < .25 for row in sites)
    anchors[name] = p.plate.write_pads(exports, name, new, holder, {
        **anchors[name], 'ties_unchanged':False, 'tie_count':6,
        'tie_width_mm':TIE_MM, 'previous_tie_width_mm':1.,
        'tie_section_each_mm2':TIE_MM*.4,
        'tie_contact_mm2':contacts, 'previous_tie_contact_mm2':old_contacts,
        'pad_thickness_mm':.4,
        'outward_extension_mm':BATTERY_PAD_EXTENSION_MM,'previous_outward_extension_mm':6.,
        'solid_area_mm2':round(new.slice(.1).area(),3),
        'tie_sites':sites,
        'tie_site_probe_scope':{'current_tie_width_mm':TIE_MM,
            'backing_probe_offsets_mm':[-.4,0.,.4],'cutter_corridor_width_mm':3.,
            'full_width_contact_basis':'The separate nominal tie_contact_mm2 measurements cover each complete widened neck.'},
        'cleanup':'Cut each outward two-layer tie before lifting the body; do not twist the rod rings.',
        'physical_strength_and_removal_verified':False,
    })
    save(exports/'anchors.json', {'parts':anchors})
    return manifest, anchors


def make(job, output, only=None):
    selected = set(JOBS[job])
    complete = {n for group in p.plate.read_json(HERE/p.plate.BOM)['groups'].values() for n in group['parts']}
    assert set().union(*map(set,JOBS.values())) == complete
    assert sum(map(len,JOBS.values())) == len(complete) == 9
    if only is not None:
        # A requested single-component diagnostic is a subset of this job,
        # not another complete assembly or a change to the canonical BOM.
        subset = set(only)
        assert subset and subset <= selected, (job, subset, selected)
        selected = subset
    stage = battery_stage if job=='battery' else BASE_STAGE
    origins = dict(p.previous.pads.ORIGINS)
    if job=='battery':
        # Validate the full staging template before filtering. The enlarged
        # battery pads need additional edge clearance; the unused cable is
        # moved aside in that temporary template and excluded from this job.
        origins.update(Battery_Holder=(30.,63.),Cable_Clip_12_Wire=(90.,56.))
    with patch.object(p, 'stage_parts', side_effect=stage), \
         patch.object(p.previous.pads,'ORIGINS',origins):
        generated = p.make(output)
    with ZipFile(generated) as archive:
        files = {n:archive.read(n) for n in archive.namelist()}
    model, settings, ranges = (ET.fromstring(files[n]) for n in (p.MODEL,p.plate.MODEL_SETTINGS,p.RANGES))
    names = p.previous.names(settings)
    build = model.find('./{*}build')
    old_order = [names[item.get('objectid')] for item in build]
    chosen_ids = {identifier for identifier,name in names.items() if name in selected}
    for item in list(build):
        if item.get('objectid') not in chosen_ids: build.remove(item)
    order = [names[item.get('objectid')] for item in build]
    assert set(order)==selected and len(order)==len(selected)
    for obj in list(settings.findall('object')):
        if obj.get('id') not in chosen_ids: settings.remove(obj)
    plate = settings.find('plate')
    p.set_fields(plate, {'plater_name':f'Magic Wand R42 {job} · A1 mini PETG'})
    for instance in list(plate.findall('model_instance')):
        if instance.find("metadata[@key='object_id']").get('value') not in chosen_ids:
            plate.remove(instance)
    assemble = settings.find('assemble')
    if assemble is not None:
        for item in list(assemble):
            if item.get('object_id') not in chosen_ids: assemble.remove(item)
    for entry in list(ranges):
        name = old_order[int(entry.get('id'))-1]
        if name not in selected: ranges.remove(entry)
        else: entry.set('id',str(order.index(name)+1))
    # Drop unreachable resources too, so excluded parts cannot return on reopen.
    resources = model.find('./{*}resources')
    reachable = set(chosen_ids)
    by_id = {obj.get('id'):obj for obj in resources}
    pending = list(reachable)
    while pending:
        for component in by_id[pending.pop()].findall('./{*}components/{*}component'):
            identifier = component.get('objectid')
            if identifier not in reachable:
                reachable.add(identifier); pending.append(identifier)
    for obj in list(resources):
        if obj.get('id') not in reachable: resources.remove(obj)
    for name,root in ((p.MODEL,model),(p.plate.MODEL_SETTINGS,settings),(p.RANGES,ranges)):
        files[name] = ET.tostring(root,encoding='utf-8',xml_declaration=True)
    target = output/f'R42-{job}-A1-mini-PETG-layout.3mf'
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for name,value in files.items(): archive.writestr(name,value)
    generated.unlink()
    exports = output/'build-source/exports'
    for filename in ('manifest.json','anchors.json'):
        data = p.plate.read_json(exports/filename)
        data['parts'] = {n:v for n,v in data['parts'].items() if n in selected}
        if 'plate_parts' in data: data['plate_parts'] = order
        save(exports/filename,data)
    checks = p.plate.read_json(output/'print-checks.json')
    checks['build_list'] = order
    for field in ('source_parts','anchors','material_bounds_xy_mm','plate_extents_mm','slow_bands_mm'):
        if isinstance(checks.get(field),dict): checks[field] = {n:v for n,v in checks[field].items() if n in selected}
    if job=='battery': checks['anchors'] = p.plate.read_json(exports/'anchors.json')['parts']
    # The final deposited-path audit, including the enlarged pads, is authoritative.
    checks.update(job=job,layout_sha256=p.plate.digest(target),split_driver_sha256=p.plate.digest(Path(__file__)),
                  complete_bom_sha256=p.plate.digest(HERE/'complete-assembly.json'),
                  part_selection_complete_and_disjoint=only is None, physical_ready_for_send=False,
                  physical_hold_reason='Clear failed R41 plastic and reseat the plate before any new job.')
    save(output/'print-checks.json',checks)
    save(output/'job.json', {'job':job,'parts':order,'source_bom_sha256':checks['complete_bom_sha256'],
                           'model_geometry_changed':False,'battery_tie_width_mm':TIE_MM if job=='battery' else None,
                           'battery_pad_extension_mm':BATTERY_PAD_EXTENSION_MM if job=='battery' else None,
                           'battery_holder_native_brim':False})
    return target


def inspect(job, archive, output):
    if job=='keys':
        audit.common.PLOT_DIRECTORY = output
        return audit.audit(archive,output)
    checker = audit.common.load_checker()
    generic = audit.common.inspect.__globals__
    previous_regions = audit.d.BATTERY.h18.regions
    def regions(name):
        if name!='Battery_End_Door': return previous_regions(name)
        door = audit.d.DOOR
        return {'tongue_slit':audit.d.box(door['tongue_root_x_mm']+.05,door['window_x_mm'][0]-.05,
            door['y_mm'][0]-1.,door['y_mm'][1]+1.,door['tongue_z_mm'][1]+.05,
            door['tongue_z_mm'][1]+door['slit_mm']-.05)}
    with patch.dict(generic, {'BRIM_WIDTH':6}), \
         patch.object(audit.d.BATTERY.h18,'regions',side_effect=regions), \
         patch.object(checker.project22.studio.p19,'command_audit',side_effect=p.command_audit):
        result = audit.common.inspect(archive,output/'build-source/exports',lambda:({},{}),
                                      p.plate.read_json(output/'print-checks.json'))
    result.update(split_checker_sha256=p.plate.digest(Path(__file__)),physical_strength_verified=False,
                  physical_support_removal_verified=False)
    return result


def slice_archive(job, source, output, suffix='', command_checker=None):
    import project22
    studio = project22.studio.p19
    with ZipFile(source) as archive: config = json.loads(archive.read(p.PROJECT))
    for name in ('tmp','data','profile-home/Library/Preferences'):
        (output/name).mkdir(parents=True,exist_ok=True)
    target = output/f'R42-{job}{suffix}.gcode.3mf'
    env = {**os.environ,'TMPDIR':str(output/'tmp'),'CFFIXED_USER_HOME':str(output/'profile-home')}
    command = [str(studio.BAMBU),'--datadir',str(output/'data'),'--debug','2','--orient','0',
               '--arrange','0','--slice','0','--export-3mf',target.name,'--outputdir',str(output),str(source)]
    with (output/f'slice{suffix}.log').open('w') as log:
        subprocess.run(command,cwd=output,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
    raw = p.plate.read_json(output/'result.json')
    assert raw['return_code']==0,raw
    row, = raw['sliced_plates']
    checks = p.plate.read_json(output/'print-checks.json')
    assert {item['name'] for item in row['objects']}==set(checks['build_list'])
    studio.restore_registration(target,config)
    check_commands = p.command_audit if command_checker is None else command_checker
    checks.update(archive_sha256=p.plate.digest(target),commands=check_commands(target,config),
        estimate_seconds=round(row['total_predication']),filament_g=round(sum(f['total_used_g'] for f in row['filaments']),2),
        warnings=[row['warning_message']] if row.get('warning_message') else [],archive_warnings=studio.slice_info_warnings(target))
    assert not checks['warnings'] and not checks['archive_warnings'],checks
    save(output/'print-checks.json',checks)
    return target


def run(job, output, retained):
    layout = make(job,output)
    first = slice_archive(job,layout,output)
    result = inspect(job,first,output)
    save(output/'initial-audit.json',result)
    assert result['passed'],result['failures']
    # Reopen the exact passing editable archive once and check its own paths.
    import roundtrip23 as rt
    before, before_model, before_gcode = rt.roundtrip22.common.archive_settings(first)
    reopened = slice_archive(job,first,output,'-reopened')
    after, after_model, after_gcode = rt.roundtrip22.common.archive_settings(reopened)
    assert rt.object_recipe(before_model)==rt.object_recipe(after_model)
    assert before==after,'Reopened global settings changed'
    result = inspect(job,reopened,output)
    save(output/'slice-audit.json',result)
    assert result['passed'],result['failures']
    save(output/'reopen-checks.json',{'passed':True,'input_sha256':p.plate.digest(first),
        'selected_archive_sha256':p.plate.digest(reopened),'settings_identical':True,
        'object_recipes_identical':True,'selected_archive_own_paths_audited':True,
        'normalized_toolpaths_identical':rt.roundtrip22.common.normalized_gcode(before_gcode)==rt.roundtrip22.common.normalized_gcode(after_gcode)})
    package = p.previous.recipe.make_print_only(reopened,output)
    final = output/f'R42-{job}-print-only.3mf'
    package.rename(final)
    receipt = p.plate.read_json(output/'print-only.json')
    receipt.update(file=final.name,sha256=p.plate.digest(final));save(output/'print-only.json',receipt)
    retained.mkdir(parents=True,exist_ok=False)
    selected = [layout,first,reopened,final,*[output/n for n in ('job.json','initial-audit.json','slice-audit.json',
                   'reopen-checks.json','print-checks.json','print-only.json')]]
    selected += list(output.glob('audit*.png'))
    for path in selected: shutil.copy2(path,retained/path.name)
    for name in ('manifest.json','anchors.json'):
        shutil.copy2(output/'build-source/exports'/name,retained/f'print-{name}')
    checks = p.plate.read_json(output/'print-checks.json')
    save(retained/'job-review.json',{'job':job,'parts':list(JOBS[job]),'digital_checks_passed':True,
        'physical_ready_for_send':False,'physical_hold_reason':checks['physical_hold_reason'],
        'physical_success_guaranteed':False,'estimate_seconds':checks['estimate_seconds'],'filament_g':checks['filament_g'],
        'artifact_sha256':{path.name:p.plate.digest(retained/path.name) for path in selected},
        'driver_sha256':p.plate.digest(Path(__file__))})
    print(json.dumps({'job':job,'passed':True,'parts':checks['build_list'],
                      'seconds':checks['estimate_seconds'],'grams':checks['filament_g']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job',choices=JOBS)
    parser.add_argument('output',type=Path)
    parser.add_argument('retained',type=Path)
    args=parser.parse_args()
    run(args.job,args.output.resolve(),args.retained.resolve())
