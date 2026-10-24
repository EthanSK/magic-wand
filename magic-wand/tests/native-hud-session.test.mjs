import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

// Compile the actual receiver methods with inert transports. No BLE owner,
// native mouse events or installed Agentic Mouse process is involved.
test('native HUD close cancels actions, rejects stale context and closes any child', {skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 const method=(name)=>{
  const start=source.indexOf('    func '+name+'(');assert(start>=0,name);
  const open=source.indexOf('{',start);let depth=1,end=open+1;
  while(depth){if(source[end]==='{')depth++;if(source[end]==='}')depth--;end++;}
  return source.slice(start,end);
 };
 const a=source.indexOf('        context.onChange = '),b=source.indexOf('\n        context.start()',a);
 const callback=source.slice(a,b);
 const modeStart=source.indexOf('        context.onModeChange = '),modeEnd=source.indexOf('        // Review selection',modeStart);
 const modeCallback=source.slice(modeStart,modeEnd);
 const code=`import Foundation
func AXIsProcessTrusted()->Bool {true}
func log(_ parts:Any...) {}
enum CGEventType {case leftMouseDragged,rightMouseDragged,mouseMoved}
enum CGMouseButton {case left,right}
enum EventTap {case cghidEventTap}
final class CGEvent {
 static var posted=0
 init?(mouseEventSource:Int?,mouseType:CGEventType,mouseCursorPosition:CGPoint,mouseButton:CGMouseButton){}
 func post(tap:EventTap){Self.posted+=1}
}
final class Recording {var isRecording=false}
final class Rest {var parked=false;func pointerActivated(){parked=false};func pointerStopped(){}}
final class Context {var isActive=false,isFresh=true;var onChange:((Bool)->Void)?;var onModeChange:((String?)->Void)?;func set(_ v:Bool){isActive=v;onChange?(v)}}
final class Application {var bundleIdentifier="com.microsoft.VSCode"}
final class NSWorkspace {static let shared=NSWorkspace();var frontmostApplication:Application?=Application()}
final class Trace {var boundaries:[String]=[];func boundary(_ reason:String,mode:String?=nil,now:Double=0){boundaries.append(reason)}}
final class Controls {var phases:[String]=[];func persistent(_ phase:String,x:Double=0,y:Double=0){phases.append(phase)}}
final class Review {func cancel()->[Int]{[]};var isHeld=false;var committed=false;var starts:[String]=[];var inputs=0;func beginDetents(mode:String,now:Double){starts.append(mode)};func motion(y:Double,now:Double)->[Int]{[]};func detents(_ count:Int32,now:Double)->[Int]{inputs+=1;return[]};func endDetents(commit:Bool)->[Int]{committed=commit;return[]}}
final class Harness {
 let context=Context(),controls=Controls(),review=Review(),motionFilter=WandMotionFilter(),reviewTrace=Trace(),recording=Recording(),dwell=WandDwellClick()
 var deskSleep=WandDeskSleep()
 var recordingPointerPaused=false,recordingRestoreFollow:Bool?
${source.includes('var restFollow=WandRestFollowMemory()')?' var restFollow=WandRestFollowMemory()':''}
 let restDetection=Rest()
 var ready=true,restoring=false,scrollActive=false,acceptHUDContext=true
 var buttons=0,movementCount=0,pointerDisplays=[CGRect(x:0,y:0,width:1000,height:1000)]
 var selectedReviewMode:String?,hiddenReviewOperating=false,hiddenReviewPending=false,screenshotActive=false,screenshotHUD=false
 var hudSession=false,hudEntryPress=false,hudActive=false,pointerInHUD=false,middleOperating=false,middleSecondTap=false,navigationOpenedHUD=false
 var middleHeld=false,hudOpenedAt=0.0
 var wandShortcutMode:String?,wandShortcutX=0.0,wandShortcutY=0.0,wandShortcutTime=0.0
 var wandShortcutCircle=WandReviewNavigation();var middleReviewExit=false
 var reviewExitGesture=WandReviewExitGesture();var reviewExitTimer:Timer?
 var pointerRouter=WandPointerRouter()
 var deliveryPoint:CGPoint?
 func performPointer(_ actions:[WandPointerRouter.Action]){}
 func scheduleDwell(){}
 func syncRecordingLight(){}
 func status(){}
 var appMode:String?,reviewTimer:Timer?,middleTap:Timer?,middleHold:Timer?,hudWatchdog:Timer?
 var middleLastRelease = -100.0,middlePressedAt=0.0,middleDoubleConsumed=false,hudEntryPressStarted=0.0
 var reviewOriginY=0.0,navX=0.0,navY=0.0,navOriginX=0.0,navOriginY=0.0,operationOriginX=0.0,operationOriginY=0.0,middleX=0.0,middleY=0.0
 var navStream=WandAngularStream(),moveStream=WandAngularStream(),legacyHUDStream=WandAngularStream()
 var hudLastUpdate=Date.distantPast,commands:[String]=[]
 var hudDoubleClickInterval:Double {0.3}
 func queue(_ s:String){commands.append(s)}
 func setWandShortcut(_ mode:String?){wandShortcutMode=mode}
 func cancelCircleScroll(){}
 func sendReview(_ v:[Int]){}
 var traceInputs=0
 func recordReviewInput(rawX:Double,rawY:Double,dx:Double,dy:Double,now:Double,blocked:String?,step:Int32){traceInputs+=1}
 func releaseButtons(){}
 init(){${callback}
${modeCallback}}
 ${['setScreenshotActive','finishWandShortcut','exitSelectedReview','commitSelectedReview','beginReviewCommitHold','commitReviewHold','closeHUD','enterPointerMode','handleMiddle','handleMove','handleNavigation','resumeHUDNavigation','handleHUD','startHUDWatchdog','stopHUDWatchdog','postPointerMove','recordingChanged','manualPointerDuringRecording'].map(method).join('\n')}
}
func settle(_ seconds:Double){RunLoop.main.run(until:Date().addingTimeInterval(seconds))}
// Ethan's hold-to-show HUD. Holding Middle shows and steers it; releasing
// uses the outlined card; Agentic Mouse closes it after an ordinary action
// and keeps it open only for a submenu or a card that needs more motion.
let h=Harness()
h.handleMiddle("1")
precondition(h.hudSession && h.middleHeld && Array(h.controls.phases.suffix(2))==["open","navigate"] && h.commands.contains("setHUDOpen(true);"),"holding Middle shows and steers the HUD")
h.context.set(true);h.handleNavigation("8000,0")
precondition(h.controls.phases.last=="motion","held motion steers the outline")
h.middlePressedAt-=0.3;h.handleMiddle("0")
precondition(Array(h.controls.phases.suffix(3))==["motion","park","choose"] && !h.middleHeld && !h.hudActive,"releasing a hold uses the outlined card at once")
let beforeClose=h.controls.phases.count
h.context.set(false)
precondition(!h.hudSession && !h.controls.phases.dropFirst(beforeClose).contains("dismiss"),"Agentic Mouse closed it, so no dismiss cuts short the action's follow-up")
h.context.set(true);h.handleNavigation("20000,0");h.handleHUD("B,0,0");h.handleMove("B,0,0");settle(0.35)
precondition(!h.hudSession && h.controls.phases.count==beforeClose,"a stale positive heartbeat never reopens or steers a closed HUD")

let menu=Harness();menu.handleMiddle("1");menu.context.set(true);menu.middlePressedAt-=0.3;menu.handleMiddle("0")
precondition(menu.hudSession && !menu.hudActive,"a kept-open HUD waits for the next hold")
let waiting=menu.controls.phases.count
menu.handleNavigation("9000,0")
precondition(menu.controls.phases.count==waiting,"an unheld HUD never moves its outline")
menu.handleMiddle("1")
precondition(menu.controls.phases.last=="navigate" && menu.middleHeld && !menu.controls.phases.dropFirst(waiting).contains("open"),"the next hold steers the page or adjusts the armed card")
menu.handleNavigation("0,7000");menu.middlePressedAt-=0.3;menu.handleMiddle("0")
precondition(menu.controls.phases.last=="choose")

let tap=Harness();tap.handleMiddle("1");tap.context.set(true);tap.handleMiddle("0")
precondition(tap.middleTap != nil && tap.controls.phases.last=="park","a tap waits out the double-click window")
settle(0.35)
precondition(tap.controls.phases.last=="activate" && tap.middleTap == nil,"a lone tap then uses the outlined card")
let double=Harness();double.handleMiddle("1");double.context.set(true);double.handleMiddle("0");double.handleMiddle("1")
precondition(!double.hudSession && double.controls.phases.last=="dismiss","double click still dismisses")
double.handleMiddle("0");settle(0.35)
precondition(!double.controls.phases.contains("activate") && !double.controls.phases.contains("choose") && !double.hudSession,"and never acts")
let lateTap=Harness();lateTap.handleMiddle("1");lateTap.context.set(true);lateTap.handleMiddle("0")
lateTap.middleLastRelease = -100;lateTap.handleMiddle("1")
precondition(lateTap.middleTap == nil && Array(lateTap.controls.phases.suffix(2))==["activate","navigate"],"a tap whose window ended is used before the next hold, never lost")
let hidden=Harness();hidden.handleMiddle("1");hidden.context.set(true);hidden.handleMiddle("0");hidden.context.set(false);settle(0.4)
precondition(!hidden.controls.phases.contains("activate"),"a closed HUD cancels the pending tap")
let racing=Harness();racing.handleMiddle("1");racing.context.set(true);racing.context.set(false)
precondition(racing.hudSession && racing.middleHeld,"a close during a live hold waits for its release")
racing.middlePressedAt-=0.3;racing.handleMiddle("0")
precondition(racing.controls.phases.last=="choose")
let lost=Harness();lost.handleMiddle("1");lost.hudLastUpdate=Date.distantPast;settle(0.3)
precondition(!lost.hudSession && !lost.acceptHUDContext && lost.controls.phases.last=="dismiss","lost telemetry during a hold clears the whole session")
lost.context.set(true);precondition(!lost.hudSession)
let stale=Harness();stale.hudSession=true;stale.hudOpenedAt=ProcessInfo.processInfo.systemUptime-5;stale.handleMiddle("1")
precondition(stale.hudSession && stale.middleHeld && stale.controls.phases.contains("open"),"a session Agentic Mouse no longer shows restarts as a fresh HUD")
let shortcut=Harness();shortcut.hudSession=true;shortcut.pointerInHUD=true;shortcut.middleOperating=true;shortcut.wandShortcutMode="changes"
shortcut.handleMiddle("0")
precondition(shortcut.wandShortcutMode==nil && shortcut.review.committed,"physical Middle release immediately finishes review")
shortcut.wandShortcutMode="files";shortcut.closeHUD(reason:"disconnect")
precondition(shortcut.wandShortcutMode==nil && !shortcut.review.committed,"lost HUD cancels review")
let screenshot=Harness();screenshot.hudSession=true;screenshot.hudActive=true
screenshot.setScreenshotActive(true);screenshot.enterPointerMode()
precondition(!screenshot.hudSession && screenshot.screenshotHUD)
precondition(!screenshot.controls.phases.contains("dismiss"))
screenshot.setScreenshotActive(false)
precondition(screenshot.hudSession && !screenshot.hudActive && !screenshot.screenshotHUD,"the HUD returns waiting, never steering unheld")
let pinned=Harness();pinned.selectedReviewMode="changes";pinned.wandShortcutMode="changes";pinned.handleMiddle("1")
precondition(pinned.reviewExitGesture.pending && !pinned.review.committed,"Middle-down freezes the existing working set")
for i in 1...80 {pinned.handleNavigation("\\(i*1000),\\(i*2000)")}
precondition(pinned.review.inputs==0,"held motion never reaches Better Git")
pinned.commitReviewHold(now:ProcessInfo.processInfo.systemUptime+0.6)
precondition(pinned.selectedReviewMode=="changes" && pinned.wandShortcutMode=="changes" && !pinned.controls.phases.contains("exitReview") && pinned.review.committed)
precondition(pinned.review.starts==["changes"] && pinned.reviewExitGesture.pending,"long press arms the next set but remains frozen until release")
for i in 81...160 {pinned.handleNavigation("\\(i*1000),\\(i*2000)")}
pinned.commitReviewHold(now:ProcessInfo.processInfo.systemUptime+2)
precondition(pinned.review.inputs==0 && pinned.review.starts.count==1,"continued holding neither edits nor commits the next set")
pinned.handleMiddle("0");settle(0.36)
precondition(!pinned.hudSession && pinned.selectedReviewMode=="changes" && !pinned.reviewExitGesture.pending,"release stays in review and unfreezes")
pinned.handleNavigation("161000,322000")
precondition(pinned.review.inputs==1,"new motion after release resumes review")
precondition(pinned.traceInputs==161,"accepted and blocked review points both reach diagnostic capture count="+String(pinned.traceInputs)+"")
NSWorkspace.shared.frontmostApplication?.bundleIdentifier="other"
pinned.handleNavigation("162000,324000")
precondition(pinned.review.inputs==1,"focus loss blocks review immediately, before the timer")
NSWorkspace.shared.frontmostApplication?.bundleIdentifier="com.microsoft.VSCode"
pinned.context.isFresh=false;pinned.handleNavigation("163000,326000")
precondition(pinned.review.inputs==1,"expired context cannot deliver a review step")
pinned.context.isFresh=true
pinned.handleMiddle("1");pinned.handleMiddle("0")
precondition(pinned.selectedReviewMode==nil && !pinned.review.committed,"a later short tap cancels and exits")
let cancel=Harness();cancel.selectedReviewMode="files";cancel.wandShortcutMode="files";cancel.handleMiddle("1");cancel.handleMiddle("0");settle(0.6)
precondition(cancel.selectedReviewMode==nil && cancel.wandShortcutMode==nil && !cancel.review.committed,"short tap cancels the timer without staging later")
let late=Harness();late.selectedReviewMode="files";late.wandShortcutMode="files";late.middleReviewExit=true
late.beginReviewCommitHold(now:ProcessInfo.processInfo.systemUptime-0.6);late.handleMiddle("0")
precondition(late.review.committed && late.review.starts==["files"] && late.selectedReviewMode=="files","long release works even when the timer was delayed")
let submenu=Harness();submenu.hudSession=true;submenu.context.set(true);submenu.resumeHUDNavigation()
let navigationStarts=submenu.controls.phases.filter{$0=="navigate"}.count
submenu.context.onModeChange?("vsCode")
precondition(submenu.appMode=="vsCode" && submenu.hudSession && submenu.hudActive)
precondition(submenu.controls.phases.filter{$0=="navigate"}.count==navigationStarts,"app-specific submenu must retain one navigation owner")
let asleep=Harness();asleep.hudSession=true;asleep.resumeHUDNavigation()
for i in 0...60 {_=asleep.deskSleep.sample(parked:true,buttons:false,now:100+Double(i))}
asleep.hudLastUpdate=Date.distantPast;settle(1)
precondition(asleep.hudSession && asleep.hudActive,"sleep stops NAV heartbeat without closing the HUD")
asleep.deskSleep.reset();asleep.closeHUD(reason:"test done")
let independent=Harness();independent.hudSession=true;independent.enterPointerMode();precondition(independent.hudSession,"Bottom leaves Middle HUD alone")

// Every Middle hold, including the second hold that adjusts an armed card
// such as Switch App, freezes the Bottom pointer lane for its length only.
// Use the real pointer posting and Middle/navigation handlers with inert events.
let switching=Harness(),anchor=CGPoint(x:400,y:400)
precondition(switching.postPointerMove(dx:20,dy:10,from:anchor)==CGPoint(x:420,y:410))
switching.handleMiddle("1")
let entryPosts=CGEvent.posted
for _ in 0..<100 {precondition(switching.postPointerMove(dx:30,dy:-15,from:anchor)==anchor,"a Middle hold freezes an already-following pointer")}
switching.handleNavigation("10000,0")
precondition(CGEvent.posted==entryPosts && switching.controls.phases.last=="motion","the hold still steers the HUD without moving the pointer")
switching.context.set(true);switching.middlePressedAt-=0.3;switching.handleMiddle("0")
precondition(switching.postPointerMove(dx:-20,dy:10,from:anchor)==CGPoint(x:380,y:410),"release resumes new pointer movement without replaying the held sweep")
switching.handleMiddle("1")
let pressPosts=CGEvent.posted
precondition(switching.postPointerMove(dx:60,dy:40,from:anchor)==anchor,"the second hold freezes the pointer too")
switching.handleNavigation("-20000,0");switching.handleNavigation("20000,0")
precondition(switching.controls.phases.last=="motion" && CGEvent.posted==pressPosts,"left and right reach the armed card without moving the pointer")
switching.middlePressedAt-=0.3;switching.handleMiddle("0")
precondition(switching.postPointerMove(dx:5,dy:0,from:anchor)==CGPoint(x:405,y:400),"Middle release restores pointing even while the HUD stays open")
switching.handleMiddle("1");switching.closeHUD(reason:"context ended")
precondition(switching.postPointerMove(dx:7,dy:0,from:anchor)==CGPoint(x:407,y:400),"a cancelled hold cannot leave the pointer frozen")
let independentReview=Harness();independentReview.selectedReviewMode="changes";independentReview.handleMiddle("1")
precondition(independentReview.postPointerMove(dx:8,dy:0,from:anchor)==CGPoint(x:408,y:400),"independent review commit holds retain the Bottom pointer lane")

// Recording freezes delivery and forgets speech-time travel without changing
// the latched follow choice. Exercise the actual receiver callback and emitter.
for following in [false,true] {
 let speech=Harness();speech.dwell.follow(following)
 speech.pointerRouter=WandPointerRouter(lowDelay:0.09)
 _=speech.pointerRouter.bottom(down:true)
 _=speech.pointerRouter.frame(dx:25,dy:0,buttons:0,hud:false,now:1)
 precondition(speech.pointerRouter.pendingCount==1)
 speech.dwell.move(dx:40,dy:0,now:1,eligible:true)
 speech.deliveryPoint=CGPoint(x:900,y:900)
 speech.recording.isRecording=true;speech.recordingChanged(true)
 precondition(!speech.dwell.following && speech.recordingPointerPaused && !speech.dwell.armed && speech.pointerRouter.pendingCount==0 && speech.deliveryPoint==nil)
 let before=CGEvent.posted
 for _ in 0..<100 {precondition(speech.postPointerMove(dx:50,dy:30,from:anchor)==anchor)}
 precondition(CGEvent.posted==before,"recording suppresses both pointer motion and native drag movement")
 speech.recording.isRecording=false;speech.recordingChanged(false)
 precondition(speech.dwell.following==following && !speech.dwell.armed && speech.pointerRouter.drain(now:100).isEmpty)
 precondition(speech.postPointerMove(dx:3,dy:-2,from:anchor)==CGPoint(x:403,y:398),"resume applies only new motion from the visible pointer")
}
let manual=Harness();manual.dwell.follow(true)
manual.recording.isRecording=true;manual.recordingChanged(true)
manual.manualPointerDuringRecording();manual.dwell.follow(true)
precondition(!manual.recordingPointerPaused && manual.recording.isRecording)
precondition(manual.postPointerMove(dx:6,dy:2,from:anchor)==CGPoint(x:406,y:402),"manual Bottom re-entry allows pointer movement while recording")
manual.dwell.follow(false);manual.recording.isRecording=false;manual.recordingChanged(false)
precondition(!manual.dwell.following,"recording end preserves a manual switch off")
print("PASS: hold-to-show HUD, native close, kept-open next hold, tap and double click, stale input rejection, watchdog teardown, review hold")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-hud-'));
 try {
  writeFileSync(join(dir,'main.swift'),code);
  const compile=spawnSync('swiftc',['-Onone',new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(compile.status,0,compile.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);
 }finally{rmSync(dir,{recursive:true,force:true});}
});

test('complete published receiver typechecks together', {skip:process.platform!=='darwin'},()=>{
 const directory=new URL('../receiver/Sources/',import.meta.url);
 const files=['WandPointerControl.swift','WandRecordingState.swift','WandControlTransport.swift','WandContextListener.swift','WandReviewTrace.swift','WandDeviceConfiguration.swift','main.swift'].map(name=>new URL(name,directory).pathname);
 const result=spawnSync('swiftc',['-typecheck',...files],{encoding:'utf8'});
 assert.equal(result.status,0,result.stderr);
});

// Exercise the real IMU receiver method with inert transports. A table report
// may park the pointer, but never owns the recording lifecycle or an open HUD.
test('table rest never stops dictation or closes an explicit HUD', {skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 const start=source.indexOf('    func handleIMU('),open=source.indexOf('{',start);let depth=1,end=open+1;
 while(depth){if(source[end]==='{')depth++;if(source[end]==='}')depth--;end++;}
 const code=`import Foundation
func log(_ values:Any...){}
struct Filter {var configured=true;func observeGravity(x:Double,y:Double,z:Double){}}
final class Dwell {var following=true;func intent(_ value:Bool,now:Double){};func follow(_ value:Bool){following=value};func inhibit(until:Double){}}
final class Rest {var parked=false;var deskQuietSince:Double?;var hasReference=true;var sawButtons=false;enum Event{case probe,pickedUp,settling,putDown};func update(x:Double,y:Double,z:Double,gyro:Double,now:Double,buttons:Bool,idle:Bool)->[Event]{sawButtons=buttons;if buttons{return []};parked=true;deskQuietSince=now-61;return [.putDown]}}
final class Controls {var speechEvents=0;func speech(down:Bool)->Bool{speechEvents+=1;return true}}
final class Recording {var isRecording=true}
final class Harness {
 var ready=true,restoring=false,scrollActive=false,buttons=0,restDiagnosticsRemaining=0,hudSession=false
 var recordingPointerPaused=false
${source.includes('var restFollow=WandRestFollowMemory()')?' var restFollow=WandRestFollowMemory()':''}
 var motionFilter=Filter();let dwell=Dwell(),restDetection=Rest(),controls=Controls(),recording=Recording()
 struct Sleep {var sleeping=false;mutating func sample(parked:Bool,buttons:Bool,now:Double)->Bool?{sleeping=parked && !buttons;return sleeping}}
 var deskSleep=Sleep()
 var probeTimer:Timer?,queued:[String]=[],entered=0
 func reconcileBottomHold(down:Bool,now:Double,reason:String){};func scheduleDwell(){};func cancelCircleScroll(){};func releaseButtons(){}
 func enterPointerMode(){entered+=1;hudSession=false};func queue(_ text:String){queued.append(text)}
 ${source.slice(start,end)}
}
let h=Harness();h.handleIMU("0,0,8192,0,0,0,0")
precondition(!h.dwell.following && h.entered==1)
precondition(h.controls.speechEvents==0 && h.recording.isRecording)
let hud=Harness();hud.hudSession=true;hud.handleIMU("0,0,8192,0,0,0,0")
precondition(hud.hudSession && hud.entered==0 && !hud.restDetection.sawButtons)
precondition(hud.controls.speechEvents==0 && hud.recording.isRecording)
precondition(hud.deskSleep.sleeping && hud.queued.contains{ $0.contains("setWandDeskSleeping(true)") },"desk sleep preserves HUD and recording")
print("PASS: table rest cannot stop recording or dismiss open HUD")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-rest-'));
 try {writeFileSync(join(dir,'main.swift'),code);const build=spawnSync('swiftc',[new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});

test('receiver selection taps have independent identities after navigation and previous taps', {skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/WandControlTransport.swift',import.meta.url),'utf8');
 const start=source.indexOf('    private var persistentID');
 const end=source.indexOf('\n    func speech(',start);
 assert(start>=0&&end>start);
 const code=`import Foundation
final class Transport {
 let agenticPath="test-only"
 var packets:[[String:Any]]=[]
 func send(_ packet:[String:Any],path:String,limit:Int)->Bool {packets.append(packet);return true}
 ${source.slice(start,end)}
}
let t=Transport()
t.persistent("navigate");t.persistent("motion",x:12);t.persistent("park")
t.persistent("activate");t.persistent("activate")
let ids=t.packets.map{$0["id"] as! String}
precondition(ids[0]==ids[1] && ids[1]==ids[2],"navigation packets must share identity")
precondition(ids[3] != ids[2],"selection after navigation must not be rejected as duplicate")
precondition(ids[4] != ids[3],"a second physical tap must be independently selectable")
precondition(t.packets[3]["seq"] as! Int==1 && t.packets[4]["seq"] as! Int==1)
print("PASS: real receiver generates independent selection identities")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-tap-id-'));
 try {writeFileSync(join(dir,'main.swift'),code);const build=spawnSync('swiftc',[join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});

test('actual UART marker handler ignores echoed source and never hides a failed upload', {skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 const start=source.indexOf('            if line.contains("Error")');
 const end=source.indexOf('            if line.hasPrefix("WAND_DIAG ")',start);
 assert(start>=0&&end>start);
 const handler=source.slice(start,end);
 const code=`import Foundation
import AppKit
func log(_ values:Any...) {}
struct Filter {func reset(){}}
struct Context {var isActive=false}
final class Harness {
 var loadingBridge=false,loadingRuntime=false,bridgeLoadFailed=false,ready=false,lightMode="",generation=0,rawLastArrival=0.0,hudSession=false,hudOpenedAt=0.0
 let commands=["PROGRAM"],modeBridge="bridge",context=Context(),motionFilter=Filter()
 var selectedReviewMode:String?
 func setWandShortcut(_ mode:String){}
 var sent:[String]=[];var loads=0
 func queue(_ value:String){sent.append(value)}
 func loadModeBridge(){loads+=1;loadingBridge=true}
 func bridgeRevision(_ value:String)->String{"revision"}
 func status(){};func syncRecordingLight(){};func resumeHUDNavigation(){}
 func receive(_ value:String){for line in [value]{${handler}}}
}
let h=Harness()
h.receive("if (...) print(\\\"WAND_NEEDS_CONFIG\\\");")
precondition(h.sent.isEmpty)
h.receive("WAND_NEEDS_CONFIG");h.receive(">WAND_NEEDS_CONFIG")
precondition(h.sent == ["PROGRAM"])
h.receive("OUT OF MEMORYUncaught SyntaxError: Got EOF expected '}'")
h.receive("WAND_BRIDGE_READY BOTTOM=D1")
h.receive("WAND_MODE_ROUTING_READY")
precondition(!h.ready && h.bridgeLoadFailed)
let valid=Harness();valid.receive(">WAND_BRIDGE_READY");precondition(valid.sent.count==1)
valid.receive("WAND_MODE_ROUTING_READY");precondition(valid.ready)
print("UART regression passed")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-uart-'));
 try {const file=join(dir,'main.swift'),bin=join(dir,'test');writeFileSync(file,code);
 const build=spawnSync('swiftc',[file,'-o',bin],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);
 const run=spawnSync(bin,[],{encoding:'utf8'});assert.equal(run.status,0,run.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
