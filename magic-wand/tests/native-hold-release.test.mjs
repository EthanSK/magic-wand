import {fileURLToPath as wandSourcePath} from 'node:url';
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
var logged:[String]=[]
func log(_ v:Any...) {logged.append(v.map{"\\($0)"}.joined(separator:" "))}
enum Tap {case cghidEventTap}
final class CGEvent {var location=CGPoint.zero;init?(source:Int?){ };func post(tap:Tap){}}
final class Rest {var activated=false,stopped=0;func pointerActivated(){activated=true};func pointerStopped(){activated=false;stopped+=1}}
final class SwitchAppContext {var switchAppAdjusting=false}
final class Harness {
 var tripleClick=WandTripleClick(),pendingRecenter:Timer?
 var scrollFollowBefore=false
 var queuedExitClicks:[CGPoint]=[]
 func cancelMouseExitClick(){}
 func scheduleMouseExitClick(at point:CGPoint){queuedExitClicks.append(point);dwell.follow(false)}
 let context=SwitchAppContext()
 var actionPause=WandActionPause()
 let screenshot=WandScreenshotGesture();var screenshotRaw=0;func handleScreenshotRaw(_ v:[Int],now:Double){screenshotRaw+=1}
 let restDetection=Rest()
 let heldScroll=WandHeldScroll(),pointerRouter=WandPointerRouter(),motionFilter=WandMotionFilter(),dwell=WandDwellClick(),recenterGesture=WandRecenterGesture(),flickScroll=WandFlickScroll()
 var heldSafetyTimer:Timer?,heldTargetToken=UUID(),heldScrollAnchor:CGPoint?,deliveryPoint:CGPoint?,flickAnchor:CGPoint?
 var pointerOrigin=WandPointerOrigin();func currentPointerOrigin()->CGPoint{pointerOrigin.origin(system:CGEvent(source:nil)?.location ?? .zero,now:ProcessInfo.processInfo.systemUptime)}
 var controlVersion=WandControlVersion.scrollV2,ready=true,restoring=false,scrollActive=false,hudSession=false,flickScrollEnabled=false,heldScrollDiagnostics=false
 var physicalTapDuration:Double?=nil;func mouseButtonPhysicalTapDuration()->Double?{physicalTapDuration}
 var screenshotActive=false,hudButtonHeld=false,hudButtonMouseX=0.0,hudButtonMouseSampleAt = -100.0
 var commands:[String]=[],scrollPostedX=0,scrollPostedY=0
 var clickPoints:[CGPoint]=[]
 var recordingPointerPaused=false
 var scrollAnchor:CGPoint?,scrollWatchdog:Timer?
 var rawLastArrival=0.0,rawWindowStart=0.0,rawReports=0,rawMaxGap=0.0,buttons=0,wheels=0,frames=0,ups=0,downs=0,light=false
 func transition(to:Int,at:CGPoint){if to==1 && buttons==0 {downs+=1;clickPoints.append(at)};buttons=to;if to==0 {ups+=1}}
 func queue(_ s:String){commands.append(s)}
 func enterPointerMode(){hudSession=false}
 func resumeHUDNavigation(){}
 func setCircleLight(_ b:Bool){light=b}
 func performPointer(_ a:[WandPointerRouter.Action]){}
 func scheduleDwell(){}
 func releaseButtons(){buttons=0}
 func postPointerMove(dx:Int,dy:Int,from p:CGPoint)->CGPoint{p}
 func handleFrame(x:Int,y:Int,b:Int,stopX:Int?=nil,stopY:Int?=nil){frames+=1}
 static var wheelPairs:[(Int32,Int32)]=[]
 func finishNativeScroll(cancelled:Bool){}
 func postNativeScroll(x:Int32,y:Int32,at:CGPoint?){_ = Self.wheelEvents(x:x,y:y,at:at)}
 func postHeldScroll(x:Int32,y:Int32,at:CGPoint?){_ = Self.wheelEvents(x:x,y:y,at:at)}
 func postSustainedScroll(x:Int32,y:Int32,at:CGPoint?){_ = Self.wheelEvents(x:x,y:y,at:at)}
 static func wheelEvents(x:Int32,y:Int32,at:CGPoint?)->[CGEvent]{wheelPairs.append((x,y));return []}
 ${['beginMouseButtonHold','restoreMouseAfterScroll','deviceFollowChanged','finishScroll','finishMouseButtonHold','reconcileMouseButtonHold','handleRaw','consumeEarlyHorizontalIntent','finishHorizontalStrokeIfNeeded'].map(method).join('\n')}
}
let h=Harness();precondition(h.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
let now=ProcessInfo.processInfo.systemUptime
let hudOnly=Harness();hudOnly.hudButtonHeld=true
precondition(hudOnly.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
for _ in 0..<40 {hudOnly.handleRaw("10000,2680,0,4")}
precondition(hudOnly.hudButtonMouseX < 0 && hudOnly.frames == 0 && hudOnly.buttons == 0,"HUD-only samples provide HIGH sensitivity without pointer events")
// Held Switch App: plain forward and back, no circular direction latch.
let chooser=Harness();chooser.hudButtonHeld=true;chooser.hudSession=true;chooser.context.switchAppAdjusting=true
precondition(chooser.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
for _ in 0..<30 {chooser.handleRaw("10000,2680,0,4")}
let forward=chooser.hudButtonMouseX
for _ in 0..<30 {chooser.handleRaw("10000,-2680,0,4")}
precondition(forward < 0 && abs(chooser.hudButtonMouseX) < abs(forward) * 0.2,"reversing moves straight back: \\(forward) then \\(chooser.hudButtonMouseX)")
let circle=Harness();circle.hudButtonHeld=true;circle.hudSession=true;circle.context.switchAppAdjusting=true
precondition(circle.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
var path=0.0,last=0.0
for i in 0..<200 {let a=Double(i)/200*2 * .pi;circle.handleRaw("10000,\\(Int(2680*cos(a))),\\(Int(2680*sin(a))),4");path+=abs(circle.hudButtonMouseX-last);last=circle.hudButtonMouseX}
precondition(abs(circle.hudButtonMouseX) < path * 0.15,"a full circle returns near its start instead of latching one direction")

let explicit=Harness();precondition(explicit.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
_=explicit.recenterGesture.edge(down:true,now:now-1)
explicit.beginMouseButtonHold(now:now-1)
precondition(explicit.heldScroll.scrollable,"a plain hold scrolls until its target is proven draggable")
_=explicit.recenterGesture.edge(down:false,now:now-0.95)
explicit.finishMouseButtonHold(now:now-0.95)
_=explicit.recenterGesture.edge(down:true,now:now-0.85)
explicit.beginMouseButtonHold(now:now-0.85)
precondition(!explicit.heldScroll.scrollable,"only the second held click requests a real drag")
explicit.handleRaw("10000,2680,0,1")
precondition(explicit.heldScroll.dragging && explicit.buttons==1,"explicit drag posts mouse-down")
precondition(!explicit.recenterGesture.edge(down:false,now:now),"held second click must not recenter")
explicit.handleRaw("10000,2680,0,0")
precondition(!explicit.heldScroll.active && explicit.buttons==0,"release drops the explicit drag")
_=explicit.recenterGesture.edge(down:true,now:now+1)
explicit.beginMouseButtonHold(now:now+1)
precondition(explicit.heldScroll.scrollable,"the next ordinary hold returns to scrolling")
explicit.finishMouseButtonHold(now:now+2)
h.heldScroll.begin(now:now-1);_=h.pointerRouter.mouseButton(down:true);h.light=true
h.handleRaw("10000,0,2680,0") // no @BOTTOM 0: raw physical-up must still stop first
precondition(!h.heldScroll.active && !h.pointerRouter.mouseButtonHeld && !h.light)
precondition(h.frames==0,"release sample cannot move or click")
precondition(h.heldScroll.sample(y:20,dt:0.01)==0)
h.heldScroll.begin(now:now-1,scrollable:false);_=h.pointerRouter.mouseButton(down:true)
precondition(h.heldScroll.startDrag(now:now));h.buttons=1
h.handleRaw("10000,0,2680,0")
precondition(h.buttons==0 && !h.heldScroll.active,"missed release must drop native drag")
h.heldScroll.begin(now:20);h.reconcileMouseButtonHold(down:true,now:20.7,reason:"sensor")
precondition(!h.heldScroll.stale(now:21.4) && h.heldScroll.stale(now:21.6))
h.reconcileMouseButtonHold(down:false,now:21.6,reason:"timeout")
precondition(!h.heldScroll.active)
h.reconcileMouseButtonHold(down:true,now:22,reason:"late telemetry")
precondition(!h.heldScroll.active,"late telemetry must not restart a cancelled hold")
h.heldScroll.begin(now:30);h.scrollActive=true
h.finishMouseButtonHold(now:31)
precondition(!h.heldScroll.active,"release teardown is independent of other mode state")
// A released scroll restores its pre-scroll mouse-follow choice, for both
// raw-up-first and edge-first delivery. Neither duplicate release can flip it.
let config=[0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]
for prior in [false,true] {
 for rawFirst in [false,true] {
  let exit=Harness();precondition(exit.motionFilter.configure(config));exit.controlVersion = .sustainedV3
  exit.dwell.follow(prior);exit.restDetection.activated=prior;logged=[]
  exit.beginMouseButtonHold(now:now-1);_=exit.pointerRouter.mouseButton(down:true)
  for i in 1...20 {_=exit.heldScroll.sample(y:20,dt:0.01,now:now-0.8+Double(i)*0.01)}
  precondition(exit.heldScroll.hasScrollGesture,"the restoration case includes an actual scroll stroke")
  if rawFirst {exit.handleRaw("10000,0,2680,0")}                      // raw up, then the edge
  else {exit.finishMouseButtonHold(now:now);_=exit.pointerRouter.mouseButton(down:false)} // edge, then raw up
  precondition(exit.frames==0,"the release sample itself never moves or clicks")
  exit.finishMouseButtonHold(now:now+0.01);exit.handleRaw("10000,0,2680,0") // the other report of the same release
  exit.reconcileMouseButtonHold(down:false,now:now+0.02,reason:"sensor button state")
  let expected="global.wandPointerPauseUntil=0;setMouseFollow("+(prior ? "true":"false")+");"
  precondition(exit.commands.filter{$0==expected}.count==1,"restore the original follow choice once")
  precondition(exit.dwell.following==prior && exit.restDetection.activated==prior,"scroll preserves the prior follow choice")
  precondition(logged.filter{$0==(prior ? "SCROLL_FINISHED_MOUSE_ON":"SCROLL_FINISHED_MOUSE_OFF")}.count==1,"duplicate release restores once")
  // Normal pointing resumes on the next following frame, with no suppression wait.
  let frames=exit.frames
  exit.handleRaw("10000,2680,0,0")
  precondition(exit.frames==frames+1,"the next following frame moves the pointer at once")
  exit.handleRaw("10000,2680,0,4");precondition(exit.frames==frames+1,"HUD-only frames never move the pointer")
 }
 let chord=Harness();chord.dwell.follow(prior);chord.scrollFollowBefore=prior;chord.scrollActive=true
 chord.finishScroll(released:true)
 precondition(chord.dwell.following==prior && !chord.scrollActive && chord.commands==["global.wandPointerPauseUntil=0;setMouseFollow("+(prior ? "true":"false")+");"],"chord release restores prior follow")
 let watchdog=Harness();watchdog.dwell.follow(prior);watchdog.scrollActive=true
 watchdog.finishScroll()
 precondition(watchdog.dwell.following==prior && watchdog.commands.isEmpty,"a chord watchdog stop is not a release")
 // Short taps, native drags and lost telemetry keep the device's own follow choice.
 let tap=Harness();tap.dwell.follow(prior);tap.heldScroll.begin(now:100);tap.finishMouseButtonHold(now:100.05)
 precondition(tap.dwell.following==prior && tap.commands.isEmpty,"short taps retain their existing meaning")
 // A 207 ms physical tap whose release arrived late (Mac sees 0.4 s) is still a tap:
 // it never turns mouse follow back on, so the mouse button can exit mouse mode.
 let late=Harness();late.dwell.follow(prior);late.physicalTapDuration=0.207;late.heldScroll.begin(now:100);late.finishMouseButtonHold(now:100.4)
 precondition(late.dwell.following==prior && !late.commands.contains{$0.contains("setMouseFollow")},"a physically short tap is never a completed scroll")
 let longHold=Harness();longHold.dwell.follow(prior);longHold.physicalTapDuration=0.4;longHold.beginMouseButtonHold(now:100);longHold.finishMouseButtonHold(now:100.4)
 precondition(!longHold.dwell.following && longHold.queuedExitClicks.isEmpty,"a physically long quiet hold stops follow without clicking")
 precondition(longHold.commands.contains{$0.contains("setMouseFollow(false)")},"quiet holds leave follow off from either prior state")
 let drag=Harness();drag.dwell.follow(prior);drag.heldScroll.begin(now:100,scrollable:false);_=drag.heldScroll.startDrag(now:100.3);drag.finishMouseButtonHold(now:101)
 precondition(drag.dwell.following==prior && !drag.commands.contains{$0.contains("setMouseFollow")},"native dragging is not a scroll gesture")
 let lost=Harness();lost.dwell.follow(prior);lost.heldScroll.begin(now:100);lost.reconcileMouseButtonHold(down:false,now:101,reason:"timeout",released:false)
 precondition(lost.dwell.following==prior && !lost.commands.contains{$0.contains("setMouseFollow")},"lost telemetry must not activate mouse")
}
// Quiet release is independent of edge order. Small unqualified hand noise is
// not a scroll gesture; a real V3 stroke counts even before one pixel is emitted.
for version in [WandControlVersion.scrollV2,.sustainedV3] {
 for rawFirst in [false,true] {
  let quiet=Harness();quiet.controlVersion=version;quiet.dwell.follow(true)
  quiet.beginMouseButtonHold(now:now-1,following:true);_=quiet.pointerRouter.mouseButton(down:true)
  for i in 1...20 {_=quiet.heldScroll.sample(x:0.05,y:-0.05,dt:0.01,now:now-0.8+Double(i)*0.01)}
  precondition(!quiet.heldScroll.hasScrollGesture,"subthreshold noise must not count as scrolling")
  if rawFirst {quiet.handleRaw("10000,0,0,0")} else {quiet.finishMouseButtonHold(now:now)}
  quiet.finishMouseButtonHold(now:now+0.01)
  precondition(!quiet.dwell.following && quiet.queuedExitClicks.isEmpty && quiet.downs==0,"quiet hold turns follow off without an OS click")
  precondition(quiet.commands.filter{$0=="global.wandPointerPauseUntil=0;setMouseFollow(false);"}.count==1,"duplicate release changes follow once")
  precondition(quiet.heldScroll.consumes(buttons:1) && quiet.heldScroll.consumes(buttons:0),"quiet hold consumes the firmware endpoint click")
 }
}
let smallStroke=Harness();smallStroke.controlVersion = .sustainedV3;smallStroke.dwell.follow(true)
smallStroke.beginMouseButtonHold(now:100,following:true)
for i in 1...10 {_=smallStroke.heldScroll.sample(y:8,dt:0.01,now:100+Double(i)*0.01)}
precondition(smallStroke.heldScroll.hasScrollGesture,"a qualified stroke is counted before output rounding")
smallStroke.finishMouseButtonHold(now:100.4)
precondition(smallStroke.dwell.following && smallStroke.commands.contains{$0.contains("setMouseFollow(true)")},"actual scrolling restores follow even with no emitted whole pixel")
// Exit follow queues the short-release click for double/triple recognition. The
// actual finish method owns both raw-up and edge-up, so duplicate reports are inert.
for physicalDuration:Double? in [nil,0.12] {
 let click=Harness();click.dwell.follow(true);click.beginMouseButtonHold(now:100,following:true)
 click.heldScrollAnchor=CGPoint(x:800,y:600)
 click.physicalTapDuration=physicalDuration
 click.finishMouseButtonHold(now:physicalDuration == nil ? 100.12:100.4)
 precondition(click.queuedExitClicks.count==1 && click.downs==0 && click.buttons==0 && !click.dwell.following,"short exit release queues a click and immediately stops follow")
 precondition(click.queuedExitClicks==[.zero],"exit click captures the release pointer, not the old press anchor")
 click.finishMouseButtonHold(now:100.5);click.reconcileMouseButtonHold(down:false,now:100.6,reason:"duplicate")
 precondition(click.queuedExitClicks.count==1,"raw/edge duplicate release cannot queue twice")
}
let enter=Harness();enter.beginMouseButtonHold(now:100,following:false);enter.finishMouseButtonHold(now:100.12)
precondition(enter.downs==0 && enter.queuedExitClicks.isEmpty,"entering follow does not click")
let cancelledClick=Harness();cancelledClick.beginMouseButtonHold(now:100,following:true);cancelledClick.finishMouseButtonHold(now:100.12,released:false)
precondition(cancelledClick.downs==0 && cancelledClick.queuedExitClicks.isEmpty,"cancellation does not click")
let heldClick=Harness();heldClick.beginMouseButtonHold(now:100,following:true);heldClick.finishMouseButtonHold(now:101)
precondition(heldClick.downs==0 && heldClick.queuedExitClicks.isEmpty,"a scroll hold does not click")
let draggingClick=Harness();draggingClick.beginMouseButtonHold(now:100,following:true)
_=draggingClick.heldScroll.setTarget(scrollable:false,now:100.01);_=draggingClick.heldScroll.startDrag(now:100.3)
draggingClick.physicalTapDuration=0.1;draggingClick.finishMouseButtonHold(now:100.4)
precondition(draggingClick.downs==0 && draggingClick.queuedExitClicks.isEmpty,"even a delayed short-duration report cannot click after native dragging")

for horizontal in [false,true] {
 let axis=Harness();precondition(axis.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
 axis.heldScroll.begin(now:now-1);_=axis.pointerRouter.mouseButton(down:true);Harness.wheelPairs=[]
 for _ in 0..<50 {axis.handleRaw(horizontal ? "10000,2680,0,1":"10000,0,2680,1")}
 precondition(!Harness.wheelPairs.isEmpty,"raw motion must reach the wheel output")
 precondition(Harness.wheelPairs.allSatisfy{horizontal ? ($0.0 != 0 && $0.1 == 0):($0.0 == 0 && $0.1 != 0)},"the receiver must post only the acquired scroll axis")
 let count=Harness.wheelPairs.count
 axis.handleRaw("10000,2680,2680,0")
 precondition(Harness.wheelPairs.count==count && !axis.heldScroll.active,"release must stop both axes before emitting movement")
}
let continuing=Harness();continuing.controlVersion = .sustainedV3
precondition(continuing.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
_=continuing.recenterGesture.edge(down:true,now:now-1)
continuing.beginMouseButtonHold(now:now-1)
continuing.heldScrollDiagnostics=true
// A short straight stroke (20 degrees per second for 80 ms) through the real raw handler.
for _ in 0..<8 {continuing.handleRaw("10000,0,2680,1")}
precondition(continuing.heldScroll.sustained.started,"a held straight stroke starts V3 scrolling")
Harness.wheelPairs=[]
RunLoop.current.run(until:Date().addingTimeInterval(0.12))
precondition(!Harness.wheelPairs.isEmpty,"actual receiver timer keeps scrolling without fresh movement")
continuing.handleRaw("10000,0,2680,0")
let stoppedCount=Harness.wheelPairs.count
RunLoop.current.run(until:Date().addingTimeInterval(0.06))
precondition(Harness.wheelPairs.count==stoppedCount && !continuing.heldScroll.active,"raw button-up cancels the real continuation timer")
let summary=logged.filter{$0.hasPrefix("V3_SCROLL_HOLD ")}
precondition(summary.count==1 && summary[0].contains(" strokes=1 ") && summary[0].contains(" end=release ") && summary[0].hasSuffix(" axis=vertical"),"opt-in diagnostics write one line per hold: "+summary.joined())
precondition(!summary[0].contains("."),"the diagnostic line has whole counts and rates, never coordinates")
let quietLog=Harness();quietLog.controlVersion = .sustainedV3
precondition(quietLog.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
logged=[];quietLog.beginMouseButtonHold(now:now-1)
for _ in 0..<8 {quietLog.handleRaw("10000,0,2680,1")}
quietLog.handleRaw("10000,0,2680,0")
precondition(!quietLog.heldScroll.active && !logged.contains{$0.hasPrefix("V3_SCROLL_HOLD")},"diagnostics stay off unless enabled")
print("PASS: missing release, native drag release, stale telemetry and scroll-to-mouse from both prior states")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-release-'));
 try {writeFileSync(join(dir,'main.swift'),code);const built=spawnSync('swiftc',[wandSourcePath(new URL('../receiver/Sources/WandRunLoop.swift',import.meta.url)),'-O',new URL('../receiver/Sources/WandActionPause.swift',import.meta.url).pathname,new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(built.status,0,built.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
