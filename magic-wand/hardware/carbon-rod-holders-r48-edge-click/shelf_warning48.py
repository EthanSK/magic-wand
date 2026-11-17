"""Resolve Bambu's front-shelf warning against its own deposited moves."""
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np

from native48 import read, write, digest, R47

WARNING='It seems object Front_pull_shelf has floating regions. Please re-orient the object or enable support generation.'


def configure_layout(target):
    """Give the thin, disposable front comb a wall before its infill starts."""
    import compose47
    import plate45
    from manifold3d import Manifold
    from battery_print48 import write_project

    project = compose47.read(target)
    front_id, = [identifier for identifier, name in project['names'].items() if name == 'Front_pull_shelf']
    front = project['objects'][front_id]
    compose47.set_fields(front, {
        'is_infill_first': '0', 'wall_loops': '2', 'sparse_infill_density': '20%',
        'outer_wall_speed': '40', 'inner_wall_speed': '45', 'sparse_infill_speed': '45',
        'internal_solid_infill_speed': '45', 'top_surface_speed': '35', 'gap_infill_speed': '30',
        'bottom_shell_layers': '5',
    })
    # A first top skin over the sparse left comb had two unsupported short
    # moves at 16.2 mm. Carry a narrow dense strip from its foot through the
    # skin. Its neighbouring top skin on layer 16.0 needs the same footing,
    # so the front spine spans the left piece to its separation slot. Only
    # the disposable piece changes; the other fingers stay hollow.
    # Starting the strip at the bed avoids a new unsupported bottom skin.
    resources = project['model'].find('./{*}resources')
    component_list = project['resources'][front_id].find('./{*}components')
    number = max(int(part.get('id')) for part in resources) + 1
    strips = (
        ('Solid spine beneath left comb skins', (-8.1, -4.95), (11.11, 5.10), 33.65),
        ('Backing below left comb frame corner', (-7.7, 14.8), (-2.5, 17.6), 6.6),
        ('Backing below middle comb skin', (14.4, -3.8), (16.85, -1.30), 32.0),
    )
    existing = {compose47.fields(part).get('name') for part in front.findall('part')}
    for label, low, high, top in strips:
        assert label not in existing, 'Begin with a freshly composed project'
        region = Manifold.cube((high[0]-low[0], high[1]-low[1], top+.01)).translate((*low, -.01))
        plate45.mesh_resource(resources, number, label, region)
        ET.SubElement(component_list, plate45.tag('component'), objectid=str(number))
        modifier = ET.SubElement(front, 'part', id=str(number), subtype='modifier_part')
        compose47.set_fields(modifier, {'name': label, 'sparse_infill_density': '100%',
                                        'wall_loops': '3', 'infill_wall_overlap': '25%'})
        number += 1
    temporary = target.with_suffix('.front-shelf.3mf')
    write_project(project, temporary)
    temporary.replace(target)


def deposited(archive, out):
    import scope47, roof_strokes45
    with scope47.key_group(archive):
        roof_strokes45.inspect(archive,owner_name='Front_pull_shelf',
                               support_owners=('Key_Carrier','External_cradle'),report_path=out)


def verified_deposition(archive, report):
    """Reuse the complete front-support trace only for identical inputs."""
    import grounded45, native_order45, roof_strokes45, scope47
    from holder45 import inherited
    source_paths = [Path(module.__file__) for module in (grounded45, native_order45, roof_strokes45, scope47)]
    native_checker = inherited.common.load_checker().audit
    source_paths += [Path(native_checker.__file__), Path(native_checker.q.__file__),
                     Path(native_checker.start_audit.__file__)]
    inputs = {'archive': digest(archive), 'frame': digest(archive.parent/'frame.json'),
              'owner': 'Front_pull_shelf', 'support_owners': ['Key_Carrier','External_cradle'],
              'checker': {path.name:digest(path) for path in source_paths}}
    receipt = report.with_suffix('.inputs.json')
    if report.is_file() and receipt.is_file():
        if read(receipt) == {**inputs, 'report': digest(report)}:
            return
    deposited(archive, report)
    assert read(report)['archive_sha256'] == inputs['archive']
    write(receipt, {**inputs, 'report': digest(report)})


def compare(archive, scratch):
    from native48 import endpoint_gap
    out=archive.parent
    old=R47/'exports/complete-plate/R47-Complete-A1-mini-PETG.gcode.3mf'
    old_report=scratch/'contact-regression/r47/front-roof-strokes.json'
    new_report=out/'front-roof-strokes.json'
    # These captures have the same print and bed reference frame. Keep
    # every unsupported sequence so an old spatially unrelated span can
    # never vouch for a new hanging tip.
    for path, report in ((old, old_report), (archive, new_report)):
        verified_deposition(path, report)
    previous,now=read(old_report),read(new_report)
    assert previous['archive_sha256']==digest(old) and now['archive_sha256']==digest(archive)
    assert np.allclose(read(out/'frame.json')['bed_translation'], read(old.parent/'frame.json')['bed_translation'])
    old_gaps=previous['sequence_gaps']
    unmatched=[]
    ordinary=[]
    for row in now['sequence_gaps']:
        if row['classification']=='short straight two-ended bridge':
            ordinary.append(row);continue
        same=[r for r in old_gaps if r['z']==row['z'] and r['classification']==row['classification']
              and r['before']==row['before'] and r['after']==row['after']
              and r['mm']+.2>=row['mm'] and endpoint_gap(r,row)<.5]
        if not same:unmatched.append(row)
    from support_tip48 import omission
    qualified_tips = []
    remaining = []
    for row in unmatched:
        check = omission(archive, row) if len(unmatched)==1 else None
        if check and check['passed']:
            qualified_tips.append(check)
        else:
            remaining.append(row)
    helper=read(out/'helper-starts.json')['owners']['Front_pull_shelf']
    native=read(archive.with_suffix('.native.json'))
    assert native['archive_sha256']==digest(archive)
    reported=[p['warning_message'] for p in native['plates'] if p.get('warning_message')]
    result={'archive_sha256':digest(archive),'front_shelf_warning_text':WARNING,
            'omission_checker_sha256':digest(Path(__file__).with_name('support_tip48.py')),
            'front_shelf_warning_reported_in_this_slice':WARNING in reported,'native_warning_messages':reported,
            'native_warning_position_available':False,'r47_archive_sha256':digest(old),
            'r48_reconstructed_moves_sha256':digest(new_report),'r47_reconstructed_moves_sha256':digest(old_report),
            'checked_layers':helper['checked_layers'], 'unrooted_islands':helper['unrooted_actual_components'],
            'islands_backed_across_one_empty_layer':helper['starts_backed_across_one_empty_layer'],
            'r47_gap_classification':previous['sequence_classifications'],'r48_gap_classification':now['sequence_classifications'],
            'ordinary_two_ended_count':len(ordinary),'raw_unmatched_strokes':unmatched,
            'qualified_disposable_strokes':qualified_tips, 'new_unqualified_strokes':remaining,
            'passed':bool(not helper['unrooted_actual_components'] and not remaining)}
    write(out/'front-shelf-warning.json',result)
    return result
