import {fileURLToPath as wandSourcePath} from 'node:url';
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

// Ethan's smart Bottom hold: scroll over a real scroll area, native drag over
// a draggable target, and never a drag while the target is unknown. The real
// receiver methods run with an inert, scripted Accessibility answer.
const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
const pointer=readFileSync(new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url),'utf8');
const ready=pointer.includes('enum WandHoldTarget')&&source.includes('    func probeHoldTarget(');

test('Bottom hold scrolls scroll areas, drags draggable targets and never drags on doubt',{skip:process.platform!=='darwin'||!ready},()=>{
 function method(name){const a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
 const code=`import Foundation
func AXIsProcessTrusted()->Bool {true}
var logged:[String]=[]
func log(_ v:Any...) {logged.append(v.map{"\\($0)"}.joined(separator:" "))}
enum Tap {case cghidEventTap}
final class CGEvent {var location=CGPoint.zero;init?(source:Int?){ };func post(tap:Tap){}}
final class Rest {var activated=false;func pointerActivated(){activated=true};func pointerStopped(){activated=false}}
final class SwitchAppContext {var switchAppAdjusting=false}
final class Harness {
 let context=SwitchAppContext()
 let switchAppWinding=WandSwitchAppWinding()
 var actionPause=WandActionPause()
 let screenshot=WandScreenshotGesture();var screenshotRaw=0;func handleScreenshotRaw(_ v:[Int],now:Double){screenshotRaw+=1}
 let restDetection=Rest()
 let heldScroll=WandHeldScroll(),pointerRouter=WandPointerRouter(),motionFilter=WandMotionFilter(),dwell=WandDwellClick(),recenterGesture=WandRecenterGesture(),flickScroll=WandFlickScroll()
 var heldSafetyTimer:Timer?,heldTargetToken=UUID(),heldScrollAnchor:CGPoint?,deliveryPoint:CGPoint?,flickAnchor:CGPoint?
 var controlVersion=WandControlVersion.scrollV2,ready=true,restoring=false,scrollActive=false,hudSession=false,flickScrollEnabled=false,heldScrollDiagnostics=false
 var screenshotActive=false,middleHeld=false,middleMouseX=0.0,middleMouseSampleAt = -100.0
 var commands:[String]=[],scrollPostedX=0,scrollPostedY=0
 var scrollFollowOffUntil:Double?,recordingPointerPaused=false,recordingRestoreFollow:Bool?,restFollow=WandRestFollowMemory()
 static let scrollFollowOffConfirmSeconds=1.0
 var scrollAnchor:CGPoint?,scrollWatchdog:Timer?
 var rawLastArrival=0.0,rawWindowStart=0.0,rawReports=0,rawMaxGap=0.0,buttons=0,frames=0,downs=0,light=false
 let holdTargetQueue=DispatchQueue(label:"test.hold-target")
 static var scriptedRoles:[String]=[]
 static var probeDelay=0.0
 static var probes=0
 static func holdTargetRoles(at point:CGPoint,budget:TimeInterval=0.06)->[String]{
  probes+=1
  if probeDelay>0 {Thread.sleep(forTimeInterval:probeDelay)}
  return scriptedRoles
 }
 func transition(to:Int,at:CGPoint){if to==1 && buttons==0 {downs+=1};buttons=to}
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
 static func wheelEvents(x:Int32,y:Int32,at:CGPoint?)->[CGEvent]{wheelPairs.append((x,y));return []}
 ${['beginBottomHold','probeHoldTarget','leaveMouseOffAfterScroll','manualPointerDuringRecording','finishScroll','finishBottomHold','reconcileBottomHold','handleRaw'].map(method).join('\n')}
}
func wait(_ seconds:Double){RunLoop.main.run(until:Date().addingTimeInterval(seconds))}
func press(_ roles:[String],delay:Double=0)->Harness {
 let h=Harness();precondition(h.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
 Harness.scriptedRoles=roles;Harness.probeDelay=delay
 _=h.recenterGesture.edge(down:true,now:ProcessInfo.processInfo.systemUptime)
 h.beginBottomHold(now:ProcessInfo.processInfo.systemUptime)
 if h.heldScroll.resolving {h.probeHoldTarget(at:.zero,token:h.heldTargetToken)}
 _=h.pointerRouter.bottom(down:true)
 return h
}

// Classification: only a positive answer can drag.
precondition(WandHoldTarget.classify(roles:["AXStaticText","AXGroup","AXScrollArea"]) == .scroll)
precondition(WandHoldTarget.classify(roles:["AXGroup","AXWebArea"]) == .scroll,"web documents scroll")
precondition(WandHoldTarget.classify(roles:["AXValueIndicator","AXScrollBar","AXScrollArea"]) == .drag,"a scroll bar thumb drags")
precondition(WandHoldTarget.classify(roles:["AXSlider"]) == .drag && WandHoldTarget.classify(roles:["AXSplitter"]) == .drag)
precondition(WandHoldTarget.classify(roles:["AXToolbar","AXWindow"]) == .drag,"a title bar or toolbar drags the window")
precondition(WandHoldTarget.classify(roles:["AXDockItem","AXList","AXApplication"]) == .drag)
precondition(WandHoldTarget.classify(roles:[]) == .unknown,"a failed hit test proves nothing")
precondition(WandHoldTarget.classify(roles:["AXTextField","AXGroup"]) == .unknown,"a broken chain proves nothing")

precondition(WandHoldTarget.classify(roles:["AXStaticText","AXGroup","AXNotificationCenterAlert","AXScrollArea"]) == .drag,"a notification is a native drag target")

// Screenshot mode owns Bottom before any ordinary hold (native-screenshot
// test). A screenshot context alone never turns an ordinary hold into a press.
let shot=Harness();shot.screenshotActive=true
precondition(shot.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
shot.beginBottomHold(now:ProcessInfo.processInfo.systemUptime)
precondition(shot.buttons==0 && !shot.heldScroll.dragging && shot.heldScroll.resolving,"an ordinary hold keeps its target probe")
shot.finishBottomHold(now:ProcessInfo.processInfo.systemUptime)
let owned=Harness();precondition(owned.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
owned.heldScroll.begin(now:ProcessInfo.processInfo.systemUptime);_=owned.screenshot.requestShortcut(now:ProcessInfo.processInfo.systemUptime)
owned.handleRaw("10000,0,0,0")
precondition(owned.screenshotRaw==1 && owned.heldScroll.active,"screenshot ownership precedes the raw button-up reconciliation")

// Over a scroll area: scrolls, never presses the mouse button.
let scroll=press(["AXStaticText","AXScrollArea"]);wait(0.05)
precondition(scroll.heldScroll.scrollable && !scroll.heldScroll.resolving,"the answer arrives before the hold decision")
wait(0.22);Harness.wheelPairs=[]
for _ in 0..<30 {scroll.handleRaw("10000,0,2680,1")}
precondition(!Harness.wheelPairs.isEmpty && scroll.downs==0,"a scroll area scrolls and never drags")
scroll.handleRaw("10000,0,2680,0");precondition(!scroll.heldScroll.active && scroll.buttons==0)

// Over a draggable target: a native drag after the existing 220 ms decision.
let drag=press(["AXGroup","AXWindow"]);wait(0.05)
precondition(!drag.heldScroll.scrollable,"a window surface is a drag target")
drag.handleRaw("10000,0,2680,1")
precondition(drag.downs==0,"a short tap can never become a drag")
wait(0.2);drag.handleRaw("10000,0,2680,1")
precondition(drag.downs==1 && drag.buttons==1 && drag.heldScroll.dragging,"one native button-down once the hold qualifies")
Harness.wheelPairs=[];drag.handleRaw("10000,0,2680,1");precondition(Harness.wheelPairs.isEmpty,"a drag never scrolls")
drag.handleRaw("10000,0,2680,0");precondition(drag.buttons==0 && !drag.heldScroll.active,"release always lifts the button")

// Unknown answer: keeps scrolling, never selects text.
let unknown=press([]);wait(0.27)
for _ in 0..<30 {unknown.handleRaw("10000,0,2680,1")}
precondition(unknown.downs==0 && unknown.heldScroll.scrollable,"an unknown target scrolls")
unknown.handleRaw("10000,0,2680,0")

// Slow answer: the hold settles on scrolling at the decision and the late
// drag answer can never flip it mid-gesture.
let slow=press(["AXWindow"],delay:0.35);wait(0.25)
for _ in 0..<10 {slow.handleRaw("10000,0,2680,1")}
precondition(slow.heldScroll.scrollable && !slow.heldScroll.resolving && slow.downs==0,"unresolved at the decision: scroll")
wait(0.2);slow.handleRaw("10000,0,2680,1")
precondition(slow.heldScroll.scrollable && slow.downs==0,"a late drag answer is ignored")
precondition(logged.contains{ $0.contains("late") },"the late answer is recorded, not applied")
slow.handleRaw("10000,0,2680,0")

// Answer after release: the gesture token drops it.
let gone=press(["AXWindow"],delay:0.1)
gone.finishBottomHold(now:ProcessInfo.processInfo.systemUptime);_=gone.pointerRouter.bottom(down:false)
wait(0.2)
precondition(!gone.heldScroll.active && gone.downs==0 && gone.buttons==0,"a reply for a finished hold never acts")

// Explicit tap-then-hold: always a native drag, with no probe at all.
let explicit=Harness();precondition(explicit.motionFilter.configure([0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]))
let t=ProcessInfo.processInfo.systemUptime
_=explicit.recenterGesture.edge(down:true,now:t-1);_=explicit.recenterGesture.edge(down:false,now:t-0.95)
_=explicit.recenterGesture.edge(down:true,now:t-0.85)
let before=Harness.probes
explicit.beginBottomHold(now:t-0.85)
precondition(!explicit.heldScroll.resolving && !explicit.heldScroll.scrollable && Harness.probes==before,"no probe for the explicit drag")
explicit.handleRaw("10000,0,2680,1");precondition(explicit.downs==1,"explicit drag still presses")
explicit.handleRaw("10000,0,2680,0");precondition(explicit.buttons==0)
print("PASS: contextual Bottom hold")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-context-hold-'));
 try {writeFileSync(join(dir,'main.swift'),code);const built=spawnSync('swiftc',[wandSourcePath(new URL('../receiver/Sources/WandRunLoop.swift',import.meta.url)),'-Onone',new URL('../receiver/Sources/WandActionPause.swift',import.meta.url).pathname,new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(built.status,0,built.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
