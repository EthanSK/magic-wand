// Execute the production experiment mode boundary with inert state. V1/Puck
// must retain automatic clicks; requested changes wait for the current hold.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

test('manual mode supports Sense V2/V3, preserves V1/Puck clicks and reports deferred requests accurately', {skip:process.platform!=='darwin'},()=>{
 const root=new URL('../receiver/Sources/',import.meta.url);
 const source=readFileSync(new URL('main.swift',root),'utf8');
 const a=source.indexOf('    func refreshManualClickExperiment(');assert(a>=0);
 let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}
 const code=`import Foundation
func log(_ values:Any...){}
final class Experiment {
 var manualClick=true,applied=false,supported=false
 func setManualClickSupport(_ value:Bool,reason:String){supported=value}
 func setAppliedManualClick(_ value:Bool){applied=value}
}
struct Options {func enabled(_ key:String)->Bool{false}}
final class Harness {
 var isSense=true,manualClickExperiment=false,ready=true,buttons=0
 var controlVersion=WandControlVersion.sustainedV3
 let heldScroll=WandHeldScroll(),pointerRouter=WandPointerRouter(),dwell=WandDwellClick()
 let options=Options(),experiment=Experiment()
 var commands:[String]=[]
 func queue(_ text:String){commands.append(text)}
 func scheduleDwell(){}
 ${source.slice(a,b)}
}
let h=Harness();h.dwell.follow(true);h.refreshManualClickExperiment()
precondition(h.manualClickExperiment && h.experiment.applied && h.experiment.supported)
h.heldScroll.begin(now:10,sustain:true);h.experiment.manualClick=false;h.refreshManualClickExperiment()
precondition(h.manualClickExperiment && h.experiment.applied && !h.experiment.manualClick,"requested off stays pending during an owned hold")
_=h.heldScroll.end(now:10.4);h.refreshManualClickExperiment()
precondition(!h.manualClickExperiment && !h.experiment.applied,"release applies the requested off mode")
h.experiment.manualClick=true;h.controlVersion = .pointerV1;h.refreshManualClickExperiment()
precondition(!h.manualClickExperiment && !h.experiment.applied && !h.experiment.supported,"V1 never loses its automatic click owner")
h.dwell.move(dx:12,dy:0,now:20,eligible:true)
precondition(h.dwell.tick(now:20.2),"V1 still automatically clicks after its original pause")
h.controlVersion = .scrollV2;h.refreshManualClickExperiment()
precondition(h.manualClickExperiment && h.experiment.applied && h.experiment.supported,"returning to supported controls applies the saved request")
h.isSense=false;h.refreshManualClickExperiment()
precondition(!h.manualClickExperiment && !h.experiment.applied && !h.experiment.supported,"Puck keeps its original click/tap lifecycle")
print("PASS: V1/Puck keep clicks; supported modes and deferred checkbox state agree")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-manual-mode-'));
 try {
  writeFileSync(join(dir,'main.swift'),code);
  const build=spawnSync('swiftc',['-O',fileURLToPath(new URL('WandPointerControl.swift',root)),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(build.status,0,build.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);
 }finally{rmSync(dir,{recursive:true,force:true});}
});

// A known draggable target owns a held press before the first post-threshold
// raw frame arrives. The quiet-hold timer must not cancel that pending drag.
test('manual quiet-stop leaves known native drag ownership intact', {skip:process.platform!=='darwin'},()=>{
 const root=new URL('../receiver/Sources/',import.meta.url);
 const source=readFileSync(new URL('main.swift',root),'utf8');
 const start=source.indexOf('    func stopManualQuietHold(');assert(start>=0);
 let end=source.indexOf('{',start)+1,depth=1;
 while(depth){if(source[end]==='{')depth++;if(source[end]==='}')depth--;end++;}
 const code=`import Foundation
// Inert real-method test. Native events and device commands are never sent.
struct RecenterStub {var isSecondPress=false}
struct ScreenshotStub {var ownsPointer=false}
final class RestStub {func pointerStopped(){}}
final class Harness {
 var manualClickExperiment=true,scrollFollowBefore=true,scrollActive=false
 let heldScroll=WandHeldScroll()
 var recenterGesture=RecenterStub(),screenshot=ScreenshotStub()
 let dwell=WandDwellClick(),restDetection=RestStub()
 var stopped=0,commands:[String]=[]
 func mouseButtonPhysicalHoldDuration()->Double? {0.25}
 func scheduleDwell(){}
 func queue(_ s:String){commands.append(s)}
 func finishMouseButtonHold(now:Double,released:Bool){stopped+=1;_=heldScroll.end(now:now)}
 ${source.slice(start,end)}
}
func log(_ values:Any...){}
func setup(drag:Bool?=nil)->Harness {
 let h=Harness();h.heldScroll.begin(now:0,sustain:true,resolving:true)
 if let drag {precondition(h.heldScroll.setTarget(scrollable:!drag,now:0.05))}
 return h
}
func expect(_ b:Bool,_ s:String){if !b {print("FAIL: "+s);exit(1)}}
let drag=setup(drag:true)
drag.stopManualQuietHold(now:0.25)
expect(drag.stopped==0 && drag.heldScroll.active,"known drag target must survive timer before its first held raw frame")
expect(drag.heldScroll.startDrag(now:0.251),"the next raw frame can start native dragging")
let scroll=setup(drag:false);scroll.stopManualQuietHold(now:0.25)
expect(scroll.stopped==1,"quiet hold over scrolling content still stops follow")
let unknown=setup();unknown.stopManualQuietHold(now:0.25)
expect(unknown.stopped==1,"unknown quiet target retains stop behavior")
let moving=setup(drag:false)
for i in 1...25 {_=moving.heldScroll.sample(x:0,y:20,dt:0.01,now:Double(i)/100)}
moving.stopManualQuietHold(now:0.25)
expect(moving.stopped==0,"recognised scroll wins")
let second=setup(drag:true);second.recenterGesture.isSecondPress=true;second.stopManualQuietHold(now:0.25)
expect(second.stopped==0,"explicit second-press dragging is unchanged")
let shot=setup(drag:false);shot.screenshot.ownsPointer=true;shot.stopManualQuietHold(now:0.25)
expect(shot.stopped==0,"screenshot pointer ownership is unchanged")
let off=setup(drag:false);off.scrollFollowBefore=false;off.stopManualQuietHold(now:0.25)
expect(off.stopped==0,"starting off cannot acquire follow")
print("PASS: known drag survives quiet timer; scroll/unknown quiet-stop, active scroll, explicit drag, screenshot, follow-off preserved")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-manual-drag-owner-'));
 try {
  writeFileSync(join(dir,'main.swift'),code);
  const built=spawnSync('swiftc',['-O',fileURLToPath(new URL('WandPointerControl.swift',root)),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(built.status,0,built.stderr);
  const ran=spawnSync(join(dir,'check'),[],{encoding:'utf8'});
  assert.equal(ran.status,0,ran.stdout+ran.stderr);
  console.log(ran.stdout.trim());
 }finally{rmSync(dir,{recursive:true,force:true});}
});
