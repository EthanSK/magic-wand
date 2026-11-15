"""Adversarial physical access fixtures for R42's support-removal check.

Run through geometry_budget.py with the same CAD runtime as audit42.py.
"""
import unittest
from pathlib import Path
import tempfile
from zipfile import ZipFile

import numpy as np

import audit42 as audit


class SupportRemovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = audit.common.load_checker().audit
        box = audit.d.box
        # An enclosed hollow cube has no cleanup route, even though its
        # interior air and the support both touch a probe's local XY bounds.
        cls.closed = box(0., 10., 0., 10., 0., 10.) - box(1., 9., 1., 9., 1., 9.)
        cls.open = cls.closed - box(-1., 11., -1., 2., 1., 9.)
        cls.local = np.asarray([(x, y, top) for top in np.arange(3.2, 7.21, .2)
                                for x in np.arange(3., 7.01, .5)
                                for y in np.arange(3., 7.01, .5)])
        cls.data = np.zeros((len(cls.local), 8))
        cls.data[:, :3] = cls.local
        cls.data[:, 3] = 1.0
        cls.data[:, 4] = .2
        cls.data[:, 7] = cls.local[:, 2]
        cls.support = np.ones(len(cls.local), dtype=bool)
        cls.model = ~cls.support

    def result(self, solid):
        return audit.support_removal_grid(solid, self.checker, self.data, self.local,
                                          self.model, self.support, {})

    def test_sealed_cavity_rejects_interior_boundary_as_exit(self):
        row = self.result(self.closed)
        self.assertGreater(row['support_core_cells'], 20)
        self.assertEqual(row['reachable_support_core_cells'], 0)
        self.assertFalse(row['passed'])

    def test_actual_open_side_reaches_support(self):
        row = self.result(self.open)
        self.assertGreater(row['support_core_cells'], 20)
        self.assertEqual(row['reachable_fraction'], 1.)
        self.assertTrue(row['passed'])

    def test_obstructed_support_stays_in_denominator(self):
        obstructed = self.open + audit.d.box(4.5, 5.5, 2., 8., 2., 8.)
        row = self.result(obstructed)
        self.assertLess(row['reachable_fraction'], .98)
        self.assertFalse(row['passed'])


class RoofBackingTests(unittest.TestCase):
    def setUp(self):
        self.checker = audit.common.load_checker().audit
        self.local = np.asarray([(x, y, z) for z in (.2, .4)
                                 for x in np.arange(0., 2.01, .2)
                                 for y in np.arange(0., 2.01, .2)])
        self.data = np.zeros((len(self.local), 8))
        self.data[:, 3:5] = (.45, .2)
        self.data[:, 7] = self.local[:, 2]
        self.model = np.ones(len(self.local), dtype=bool)
        self.bounds = ((-1., -1., .3), (8., 4., .5))

    def result(self, bounds=None):
        return audit.deposited_roof_backing(self.checker, self.data, self.local,
                                            self.model, bounds or self.bounds)

    def test_matching_actual_lower_beads_pass(self):
        self.assertTrue(self.result()['passed'])

    def test_shifted_roof_with_no_backing_fails(self):
        self.local[self.data[:, 7]>.3, 0] += 4.
        self.assertFalse(self.result()['passed'])

    def test_empty_region_fails(self):
        self.assertFalse(self.result(((10., 10., .3), (12., 12., .5)))['passed'])


class NativeSupportOwnershipTests(unittest.TestCase):
    def test_duplicate_gcode_owner_labels_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=Path(directory)/'duplicate-owners.3mf'
            with ZipFile(archive,'w') as target:
                target.writestr('Metadata/slice_info.config',
                    '<config><plate><object name="Key_Carrier" identify_id="2"/>'
                    '<object name="DFRobot_Hole_Bracket" identify_id="2"/></plate></config>')
            with self.assertRaises(AssertionError):
                audit.native_support_owners(archive)

    def test_support_from_an_unchecked_part_cannot_disappear_from_the_audit(self):
        frame=np.eye(4)
        frame[:3,:3]=((1.,0.,0.),(0.,0.,-1.),(0.,1.,0.))
        check=audit.make_support_check({'print_to_assembly':frame.tolist()},
             audit.d.box(0.,1.,0.,1.,0.,1.),{},
             {audit.d.CARRIER:2,audit.d.BRACKET:4})
        data=np.zeros((1,8));data[0,6]=99
        with self.assertRaisesRegex(AssertionError,'unaudited owner'):
            check(data,np.zeros((1,3)),np.asarray(['Support interface']),{},None,None)


class DepositedConnectivityTests(unittest.TestCase):
    def test_high_coverage_split_between_two_pieces_fails(self):
        goal=audit.common.rectangle((0.,0.,10.,1.))
        beads=audit.common.rectangle((0.,0.,4.8,1.))+audit.common.rectangle((5.2,0.,10.,1.))
        row=audit.connected_section(goal,beads)
        self.assertGreater(row['coverage_fraction'],.9)
        self.assertFalse(row['passed'])

    def test_actual_connection_outside_witness_is_retained(self):
        goal=audit.common.rectangle((0.,0.,10.,1.))
        beads=(audit.common.rectangle((0.,0.,4.8,1.))+audit.common.rectangle((5.2,0.,10.,1.))
               +audit.common.rectangle((4.7,.9,5.3,1.3)))
        self.assertTrue(audit.connected_section(goal,beads)['passed'])


class SeatMeasurementTests(unittest.TestCase):
    def test_floor_probe_detects_a_surface_above_the_expected_floor(self):
        # A floor-height probe must see a real protrusion, rather than
        # clipping it away at the same height its acceptance gate checks.
        d = audit.d
        bump = d.box(-.2, .2, 0., .4, 19., 19.26)
        row = d.seat_metrics(d.bracket() + bump)
        self.assertGreater(row['highest_fixed_floor_or_root_surface_mm'], d.FLOOR_TOP + .02)


if __name__ == '__main__':
    unittest.main()
