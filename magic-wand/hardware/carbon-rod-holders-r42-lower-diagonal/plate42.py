"""Prepare R42's complete DFRobot plate with the checked R37 PETG recipe.

CAD/export generation belongs to assembly42.py. This composes those exact
meshes with the existing removable pads, native Studio supports and recipe;
it does not connect to a printer. Audit the actual slice before packaging.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import trimesh

import holder42 as design
import plate38 as previous

HERE = Path(__file__).resolve().parent
plate = previous.plate
command_audit = previous.command_audit
PROJECT = previous.PROJECT
RANGES = previous.RANGES
MODEL = previous.MODEL

# Selected from R42's exported downward faces. The diagonal roofs span
# several print heights, so their actual height interval replaces R38's
# single horizontal-roof height. X/Z rectangles are in assembly coordinates.
LEDGES = (
    ('diagonal OP1 slot', (-10.82, 9.18, -.76, 11.35), (36.003, 40.694)),
    ('white connector ledge', (.773, 6.05, 8.241, 9.18), (14.763, 18.245)),
    ('upper left key lip', (-27.85, 9.93, -14.15, 11.12), (18.35, 18.35)),
    ('outer finger guard', (-21., .6, -13., 1.9), (24.95, 25.3)),
)

# These two early stop feet were one-ended cantilevers on layer 0.6.
# Coordinates are in the normalized front-down bracket print frame, from
# the actual source mesh and selected paths, not assembly/world axes.
BRACKET_FEET = (
    ('left backup-stop foot', ((.30, 5.35, .35), (2.10, 9.47, .76))),
    ('right backup-stop foot', ((19.10, 5.80, .35), (20.90, 9.47, .76))),
)


def bracket_support_boxes(record):
    frame = np.asarray(record['print_to_assembly'])
    expected = np.asarray(((1., 0., 0.), (0., 0., 1.), (0., -1., 0.)))
    assert np.allclose(frame[:3,:3], expected), 'Re-screen feet after changing bracket orientation'
    assert np.allclose(frame[:3,3], (-10.6, -11.835, 22.7), atol=.001), 'Re-screen feet after changing bracket bounds'
    return BRACKET_FEET


def support_boxes(record):
    assert LEDGES, 'Select and inspect R42 roofs before preparing its plate'
    frame = np.asarray(record['print_to_assembly'])
    expected = np.asarray(((1., 0., 0.), (0., 0., -1.), (0., 1., 0.)))
    assert np.allclose(frame[:3, :3], expected), 'Re-screen roofs after changing orientation'
    x_shift, y_shift = -frame[0, 3], -frame[2, 3]
    return [(label, ((x0+x_shift-.15, z0+y_shift-.15, heights[0]-.05),
                     (x1+x_shift+.15, z1+y_shift+.15, heights[1]+.35)))
            for label, (x0, z0, x1, z1), heights in LEDGES]


def stage_parts(selected, exports, holder, anchors20, manifold):
    extensions = {**previous.pads.PAD_EXTENSION, design.BRACKET: 7.}
    with patch.object(previous.pads, 'PAD_EXTENSION', extensions):
        manifest, anchors = previous.stage_parts(selected, exports, holder, anchors20, manifold)
    # R42's lower board approaches the first two print layers. Move only
    # the disposable connections away from its loading space; keep the
    # functional bracket and the 1 mm-wide external breakaway section.
    # An extra 0.1 mm of overlap retains 0.102 mm2 contact per side.
    # That clears the existing 0.1 gate; R41 had 0.14 mm2, not the same area.
    name = design.BRACKET
    body = holder.read(exports / f'{name}{plate.SOURCE_SUFFIX}')
    first = body.slice(.1)
    tip = first ^ manifold.CrossSection.square((3., 50.)).translate((0., -10.))
    bounds = tip.bounds()
    y = (bounds[1] + bounds[3]) / 2 + .4
    left = manifold.CrossSection.circle(2.4, 48).translate((-3.4, y))
    left += manifold.CrossSection.square((1.46, 1.)).translate((-1.22, y-.5))
    right = left.mirror((1., 0.)).translate((body.bounding_box()[3], 0.))
    contacts = [(side ^ first).area() for side in (left, right)]
    assert min(contacts) > .1, contacts
    original = manifold.Manifold.extrude(left + right, .4)
    enlarged = previous.pads.solid_pads(original, body, 7., name)
    anchors[name] = plate.write_pads(exports, name, enlarged, holder, {
        'tie_overlap_at_first_layer_mm2': contacts,
        'tie_shift_print_y_mm': .4, 'tie_span_print_y_mm': 1.,
        'tie_x_overlap_mm': .24, 'previous_tie_x_overlap_mm': .14,
        'ties_unchanged': False,
        'hole_centres_print_xy_mm': [], 'pad_thickness_mm': .4,
        'old_area_mm2': round(original.slice(.1).area(), 3),
        'solid_area_mm2': round(enlarged.slice(.1).area(), 3),
    })
    (exports/'anchors.json').write_text(json.dumps({'parts': anchors}, indent=2)+'\n')
    return manifest, anchors


def set_fields(obj, values):
    for key, value in values.items():
        entry = obj.find(f"metadata[@key='{key}']")
        if entry is None:
            entry = ET.SubElement(obj, 'metadata', key=key)
        entry.set('value', value)


def configure_layout(path, title):
    """Remap the existing seven-part recipe onto the nine-part DFRobot BOM.

    The two post clips receive their own flat, tied pads. Layer-range IDs
    refer to one-based build order, so remap by verified names rather than
    copying old object numbers or requiring the old Grove build list.
    """
    import project22

    previous.BASE_CONFIGURE(path, title)
    with ZipFile(path) as source:
        files = {name: source.read(name) for name in source.namelist()}
    with ZipFile(previous.BASE) as source:
        baseline = {name: source.read(name) for name in
                    (PROJECT, RANGES, MODEL, plate.MODEL_SETTINGS)}
    config = json.loads(baseline[PROJECT])
    settings = ET.fromstring(files[plate.MODEL_SETTINGS])
    model = ET.fromstring(files[MODEL])
    names = previous.names(settings)
    order = [names[x.get('objectid')] for x in model.findall('./{*}build/{*}item')]
    old_names = previous.names(ET.fromstring(baseline[plate.MODEL_SETTINGS]))
    old_order = [old_names[x.get('objectid')] for x in
                 ET.fromstring(baseline[MODEL]).findall('./{*}build/{*}item')]
    ranges = ET.fromstring(baseline[RANGES])
    for entry in ranges.findall('object'):
        old_name = old_order[int(entry.get('id')) - 1]
        name = design.BRACKET if old_name == 'Grove_Touch_Bracket' else old_name
        assert name in order, (old_name, name, order)
        entry.set('id', str(order.index(name) + 1))

    carrier = next(x for x in settings.findall('object')
                   if names[x.get('id')] == design.CARRIER)
    set_fields(carrier, {
        'enable_support': '1', 'support_type': 'normal(auto)', 'support_style':'snug',
        'support_threshold_angle': '45',
        'support_on_build_plate_only': '0', 'support_top_z_distance': '0.2',
        'support_bottom_z_distance': '0.2', 'support_object_xy_distance': '0.35',
        'support_interface_top_layers': '2', 'support_interface_spacing': '0.20',
        'bridge_no_support': '0',
    })
    manifest = plate.read_json(path.parent/'build-source/exports/manifest.json')
    identifier = max(int(x.get('id')) for x in model.findall('./{*}resources/{*}object')) + 1
    for label, bounds in support_boxes(manifest['parts'][design.CARRIER]):
        project22.studio.p19.add_mesh_part(
            model, carrier, trimesh.creation.box(bounds=bounds), identifier,
            'support_enforcer', f'REMOVE AFTER PRINT - {label} support')
        identifier += 1

    # The rear-down rod bore runs vertically in print coordinates. Keep the
    # native support generator out of the gripping surface over its entire
    # height; the final audit checks actual paths, not just this selection.
    frame = np.asarray(manifest['parts'][design.CARRIER]['print_to_assembly'])
    height = float(manifest['parts'][design.CARRIER]['print_height_mm'])
    # Blockers select contacts, not traversing columns. The additional
    # radial margin covers Normal support's contact/base expansion. Do not
    # enforce the already-backed rod ledge inside this projection.
    blocker = trimesh.creation.cylinder(radius=5.8, height=height+.4, sections=96)
    blocker.apply_translation((-frame[0,3], -frame[2,3], (height+.4)/2))
    project22.studio.p19.add_mesh_part(
        model, carrier, blocker, identifier, 'support_blocker', 'KEEP CLEAR - rod grip channel')
    identifier += 1
    inverse_frame = np.linalg.inv(frame)[:3,:]
    working = design.geometry()[1]
    for label in ('clip_gap_mid', 'clip_gap_rear'):
        bounds = np.asarray(working[label].transform(inverse_frame).bounding_box()).reshape(2,3)
        bounds[0,:2]-=1.5
        bounds[1,:2]+=1.5
        project22.studio.p19.add_mesh_part(
            model, carrier, trimesh.creation.box(bounds=bounds), identifier,
            'support_blocker', f'KEEP CLEAR - {label}')
        identifier += 1

    # Small pivot seats need a clean surface as well as nominal clearance.
    # Native contact exclusions use the same expansion margin as the rod
    # route. Clip the non-printing selection at the bed, not the model.
    for side in (-1,1):
        x0,x1=design.r.h29.SUPPORT_X
        x0,x1=x0-.6,x1+.6
        if side<0:x0,x1=-x1,-x0
        shape=(design.mf.Manifold.cylinder(x1-x0,2.3,2.3,96).rotate((0.,90.,0.))
               .translate((x0,design.r.AXIS_Y+design.r.CLICK_SHIFT,design.r.AXIS_Z))
               .transform(inverse_frame))
        shape ^= design.box(-100.,100.,-100.,100.,0.,height+.4)
        mesh=shape.to_mesh()
        blocker=trimesh.Trimesh(vertices=mesh.vert_properties[:,:3],faces=mesh.tri_verts,process=False)
        project22.studio.p19.add_mesh_part(
            model,carrier,blocker,identifier,'support_blocker',f'KEEP CLEAR - snap hinge {side}')
        identifier+=1

    bracket = next(x for x in settings.findall('object')
                   if names[x.get('id')] == design.BRACKET)
    set_fields(bracket, {
        'enable_support':'1', 'support_type':'normal(manual)',
        'support_on_build_plate_only':'1', 'support_top_z_distance':'0.2',
        'support_bottom_z_distance':'0.2', 'support_object_xy_distance':'0.35',
        'support_interface_top_layers':'2', 'support_interface_spacing':'0.20',
        'bridge_no_support':'0',
    })
    for label, bounds in bracket_support_boxes(manifest['parts'][design.BRACKET]):
        project22.studio.p19.add_mesh_part(
            model, bracket, trimesh.creation.box(bounds=bounds), identifier,
            'support_enforcer', f'REMOVE AFTER PRINT - {label} support')
        identifier += 1

    inverse = np.linalg.inv(np.asarray(
        manifest['parts'][design.CARRIER]['print_to_assembly']))[:3, :]
    for number, seat in enumerate(design.op1_seats().decompose(), 1):
        bounds = np.asarray(seat.transform(inverse).bounding_box()).reshape(2, 3)
        bounds[0] -= .15
        bounds[1] += .15
        project22.studio.p19.add_mesh_part(
            model, carrier, trimesh.creation.box(bounds=bounds), identifier,
            'modifier_part', f'OP1 mounting seat {number} solid infill',
            (('sparse_infill_density', '100%'), ('outer_wall_line_width', '0.4'),
             ('inner_wall_line_width', '0.4'), ('internal_solid_infill_line_width', '0.4')))
        identifier += 1

    # Existing small-part motion pattern from R39, now on the DFRobot bracket.
    for obj in settings.findall('object'):
        if names[obj.get('id')] in (design.CARRIER, design.BRACKET):
            values = {'outer_wall_speed': '40', 'inner_wall_speed': '65',
                      'outer_wall_acceleration': '1000', 'inner_wall_acceleration': '1500',
                      'top_surface_speed': '30'}
            if names[obj.get('id')] == design.BRACKET:
                values.update(sparse_infill_density='100%', wall_loops='4',
                              wall_generator='arachne', min_bead_width='60%',
                              wall_distribution_count='2')
            set_fields(obj, values)
        if names[obj.get('id')].startswith(design.CLIP):
            set_fields(obj, {'initial_layer_line_width': '0.4', 'outer_wall_line_width': '0.4',
                             'inner_wall_line_width': '0.4', 'internal_solid_infill_line_width': '0.4'})
    config['reduce_crossing_wall'] = '1'
    files.update({PROJECT: json.dumps(config).encode(),
                  RANGES: ET.tostring(ranges, encoding='utf-8', xml_declaration=True),
                  MODEL: ET.tostring(model, encoding='utf-8', xml_declaration=True),
                  plate.MODEL_SETTINGS: ET.tostring(settings, encoding='utf-8', xml_declaration=True)})
    with ZipFile(path, 'w', ZIP_DEFLATED) as target:
        for name, content in files.items():
            target.writestr(name, content)


def make(output):
    output.mkdir(parents=True, exist_ok=True)
    assert not any(output.iterdir()), 'Use a fresh preparation directory'
    selected = {n for g in plate.read_json(HERE/plate.BOM)['groups'].values() for n in g['parts']}
    clips = tuple(sorted(n for n in selected if n.startswith(design.CLIP)))
    assert len(selected) == 9 and len(clips) == 2, selected
    assert design.BRACKET in selected and 'Grove_Touch_Bracket' not in selected
    origins = {n: v for n, v in previous.pads.ORIGINS.items() if n in selected}
    origins[design.BRACKET] = (109., 120.)
    origins.update({clips[0]: (18., 24.), clips[1]: (35., 24.)})
    assert set(origins) == selected
    plate.BRACKET = design.BRACKET
    plate.CLIPS = clips
    plate.LOCAL_PADS = (plate.KEY, plate.BRACKET, *clips)
    plate.ORIGINS = origins
    plate.BRIM_WIDTH = 6
    plate.stage_parts = stage_parts
    plate.configure_layout = configure_layout
    plate.build(HERE, output, plate.FLASHFORGE_PROFILE, False, True)
    target = output/'R42-Complete-A1-mini-PETG-layout.3mf'
    report_path = output/'print-checks.json'
    report = plate.read_json(report_path)
    with ZipFile(target) as archive:
        config = json.loads(archive.read(PROJECT))
    report.update(layout_sha256=plate.digest(target), driver_sha256=plate.digest(Path(__file__)),
                  recipe_source_sha256=plate.digest(previous.BASE),
                  effective_filament_settings={k: config[k] for k in report['effective_filament_settings']},
                  support_enforcers=support_boxes(
                      plate.read_json(output/'build-source/exports/manifest.json')['parts'][plate.KEY]),
                  bracket_support_enforcers=bracket_support_boxes(
                      plate.read_json(output/'build-source/exports/manifest.json')['parts'][design.BRACKET]),
                  physical_success_verified=False)
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    return target


def package(archive, output):
    target = previous.recipe.make_print_only(archive, output)
    renamed = output/'R42-DFRobot-Diagonal-print-only.3mf'
    target.rename(renamed)
    receipt_path = output/'print-only.json'
    receipt = plate.read_json(receipt_path)
    receipt.update(file=renamed.name, sha256=sha256(renamed.read_bytes()).hexdigest())
    receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
    return renamed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--package', type=Path)
    args = parser.parse_args()
    print(package(args.package.resolve(), args.output.resolve()) if args.package
          else make(args.output.resolve()))
