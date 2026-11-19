"""Compare a reopened recovery layout and package the selected native machine instructions."""
from pathlib import Path
from hashlib import sha256
import json
import sys
from zipfile import ZipFile
from release_accessories52 import package

def release(final, repeat):
    name='Battery-recovery.gcode.3mf'
    checks=[json.loads((d/'checks.json').read_text()) for d in (final,repeat)]
    hashes=[c.pop('archive_sha256') for c in checks]
    assert checks[0]==checks[1]
    checked=checks[0]
    bridge=checked['floor_backing']
    assert bridge['long_straight_moves'] and bridge['maximum_unbacked_run_mm'] <= 3.0
    assert bridge['maximum_long_move_angle_from_cross_tray_degrees'] <= 1.0
    assert not checked['completely_floating_islands'] and not checked['automatic_support_samples']
    assert not checked['shared_pull_rail_and_body_extrusion_sequences']
    assert not checked['removable_native_bead_samples_in_8mm_rod_bore']
    assert not checked['cell_core_positive_samples_after_rail_removal'] and not checked['lid_guide_core_samples']
    assert checked['canonical_hardware']['passed'] and checked['bed_area_mm2']['outside_feet'] > 400

    body,insert=checked['first_layer_connected_groups']
    assert body['bed_ears']==6 and body['includes_outer_rim'] and body['area_mm2'] > 500
    assert insert['bed_ears']==0 and not insert['includes_outer_rim']

    commands=[]
    for folder,expected in zip((final,repeat),hashes):
        arch=folder/name
        assert sha256(arch.read_bytes()).hexdigest()==expected
        with ZipFile(arch) as z:
            lines=z.read('Metadata/plate_1.gcode').splitlines()
        commands.append([s.split(b';')[0].strip() for s in lines if s.startswith((b'G0 ',b'G1 ',b'G2 ',b'G3 ')) and b' E' in s.split(b';')[0]])
    from difflib import SequenceMatcher
    edits=[dict(kind=k,original=[i,j],repeat=[a,b]) for k,i,j,a,b in SequenceMatcher(None,*commands,autojunk=False).get_opcodes() if k!='equal']
    report=final/'reopened.json'
    report.write_text(json.dumps(dict(native_sha256=hashes[0],repeat_sha256=hashes[1],original_commands=len(commands[0]),repeat_commands=len(commands[1]),gcode_command_differences=edits,same_hardware_and_slice_checks=True),indent=2)+'\n')
    package(final/name,final/'Magic-Wand-R52-Battery-Crosswise-print-only.3mf',{'Battery_Holder'},[final/'checks.json',report])

if __name__=='__main__':release(*map(Path,sys.argv[1:3]))
