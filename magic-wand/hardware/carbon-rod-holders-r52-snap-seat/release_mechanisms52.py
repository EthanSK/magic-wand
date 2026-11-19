"""Package the audited carrier and paddle, checking the exact source of each result."""
import json
from pathlib import Path
import sys

from release_accessories52 import package
from orient51 import digest

PARTS = {'DFRobot_Hole_Bracket', 'Key_Carrier'}
OPENINGS = ('mount_opening', 'switch', 'socket', 'maximum_socket')
REMOVABLE = ('Exterior cradle / ', 'Support', 'Brim')


def release(directory):
    archive = directory / 'Mechanisms.gcode.3mf'
    layout = directory / 'layout.3mf'
    archive_hash = digest(archive)
    frame_hash = digest(directory / 'layout.frame.json')
    paths = {}

    def report(name, source=directory):
        path = source / (name + '.json')
        paths[name] = path
        return json.loads(path.read_text())

    frame = report('layout.frame')
    assert frame['layout_sha256'] == digest(layout)
    native = report('Mechanisms.gcode.native')
    assert native['return_code'] == 0 and not native['plates'][0]['warning_message']
    walls = report('roofs')
    sockets = report('sockets')
    removal = report('removal')
    separation = report('separation-and-machine')
    rod = report('rod-passage')
    springs = report('spring-paths')
    fixture = report('op1-spring-fixture')
    wire = report('op1-wire-passage')
    bases = report('wide-bases')
    for data in (native, walls, sockets, removal, separation, rod, springs, fixture, wire, bases):
        assert data['archive_sha256'] == archive_hash
    for data in (walls, sockets, rod, wire):
        assert data['frame_sha256'] == frame_hash

    assert set(walls['parts']) == set(frame['parts']) == set(separation['parts']) == PARTS
    assert separation['machine']['passed'] and separation['minimum_separation_mm'] > 1
    mechanics = report('mechanical-fit', directory.parent)
    contact = report('contact-misalignment', directory.parent)
    assert mechanics['passes'] and contact['passes']
    for part, features in walls['parts'].items():
        mesh_hash = digest(directory.parent / (part + '-assembly.stl'))
        assert features['source_sha256'] == frame['parts'][part]['source_sha256'] == mesh_hash
        assert mechanics['checked_mesh_sha256'][part] == mesh_hash
        base = bases['parts'][part]
        assert base['all_roots_connected']
        assert len(base['root_component_ids']) >= (13 if part == 'Key_Carrier' else 3)
        assert base['native_area_inside_removable_plate_outlines_mm2'] >= 2849
        assert base['same_component_area_mm2'] >= base['native_area_inside_removable_plate_outlines_mm2']
        assert not features['completely_unrooted_model_islands']
        protected = dict(features['protected_support'])
        if part == 'Key_Carrier':
            assert wire['carrier_sha256'] == mesh_hash
            projected = protected.pop('wire_core_bead_samples')
            assert projected == wire['projected_support_samples'] == wire['samples_on_removable_fixture']
            assert wire['minimum_fixture_surface_z_mm'] > wire['carrier_collar_z_mm'][1]
            assert wire['finite_passage_support_samples'] == wire['finite_passage_permanent_samples'] == 0
            pull = removal['spring_fixture']
            assert pull['snip_locations'] == len(fixture['positive_fixture_contacts'])
            assert pull['withdrawal_machine_xyz_mm'] == fixture['fixture_pull_machine_mm'] == [0, 60, 0]
            assert max(pull['carrier_overlap_after_cut_mm3'], pull['other_prop_overlap_during_pull_mm3']) < .001
        assert not any(protected.values())
        bore = features['bearing_space']
        assert bore['conservative_native_radius_mm'] >= bore['hardware_radius_mm']
    assert contact['paddle_hash'] == mechanics['checked_mesh_sha256']['DFRobot_Hole_Bracket']

    assert sockets['mode'] == 'complete insertion and removal'
    for key in (0, 2, 3, 4):
        for opening in OPENINGS:
            result = sockets['routes'][f'key_{key}_{opening}']
            assert result['checked'] > 0 and not result['obstructed_poses'], (key, opening)
    for name, route in sockets['routes'].items():
        # Props can intersect an external approach before they are peeled off.
        assert all(kind.startswith(REMOVABLE) for kind in route['worst_per_feature']), name
    assert not rod['support_or_brim_in_passage']
    assert not rod['new_model_contact_layers_mm'] and rod['relative_to_reference_min_radius_mm'] >= 0
    assert len(springs['leaves']) == 2
    for leaf in springs['leaves']:
        assert leaf['travel_mm'] >= mechanics['lift_mm'] > 0 and leaf['poses'] >= 2
        sweep = leaf['fixed_material_in_lift']
        assert sweep['checked_samples'] and not sweep['violations']
    assert fixture['carrier_sha256'] == mechanics['checked_mesh_sha256']['Key_Carrier']
    assert len(fixture['working_arm_slits']) == 2
    assert min(a['min_gap_mm_z'][0] for a in fixture['working_arm_slits']) >= 0.35
    assert len(fixture['positive_fixture_contacts']) >= 2
    assert all(c['positive_neck_samples'] and c['leaf_samples'] and
               c['minimum_xy_bead_gap_same_or_adjacent_layer_mm'] <= 0
               for c in fixture['positive_fixture_contacts'])
    assert not fixture['bay_islands_without_positive_material_below']
    assert fixture['fixture_pull_extra_interference_mm3'] < 0.001
    assert not removal['blocked'] and removal['long_props'] == len(removal['pull_order'])
    assert all(pull['model_collision_mm3'] < 0.001 for pull in removal['pull_order'])
    assert all(area['fine']['unreachable_sample_count'] == 0 for area in removal['native_support_openings'].values())
    return package(archive, directory / 'Magic-Wand-R52-Wide-Base-Key-Carrier-and-Paddle-print-only.3mf',
                   PARTS, paths.values())


if __name__ == '__main__':
    release(Path(sys.argv[1]))
