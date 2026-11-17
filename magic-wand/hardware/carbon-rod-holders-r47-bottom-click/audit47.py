"""R47 adapter for the established whole-bead R45 audit; no printer control.

Run after plate47 and slice45. Keep the inherited helper removal proof and
route scanner; replace only the carrier's moved routes and material targets.
The final source/export/geometry receipt must match before this is run.
"""
import json
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np
import holder47 as h
import build47 as b
import plate47
import audit45 as audit
import audit46
import web_qualification45
from plate45 import digest
from owner45 import layout_owners


def chamfer_gate(rows):
    """Keep the construction overlap visible; test every designed slab."""
    member = rows['complete chamfer']
    fringe = [r for r in member['layer_volumes'] if r['top_mm'] < 28.4]
    # standing45 constructs its first slab at 28.2 minus one nanometre.
    # The layer ending at 28.2 contains only this explicit joining overlap.
    assert all(r['top_mm'] == 28.2 and r['target_mm3'] < .0001 for r in fringe)
    designed = [r for r in member['layer_volumes'] if r['top_mm'] >= 28.4]
    assert len(designed) == 13 and designed[-1]['top_mm'] == 30.8
    member['construction_overlap_slabs'] = fringe
    member['designed_slabs_minimum_fraction'] = min(r['fraction'] for r in designed)
    return (all(r['fraction'] >= .9 for r in designed)
            and all(r['minimum_layer_fraction'] >= .9
                    for name, r in rows.items() if name != 'complete chamfer'))


