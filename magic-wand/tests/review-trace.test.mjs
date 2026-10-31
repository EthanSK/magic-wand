import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {chmodSync,statSync} from 'node:fs';
test('trace switch is local, opt-in and can be disabled without restarting',()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-trace-switch-'));
 const cli=new URL('../scripts/review_trace.py',import.meta.url).pathname;
 const run=(state)=>spawnSync('python3',[cli,'capture',state,'--support',dir],{encoding:'utf8'});
 try {
  assert.equal(JSON.parse(run('status').stdout).enabled,false);
  assert.equal(run('on').status,0);
  assert.equal(JSON.parse(run('status').stdout).enabled,true);
  const config=join(dir,'review-trace.json');assert.equal(statSync(config).mode & 0o777,0o600);
  const window=JSON.parse(readFileSync(config,'utf8'));
  assert(window.captureUntil>Date.now()/1000+590 && window.captureUntil<=Date.now()/1000+600);
  assert.equal(window.deleteAfter-window.captureUntil,7200);
  assert.deepEqual(JSON.parse(readFileSync(join(dir,'DebugReadings/capture-window.json'),'utf8')),window);
  chmodSync(config,0o666);assert.equal(JSON.parse(run('status').stdout).enabled,false);
  assert.equal(run('off').status,0);assert.equal(JSON.parse(run('status').stdout).enabled,false);
  assert.equal(JSON.parse(readFileSync(config,'utf8')).deleteAfter,window.deleteAfter);
 }finally{rmSync(dir,{recursive:true,force:true});}
});
test('review traces are private, bounded, optional and independent of input delivery',{skip:process.platform!=='darwin'},()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-review-trace.noindex-'));
 try {
  writeFileSync(join(dir,'main.swift'),readFileSync(new URL('./fixtures/review-trace-main.swift',import.meta.url)));
  const source=new URL('../receiver/Sources/WandReviewTrace.swift',import.meta.url).pathname;
  const built=spawnSync('swiftc',['-O',source,join(dir,'main.swift'),'-o',join(dir,'test')],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  const run=spawnSync(join(dir,'test'),[dir],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);
 }finally{rmSync(dir,{recursive:true,force:true});}
});
test('offline replay uses canonical review code and reports malformed input',{skip:process.platform!=='darwin'},()=>{
 const dir=mkdtempSync(join(tmpdir(),'wand-review-replay.noindex-'));
 try {
  const rows=[{schema:1,kind:'boundary',reason:'begin',t:1}];
  let x=0,y=-1,t=1;
  for(const [start,end,step] of [[-Math.PI/2,0,1],[0,-Math.PI/2,-1]]){
   for(let i=1;i<=30;i++){
    const a=start+(end-start)*i/30,xx=Math.cos(a),yy=Math.sin(a);t+=.03;
    rows.push({schema:1,kind:'input',t,dx:xx-x,dy:yy-y,eligible:true,step:i===30?step:0});x=xx;y=yy;
   }
  }
  // Counts, not exact synthetic event timing, are the contract here. A real
  // capture records exact step timing for the report's differences list.
  const path=join(dir,'trace.jsonl');writeFileSync(path,rows.map(r=>JSON.stringify(r)).join('\n')+'\nmalformed\n');
  const cli=new URL('../scripts/review_trace.py',import.meta.url).pathname;
  const run=spawnSync('python3',[cli,'replay',path],{encoding:'utf8'});assert.equal(run.status,0,run.stderr);
  const result=JSON.parse(run.stdout);assert.equal(result.inputPoints,60);
  assert.equal(result.recordedNext,1);assert.equal(result.recordedPrevious,1);
  assert.equal(result.replayedNext,1);assert.equal(result.replayedPrevious,1);
  assert.equal(result.malformedRecords,1);assert.equal(result.classifierSHA256.length,64);
 }finally{rmSync(dir,{recursive:true,force:true});}
});

test('private replay reports cannot enter another monorepo component', () => {
 const cli = new URL('../scripts/review_trace.py', import.meta.url).pathname;
 const code = `import runpy, sys, tempfile
from pathlib import Path
m = runpy.run_path(sys.argv[1], run_name='report_path_test')
resolve = m['report_target']
repo, component = m['REPOSITORY'], m['ROOT']
for target in [repo / 'docs/private-report.json', repo / 'control-stones/private-report.json', component / 'private-report.json']:
 try:
  resolve(target)
 except ValueError:
  pass
 else:
  raise AssertionError('public report path was accepted')
for target in [repo / 'work/report.json', component / 'work/report.json', Path(tempfile.gettempdir()) / 'wand-report.json']:
 assert resolve(target) == target.resolve()
print('Private report paths stay outside published sources')
`;
 const result = spawnSync('python3', ['-I', '-c', code, cli], {encoding:'utf8'});
 assert.equal(result.status, 0, result.stdout + result.stderr);
});
