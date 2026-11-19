"""Release the six separately based parts only after checking both native slices."""
import json
from pathlib import Path
import sys
from plate52 import digest
from release_accessories52 import package
from wide_accessories52 import POSITIONS


def release(selected, reopened):
    checks=[]
    for folder in (selected,reopened):
        result=json.loads((folder/'wide-bases.json').read_text())
        assert result['native_sha256']==digest(folder/'Wide-accessories.gcode.3mf')
        assert result['layout_sha256']==digest(folder/'layout.3mf')
        assert json.loads((folder/'separation-and-machine.json').read_text())['archive_sha256']==result['native_sha256']
        assert not json.loads((folder/'Wide-accessories.gcode.native.json').read_text())['plates'][0]['warning_message']
        checks.append(result)
    a,b=checks
    assert a['layout_sha256']==b['layout_sha256'] and set(a['parts'])==set(b['parts'])==set(POSITIONS)
    for name in POSITIONS:
        for source,repeat in zip(a['parts'][name],b['parts'][name],strict=True):
            assert source['layer']==repeat['layer']
            assert abs(source['connected_material_mm2']-repeat['connected_material_mm2']) < 3
            assert not source['unconnected_material'] and not repeat['unconnected_material']
            assert len(source['tie_widths_mm'])==len(repeat['tie_widths_mm'])==2
    assert max(abs(x-y) for x,y in zip(a['lid_window_minimum_clear_radii_mm'],b['lid_window_minimum_clear_radii_mm'])) < .15
    (selected/'reopened.json').write_text(json.dumps(b,indent=2)+'\n')
    package(selected/'Wide-accessories.gcode.3mf',selected/'Magic-Wand-R52-Six-Wide-Base-Accessories-print-only.3mf',
            set(POSITIONS),[selected/f for f in ('base-cuts.json','wide-bases.json','reopened.json','separation-and-machine.json')])


if __name__=='__main__':release(*map(Path,sys.argv[1:3]))
