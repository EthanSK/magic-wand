#!/usr/bin/env python3
"""Regressions for the interfaces R20 changes. Geometry only; run with the CAD Python:

    <cad-python> -B -m unittest discover -s magic-wand/hardware/carbon-rod-holders-r20-finger-guard -p test_holder20.py -v
"""
import sys
sys.dont_write_bytecode = True
import json, math, unittest
import holder20 as h

base = h.base; h19 = h.h19
def sd(a, b): return float((a - b).volume() + (b - a).volume())
def ov(a, b): return max(0., float((a ^ b).volume()))


class RingFunctions(unittest.TestCase):
    def test_parameterised_ring_is_the_r7_ring_at_30_degrees(self):
        gap = h.ROD['clip_gap_degrees']; self.assertLess(sd(h.clip_ring(9.0, 12.6, gap, h.ROD['clip_root_wall']), base.ring(10.8, None, 3.6)), 1e-6)

    def test_parameterised_lead_in_is_the_r16_one(self):
        a = h.P['arrow_ring']; k = 1 / math.tan(math.radians(a['lead_angle_degrees']))
        mine, lead = h.clip_skirt(9.0, 12.6, +1, h.ROD['clip_gap_degrees'], h.ROD['clip_root_wall'], a['root_phi_degrees_above_equator'], k, a['skin_thickness_mm'])
        theirs, length = base.arc_skirt(9.0, 12.6, +1, 3.6, h.ROD['clip_root_wall'], a['root_phi_degrees_above_equator'], k, a['skin_thickness_mm'])
        self.assertLess(sd(mine, theirs), 1e-6); self.assertAlmostEqual(lead, k * length, places=6)


class KeyHolder(unittest.TestCase):
    def test_build_with_r16_values_is_the_accepted_r16_solid(self):
        self.assertLess(sd(h.key_carrier_build(h.K20['r16_ring_bore_mm'], False), base.carrier()), 1e-6)

    def test_changes_are_only_rings_and_windows(self):
        new, old = h.key_carrier(), base.carrier(); c = h.P['carrier_rings']
        rings = h.cyl(6.0, c['mid_band_y_mm'][0] - .3, c['rear_band_y_mm'][1] + .3).rotate((-90, 0, 0)) ^ h.box(-7, 7, -10, 40, -7, base.slab_bottom() + 1.05)
        self.assertLess(float(((old - new) - h.key_windows() - rings).volume()), .01); self.assertLess(float(((new - old) - rings).volume()), .01)

    def test_bore_is_tighter_here_only_and_every_bought_space_is_clear(self):
        new = h.key_carrier(); self.assertEqual(h.ROD['clip_diameter'], 7.9); self.assertLess(h.K20['ring_bore_mm'], h.ROD['clip_diameter'])
        for name, region in h.part_regions('Key_Carrier').items():
            worst = max(ov(new, p) for p in region.poses()) if isinstance(region, h.spaces16.Swept) else ov(new, region); self.assertLess(worst, .002, name)


class BatteryHolder(unittest.TestCase):
    def test_r19_parameters_and_solid_are_untouched_after_the_r20_build(self):
        before = (list(h19.B19['plate_y_mm']), list(h19.CAGE['far_band_y_mm'])); new = h.battery_module()
        self.assertEqual((h19.B19['plate_y_mm'], h19.CAGE['far_band_y_mm']), before)
        record = json.loads((h.R19 / 'exports/manifest.json').read_text())['parts']['Battery_Holder']; self.assertAlmostEqual(h19.battery_module().volume(), record['volume_mm3'], places=3)
        self.assertAlmostEqual(new.bounding_box()[4], h.B20['plate_y_mm'][1], places=6)

    def test_cell_bay_is_r19_and_the_end_frame_stops_the_cell(self):
        new, old = h.battery_module(), h19.battery_module(); cut = lambda s: s ^ h.box(-40, 40, -30, h.B20['far_band_y_mm'][0] - .6, -20, 40)
        self.assertLess(sd(cut(new), cut(old)), .01); self.assertLess(ov(new, base.cell_shape(True)), .002); self.assertGreater(ov(new, base.cell_shape(True).translate((0, .6, 0))), .05)


