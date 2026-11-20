"""Independent native checks for the whole kit, heater commands, and clip separation."""
import itertools
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import sys
from zipfile import ZipFile

import numpy as np

from plate52 import EXTRAS, PROJECT, OLD_PLATE
from sockets52 import paths
from orient51 import digest
from plate38 import command_audit


def audit(archive, layout, output, expected=None):
    with ZipFile(archive) as src:
        objects=ET.fromstring(src.read('Metadata/slice_info.config')).find('plate').findall('object')
        owners={o.get('name'):int(o.get('identify_id')) for o in objects}
        gcode=src.read('Metadata/plate_1.gcode').decode()
    if expected is None:expected={'Key_Carrier','DFRobot_Hole_Bracket','Battery_End_Door',*EXTRAS}
    assert set(owners)==set(expected),owners
    with ZipFile(layout) as src:
        cfg=json.loads(src.read(PROJECT))
    verified=command_audit(archive,cfg)
    assert verified['passed'] and verified['first_object_nozzle_target_c']==245 and verified['first_object_bed_target_c']==60
    assert verified['ending_heater_targets_c']==[0,0]
    data,features,_=paths.extrusion_points(gcode,.20)
    include=[i for i,label in enumerate(features) if not label.startswith(('Support','Prime tower','Skirt','Brim'))]
    normal=np.isin(data[:,5],include)
    footprints={}
    for name,owner in owners.items():
        printed=data[normal] if len(owners) == 1 else data[normal & (data[:,6]==owner)]
        assert len(printed) and (printed[:,7] <= .201).any(),name
        xy=printed[:,:2];rad=printed[:,3:4]*.5+.10
        footprints[name]=np.stack([(xy-rad).min(0),(xy+rad).max(0)])
    gaps={}
    for first,second in itertools.combinations(footprints,2):
        a,b=footprints[first],footprints[second]
        delta=np.maximum(0,np.maximum(a[0]-b[1],b[0]-a[1]))
        gap=round(float(np.linalg.norm(delta)),3)
        gaps[first+' / '+second]=gap
    assert all(gap > 1.0 for gap in gaps.values()), gaps
    minimum_gap = min(gaps.values(), default=None)
    report={'archive_sha256':digest(archive),'layout_sha256':digest(layout),'parts':list(owners),
            'minimum_separation_mm':minimum_gap,'projected_part_separation_lower_bounds_mm':gaps,
            'machine':verified,'filament_retraction_mm':cfg['filament_retraction_length'],
            'filament_retraction_speed_mm_s':cfg['filament_retraction_speed'],
            'timelapse_type':cfg['timelapse_type']}
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(len(owners), 'parts;', minimum_gap, 'mm minimum normal path gap' if gaps else '(single part)')


if __name__=='__main__':
    audit(*map(Path,sys.argv[1:4]))
