import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

test('native held scrolling and dragging stop on physical up even without the edge', {skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 function method(name){const a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
 const code=`import Foundation
func AXIsProcessTrusted()->Bool {true}
func log(_ v:Any...) {}
enum Tap {case cghidEventTap}
final class CGEvent {var location=CGPoint.zero;init?(source:Int?){ };func post(tap:Tap){}}
final class Rest {var activated=false;func pointerActivated(){activated=true}}
final class Harness {
 let restDetection=Rest()
 let heldScroll=WandHeldScroll(),pointerRouter=WandPointerRouter(),motionFilter=WandMotionFilter(),dwell=WandDwellClick(),recenterGesture=WandRecenterGesture(),flickScroll=WandFlickScroll()
 var heldSafetyTimer:Timer?,heldTargetToken=UUID(),heldScrollAnchor:CGPoint?,deliveryPoint:CGPoint?,flickAnchor:CGPoint?
 var controlVersion=WandControlVersion.scrollV2,ready=true,restoring=false,scrollActive=false,hudSession=false,flickScrollEnabled=false
 var commands:[String]=[],scrollPostedX=0,scrollPostedY=0
 var scrollAnchor:CGPoint?,scrollWatchdog:Timer?
 var rawLastArrival=0.0,rawWindowStart=0.0,rawReports=0,rawMaxGap=0.0,buttons=0,wheels=0,frames=0,ups=0,light=false
 func transition(to:Int,at:CGPoint){buttons=to;if to==0 {ups+=1}}
 func queue(_ s:String){commands.append(s)}
 func enterPointerMode(){hudSession=false}
 func resumeHUDNavigation(){}
 func setCircleLight(_ b:Bool){light=b}
 func performPointer(_ a:[WandPointerRouter.Action]){}
 func scheduleDwell(){}
 func postPointerMove(dx:Int,dy:Int,from p:CGPoint)->CGPoint{p}
 func handleFrame(x:Int,y:Int,b:Int){frames+=1}
 static func wheelEvents(x:Int32,y:Int32,at:CGPoint?)->[CGEvent]{[]}
 ${['enableMouseAfterScroll','finishScroll','finishBottomHold','reconcileBottomHold','handleRaw'].map(method).join('\n')}
}
let h=Harness();precondition(h.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
let now=ProcessInfo.processInfo.systemUptime
h.heldScroll.begin(now:now-1);_=h.pointerRouter.bottom(down:true);h.light=true
h.handleRaw("10000,0,2680,0") // no @BOTTOM 0: raw physical-up must still stop first
precondition(!h.heldScroll.active && !h.pointerRouter.bottomHeld && !h.light)
precondition(h.frames==0,"release sample cannot move or click")
precondition(h.heldScroll.sample(y:20,dt:0.01)==0)
h.heldScroll.begin(now:now-1,scrollable:false);_=h.pointerRouter.bottom(down:true)
precondition(h.heldScroll.startDrag(now:now));h.buttons=1
h.handleRaw("10000,0,2680,0")
precondition(h.buttons==0 && !h.heldScroll.active,"missed release must drop native drag")
h.heldScroll.begin(now:20);h.reconcileBottomHold(down:true,now:20.7,reason:"sensor")
precondition(!h.heldScroll.stale(now:21.4) && h.heldScroll.stale(now:21.6))
h.reconcileBottomHold(down:false,now:21.6,reason:"timeout")
precondition(!h.heldScroll.active)
h.reconcileBottomHold(down:true,now:22,reason:"late telemetry")
precondition(!h.heldScroll.active,"late telemetry must not restart a cancelled hold")
h.heldScroll.begin(now:30);h.scrollActive=true
h.finishBottomHold(now:31)
precondition(!h.heldScroll.active,"release teardown is independent of other mode state")
for prior in [false,true] {
 let exit=Harness();exit.dwell.follow(prior);exit.heldScroll.begin(now:100)
 exit.finishBottomHold(now:101)
 precondition(exit.dwell.following && exit.restDetection.activated,"completed scroll enables mouse regardless of prior follow")
 precondition(exit.commands.contains("global.wandPointerPauseUntil=0;setMouseFollow(true);"))
 let chord=Harness();chord.dwell.follow(prior);chord.scrollActive=true
 chord.finishScroll(resumeMouse:true)
 precondition(chord.dwell.following && !chord.scrollActive,"chord release enables mouse")
}
let tap=Harness();tap.heldScroll.begin(now:100);tap.finishBottomHold(now:100.05)
precondition(!tap.dwell.following,"short taps retain their existing meaning")
let drag=Harness();drag.heldScroll.begin(now:100,scrollable:false);_=drag.heldScroll.startDrag(now:100.3);drag.finishBottomHold(now:101)
precondition(!drag.dwell.following,"native dragging is not a scroll gesture")
let lost=Harness();lost.heldScroll.begin(now:100);lost.reconcileBottomHold(down:false,now:101,reason:"timeout",resumeMouse:false)
precondition(!lost.dwell.following,"lost telemetry must not activate mouse")
print("PASS: missing release, native drag release, stale telemetry and scroll-to-mouse from both prior states")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-release-'));
 try {writeFileSync(join(dir,'main.swift'),code);const built=spawnSync('swiftc',['-O',new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(built.status,0,built.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
