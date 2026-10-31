import {fileURLToPath as wandSourcePath} from 'node:url';
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync,readdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

// Compile the actual receiver methods with inert transports. No BLE owner,
// native mouse events or installed Agentic Mouse process is involved.
test('native HUD close cancels actions, rejects stale context and closes any child', {skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 const method=(name)=>{
  const start=source.indexOf('    '+(name==='mouseMovementEvent'?'static ':'')+'func '+name+'(');assert(start>=0,name);
  const open=source.indexOf('{',start);let depth=1,end=open+1;
  while(depth){if(source[end]==='{')depth++;if(source[end]==='}')depth--;end++;}
  return source.slice(start,end);
 };
 const a=source.indexOf('        context.onChange = '),b=source.indexOf('\n        context.start()',a);
 const callback=source.slice(a,b);
 const modeStart=source.indexOf('        context.onModeChange = '),modeEnd=source.indexOf('        // Review selection',modeStart);
 const modeCallback=source.slice(modeStart,modeEnd);
 const selectionStart=source.indexOf('        context.onSelectionChange = '),selectionEnd=source.indexOf('        context.onScreenshotChange',selectionStart);
 const selectionCallback=source.slice(selectionStart,selectionEnd);
 const code=`import Foundation
func AXIsProcessTrusted()->Bool {true}
func log(_ parts:Any...) {}
enum CGEventType {case leftMouseDragged,rightMouseDragged,mouseMoved}
enum CGMouseButton {case left,right}
enum CGEventField {case mouseEventDeltaX,mouseEventDeltaY}
enum EventTap {case cghidEventTap}
final class CGEvent {
 static var posted=0
 init?(mouseEventSource:Int?,mouseType:CGEventType,mouseCursorPosition:CGPoint,mouseButton:CGMouseButton){}
 func setIntegerValueField(_ field:CGEventField,value:Int64){}
 func post(tap:EventTap){Self.posted+=1}
}
final class Recording {var isRecording=false}
final class Rest {var parked=false;func pointerActivated(){parked=false};func pointerStopped(){}}
final class Context {var isActive=false,isFresh=true;var onChange:((Bool)->Void)?;var onModeChange:((String?)->Void)?;var onSelectionChange:((String?)->Void)?;func set(_ v:Bool){isActive=v;onChange?(v)}}
final class Application {var bundleIdentifier="com.microsoft.VSCode"}
final class NSWorkspace {static let shared=NSWorkspace();var frontmostApplication:Application?=Application()}
final class Trace {var boundaries:[String]=[];func boundary(_ reason:String,mode:String?=nil,now:Double=0){boundaries.append(reason)}}
final class Controls {var phases:[String]=[];var points:[CGPoint]=[];func persistent(_ phase:String,x:Double=0,y:Double=0,mouseX:Double?=nil){phases.append(phase);points.append(CGPoint(x:x,y:y))}}
final class Review {func cancel()->[Int]{[]};var isHeld=false;var committed=false;var starts:[String]=[];var modeChanges:[String]=[];var endings:[Bool]=[];var inputs=0;func beginDetents(mode:String,now:Double){starts.append(mode)};func changeMode(_ mode:String,now:Double)->[Int]{modeChanges.append(mode);return[]};func tick(now:Double)->[Int]{[]};func motion(y:Double,now:Double)->[Int]{[]};func detents(_ count:Int32,now:Double)->[Int]{inputs+=1;return[]};func endDetents(commit:Bool)->[Int]{endings.append(commit);committed=commit;return[]}}
final class Harness {
 func cancelMouseExitClick(){}
 var scrollFollowBefore=false
 func finishNativeScroll(cancelled:Bool){}

 var pointerTravel=0.0
 var actionPause=WandActionPause()
 let screenshot=WandScreenshotGesture();var screenshotRaw=0;func handleScreenshotRaw(_ v:[Int],now:Double){screenshotRaw+=1}
 let context=Context(),controls=Controls(),review=Review(),motionFilter=WandMotionFilter(),reviewTrace=Trace(),recording=Recording(),dwell=WandDwellClick()
 var deskSleep=WandDeskSleep()
 var recordingPointerPaused=false,recordingRestoreFollow:Bool?
 var clickFollowChoice:(following:Bool,paused:Bool,restore:Bool?,rest:WandRestFollowMemory)?
${source.includes('var restFollow=WandRestFollowMemory()')?' var restFollow=WandRestFollowMemory()':''}
 let restDetection=Rest()
 var ready=true,restoring=false,scrollActive=false,acceptHUDContext=true
 var buttons=0,movementCount=0,pointerDisplays=[CGRect(x:0,y:0,width:1000,height:1000)]
 var selectedReviewMode:String?,hiddenReviewOperating=false,hiddenReviewPending=false,screenshotActive=false,screenshotHUD=false
 var hudSession=false,hudEntryPress=false,hudActive=false,pointerInHUD=false,hudButtonOperating=false,hudButtonSecondTap=false,navigationOpenedHUD=false
 var hudButtonHeld=false,hudButtonQualified=false,hudOpenedAt=0.0;let hudHoldSeconds=0.14
 var hudButtonMouseX=0.0,hudButtonMouseSampleAt = -100.0; var hudButtonMouseOffset:Double? {let age=ProcessInfo.processInfo.systemUptime-hudButtonMouseSampleAt;return age>=0 && age<=0.25 ? hudButtonMouseX:nil}
 var wandShortcutMode:String?,wandShortcutX=0.0,wandShortcutY=0.0,wandShortcutTime=0.0
 var wandShortcutCircle=WandReviewNavigation();var hudButtonReviewExit=false
 var reviewExitGesture=WandReviewExitGesture();var reviewExitTimer:Timer?
 var pointerRouter=WandPointerRouter()
 class ClickLight { var sent=0;func clickLight(){sent+=1} }
 let senseVirtual:ClickLight?=ClickLight()
 var deliveryPoint:CGPoint?
 var pointerOrigin=WandPointerOrigin(),systemCursor=CGPoint.zero;func currentPointerOrigin()->CGPoint{pointerOrigin.origin(system:systemCursor,now:ProcessInfo.processInfo.systemUptime)}
 func performPointer(_ actions:[WandPointerRouter.Action]){}
 func scheduleDwell(){}
 func syncRecordingLight(){}
 func status(){}
 var appMode:String?,reviewTimer:Timer?,hudButtonTap:Timer?,hudButtonHold:Timer?,hudWatchdog:Timer?
 var hudButtonLastRelease = -100.0,hudButtonPressedAt=0.0,hudButtonDoubleConsumed=false,hudEntryPressStarted=0.0
 var hudButtonClosedTap=false
 let heldScroll=WandHeldScroll()
 var transitions:[(buttons:Int,at:CGPoint)]=[]
 func transition(to next:Int,at point:CGPoint){let allowed=actionPause.paused ? next & buttons : next;transitions.append((allowed,point));buttons=allowed}
 var reviewOriginY=0.0,navX=0.0,navY=0.0,navOriginX=0.0,navOriginY=0.0,operationOriginX=0.0,operationOriginY=0.0,hudButtonX=0.0,hudButtonY=0.0
 var navStream=WandAngularStream(),moveStream=WandAngularStream(),legacyHUDStream=WandAngularStream()
 var hudLastUpdate=Date.distantPast,commands:[String]=[]
 var hudDoubleClickInterval:Double {0.3}
 func queue(_ s:String){commands.append(s)}
 func cancelCircleScroll(){}
 func sendReview(_ v:[Int]){}
 var traceInputs=0
 func recordReviewInput(rawX:Double,rawY:Double,dx:Double,dy:Double,now:Double,blocked:String?,step:Int32){traceInputs+=1}
 var cancelledScreenshotHold=false
 func finishMouseButtonHold(now:Double,released:Bool=true){cancelledScreenshotHold = !released}
 var screenshotContexts:[Bool]=[]
 func screenshotContextChanged(_ active:Bool){screenshotContexts.append(active)}
 func releaseButtons(){}
 init(){${callback}
${modeCallback}
${selectionCallback}}
 ${['setScreenshotActive','setWandShortcut','switchWandShortcut','finishWandShortcut','exitSelectedReview','commitSelectedReview','beginReviewCommitHold','commitReviewHold','scheduleReviewTapTimeout','expireReviewTap','cancelReviewTap','requestReviewToggle','closeHUD','enterPointerMode','handleHUDButton','hudDoubleRightClick','handleMove','handleNavigation','resumeHUDNavigation','handleHUD','startHUDWatchdog','stopHUDWatchdog','postPointerMove','mouseMovementEvent','recordingChanged','manualPointerDuringRecording'].map(method).join('\n')}
}
func settle(_ seconds:Double){RunLoop.main.run(until:Date().addingTimeInterval(seconds))}
// Ethan's hold-to-show HUD. Holding the HUD button shows and steers it; releasing
// uses the outlined card; Agentic Mouse closes it after an ordinary action
// and keeps it open only for a submenu or a card that needs more motion.
let h=Harness()
h.handleHUDButton("1")
precondition(h.hudSession && h.hudButtonHeld && Array(h.controls.phases.suffix(2))==["open","navigate"] && h.commands.contains("setHUDOpen(true);"),"holding the HUD button shows and steers the HUD")
h.context.set(true);h.handleNavigation("8000,0")
precondition(!h.controls.phases.contains("qualify"),"a short hold does not qualify")
h.hudButtonPressedAt-=0.2;h.handleNavigation("9000,0")
precondition(h.controls.phases.filter{$0=="qualify"}.count==1,"qualify while still held")
h.handleNavigation("10000,0")
precondition(h.controls.phases.filter{$0=="qualify"}.count==1,"qualify once per hold")
precondition(h.controls.phases.last=="motion","held motion steers the outline")
h.hudButtonPressedAt-=0.3;h.handleHUDButton("0")
precondition(Array(h.controls.phases.suffix(3))==["motion","park","choose"] && !h.hudButtonHeld && !h.hudActive,"releasing a hold uses the outlined card at once")
let beforeClose=h.controls.phases.count
h.context.set(false)
precondition(!h.hudSession && !h.controls.phases.dropFirst(beforeClose).contains("dismiss"),"Agentic Mouse closed it, so no dismiss cuts short the action's follow-up")
h.context.set(true);h.handleNavigation("20000,0");h.handleHUD("B,0,0");h.handleMove("B,0,0");settle(0.35)
precondition(!h.hudSession && h.controls.phases.count==beforeClose,"a stale positive heartbeat never reopens or steers a closed HUD")

let menu=Harness();menu.handleHUDButton("1");menu.context.set(true);menu.hudButtonPressedAt-=0.3;menu.handleHUDButton("0")
precondition(menu.hudSession && !menu.hudActive,"a kept-open HUD waits for the next hold")
let waiting=menu.controls.phases.count
menu.handleNavigation("9000,0")
precondition(Array(menu.controls.phases.suffix(2))==["hover","motion"] && menu.hudWatchdog==nil,"unheld input is passive hover; native app accepts it only for an armed Switch App")
menu.hudLastUpdate=Date.distantPast;settle(1.1)
precondition(menu.hudSession && !menu.controls.phases.contains("dismiss"),"passive hover must not expire after a pause")
_=menu.pointerRouter.mouseButton(down:true)
menu.handleNavigation("19000,0")
precondition(!menu.hudActive && menu.controls.phases.last=="park","the mouse button parks passive hover before scrolling or dragging")
let parkedCount=menu.controls.phases.count
menu.handleNavigation("29000,0")
precondition(menu.controls.phases.count==parkedCount,"The mouse button movement cannot leak into the HUD")
_=menu.pointerRouter.mouseButton(down:false)
menu.handleNavigation("39000,0")
precondition(Array(menu.controls.phases.suffix(2))==["hover","motion"] && menu.controls.points.last==CGPoint.zero,"release starts from a new origin without replaying mouse-button movement")
menu.handleHUDButton("1")
precondition(Array(menu.controls.phases.suffix(2))==["park","navigate"] && menu.hudButtonHeld && menu.hudWatchdog != nil && !menu.controls.phases.dropFirst(waiting).contains("open"),"the next hold steers the page or adjusts the armed card")
menu.handleNavigation("0,7000");menu.hudButtonPressedAt-=0.3;menu.handleHUDButton("0")
precondition(menu.controls.phases.last=="choose")

// Ethan (2026-10-30): double-clicking the HUD button from closed "should do
// the right mouse menu, like right click". He approved the closed-HUD single
// tap waiting up to 300 ms, so Switch App waits out the double-click window.
let instant=Harness();instant.handleHUDButton("1");instant.context.set(true);instant.handleHUDButton("0")
precondition(instant.hudButtonTap != nil && !instant.controls.phases.contains("activate"),"a tap from closed waits out the double-click window")
let outlined=instant.controls.phases.count
for point in ["9000,0","-8000,7000"] {instant.handleNavigation(point)}
precondition(instant.controls.phases.count==outlined,"motion while it waits cannot change the card it will use")
settle(0.35)
precondition(instant.hudButtonTap == nil && instant.controls.phases.last=="activate" && instant.transitions.isEmpty && instant.hudSession,"a lone tap from closed then switches app, never right-clicks")
let unconfirmed=Harness();unconfirmed.handleHUDButton("1");unconfirmed.handleHUDButton("0");settle(0.35)
precondition(unconfirmed.controls.phases.last=="activate","as before, a closed tap does not need the HUD's first heartbeat")
for following in [false,true] {
 let right=Harness();right.dwell.follow(following);right.systemCursor=CGPoint(x:321,y:654)
 right.handleHUDButton("1");right.context.set(true);right.handleHUDButton("0");right.handleHUDButton("1")
 precondition(right.transitions.map{$0.buttons}==[2,0] && right.transitions.allSatisfy{$0.at==CGPoint(x:321,y:654)},"a double click from closed right-clicks once at the visible pointer")
 precondition(right.senseVirtual?.sent==1,"the sent right click triggers one LED acknowledgement")
 precondition(!right.hudSession && right.hudButtonTap == nil && right.controls.phases.last=="dismiss" && right.buttons==0,"and dismisses the HUD the first press showed")
 right.handleHUDButton("0");settle(0.35)
 precondition(!right.controls.phases.contains("activate") && !right.controls.phases.contains("choose") && right.transitions.count==2,"Switch App never fires and the second release is consumed")
 precondition(right.dwell.following==following,"mouse follow stays as it was")
 right.handleHUDButton("1")
 precondition(right.hudSession && right.hudButtonHeld && right.transitions.count==2,"the next press is an ordinary hold-to-show")
}
let heldFirst=Harness();heldFirst.handleHUDButton("1");heldFirst.context.set(true);heldFirst.hudButtonPressedAt-=0.3;heldFirst.handleHUDButton("0")
heldFirst.handleHUDButton("1")
precondition(heldFirst.transitions.isEmpty && heldFirst.hudSession && heldFirst.hudButtonHeld,"a hold that opened the HUD is never the first click of a right-click")
let lateClosed=Harness();lateClosed.handleHUDButton("1");lateClosed.context.set(true);lateClosed.handleHUDButton("0")
lateClosed.hudButtonLastRelease = -100;lateClosed.handleHUDButton("1")
precondition(lateClosed.transitions.isEmpty && lateClosed.hudButtonTap == nil && Array(lateClosed.controls.phases.suffix(2))==["activate","navigate"],"a closed tap whose window ended (late timer) switches app before the next hold")
let closedEarly=Harness();closedEarly.handleHUDButton("1");closedEarly.context.set(true);closedEarly.handleHUDButton("0")
closedEarly.closeHUD(reason:"disconnect");closedEarly.handleHUDButton("1")
precondition(closedEarly.transitions.isEmpty && !closedEarly.hudButtonClosedTap,"a HUD closed meanwhile (disconnect, native close) cancels the right-click")
settle(0.35);precondition(!closedEarly.controls.phases.contains("activate"))
let dragging=Harness();dragging.handleHUDButton("1");dragging.context.set(true);dragging.handleHUDButton("0")
_=dragging.pointerRouter.mouseButton(down:true);dragging.handleHUDButton("1")
precondition(dragging.transitions.isEmpty && !dragging.hudSession && dragging.controls.phases.last=="dismiss","while the mouse button is held the double click only dismisses")
let paused=Harness();paused.handleHUDButton("1");paused.context.set(true);paused.handleHUDButton("0")
paused.actionPause.pause();paused.handleHUDButton("1")
precondition(paused.buttons==0 && paused.transitions.allSatisfy{$0.buttons==0},"the debug pause never presses a native button")
// Inside an already open HUD a tap still waits out the double-click window.
let tap=Harness();tap.handleHUDButton("1");tap.context.set(true);tap.hudButtonPressedAt-=0.3;tap.handleHUDButton("0")
precondition(tap.controls.phases.last=="choose","the opening hold's release")
tap.handleHUDButton("1");tap.handleHUDButton("0")
precondition(tap.hudButtonTap != nil && tap.controls.phases.last=="park","a tap waits out the double-click window")
let selectedAtRelease=tap.controls.phases.count
for point in ["9000,0","-8000,7000","0,-9000"] {tap.handleNavigation(point)}
precondition(tap.controls.phases.count==selectedAtRelease && !tap.hudActive,"wand movement during click qualification cannot move the selected wedge")
settle(0.35)
precondition(tap.controls.phases.last=="activate" && tap.hudButtonTap == nil,"a lone tap then uses the original outlined card")
tap.handleNavigation("30000,15000")
precondition(Array(tap.controls.phases.suffix(2))==["hover","motion"] && tap.controls.points.last==CGPoint.zero,"after activation aim restarts at a fresh origin without replaying click-window motion")
// A double click inside an open HUD dismisses without acting. (From closed,
// the first tap acts at once; Agentic Mouse ignores it when that press only
// reopened a remembered submenu, so a double click still resets to home.)
let double=Harness();double.handleHUDButton("1");double.context.set(true);double.hudButtonPressedAt-=0.3;double.handleHUDButton("0")
let beforeDouble=double.controls.phases.count
double.handleHUDButton("1");double.handleHUDButton("0");double.handleHUDButton("1")
precondition(!double.hudSession && double.controls.phases.last=="dismiss","double click still dismisses")
double.handleHUDButton("0");settle(0.35)
precondition(!double.controls.phases.dropFirst(beforeDouble).contains("activate") && !double.controls.phases.dropFirst(beforeDouble).contains("choose") && !double.hudSession,"and never acts")
precondition(double.transitions.isEmpty,"a double click inside an open HUD only closes it, never right-clicks")
let lateTap=Harness();lateTap.handleHUDButton("1");lateTap.context.set(true);lateTap.hudButtonPressedAt-=0.3;lateTap.handleHUDButton("0")
lateTap.handleHUDButton("1");lateTap.handleHUDButton("0")
lateTap.hudButtonLastRelease = -100;lateTap.handleHUDButton("1")
precondition(lateTap.hudButtonTap == nil && Array(lateTap.controls.phases.suffix(2))==["activate","navigate"],"a tap whose window ended is used before the next hold, never lost")
let hidden=Harness();hidden.handleHUDButton("1");hidden.context.set(true);hidden.hudButtonPressedAt-=0.3;hidden.handleHUDButton("0")
hidden.handleHUDButton("1");hidden.handleHUDButton("0");hidden.context.set(false);settle(0.4)
precondition(!hidden.controls.phases.contains("activate"),"a closed HUD cancels the pending tap")
let racing=Harness();racing.handleHUDButton("1");racing.context.set(true);racing.context.set(false)
precondition(racing.hudSession && racing.hudButtonHeld,"a close during a live hold waits for its release")
racing.hudButtonPressedAt-=0.3;racing.handleHUDButton("0")
precondition(racing.controls.phases.last=="choose")
let lost=Harness();lost.handleHUDButton("1");lost.hudLastUpdate=Date.distantPast;settle(0.3)
precondition(!lost.hudSession && !lost.acceptHUDContext && lost.controls.phases.last=="dismiss","lost telemetry during a hold clears the whole session")
lost.context.set(true);precondition(!lost.hudSession)
let stale=Harness();stale.hudSession=true;stale.hudOpenedAt=ProcessInfo.processInfo.systemUptime-5;stale.handleHUDButton("1")
precondition(stale.hudSession && stale.hudButtonHeld && stale.controls.phases.contains("open"),"a session Agentic Mouse no longer shows restarts as a fresh HUD")
let shortcut=Harness();shortcut.hudSession=true;shortcut.pointerInHUD=true;shortcut.hudButtonOperating=true;shortcut.wandShortcutMode="changes"
shortcut.handleHUDButton("0")
precondition(shortcut.wandShortcutMode==nil && shortcut.review.committed,"physical HUD-button release immediately finishes review")
shortcut.wandShortcutMode="files";shortcut.closeHUD(reason:"disconnect")
precondition(shortcut.wandShortcutMode==nil && !shortcut.review.committed,"lost HUD cancels review")
// A capture that ends while Agentic Mouse still shows the HUD returns to it.
let screenshot=Harness();screenshot.hudSession=true;screenshot.hudActive=true;screenshot.context.set(true)
screenshot.setScreenshotActive(true);screenshot.enterPointerMode()
precondition(!screenshot.hudSession && screenshot.screenshotHUD)
precondition(!screenshot.controls.phases.contains("dismiss"))
screenshot.setScreenshotActive(false)
precondition(screenshot.cancelledScreenshotHold,"screenshot exit cancels any held drag before restoring the HUD")
precondition(screenshot.hudSession && !screenshot.hudActive && !screenshot.screenshotHUD,"the HUD returns waiting, never steering unheld")
precondition(screenshot.screenshotContexts==[true,false],"the context reaches screenshot ownership")
precondition(screenshot.commands.last=="setHUDOpen(true);" && !screenshot.commands.contains{$0.contains("setMouseFollow")},"returning to the HUD leaves the mouse-follow choice alone")
// Ethan, 2026-10-30 00:54: the HUD's own Screenshot card hides the HUD (its
// context ends) before the capture ends. No ghost session may come back: it
// blocked every stop-to-click ("it's straight up not clicking").
let ghost=Harness();ghost.hudSession=true;ghost.hudActive=true;ghost.context.set(true)
ghost.setScreenshotActive(true);ghost.enterPointerMode();ghost.context.set(false)
ghost.setScreenshotActive(false)
precondition(!ghost.hudSession && !ghost.screenshotHUD,"a hidden HUD never returns as a session")
precondition(!ghost.commands.contains("setHUDOpen(true);"),"the wand is never told a HUD is open")
let pinned=Harness();pinned.selectedReviewMode="changes";pinned.wandShortcutMode="changes";pinned.handleHUDButton("1")
precondition(pinned.reviewExitGesture.pending && !pinned.review.committed,"HUD button down freezes the existing working set")
for i in 1...80 {pinned.handleNavigation("\\(i*1000),\\(i*2000)")}
precondition(pinned.review.inputs==0,"held motion never reaches Better Git")
pinned.commitReviewHold(now:ProcessInfo.processInfo.systemUptime+0.6)
precondition(pinned.selectedReviewMode=="changes" && pinned.wandShortcutMode=="changes" && !pinned.controls.phases.contains("exitReview") && pinned.review.committed)
precondition(pinned.review.starts==["changes"] && pinned.reviewExitGesture.pending,"long press arms the next set but remains frozen until release")
for i in 81...160 {pinned.handleNavigation("\\(i*1000),\\(i*2000)")}
pinned.commitReviewHold(now:ProcessInfo.processInfo.systemUptime+2)
precondition(pinned.review.inputs==0 && pinned.review.starts.count==1,"continued holding neither edits nor commits the next set")
pinned.handleHUDButton("0");settle(0.36)
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
pinned.handleHUDButton("1");pinned.handleHUDButton("0")
precondition(pinned.selectedReviewMode=="changes" && pinned.reviewExitGesture.awaitingSecond,"single review tap waits for double-click")
settle(0.35)
precondition(pinned.selectedReviewMode==nil && !pinned.review.committed,"a later short tap cancels and exits")
let cancel=Harness();cancel.selectedReviewMode="files";cancel.wandShortcutMode="files";cancel.handleHUDButton("1");cancel.handleHUDButton("0");settle(0.6)
precondition(cancel.selectedReviewMode==nil && cancel.wandShortcutMode==nil && !cancel.review.committed,"short tap cancels the timer without staging later")
let late=Harness();late.selectedReviewMode="files";late.wandShortcutMode="files";late.hudButtonReviewExit=true
late.beginReviewCommitHold(now:ProcessInfo.processInfo.systemUptime-0.6);late.handleHUDButton("0")
precondition(late.review.committed && late.review.starts==["files"] && late.selectedReviewMode=="files","long release works even when the timer was delayed")
let toggled=Harness();toggled.selectedReviewMode="changes";toggled.wandShortcutMode="changes"
for expected in ["files","changes","files"] {
 toggled.handleHUDButton("1");toggled.handleHUDButton("0")
 precondition(toggled.reviewExitGesture.awaitingSecond && toggled.selectedReviewMode != nil)
 let before=toggled.review.inputs;toggled.handleNavigation("1000,1000")
 precondition(toggled.review.inputs==before,"waiting double-click freezes review, not pointer")
 toggled.handleHUDButton("1");toggled.handleHUDButton("0")
 precondition(toggled.controls.phases.last=="toggleReview" && !toggled.review.committed,"double click requests mode toggle without staging")
 precondition(toggled.selectedReviewMode != expected,"only native acknowledgement changes local mode")
 toggled.context.onSelectionChange?(expected)
 precondition(toggled.selectedReviewMode==expected && toggled.wandShortcutMode==expected)
 settle(0.32)
 precondition(toggled.selectedReviewMode==expected && !toggled.controls.phases.contains("exitReview"),"old tap timer cannot exit new mode")
}
precondition(toggled.controls.phases.filter{$0=="toggleReview"}.count==3)
precondition(toggled.transitions.isEmpty,"review double clicks toggle the mode, never right-click")
precondition(toggled.review.modeChanges==["files","changes","files"] && toggled.review.endings.isEmpty && toggled.review.starts.isEmpty,"mode switches preserve the live review transaction: no cancel, finish or begin")
let secondHold=Harness();secondHold.selectedReviewMode="files";secondHold.wandShortcutMode="files"
secondHold.handleHUDButton("1");secondHold.handleHUDButton("0");secondHold.handleHUDButton("1")
secondHold.commitReviewHold(now:ProcessInfo.processInfo.systemUptime+0.6);secondHold.handleHUDButton("0");settle(0.35)
precondition(secondHold.review.committed && secondHold.selectedReviewMode=="files" && !secondHold.controls.phases.contains("toggleReview"),"long second press stages and stays")
let changed=Harness();changed.selectedReviewMode="changes";changed.wandShortcutMode="changes"
changed.handleHUDButton("1");changed.handleHUDButton("0");changed.context.onSelectionChange?(nil);settle(0.35)
precondition(changed.selectedReviewMode==nil && !changed.controls.phases.contains("exitReview"),"native cancellation clears pending exit")
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
let independent=Harness();independent.hudSession=true;independent.enterPointerMode();precondition(independent.hudSession,"the mouse button leaves the HUD alone")

// Every HUD-button hold, including the second hold that adjusts an armed card
// such as Switch App, freezes the mouse-button pointer lane for its length only.
// Use the real pointer posting and the HUD button/navigation handlers with inert events.
let switching=Harness(),anchor=CGPoint(x:400,y:400)
precondition(switching.postPointerMove(dx:20,dy:10,from:anchor)==CGPoint(x:420,y:410))
switching.handleHUDButton("1")
let entryPosts=CGEvent.posted
for _ in 0..<100 {precondition(switching.postPointerMove(dx:30,dy:-15,from:anchor)==anchor,"a HUD-button hold freezes an already-following pointer")}
switching.handleNavigation("10000,0")
precondition(CGEvent.posted==entryPosts && switching.controls.phases.last=="motion","the hold still steers the HUD without moving the pointer")
switching.context.set(true);switching.hudButtonPressedAt-=0.3;switching.handleHUDButton("0")
precondition(switching.postPointerMove(dx:-20,dy:10,from:anchor)==CGPoint(x:380,y:410),"release resumes new pointer movement without replaying the held sweep")
switching.handleHUDButton("1")
let pressPosts=CGEvent.posted
precondition(switching.postPointerMove(dx:60,dy:40,from:anchor)==anchor,"the second hold freezes the pointer too")
switching.handleNavigation("-20000,0");switching.handleNavigation("20000,0")
precondition(switching.controls.phases.last=="motion" && CGEvent.posted==pressPosts,"left and right reach the armed card without moving the pointer")
switching.hudButtonPressedAt-=0.3;switching.handleHUDButton("0")
precondition(switching.postPointerMove(dx:5,dy:0,from:anchor)==CGPoint(x:405,y:400),"HUD-button release restores pointing even while the HUD stays open")
switching.handleHUDButton("1");switching.closeHUD(reason:"context ended")
precondition(switching.postPointerMove(dx:7,dy:0,from:anchor)==CGPoint(x:407,y:400),"a cancelled hold cannot leave the pointer frozen")
let independentReview=Harness();independentReview.selectedReviewMode="changes";independentReview.handleHUDButton("1")
precondition(independentReview.postPointerMove(dx:8,dy:0,from:anchor)==CGPoint(x:408,y:400),"independent review commit holds retain the mouse button pointer lane")

// Recording freezes delivery and forgets speech-time travel without changing
// the latched follow choice. Exercise the actual receiver callback and emitter.
for following in [false,true] {
 let speech=Harness();speech.dwell.follow(following)
 speech.pointerRouter=WandPointerRouter(lowDelay:0.09)
 _=speech.pointerRouter.mouseButton(down:true)
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
precondition(manual.postPointerMove(dx:6,dy:2,from:anchor)==CGPoint(x:406,y:402),"manual mouse-button re-entry allows pointer movement while recording")
manual.dwell.follow(false);manual.recording.isRecording=false;manual.recordingChanged(false)
precondition(!manual.dwell.following,"recording end preserves a manual switch off")
print("PASS: hold-to-show HUD, native close, kept-open next hold, tap and double click, stale input rejection, watchdog teardown, review hold")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-hud-'));
 try {
  writeFileSync(join(dir,'main.swift'),code);
  const compile=spawnSync('swiftc',[wandSourcePath(new URL('../receiver/Sources/WandRunLoop.swift',import.meta.url)),'-Onone',new URL('../receiver/Sources/WandActionPause.swift',import.meta.url).pathname,new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(compile.status,0,compile.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);
 }finally{rmSync(dir,{recursive:true,force:true});}
});

test('complete published receiver typechecks together', {skip:process.platform!=='darwin'},()=>{
 const directory=new URL('../receiver/Sources/',import.meta.url);
 // Compile the same complete Sources folder as build_receiver.sh; new device
 // adapters must not be omitted by a separately maintained file list.
 const files=readdirSync(directory).filter(name=>name.endsWith('.swift')).sort().map(name=>new URL(name,directory).pathname);
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
struct Filter {var configured=true;func observeGravity(x:Double,y:Double,z:Double,rotation:Double=0){}}
final class Dwell {var following=true;func intent(_ value:Bool,now:Double){};func follow(_ value:Bool){following=value};func inhibit(until:Double){}}
final class Rest {var parked=false;var deskQuietSince:Double?;var hasReference=true;var sawButtons=false;enum Event{case probe,pickedUp,settling,putDown};func update(x:Double,y:Double,z:Double,gyro:Double,now:Double,buttons:Bool,idle:Bool)->[Event]{sawButtons=buttons;if buttons{return []};parked=true;deskQuietSince=now-61;return [.putDown]}}
final class Controls {var speechEvents=0;func speech(down:Bool)->Bool{speechEvents+=1;return true}}
final class Recording {var isRecording=true}
final class Harness {
 func cancelMouseExitClick(){}
 var actionPause=WandActionPause()
 let screenshot=WandScreenshotGesture();var screenshotRaw=0;func handleScreenshotRaw(_ v:[Int],now:Double){screenshotRaw+=1}
 var ready=true,restoring=false,scrollActive=false,buttons=0,restDiagnosticsRemaining=0,hudSession=false
 var recordingPointerPaused=false
${source.includes('var restFollow=WandRestFollowMemory()')?' var restFollow=WandRestFollowMemory()':''}
 var motionFilter=Filter();let dwell=Dwell(),restDetection=Rest(),controls=Controls(),recording=Recording()
 var powerPolicyReady=true,standbyResume:Bool?,selectedReviewMode:String?
 struct Sleep {var sleeping=false,deepSleeping=true;mutating func sample(parked:Bool,buttons:Bool,now:Double)->Bool?{sleeping=parked && !buttons;return sleeping}}
 var deskSleep=Sleep()
 var probeTimer:Timer?,queued:[String]=[],entered=0
 func reconcileMouseButtonHold(down:Bool,now:Double,reason:String){};func scheduleDwell(){};func cancelCircleScroll(){};func releaseButtons(){}
 func enterPointerMode(){entered+=1;hudSession=false};func queue(_ text:String){queued.append(text)}
 ${source.slice(start,end)}
}
let h=Harness();h.handleIMU("0,0,8192,0,0,0,0")
precondition(!h.dwell.following && h.entered==1)
precondition(h.controls.speechEvents==0 && h.recording.isRecording)
precondition(!h.queued.contains{$0.contains("wandEnterDeepStandby")},"recording blocks radio-off sleep")
let hud=Harness();hud.hudSession=true;hud.handleIMU("0,0,8192,0,0,0,0")
precondition(hud.hudSession && hud.entered==0 && !hud.restDetection.sawButtons)
precondition(hud.controls.speechEvents==0 && hud.recording.isRecording)
precondition(!hud.queued.contains{$0.contains("wandEnterDeepStandby")},"an explicit HUD blocks radio-off sleep")
precondition(hud.deskSleep.sleeping && hud.queued.contains{ $0.contains("setWandDeskSleeping(true)") },"desk sleep preserves HUD and recording")
print("PASS: table rest cannot stop recording or dismiss open HUD")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-rest-'));
 try {writeFileSync(join(dir,'main.swift'),code);const build=spawnSync('swiftc',[wandSourcePath(new URL('../receiver/Sources/WandRunLoop.swift',import.meta.url)),new URL('../receiver/Sources/WandActionPause.swift',import.meta.url).pathname,new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});

test('receiver selection taps have independent identities after navigation and previous taps', {skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/WandControlTransport.swift',import.meta.url),'utf8');
 const start=source.indexOf('    private var persistentID');
 const end=source.indexOf('\n    func speech(',start);
 assert(start>=0&&end>start);
 const code=`import Foundation
final class Transport {
 var suspended=false
 func allowed()->Bool {!suspended}
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
t.persistent("toggleReview");t.persistent("toggleReview")
let toggles=t.packets.filter{$0["phase"] as? String == "toggleReview"}
precondition(toggles.count==2 && toggles[0]["id"] as! String != toggles[1]["id"] as! String,"every review toggle must have a fresh identity")
precondition(toggles.allSatisfy{$0["seq"] as? Int == 1},"toggle sequences start independently")
print("PASS: real receiver generates independent selection identities")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-tap-id-'));
 try {writeFileSync(join(dir,'main.swift'),code);const build=spawnSync('swiftc',[wandSourcePath(new URL('../receiver/Sources/WandRunLoop.swift',import.meta.url)),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
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
final class Dwell {func follow(_ on:Bool){}}
struct Recording {var isRecording=false}
struct Version {var usesHeldScroll=true}
final class Harness {
 func cancelMouseExitClick(){}
 var loadingBridge=false,loadingRuntime=false,bridgeLoadFailed=false,ready=false,lightMode="",generation=0,rawLastArrival=0.0,hudSession=false,hudOpenedAt=0.0
 let commands=["PROGRAM"],modeBridge="bridge",context=Context(),motionFilter=Filter()
 var selectedReviewMode:String?
 var controlVersion=Version()
 var standbyResume:Bool?
 let dwell=Dwell(),recording=Recording()
 func restoreKnownCalibration(){};func checkPowerPolicy(){};func requestBattery(){}
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
precondition(valid.sent.contains("global.wandHostHeldScroll=true;"))
print("UART regression passed")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-uart-'));
 try {const file=join(dir,'main.swift'),bin=join(dir,'test');writeFileSync(file,code);
 const build=spawnSync('swiftc',[wandSourcePath(new URL('../receiver/Sources/WandRunLoop.swift',import.meta.url)),file,'-o',bin],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);
 const run=spawnSync(bin,[],{encoding:'utf8'});assert.equal(run.status,0,run.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
