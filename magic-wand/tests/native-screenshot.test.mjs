import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

// Ethan's screenshot mode and Bottom triple-click shortcut, through the actual
// receiver methods and its actual @BOTTOM/@FOLLOW line handling. Native capture,
// Agentic Mouse and CGEvent posting are inert stubs: this cannot prove a
// physical screenshot, only the receiver's ownership, button and follow rules.
const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
const transport=readFileSync(new URL('../receiver/Sources/WandControlTransport.swift',import.meta.url),'utf8');
function method(name){const a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
function block(from,to){const a=source.indexOf(from),b=source.indexOf(to,a);assert(a>=0&&b>a,from);return source.slice(a,b);}
const swiftc=(dir,code,extra=[])=>{writeFileSync(join(dir,'main.swift'),code);const built=spawnSync('swiftc',['-Onone',...extra,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(built.status,0,built.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);return run.stdout;};

test('screenshot mode: follow-independent aim, one-tap latch, shared settle release, triple-click start',{skip:process.platform!=='darwin'},()=>{
 const bottom=block('            if let marker=line.range(of:"@BOTTOM ")','            if let marker=line.range(of:"@MIDDLE ")');
 const follow=block('            if let marker=line.range(of:"@FOLLOW ")','            if let marker=line.range(of:"@ZERO ")');
 assert(bottom.indexOf('screenshotBottom(')<bottom.indexOf('manualPointerDuringRecording()'),'screenshot ownership and the triple-click precede every ordinary Bottom lane');
 assert(method('handleRaw').indexOf('handleScreenshotRaw')<method('handleRaw').indexOf('reconcileBottomHold'),'screenshot raw handling precedes the button-up reconciliation');
 for(const name of ['reset','stop']) assert(method(name).includes('endScreenshot('),name+' releases any screenshot drag');
 assert(source.includes('queue("global.wandShot=0;global.wandRawPointer=true;'),'a fresh bridge session never inherits screenshot motion');
 assert(source.includes('return loading + "global.wandShot=0;'),'shutdown stops screenshot motion');
 const code=`import Foundation
func AXIsProcessTrusted()->Bool {true}
var logged:[String]=[]
func log(_ v:Any...) {logged.append(v.map{"\\($0)"}.joined(separator:" "))}
var warps=0
func CGMainDisplayID()->Int {1}
func CGDisplayBounds(_ id:Int)->CGRect {CGRect(x:0,y:0,width:2000,height:1000)}
func CGWarpMouseCursorPosition(_ point:CGPoint){warps+=1}
enum Tap {case cghidEventTap}
final class CGEvent {var location=CGPoint(x:400,y:300);init?(source:Int?){};func post(tap:Tap){}}
final class Posted {func post(tap:Tap){}}
final class Rest {var parked=false;func pointerActivated(){};func pointerStopped(){}}
final class Controls {var phases:[String]=[];var starts=0;var available=true
 func persistent(_ phase:String,x:Double=0,y:Double=0,mouseX:Double?=nil){phases.append(phase)}
 func screenshotStart()->Bool{starts+=1;return available}}
final class Harness {
 let restDetection=Rest(),controls=Controls(),screenshot=WandScreenshotGesture()
 let heldScroll=WandHeldScroll(),motionFilter=WandMotionFilter(),dwell=WandDwellClick(),recenterGesture=WandRecenterGesture(),flickScroll=WandFlickScroll()
 var pointerRouter=WandPointerRouter(),tripleClick=WandTripleClick(),restFollow=WandRestFollowMemory()
 var pendingRecenter:Timer?,clickFollowChoice:(following:Bool,paused:Bool,restore:Bool?,rest:WandRestFollowMemory)?
 var screenshotTimer:Timer?,screenshotSettleTimer:Timer?,dwellTimer:Timer?,heldSafetyTimer:Timer?
 var controlVersion=WandControlVersion.scrollV2,ready=true,restoring=false,scrollActive=false,flickScrollEnabled=false
 var screenshotActive=false,screenshotHUD=false,hudSession=false,hudActive=false,pointerInHUD=false,middleOperating=false,middleHeld=false,hudEntryPress=false,acceptHUDContext=true,hudOpenedAt=0.0
 var recordingPointerPaused=false,recordingRestoreFollow:Bool?,recenterSuppressButtons=false
 var heldTargetToken=UUID(),heldScrollAnchor:CGPoint?,flickAnchor:CGPoint?,deliveryPoint:CGPoint?
 var pointerDisplays=[CGRect(x:0,y:0,width:2000,height:1000)]
 var buttons=0,movementCount=0,reportCount=0,rawLastArrival=0.0,rawWindowStart=0.0,rawReports=0,rawMaxGap=0.0,middleMouseX=0.0,middleMouseSampleAt = -100.0
 var commands:[String]=[],downs=0,ups=0,holds=0,wheels=0
 static var selector=true
 static var moves:[(buttons:Int,to:CGPoint)]=[]
 static func screenshotSelectorVisible()->Bool {selector}
 static func mouseMovementEvent(buttons:Int,from:CGPoint,to:CGPoint)->Posted? {moves.append((buttons,to));return Posted()}
 static func wheelEvents(x:Int32,y:Int32,at:CGPoint?)->[CGEvent]{[]}
 func transition(to next:Int,at:CGPoint){if buttons & 1 == 0 && next & 1 != 0 {downs+=1};if buttons & 1 != 0 && next & 1 == 0 {ups+=1};buttons=next}
 func releaseButtons(){transition(to:0,at:.zero)}
 func queue(_ s:String){commands.append(s)}
 func syncRecordingLight(){}
 func status(){}
 func performPointer(_ a:[WandPointerRouter.Action]){}
 func setCircleLight(_ on:Bool){if on {wheels+=1}}
 func cancelCircleScroll(){}
 func finishScroll(){}
 func stopHUDWatchdog(){}
 func beginBottomHold(now:Double){holds+=1}
 func finishBottomHold(now:Double,resumeMouse:Bool=true){}
 func probeHoldTarget(at:CGPoint,token:UUID){}
 func enableMouseAfterScroll(){}
 func receive(_ line:String){for _ in [0] {
${bottom}
${follow}
 }}
 ${['setScreenshotActive','screenshotContextChanged','takeScreenshotPointer','screenshotBottom','startScreenshotShortcut','superviseScreenshot','checkScreenshot','latchScreenshotIfReady','handleScreenshotRaw','scheduleScreenshotSettle','finishScreenshotDrag','endScreenshot','recognizeBottomRecenter','recenterPointer','recordingChanged','manualPointerDuringRecording','enterPointerMode','postPointerMove','handleRaw','handleFrame','reconcileBottomHold','scheduleDwell'].map(method).join('\n')}
}
func wait(_ s:Double){RunLoop.main.run(until:Date().addingTimeInterval(s))}
let move="10000,2680,0,4",heldMove="10000,2680,0,5",still="10000,0,0,4"
func make(follow:Bool)->Harness {let h=Harness();precondition(h.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]));h.dwell.follow(follow);Harness.selector=true;Harness.moves=[];return h}
func tap(_ h:Harness,_ seconds:Double=0.06){h.receive("@BOTTOM 1");wait(seconds);h.receive("@BOTTOM 0")}
func dragThenStop(_ h:Harness){for _ in 0..<5 {h.handleRaw(move)};for _ in 0..<3 {h.handleRaw(still)};wait(0.3)}

// HUD-started capture with ordinary mouse follow off, then on.
for following in [false,true] {
 let h=make(follow:following);h.hudSession=true
 if following {h.dwell.move(dx:40,dy:0,now:ProcessInfo.processInfo.systemUptime,eligible:true)}
 h.setScreenshotActive(true)
 precondition(h.screenshot.phase == .aiming && h.commands.suffix(2)==["global.wandShot=1;setMouseFollow(moveLatched);wakeGyro();","setHUDOpen(false);"],"entry asks for screenshot motion without changing follow, then parks the HUD")
 precondition(!h.hudSession && h.screenshotHUD && h.controls.phases.last=="park","entry parks the HUD through the existing screenshot park flow")
 h.setScreenshotActive(true);precondition(h.screenshot.phase == .aiming,"a repeated heartbeat changes nothing")
 for _ in 0..<5 {h.handleRaw(move)}
 precondition(!Harness.moves.isEmpty && Harness.moves.allSatisfy{$0.buttons==0} && h.downs==0,"aiming moves the pointer with follow off and never presses")
 h.receive("@FOLLOW "+(following ? "0":"1"))
 precondition(h.dwell.following==following,"stale wand follow edges never change the choice during screenshot mode")
 h.receive("@BOTTOM 1")
 precondition(h.downs==1 && h.screenshot.dragging && h.buttons==1,"one Bottom tap latches the left drag")
 h.receive("@BOTTOM 0");h.handleRaw(still);h.handleFrame(x:0,y:0,b:0)
 h.reconcileBottomHold(down:false,now:ProcessInfo.processInfo.systemUptime,reason:"sensor button state")
 h.controlVersion = .pointerV1;h.reconcileBottomHold(down:false,now:ProcessInfo.processInfo.systemUptime,reason:"sensor button state");h.controlVersion = .scrollV2
 precondition(h.screenshot.dragging && h.buttons==1 && h.ups==0,"physical release, up telemetry and legacy frames leave it latched")
 let before=Harness.moves.count
 dragThenStop(h)
 precondition(Harness.moves.count>before && Harness.moves.dropFirst(before).allSatisfy{$0.buttons==1},"aiming after the latch drags the selection")
 precondition(h.ups==1 && h.buttons==0 && h.screenshot.phase == .done,"stopping ends the drag through the shared dwell timing")
 precondition(h.commands.last=="global.wandShot=0;sleepGyro();","screenshot motion stops with the selection")
 for _ in 0..<5 {h.handleRaw(move)};wait(0.3)
 precondition(h.ups==1 && h.downs==1,"the release happens exactly once")
 precondition(!logged.contains("HIGH_DWELL_CLICK") && warps==0 && h.wheels==0 && h.holds==0,"no ordinary click, recentre, scroll or hold leaks")
 h.setScreenshotActive(false)
 precondition(h.screenshot.phase == .idle && h.hudSession && h.commands.last=="setHUDOpen(true);","capture end returns the waiting HUD")
 precondition(h.dwell.following==following && !h.commands.contains{$0.contains("setMouseFollow(true)") || $0.contains("setMouseFollow(false)")},"the normal follow choice is untouched")
}

// HIGH sensitivity: Bottom down for the click never selects LOW.
let high=make(follow:false),low=make(follow:false);high.setScreenshotActive(true);low.setScreenshotActive(true)
Harness.moves=[];for _ in 0..<6 {high.handleRaw(move)};let highX=Harness.moves.reduce(0.0){$0+$1.to.x}
Harness.moves=[];for _ in 0..<6 {low.handleRaw(heldMove)};let lowX=Harness.moves.reduce(0.0){$0+$1.to.x}
precondition(highX==lowX,"physical Bottom state does not change screenshot sensitivity")

// Cancellations always lift the native press.
let cancelled=make(follow:false);cancelled.setScreenshotActive(true);cancelled.receive("@BOTTOM 1")
precondition(cancelled.screenshot.dragging);cancelled.setScreenshotActive(false)
precondition(cancelled.ups==1 && cancelled.screenshot.phase == .idle && cancelled.commands.last=="global.wandShot=0;sleepGyro();","native cancellation or context expiry lifts the drag")
cancelled.receive("@BOTTOM 0");precondition(cancelled.holds==0,"the latching tap's release stays consumed after cancellation")
let lost=make(follow:true);lost.setScreenshotActive(true);lost.receive("@BOTTOM 1");wait(0.95)
precondition(lost.ups==1 && lost.screenshot.phase == .done && lost.dwell.following,"lost wand telemetry lifts the drag")
let reset=make(follow:false);reset.setScreenshotActive(true);reset.receive("@BOTTOM 1")
reset.endScreenshot(reason:"receiver reset",contextActive:true,forgetPress:true)
precondition(reset.ups==1 && reset.screenshot.phase == .done && !reset.screenshot.consumeRelease,"disconnect lifts the drag and forgets the stale press")
let again=make(follow:false);again.setScreenshotActive(true);again.receive("@BOTTOM 1");again.receive("@BOTTOM 0");again.receive("@BOTTOM 1")
precondition(again.ups==1 && again.screenshot.phase == .done,"a fresh Bottom press finishes the selection now")
again.receive("@BOTTOM 0");precondition(again.holds==0,"and its release is consumed")

// Triple-click: follow off and paused by recording; firmware follow edges replayed.
let t=make(follow:false);t.recordingPointerPaused=true;t.recordingRestoreFollow=true
t.receive("@BOTTOM 1");t.receive("@FOLLOW 1");wait(0.06);t.receive("@BOTTOM 0");wait(0.1)
t.receive("@BOTTOM 1");t.receive("@FOLLOW 0");wait(0.06);t.receive("@BOTTOM 0")
precondition(t.pendingRecenter != nil && warps==0,"the double click waits for a possible third press")
wait(0.1);t.receive("@BOTTOM 1");t.receive("@FOLLOW 1")
precondition(t.controls.starts==1 && t.pendingRecenter==nil && t.screenshot.phase == .pending,"the third press requests the native selection")
precondition(!t.dwell.following && t.recordingPointerPaused && t.recordingRestoreFollow==true,"the clicks' follow and recording-override effects are undone")
precondition(t.commands.last=="global.wandShot=1;setMouseFollow(false);wakeGyro();","the wand restores follow off and supplies screenshot motion")
precondition(t.holds==2,"the third press never becomes an ordinary hold")
t.receive("@BOTTOM 0");precondition(t.holds==2 && !t.pointerRouter.bottomHeld,"its release is consumed")
for _ in 0..<5 {t.handleRaw(move)}
precondition(!Harness.moves.isEmpty && t.downs==0,"recording-paused follow still lets screenshot aim; nothing presses before the selector")
Harness.selector=false;t.setScreenshotActive(true)
for _ in 0..<4 {t.handleRaw(still);wait(0.05)}
precondition(t.screenshot.phase == .aiming && t.screenshot.anchorRequested && t.downs==0,"no press until macOS shows the selector")
Harness.selector=true;t.handleRaw(still);wait(0.08)
precondition(t.downs==1 && t.screenshot.dragging,"the drag anchors at the shown pointer with no fourth click")
precondition(warps==0,"no recentre before the screenshot anchor")
dragThenStop(t)
precondition(t.ups==1 && t.screenshot.phase == .done,"stop-to-click ends the shortcut's selection")
t.setScreenshotActive(false)
precondition(t.recordingPointerPaused && !t.dwell.following && t.screenshot.phase == .idle,"recording pause and follow choice survive the screenshot")

// Recording changes between taps are newer choices than the first-click snapshot.
let changed=make(follow:true);tap(changed);changed.receive("@FOLLOW 0");changed.recordingChanged(true)
wait(0.06);tap(changed);wait(0.06);changed.receive("@BOTTOM 1")
precondition(changed.recordingPointerPaused && !changed.dwell.following && changed.recordingRestoreFollow==true,"recording started between taps must retain the original follow choice and its newer pause")
changed.receive("@BOTTOM 0");changed.endScreenshot(reason:"test cleanup",contextActive:false)
let stopped=make(follow:false);stopped.recordingPointerPaused=true;stopped.recordingRestoreFollow=true
 tap(stopped);stopped.recordingChanged(false);wait(0.06);tap(stopped);wait(0.06);stopped.receive("@BOTTOM 1")
precondition(!stopped.recordingPointerPaused && stopped.dwell.following,"recording stopped between taps must keep its newer restored follow choice")
stopped.receive("@BOTTOM 0");stopped.endScreenshot(reason:"test cleanup",contextActive:false)

// A double click alone still centres and enables follow, after the window.
let d=make(follow:false);tap(d);wait(0.1);tap(d)
precondition(warps==0 && d.pendingRecenter != nil);wait(0.35)
precondition(warps==1 && d.dwell.following && d.controls.starts==0 && d.commands.last!.contains("setMouseFollow(true)"),"double click centres once its window passes")
// A later unrelated press after a double click centres first, as before.
let early=make(follow:false);tap(early);wait(0.1);tap(early);wait(0.01);early.receive("@BOTTOM 1")
precondition(warps==2 && early.controls.starts==0,"a bounce-fast third press is not the shortcut; the centre runs at once")
early.receive("@BOTTOM 0")
// A held second press is the explicit drag, never a screenshot.
let held=make(follow:false);tap(held);wait(0.1);held.receive("@BOTTOM 1");wait(0.3);held.receive("@BOTTOM 0");wait(0.1);tap(held)
precondition(held.controls.starts==0,"tap then hold then tap is not a triple click")
// Unavailable native route: the third press is still consumed and follow restored.
let missing=make(follow:true);missing.controls.available=false
tap(missing);wait(0.1);tap(missing);wait(0.1);missing.receive("@BOTTOM 1")
precondition(missing.controls.starts==1 && missing.screenshot.phase == .idle && missing.commands.last=="setMouseFollow(true);" && missing.holds==2,"an unavailable start consumes the gesture and restores follow")
missing.receive("@BOTTOM 0");precondition(missing.holds==2)
// A requested selection that never arrives returns the pointer.
let silent=make(follow:false);tap(silent);wait(0.1);tap(silent);wait(0.1);silent.receive("@BOTTOM 1");silent.receive("@BOTTOM 0")
precondition(silent.screenshot.ownsPointer);wait(0.95)
precondition(!silent.screenshot.ownsPointer && silent.downs==0 && silent.commands.last=="global.wandShot=0;sleepGyro();","no native selection: screenshot motion ends without a press")

// Pure recogniser and lifecycle rules.
var r=WandTripleClick()
precondition(r.edge(down:true,now:0) == .first);_=r.edge(down:false,now:0.05);_=r.edge(down:true,now:0.15);_=r.edge(down:false,now:0.2)
precondition(r.edge(down:true,now:0.55) == .first,"a gap beyond 300 ms starts a fresh run")
_=r.edge(down:false,now:0.6);_=r.edge(down:true,now:0.7);_=r.edge(down:false,now:0.75);r.cancel()
precondition(r.edge(down:true,now:0.8) == .first,"reset forgets a stale run")
_=r.edge(down:false,now:0.85);_=r.edge(down:true,now:0.95);_=r.edge(down:false,now:1.0)
precondition(r.edge(down:true,now:1.1) == .third && r.edge(down:false,now:1.2) == .none)
let g=WandScreenshotGesture();precondition(g.requestShortcut(now:10) && g.expired(now:10.7)==nil && g.expired(now:10.9)=="telemetry lost","missing wand telemetry ends a pending start")
g.telemetry(now:12);precondition(g.expired(now:12.1)=="native start timed out","Agentic Mouse must report the selection within two seconds")
precondition(g.settle.pause==0.2 && g.settle.travel==12,"the settle uses the ordinary stop-to-click timing")
print("PASS: screenshot ownership, latch, settle, cancellation and triple-click")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-screenshot-'));
 try {const out=swiftc(dir,code,[new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname]);assert.match(out,/PASS/);}finally{rmSync(dir,{recursive:true,force:true});}
});

test('triple-click start packet is exactly the native screenshot start command',{skip:process.platform!=='darwin'},()=>{
 const start=transport.indexOf('    func screenshotStart('),end=transport.indexOf('\n    func speech(',start);
 assert(start>=0&&end>start);
 const code=`import Foundation
final class Transport {
 let agenticPath="test-only";var packets:[(object:[String:Any],limit:Int)]=[]
 func send(_ object:[String:Any],path:String,limit:Int)->Bool {packets.append((object,limit));return true}
 ${transport.slice(start,end)}
}
let t=Transport();precondition(t.screenshotStart());precondition(t.screenshotStart(id:"AC1718F8-B050-47BB-B763-5BA765D69F93"))
let first=t.packets[0].object,second=t.packets[1].object
precondition(Set(first.keys)==["command","version","id"] && first["command"] as? String=="agentic_mouse_wand_screenshot_start" && first["version"] as? Int==1)
precondition(UUID(uuidString:first["id"] as! String) != nil && second["id"] as? String=="AC1718F8-B050-47BB-B763-5BA765D69F93" && t.packets[0].limit==256)
let data=try! JSONSerialization.data(withJSONObject:first,options:[.sortedKeys]);precondition(data.count<=256)
print("PASS: screenshot start packet")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-screenshot-start-'));
 try {assert.match(swiftc(dir,code),/PASS/);}finally{rmSync(dir,{recursive:true,force:true});}
});
