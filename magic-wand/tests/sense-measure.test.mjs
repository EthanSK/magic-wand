import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

test('passive measurement excludes idle/session/sequence boundaries and understands merged frames',()=>{
 const module=fileURLToPath(new URL('../hardware/xiao-wand-dashboard/measure.py',import.meta.url));
 const code=`import importlib.util,json,sys
s=importlib.util.spec_from_file_location('measure',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def row(seq,ms,session=1,active=True,flags=None,count=1,first=None):
 p={'seq':seq,'ms':ms,'sampleCount':count,'imu':{'gx':0,'gy':0,'gz':1,'ax':0,'ay':0,'az':1} if active else None}
 if flags is not None:p['imuFlags']=flags
 if first is not None:p['firstMicros']=first
 return {'packet':p,'session':session,'transport':'Bluetooth','poll':ms/1000+1,'age_ms':0}
r=m.report([row(1,10),row(2,20),row(3,30,active=False),row(4,600),row(5,900,session=2),row(7,950,session=2)],10)
assert r['estimatedMissingReadingsPercent']==0,r
r=m.report([row(1,10),row(2,40)],10);assert r['estimatedMissingReadingsPercent']==50,r
r=m.report([row(1,10),row(2,40,count=3,first=20000)],10);assert r['estimatedMissingReadingsPercent']==0,r
z=row(1,10,flags=3);z['packet']['imu']['gz']=0
assert m.report([z],10)['activeFrames']==1
json.dumps(m.report([z],10),allow_nan=False)
assert m.report([row(1,10,active=False)],10)['activeFrames']==0
print('measurement boundaries passed')`;
 const r=spawnSync('python3',['-I','-c',code,module],{encoding:'utf8'});
 assert.equal(r.status,0,r.stdout+r.stderr);
});
