#!/usr/bin/env python3
"""Focused R22 checks: fast assertions on the source parameters, the exported files and the recorded checks.
Run through the repository geometry runner after holder22/verify22/assembly22. No geometry kernel jobs beyond
light path sampling; the heavy checks live in verify22.py and are read back here."""
import sys
sys.dont_write_bytecode = True
import json, math, unittest
import numpy as np
import holder22 as h

OUT = h.HERE / 'exports'


def load(name): return json.loads((OUT / name).read_text())


class Parameters(unittest.TestCase):
    def test_shoulder_prints_at_45_degrees_or_less(self):
        self.assertLess(h.shoulder_max_slope(), 1.)
        s = h.P['slab']; self.assertAlmostEqual(float(h.shoulder_x(s['lower_rear_y_mm'])), s['lower_half_x_mm'])
        self.assertAlmostEqual(float(h.shoulder_x(s['lower_rear_y_mm'] + h.K['shoulder_curve']['length_mm'])), s['upper_half_x_mm'])

    def test_one_row_parameter_moves_keys_rings_and_rear(self):
        self.assertAlmostEqual(h.P['keys']['row_spacing'], h.K['r16_row_spacing_mm'] - h.SHIFT)
        self.assertAlmostEqual(h.P['slab']['rear_y_mm'], 26.9 - h.SHIFT)
        self.assertAlmostEqual(h.P['carrier_rings']['rear_band_y_mm'][1], h.REAR)
        self.assertEqual(h.base.key_positions()[3][1], h.P['keys']['row_spacing'])

    def test_runners_obey_45_degrees(self):
        for b in h.G['beams']:
            ys = np.arange(b['root_y_mm'], -9, -.1); prev = None
            for y in ys:
                p = h.beam_path(b, float(y))
                if p is None: continue
                x, sx, z, sz = p; self.assertLessEqual(abs(sx), h.G['max_plan_slope'] + 1e-9, b['name']); self.assertLessEqual(abs(sz), 1 + 1e-9, b['name'])
                if prev: self.assertLessEqual(math.hypot(x - prev[0], z - prev[1]), .1 * 1.001 + 1e-9, (b['name'], y))
                prev = (x, z)

    def test_cable_layout_is_feasible(self):
        c = h.wire_centres(); r = h.C['conductor_od_mm'] / 2; cx = h.C['centres_mm']
        self.assertEqual(len(c), h.C['conductors'])
        self.assertGreaterEqual(min(math.dist(a, b) for i, a in enumerate(c) for b in c[i + 1:]), 2 * r - 1e-6)
        self.assertLessEqual(max(math.hypot(x - cx, y) for x, y in c) + r, h.C['cable_bore_mm'] / 2)
        self.assertGreater(h.C['cable_entry_gap_mm'], h.C['conductor_od_mm'])


class Exports(unittest.TestCase):
    def setUp(self):
        self.man = load('manifest.json')

    def test_every_plate_part_listed_exported_and_hashed(self):
        self.assertEqual(self.man['plate_parts'], h.PLATE)
        self.assertGreaterEqual(set(self.man['build_list']), set(h.PLATE))
        for n in h.PLATE:
            self.assertEqual(h.sha(OUT / (n + '-SOURCE-REQUIRES-PREPARATION.stl')), self.man['parts'][n]['stl_sha256'], n)
        for n in h.ANCHORED: self.assertTrue((OUT / (n + '-ANCHOR-REMOVE-AFTER-PRINT.stl')).exists(), n)

    def test_reused_parts_are_byte_identical(self):
        for n in h.COPIED_R19: self.assertEqual(self.man['parts'][n]['stl_sha256'], json.loads((h.R19 / 'exports/manifest.json').read_text())['parts'][n]['stl_sha256'], n)
        for n in h.COPIED_R20: self.assertEqual(self.man['parts'][n]['stl_sha256'], json.loads((h.R20 / 'exports/manifest.json').read_text())['parts'][n]['stl_sha256'], n)
        self.assertIn('XIAO_Near_Keeper', h.PLATE); self.assertIn('ORIGINAL-COMPATIBLE', self.man['build_list']['XIAO_Near_Keeper'])
        self.assertTrue({'Battery_End_Door', 'Battery_End_Door_Easy_Trial'} <= set(h.PLATE))


class RecordedChecks(unittest.TestCase):
    def setUp(self):
        self.r = load('geometry-checks.json')

    def test_checks_match_current_source(self):
        self.assertEqual(self.r['holder22_sha256'], h.sha(h.HERE / 'holder22.py')); self.assertEqual(self.r['parameters_sha256'], h.sha(h.HERE / 'parameters.json'))

    def test_key_holder(self):
        k = self.r['key_carrier']; self.assertEqual(k['bodies'], 1)
        for i in range(5): self.assertLess(k['routes'][f'key_{i}']['max_overlap_mm3'], .005, i)
        for n, v in k['runners'].items():
            self.assertFalse(v['layers_with_no_runner_section_y_mm'], n); self.assertGreaterEqual(v['min_free_thickness_mm'], 1.2, n)
            self.assertGreaterEqual(v['rear_root_bond_layers'], 5, n); self.assertGreaterEqual(v['front_root_bond_layers'], 5, n)
        self.assertFalse([n for n, v in k['seated_runner_overlaps_mm3'].items() if v > .005])
        self.assertLess(self.r['exports']['Key_Carrier']['export_vs_source_drift_mm3'], .02)

    def test_battery_doors_seat_and_lead_in_helps(self):
        b = self.r['battery']
        for d in ('Battery_End_Door', 'Battery_End_Door_Easy_Trial'):
            self.assertLess(b[f'{d}_into_R22']['seated_overlap_mm3'], .005)
            self.assertLessEqual(b[f'{d}_into_R22']['max_overlap_mm3'], b[f'{d}_into_R20']['max_overlap_mm3'])
        self.assertLess(b['Battery_End_Door_Easy_Trial_into_R22']['max_overlap_mm3'], b['Battery_End_Door_into_R22']['max_overlap_mm3'])
        self.assertFalse([n for n, v in b['working_spaces_overlap_mm3'].items() if v > .005])

    def test_cable_clip(self):
        c = self.r['cable_clip']; self.assertTrue(c['all_wires_inside_bore']); self.assertGreaterEqual(min(c['each_wire_clearance_to_plastic_mm']), .4); self.assertGreater(c['slit_minus_wire_od_mm'], 0)


class Guide(unittest.TestCase):
    def test_schema2(self):
        g = load('assembly-guide.json'); self.assertEqual(g['schema_version'], 2); self.assertEqual(set(g['modules']), {'key', 'xiao', 'battery', 'cable'})
        for name, m in g['modules'].items():
            for st in m['steps']:
                self.assertTrue(st['title'] and st['caption'] and st['duration'] > 0)
                for s in st['samples']:
                    for a in m['actors']: self.assertEqual(len(s[a]), 12, (name, a))
            for a, rec in m['actors'].items(): self.assertTrue((OUT / rec['file']).exists(), rec['file'])
        self.assertEqual(g['sources']['assembly_mesh_sha256']['Key_Carrier'], h.sha(OUT / 'Key_Carrier-assembly.stl'))


if __name__ == '__main__':
    unittest.main(verbosity=1)