def check(archive, scratch, resume_material=False):
    out = archive.parent
    source = scratch / 'stage'
    receipt = json.loads((source / 'r47-checks.json').read_text())
    assert receipt['r47']['passed'], 'Current geometry has unresolved gates'
    expected = b.load(source / 'R47-Key-Carrier-assembly.stl')
    layout_frame = json.loads((out / 'frame.json').read_text())
    assert layout_frame['carrier_assembly_sha256'] == digest(source / 'R47-Key-Carrier-assembly.stl')
    fidelity = layout_frame['layout_body_vs_checked_carrier']
    assert fidelity['largest_change_wider_than_0.2mm_mm2'] < .005
    assert fidelity['largest_change_outside_r45_floor_band_mm2'] < .005
    frame = np.asarray(layout_frame['print_to_assembly'])
    inverse = np.linalg.inv(frame)[:3]

    # Build the complete current rib/fixed targets once. The inherited R42
    # material targets alone do not include R47's replacement R2/R3 landing.
    model, working, fixed, ribs, _, _ = b.compose(scratch / 'parent-audit-targets')
    assert abs(model.volume() - receipt['r47']['composition']['carrier_mm3']) < .001
    intended_print = model.transform(inverse)
    original_routes = audit.prior.routes
    _, inherited_material = original_routes()
    material = dict(inherited_material[h.CARRIER])
    for name, rib in ribs.items():
        label = f'{name} guard root bond' if name.startswith('R') else f'{name} rod-side guard bond'
        target = fixed ^ rib
        if name.startswith('L'):
            target ^= h.box(-9., 0., -12., 35., 0., 13.)
        material[label] = target
    material['R47 right guard landing'] = h.rib_landing()
    material['R47 landing to fixed deck'] = h.rib_landing() ^ fixed ^ h.box(0., 9., -12., 35., 0., 13.)
    material['R47 complete chin'] = h.chin()
    material['R47 chin to original deck'] = h.chin() ^ fixed
    carrier_routes = plate47.routes_for(receipt['backup_angle_deg'])()[0]
    carrier_routes[h.CARRIER]['DFRobot bracket operating stroke to backup stop'] = b.Poses([
        b.r.world(b.p.bracket(), angle)
        for angle in np.linspace(h.q.EARLY_ANGLE, receipt['backup_angle_deg'], 29)])

    def routes():
        return carrier_routes, {h.CARRIER: material}

    def precision():
        r = h.r
        bore = r.mirrored(r.d.axis_oval(r.AXIS_Y + r.CLICK_SHIFT, r.AXIS_Z,
            r.h29.BORE_R, r.h29.SUPPORT_X[0] - .5, r.h29.SUPPORT_X[1] + .5))
        return {'complete hinge bore surfaces': bore}

    def evaluate(result, directory, matrix, old, actual, targets, xyz, selected,
                 data, engine, checker, hard, interference, removable):
        fields = (xyz[selected], data[selected, 3], data[selected, 4], data[selected, 7])
        result['critical_material'] = {}
        result['target_geometry'] = {}
        for name, shape in material.items():
            # Keep the CAD witness fixed while measuring the native result;
            # clipping it to the native mesh could hide an export defect.
            intended = shape.transform(inverse) ^ intended_print
            present = intended ^ actual
            assert intended.volume() > .05, (name, 'empty final load-path witness')
            result['target_geometry'][name] = {
                'source_volume_mm3': intended.volume(), 'retained_volume_mm3': present.volume(),
                'trimmed_volume_mm3': max(0., (intended - actual).volume()),
                'basis': 'Final source-CAD member; exported mesh and deposited coverage do not shrink this witness.'}
            result['critical_material'][name] = engine.material_coverage(
                checker.q, checker.start_audit, intended, *fields)

        recipe = json.loads((b.R46_EXPORTS / 'r46-braces.json').read_text())
        braces = {}
        for name, record in recipe['records'].items():
            rows = {}
            for label, reference in {'whole member': record['witness'], **record['joint_witnesses']}.items():
                path = b.R46_EXPORTS / reference['file']
                assert digest(path) == reference['sha256']
                original = b.load(path)
                intended = original ^ intended_print
                retained = intended ^ actual
                rows[label] = engine.material_coverage(checker.q, checker.start_audit, intended, *fields)
                rows[label]['original_mm3'] = original.volume()
                rows[label]['intended_mm3'] = intended.volume()
                rows[label]['retained_mm3'] = retained.volume()
                rows[label]['export_missing_mm3'] = max(0., (intended - actual).volume())
                if label == 'whole member':
                    rows['cross_sections'] = audit46.transverse_sections(
                        intended, record['stations'], matrix, *fields, checker)
            braces[name] = rows
        result['r46_braces'] = braces
        landing = h.rib_landing().transform(inverse) ^ intended_print
        landing_sections = audit46.transverse_sections(landing, h.LANDING_RUN, matrix, *fields, checker)
        result['r47_landing_sections'] = landing_sections
        witness_directory = scratch / 'parent-audit-targets/r45-standing'
        web = json.loads((witness_directory / 'standing-web.json').read_text())
        original_load = web_qualification45.trimesh.load_mesh
        witnesses = {record['file']: record for record in web['witnesses'].values()}
        stored_volumes = {}
        def source_mesh(path, *args, **kwargs):
            path = Path(path)
            record = witnesses[path.name]
            native_source = witness_directory / record['source_mesh64']['file']
            assert digest(native_source) == record['source_mesh64']['sha256']
            stored_volumes[path.name] = float(original_load(path).volume)
            with np.load(native_source, allow_pickle=False) as source:
                return web_qualification45.trimesh.Trimesh(source['vertices'], source['faces'], process=False)
        with patch.object(web_qualification45.trimesh, 'load_mesh', side_effect=source_mesh):
            replacement = web_qualification45.inspect(checker, witness_directory, web, *fields)
        for name, row in replacement['witness_precision'].items():
            row['signed_source_mesh64_mm3'] = row.pop('signed_stl_mm3')
            row['stored_stl_signed_mm3'] = stored_volumes[web['witnesses'][name]['file']]
            row['source_mesh64_sha256'] = web['witnesses'][name]['source_mesh64']['sha256']
            row['measurement_basis'] = 'Complete pre-export CAD witness, preserved in double precision; no cropping to exported or deposited carrier.'
        result['qualified_r45_guard_replacement'] = replacement
        repair = json.loads((witness_directory / 'standing-repair.json').read_text())
        chamfer = {}
        for name, record in {'complete chamfer': repair['complete_added_witness'],
                             **repair['pre_union_bonds']}.items():
            path = witness_directory / record['file']
            assert digest(path) == record['sha256']
            shape = b.load(path)
            chamfer[name] = audit.supplemental_coverage(checker, shape, *fields)
        result['r45_chamfer_and_joints'] = chamfer
        result['r47_geometry_receipt_sha256'] = digest(source / 'r47-checks.json')
        result['r47_export_sha256'] = digest(source / 'R47-Key-Carrier-assembly.stl')
        result['physical_success_verified'] = False
        result['print_ready'] = False
        replaced = web_qualification45.LEGACY_WEB_TARGETS if replacement['qualified'] else set()
        material_ok = all(row['minimum_layer_fraction'] >= .9
            for name, row in result['critical_material'].items() if name not in replaced)
        brace_ok = all(row['minimum_layer_fraction'] >= .9
            for rows in braces.values() for name, row in rows.items() if name != 'cross_sections')
        sections_ok = all(row['coverage'] >= .9 and row['native_largest_connected_mm2'] >= np.pi * .95 ** 2
            for rows in braces.values() for row in rows['cross_sections'])
        starts = result['layer_starts']
        chamfer_ok = chamfer_gate(chamfer)
        landing_ok = all(row['coverage'] >= .9
            and row['native_largest_connected_mm2'] >= .9 * row['cad_area_mm2']
            for row in landing_sections)
        result['screen_passed'] = bool(material_ok and brace_ok and sections_ok and removable
            and replacement['qualified'] and chamfer_ok and landing_ok
            and not hard and not interference and not starts['floating_components']
            and not starts['missing_printed_components'])

    # A combined plate keeps the identical key/helper meshes at its own bed
    # translation. Use exactly their deposited beads, with the actual tower;
    # all other parts and inter-group separation are audited independently.
    engine = audit.common.load_checker()
    raw = list(engine.audit.read_project(archive))
    owner = audit.single44.previous.owners(archive)
    wanted = layout_owners(out)
    selected_owners = {name: owner[name] for name in wanted}
    names = np.asarray(raw[1])[raw[0][:, 5].astype(int)]
    mask = np.isin(raw[0][:, 6], list(selected_owners.values())) | (names == 'Prime tower')
    raw[0] = raw[0][mask]
    raw[5] = {name: raw[5][name] for name in wanted}
    with patch.object(audit.common, 'load_checker', return_value=engine), \
         patch.object(engine.audit, 'read_project', return_value=tuple(raw)), \
         patch.object(audit.single44.previous, 'owners', return_value=selected_owners), \
         patch.object(audit.prior, 'routes', routes), \
         patch.object(audit.prior.full, 'precision_support_spaces', precision), \
         patch.object(audit, 'evaluate_material', evaluate):
        if resume_material:
            proof = json.loads((out / 'pre-material-inputs.json').read_text())
            result = json.loads((out / 'candidate-audit.json').read_text())
            assert proof['archive_sha256'] == result['archive_sha256'] == digest(archive)
            assert all(digest(out / name) == sha for name, sha in proof['files'].items())
            assert all(digest(plate47.R45 / name) == sha for name, sha in proof['r45_checker_source_sha256'].items())
            reference = scratch / 'parent-audit-targets/R47-source-recheck.stl'
            b.save(reference, model)
            assert digest(reference) == proof['stage_carrier_sha256']
            assert not result['unacceptable_route_obstructions']
            checker = engine.audit
            data, features, _, _, offset, objects = raw[:6]
            xyz = data[:, :3] + offset - layout_frame['bed_translation']
            labels = np.asarray(features)[data[:, 5].astype(int)]
            carrier = (data[:, 6] == selected_owners['Key_Carrier']) & audit.common.model_mask(labels)
            object = objects['Key_Carrier']
            actual = checker.q.solid(object['vertices'] - layout_frame['bed_translation'], object['faces'])
            removable = (result['whole_bead_release']['clear'] and result['whole_shelf_bead_release']['clear']
                         and result['whole_rear_shelf_bead_release']['clear'] and result['individual_front_piece_release']['clear']
                         and not result['whole_rib_downward_release']['colliding_helper_slices'])
            evaluate(result, out, frame, None, actual, None, xyz, carrier, data, engine, checker,
                     [], [], removable)
            result['pre_material_input_proof_sha256'] = digest(out / 'pre-material-inputs.json')
            (out / 'candidate-audit.json').write_text(json.dumps(result, indent=2) + '\n')
        else:
            audit.check(archive)


if __name__ == '__main__':
    check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
