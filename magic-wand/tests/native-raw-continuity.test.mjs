// Use the actual receiver input preamble and actual filter; native output is inert.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
function method(name){let a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,n=1;while(n){if(source[b]==='{')n++;if(source[b]==='}')n--;b++;}return source.slice(a,b);}
test('continuous physical readings preserve smoothing and stillness across a host stall',()=>{
 let raw=method('handleRaw');
 raw=raw.slice(0,raw.indexOf('        // Held Switch App'))+'        recorded.append(sample)\n    }';
 // Control host time while preserving the real input/reset logic.
 raw=raw.replace('let now=ProcessInfo.processInfo.systemUptime','let now=hostTime');
 assert(source.includes('sampleTime:eventTimes.isEmpty ? nil:eventTime'),'physical sample time reaches the raw handler');
 let shot=method('handleScreenshotRaw').replace('AXIsProcessTrusted()','true');
 shot=shot.replace('let point=deliveryPoint ?? currentPointerOrigin()', 'recorded.append(sample)\n        let point=deliveryPoint ?? currentPointerOrigin()');
 const code=`import Foundation
func AXIsProcessTrusted()->Bool {true}
final class Harness {
 var ready=true,restoring=false,scrollActive=false
 var rawLastArrival=0.0,rawLastSample=0.0,hostTime=1.0
 var recorded:[WandMotionFilter.Result]=[]
 let motionFilter=WandMotionFilter(),heldScroll=WandHeldScroll(),screenshot=WandScreenshotGesture()
 var deliveryPoint:CGPoint?
 func reconcileMouseButtonHold(down:Bool,now:Double,reason:String){}
 func currentPointerOrigin()->CGPoint{.zero}
 func postPointerMove(dx:Int,dy:Int,from p:CGPoint)->CGPoint{p}
 ${raw}
 ${shot}
}
func make()->Harness {let h=Harness();h.motionFilter.path = .direct;precondition(h.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]));return h}
func trace(_ h:Harness,stalled:Bool,screenshot:Bool=false){
 for i in 0..<100 {
  let physical=1+Double(i)*0.01
  h.hostTime=physical+(stalled && i>=30 ? 0.4:0)
  let x=i<29 ? 400 : (i<40 ? 0: (i%2==0 ? 25 : -25))
  if i==29 {h.motionFilter.holdAfterAutomaticClick()}
  if screenshot {h.handleScreenshotRaw([10000,x,0,0],now:h.hostTime,sampleTime:physical)}
  else {h.handleRaw("10000,\\(x),0,0",sampleTime:physical)}
 }
}
let normal=make(),delayed=make();trace(normal,stalled:false);trace(delayed,stalled:true)
func signature(_ h:Harness)->[String]{h.recorded.map{"\\($0.x),\\($0.y),\\($0.highX),\\($0.quietForClick),\\($0.fineMoving)"}}
precondition(signature(normal)==signature(delayed),"host delivery stall reset smoothing/stillness despite continuous sensor time")
let sn=make(),sd=make();trace(sn,stalled:false,screenshot:true);trace(sd,stalled:true,screenshot:true)
precondition(signature(sn)==signature(sd),"screenshot aiming reset on host delay")
// A true physical interruption must still clear filter carry, matching reset.
let gap=make(),explicit=make();gap.handleRaw("10000,400,0,0",sampleTime:1);explicit.handleRaw("10000,400,0,0",sampleTime:1)
gap.hostTime=1.01;explicit.hostTime=1.01
gap.handleRaw("10000,0,0,0",sampleTime:1.4);explicit.handleRaw("10000,0,0,2",sampleTime:1.01)
precondition(signature(gap).last==signature(explicit).last,"real sensor gap keeps reset")
// Legacy Puck delivery still uses the host gap, without new timing assumptions.
let puck=make(),puckReset=make();puck.handleRaw("10000,400,0,0");puckReset.handleRaw("10000,400,0,0")
puck.hostTime=1.4;puckReset.hostTime=1.01;puck.handleRaw("10000,0,0,0");puckReset.handleRaw("10000,0,0,2")
precondition(signature(puck).last==signature(puckReset).last,"Puck gap behavior remains")
print("PASS continuous Sense timing, stillness, screenshot, real gaps and Puck")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-raw-continuity.noindex-'));
 try {
 writeFileSync(join(dir,'main.swift'),code);
 const built=spawnSync('swiftc',['-Onone',new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
 assert.equal(built.status,0,built.stderr);
 const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);
 }finally{rmSync(dir,{recursive:true,force:true});}
});
