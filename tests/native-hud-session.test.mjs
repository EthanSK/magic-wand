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
 const code=`import Foundation
func AXIsProcessTrusted()->Bool {true}
func log(_ parts:Any...) {}
final class Context {var isActive=false;var onChange:((Bool)->Void)?;func set(_ v:Bool){isActive=v;onChange?(v)}}
final class Controls {var phases:[String]=[];func persistent(_ phase:String,x:Double=0,y:Double=0){phases.append(phase)}}
final class Review {func cancel()->[Int]{[]};var isHeld=false;var committed=false;func motion(y:Double,now:Double)->[Int]{[]};func detents(_ count:Int32,now:Double)->[Int]{[]};func endDetents(commit:Bool)->[Int]{committed=commit;return[]}}
final class Harness {
 let context=Context(),controls=Controls(),review=Review(),motionFilter=WandMotionFilter()
 var ready=true,restoring=false,scrollActive=false,acceptHUDContext=true
 var selectedReviewMode:String?,hiddenReviewOperating=false,hiddenReviewPending=false,screenshotActive=false,screenshotHUD=false
 var hudSession=false,hudEntryPress=false,hudActive=false,pointerInHUD=false,middleOperating=false,middleSecondTap=false,navigationOpenedHUD=false
 var wandShortcutMode:String?,wandShortcutX=0.0,wandShortcutY=0.0,wandShortcutTime=0.0
 let wandShortcutScroll=WandHeldScroll()
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
 func releaseButtons(){}
 init(){${callback}}
 ${['setScreenshotActive','finishWandShortcut','closeHUD','enterPointerMode','handleMiddle','handleMove','handleNavigation','resumeHUDNavigation','handleHUD','startHUDWatchdog','stopHUDWatchdog'].map(method).join('\n')}
}
func settle(_ seconds:Double){RunLoop.main.run(until:Date().addingTimeInterval(seconds))}
let h=Harness()
h.handleMiddle("1");h.context.set(true);h.handleMiddle("0")
precondition(h.hudSession)
h.appMode="codex";h.handleMiddle("1");h.handleMiddle("0")
precondition(!h.hudSession && h.appMode==nil && h.controls.phases.last=="dismiss")
precondition(!h.controls.phases.contains("appSpecific"))
let after=h.controls.phases.count
h.context.set(false);h.context.set(true);h.handleNavigation("40000,40000");h.handleHUD("B,0,0");h.handleMove("B,0,0")
settle(0.35)
precondition(!h.hudSession && !h.controls.phases.dropFirst(after).contains("press"))
h.middleLastRelease = -100;h.handleMiddle("1");h.context.set(true);h.handleMiddle("0")
precondition(h.hudSession,"fresh Middle press must re-open")
settle(0.32);h.handleMiddle("1");h.handleMiddle("0")
precondition(h.middleTap != nil)
h.context.set(false);let closed=h.controls.phases.count;settle(0.4)
precondition(!h.controls.phases.dropFirst(closed).contains("press"),"hidden HUD must cancel delayed click")
h.middleLastRelease = -100;h.handleMiddle("1");h.handleMiddle("0");h.hudLastUpdate=Date.distantPast;settle(0.3)
precondition(!h.hudSession && !h.acceptHUDContext && h.controls.phases.last=="dismiss","watchdog clears full session")
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
precondition(screenshot.hudSession && screenshot.hudActive && !screenshot.screenshotHUD)
let pinned=Harness();pinned.selectedReviewMode="changes";pinned.handleMiddle("1");settle(0.25)
precondition(pinned.hiddenReviewOperating && pinned.wandShortcutMode=="changes" && !pinned.hudSession)
pinned.handleMiddle("0");precondition(!pinned.hiddenReviewOperating && pinned.wandShortcutMode==nil && !pinned.hudSession)
print("PASS: screenshot HUD preservation, hidden review hold, native full close, stale input rejection, delayed click cancellation, fresh reopen, watchdog teardown")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-hud-'));
 try {
  writeFileSync(join(dir,'main.swift'),code);
  const compile=spawnSync('swiftc',['-O',new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(compile.status,0,compile.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);
 }finally{rmSync(dir,{recursive:true,force:true});}
});

test('complete published receiver typechecks together', {skip:process.platform!=='darwin'},()=>{
 const directory=new URL('../receiver/Sources/',import.meta.url);
 const files=['WandPointerControl.swift','WandRecordingState.swift','WandControlTransport.swift','WandContextListener.swift','WandDeviceConfiguration.swift','main.swift'].map(name=>new URL(name,directory).pathname);
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
final class Rest {var parked=false;var hasReference=true;var sawButtons=false;enum Event{case probe,pickedUp,settling,putDown};func update(x:Double,y:Double,z:Double,gyro:Double,now:Double,buttons:Bool,idle:Bool)->[Event]{sawButtons=buttons;if buttons{return []};parked=true;return [.putDown]}}
final class Controls {var speechEvents=0;func speech(down:Bool)->Bool{speechEvents+=1;return true}}
final class Recording {var isRecording=true}
final class Harness {
 var ready=true,restoring=false,scrollActive=false,buttons=0,restDiagnosticsRemaining=0,hudSession=false
 var motionFilter=Filter();let dwell=Dwell(),restDetection=Rest(),controls=Controls(),recording=Recording()
 var probeTimer:Timer?,queued:[String]=[],entered=0
 func reconcileBottomHold(down:Bool,now:Double,reason:String){};func scheduleDwell(){};func cancelCircleScroll(){};func releaseButtons(){}
 func enterPointerMode(){entered+=1;hudSession=false};func queue(_ text:String){queued.append(text)}
 ${source.slice(start,end)}
}
let h=Harness();h.handleIMU("0,0,8192,0,0,0,0")
precondition(!h.dwell.following && h.entered==1)
precondition(h.controls.speechEvents==0 && h.recording.isRecording)
let hud=Harness();hud.hudSession=true;hud.handleIMU("0,0,8192,0,0,0,0")
precondition(hud.hudSession && hud.entered==0 && hud.restDetection.sawButtons)
precondition(hud.controls.speechEvents==0 && hud.recording.isRecording)
print("PASS: table rest cannot stop recording or dismiss open HUD")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-rest-'));
 try {writeFileSync(join(dir,'main.swift'),code);const build=spawnSync('swiftc',[join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
