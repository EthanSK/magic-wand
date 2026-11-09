#!/usr/bin/env python3
"""Regress the missing Bambu template and misleading PETG metadata before slicing or sending."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import project19


class MachineCommandsTest(unittest.TestCase):
    def test_includes_replace_inherited_fallback_but_child_values_win(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'machine').mkdir()
            profiles = {'base': {'name': 'base', 'machine_start_gcode': 'M109 S205', 'x': 1},
                        'template': {'name': 'template', 'machine_start_gcode': 'M109 S[nozzle_temperature_initial_layer]', 'x': 2},
                        'printer': {'name': 'printer', 'inherits': 'base', 'include': ['template'], 'x': 3}}
            for name, values in profiles.items():
                (root / 'machine' / (name + '.json')).write_text(json.dumps(values))
            with patch.object(project19, 'PROFILES', root):
                result = project19.resolve('machine', 'printer')
            self.assertEqual(result['name'], 'printer')
            self.assertEqual(result['x'], 3)
            self.assertEqual(result['machine_start_gcode'], profiles['template']['machine_start_gcode'])

    def audit(self, startup: str, body: str = ''):
        machine = {key: key for key in ('machine_start_gcode', 'machine_end_gcode', 'layer_change_gcode', 'time_lapse_gcode', 'change_filament_gcode')}
        expected = dict(printer_settings_id='test', nozzle_temperature_initial_layer=['255'], nozzle_temperature=['255'], textured_plate_temp_initial_layer=['70'])
        code = '; EXECUTABLE_BLOCK_START\n;===== machine: A1 mini =====\nM83\n' + startup + '\n; start printing object, unique label id: 2\n' + body + '\n; filament end gcode\nM104 S0\nM140 S0\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.gcode.3mf'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('Metadata/project_settings.config', json.dumps(machine))
                archive.writestr('Metadata/plate_1.gcode', code)
            with patch.object(project19, 'resolve', return_value=machine):
                return project19.command_audit(path, expected)

    def test_metadata_cannot_hide_205_degree_executable(self):
        with self.assertRaisesRegex(AssertionError, 'First object nozzle target'):
            self.audit('M190 S70\nM109 S205')

    def test_temperature_target_without_wait_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'No final unconditional wait'):
            self.audit('M190 S70\nM104 S255')

    def test_earlier_or_ams_only_wait_cannot_hide_wrong_final_wait(self):
        for early in ['M109 S255', 'M620 S0A\nM109 S255\nM621 S0A', 'M622 J1\nM109 S255\nM623']:
            with self.subTest(early=early), self.assertRaisesRegex(AssertionError, 'No final unconditional wait'):
                self.audit('M190 S70\n' + early + '\nM109 S205\nM104 S255')

    def test_gated_bed_wait_cannot_pass(self):
        with self.assertRaisesRegex(AssertionError, 'No final unconditional bed'):
            self.audit('M622 J1\nM190 S70\nM623\nM140 S70\nM109 S255')

    def test_cooling_after_wait_requires_another_wait(self):
        with self.assertRaisesRegex(AssertionError, 'changed after its final wait'):
            self.audit('M190 S70\nM109 S255\nM104 S205\nM104 S255')

    def test_bed_off_during_objects_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Unexpected bed change'):
            self.audit('M190 S70\nM109 S255', 'M140 S0')

    def test_absolute_extrusion_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'must stay relative'):
            self.audit('M190 S70\nM109 S255', 'M82')

    def test_later_wrong_temperature_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Unexpected nozzle change'):
            self.audit('M190 S70\nM109 S255', 'M104 S205')

    def test_correct_executable_and_shutdown_pass(self):
        self.assertTrue(self.audit('M190 S70\nM109 S255')['passed'])


if __name__ == '__main__':
    unittest.main()
