"""Run independent machine checks against the selected immutable native archive."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
import json,sys
r=Path(__file__).resolve().parent
sys.path.insert(0,str(r))
from plate53 import LABELS
from parts52 import audit
from adhesion53 import bases, verify
from part_map53 import generate
from openings53 import read_native
import numpy as np
s,meshes=map(Path,sys.argv[1:3])
a=s/'OP1-hinge.gcode.3mf'; layout=s/'layout.3mf'; frame=s/'layout.frame.json'
report=json.loads(a.with_suffix('.native.json').read_text())
assert report['archive_sha256']==sha256(a.read_bytes()).hexdigest()
assert report['return_code']==0
# Preserve the native warning for independent review along with all physical path checks.
log=(s/'native/slice.log').read_text()
assert 'got warnings:' not in log, log[-900:]
audit(a,layout,s/'separation-and-machine.json',set(LABELS))
wide=s/'wide-bases.json'
w=json.loads(wide.read_text()) if wide.exists() else {}
if w.get('archive_sha256') != report['archive_sha256']:
    w=bases(a)
    wide.write_text(json.dumps(w,indent=2)+'\n')
verify(w)
generate(a,frame,meshes,LABELS,s/'tray.png')
# Source rod lies along assembly Y and therefore stands vertically in this print.
f=np.array(json.loads(frame.read_text())['parts']['Key_Carrier']['assembly_to_machine'])
assert np.allclose(abs(f[:3,1]),[0,0,1]);d,l=read_native(a)
near=d[np.linalg.norm(d[:,:2]-f[:2,3],axis=1)<8]
rr=np.linalg.norm(near[:,:2]-f[:2,3],axis=1)-near[:,3]/2-.06
used=np.array([n.startswith(('Support','Brim','Skirt')) for n in l])[near[:,5].astype(int)]
rec=dict(archive_sha256=report['archive_sha256'],axis_mm=f[:2,3].tolist(),checked_samples=len(rr),min_radius_mm=float(rr.min()),working_rod_mm=8.0,temporary_plastic_in_rod=int((used&(rr<4.)).sum()),model_contact_layers=[float(z) for z in np.unique(np.round(near[~used & (rr<4.),7],2))])
(s/'rod.json').write_text(json.dumps(rec,indent=2)+'\n')
assert len(rr)>1000 and not rec['temporary_plastic_in_rod']
print(rec['min_radius_mm'],len(rec['model_contact_layers']),flush=True)