class XiaoHolder(unittest.TestCase):
    def test_nothing_is_removed_and_the_board_seats_between_walls_and_cheeks(self):
        new, old = h.sensor_holder(), h19.sensor_holder(); self.assertLess(float((old - new).volume()), 1e-6)
        self.assertLess(ov(new, h19.board_outline()), .002); self.assertLess(ov(new, h19.board_outline(.25, 0.)), .002); self.assertGreater(ov(new, h19.board_outline(.45, 0.)), .01)
        self.assertLess(ov(new, h19.keeper()), .002)
        for name, region in h.part_regions('XIAO_Rod_Holder').items():
            worst = max(ov(new, p) for p in region.poses()) if isinstance(region, h.spaces16.Swept) else ov(new, region); self.assertLess(worst, .002, name)


class FingerGuard(unittest.TestCase):
    def test_whole_layers_one_body_and_own_spaces_clear(self):
        g = h.guard(); self.assertAlmostEqual(h.layer_count() * h.G['layer_mm'], h.G['y_rear_mm'] - h.G['y_front_mm'], places=9); self.assertEqual(len(g.decompose()), 1)
        for name, region in h.guard_spaces().items(): self.assertLess(ov(g, region), .002, name)

    def test_seats_on_both_key_holders_with_the_stated_pad_gap(self):
        g = h.guard()
        for holder in (h.key_carrier(), h.carrier_r16()):
            self.assertLess(ov(g, holder), .002); self.assertAlmostEqual(float(g.min_gap(holder, 3.)), h.G['prop_tab']['gap_to_key_holder_mm'], delta=.02)
        for name, part in {**h.bought_parts(), **h.contact_envelopes()}.items(): self.assertLess(ov(g, part), .002, name)

    def test_slides_on_from_the_hand_side(self):
        g = h.guard(); obstacles = h.union([h.key_carrier(), *h.bought_parts().values(), *h.contact_envelopes().values()])
        for d in (1., 3., 6., 9., 12., 15., 18.): self.assertLess(ov(g.translate((0, -d, 0)), obstacles), .002, d)


class LoadPaths(unittest.TestCase):
    """The two paths the independent review questioned, member by member on the source solids."""
    def test_guard_rims_tie_gunwale_to_keel_and_rails_keep_their_section(self):
        import members20 as m
        solid = h.guard().rotate((90, 0, 0)); facts = m.guard_members(lambda y: solid.slice(y), m.layer_ys(h.G['y_front_mm'], h.G['y_rear_mm'])); m.assert_guard(facts)
        self.assertGreaterEqual(min(facts['rim_height_at_each_bay_centre_mm']['rear'].values()), 1.8 - 1e-6)

    def test_key_holder_lower_row_is_r16_and_no_layer_is_weaker_than_r16s_weakest(self):
        import members20 as m
        s = h.P['slab']; ys = m.layer_ys(s['front_y_mm'], s['rear_y_mm']); new = h.key_carrier().rotate((90, 0, 0)); old = base.carrier().rotate((90, 0, 0))
        facts = m.key_compare(m.key_layers(lambda y: new.slice(y), ys), m.key_layers(lambda y: old.slice(y), ys)); m.assert_key(facts)
        self.assertEqual(facts['lower_row_board_level']['largest_area_loss_mm2'], 0.)


class Exports(unittest.TestCase):
    def test_exported_meshes_are_the_manifest_ones(self):
        out = h.HERE / 'exports'; manifest = json.loads((out / 'manifest.json').read_text())
        self.assertEqual(manifest['plate_parts'], h.PARTS); self.assertEqual(manifest['source_sha256']['holder20.py'], h.sha(h.HERE / 'holder20.py')); self.assertEqual(manifest['source_sha256']['parameters.json'], h.sha(h.HERE / 'parameters.json'))
        for name in h.PARTS: self.assertEqual(h.sha(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')), manifest['parts'][name]['stl_sha256'], name)


if __name__ == '__main__':
    unittest.main()
