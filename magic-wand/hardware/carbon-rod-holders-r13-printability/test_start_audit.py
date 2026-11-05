#!/usr/bin/env python3
"""Regression cases for false support credit and float32 boundary layers."""
import io,json,unittest
from pathlib import Path
import numpy as np
import cad,start_audit
from verify_slice import q

class StartAuditRegression(unittest.TestCase):
    def inspect(self,mesh,points,tops,features):
        return start_audit.inspect(q,mesh,np.array(points,float),np.full(len(points),.2),np.array(features),
                                   ['Outer wall','Support - actual test backing'],np.array(tops,float),np.eye(4),np.full(len(points),.42))
    def floor(self):return cad.box(0,10,0,2,1.41,1.81)
    def test_one_empty_layer_with_direct_bead_is_backed(self):
        result=self.inspect(self.floor(),[[5,1,1.6],[5,1,1.2]],[1.6,1.2],[0,1])
        self.assertFalse(result['floating_components']);self.assertEqual(result['support_backed_islands'][0]['actual_vertical_gap_mm'],.2)
    def test_two_empty_layers_are_not_credited(self):
        result=self.inspect(self.floor(),[[5,1,1.6],[5,1,1.]],[1.6,1.],[0,1])
        self.assertTrue(result['floating_components']);self.assertFalse(result['support_backed_islands'])
    def test_sideways_bead_is_not_direct_backing(self):
        result=self.inspect(self.floor(),[[5,1,1.6],[10.1,1,1.2]],[1.6,1.2],[0,1])
        self.assertTrue(result['floating_components'])
    def test_real_missing_floor_cannot_pass_from_neighbour_paths(self):
        mesh=self.floor()+cad.box(20,21,0,1,0,2)
        result=self.inspect(mesh,[[20.5,.5,1.6]],[1.6],[0])
        self.assertTrue(any(row['area_mm2']>19 for row in result['missing_printed_components']))
    def boundary_mesh(self):
        bottom=float(np.float32(1.5000002))
        return cad.box(0,10,0,2,bottom,1.9)+cad.box(20,21,0,1,0,2)
    def test_rounding_envelope_does_not_invent_unprinted_floor(self):
        result=self.inspect(self.boundary_mesh(),[[20.5,.5,1.6]],[1.6],[0])
        self.assertFalse(result['missing_printed_components'])
        self.assertFalse(any(row.get('area_mm2',0)>19 for row in result['floating_components']))
    def test_real_beads_resolve_boundary_plane_and_use_real_backing(self):
        grid=[[x,y,1.6]for x in [1,5,9]for y in [.3,1,1.7]]
        result=self.inspect(self.boundary_mesh(),[[20.5,.5,1.6]]+grid+[[5,1,1.2]],[1.6]*10+[1.2],[0]*10+[1])
        self.assertFalse(result['missing_printed_components'])
        self.assertTrue(any(row['area_mm2']>19 for row in result['support_backed_islands']))
    def test_one_corner_bead_does_not_invent_a_whole_boundary_face(self):
        result=self.inspect(self.boundary_mesh(),[[20.5,.5,1.6],[.1,.1,1.6],[5,1,1.2]],[1.6,1.6,1.2],[0,0,1])
        self.assertFalse(any(row.get('area_mm2',0)>19 for row in result['support_backed_islands']+result['floating_components']))
    def test_unprinted_sliver_cannot_back_next_layer_bar(self):
        mesh=cad.box(0,1,0,1,0,.8)+cad.box(0,10,0,1,.2,.6)
        bar=[[float(x),.5,.6]for x in np.arange(.2,9.81,.15)]
        result=self.inspect(mesh,[[.5,.5,.2],[.5,.5,.4]]+bar,[.2,.4]+[.6]*len(bar),[0]*(len(bar)+2))
        self.assertTrue(any(row['layer_top_mm']==.6 and row['unbacked_mesh_area_mm2']>2
                            and row['print_xy_bounds_mm'][2]>9 for row in result['partial_overhangs']))

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(StartAuditRegression))
    report={'checker_sha256':cad.sha(Path(start_audit.__file__)),'regressions_sha256':cad.sha(Path(__file__)),
            'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()}
    (cad.HERE/'exports/start-audit-regressions.json').write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful()else 1)
