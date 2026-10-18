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
final class Review {func cancel()->[Int]{[]};var isHeld=false;func motion(y:Double,now:Double)->[Int]{[]}}
final class Harness {
 let context=Context(),controls=Controls(),review=Review(),motionFilter=WandMotionFilter()
 var ready=true,restoring=false,scrollActive=false,acceptHUDContext=true
 var hudSession=false,hudEntryPress=false,hudActive=false,pointerInHUD=false,middleOperating=false,middleSecondTap=false,navigationOpenedHUD=false
 var appMode:String?,reviewTimer:Timer?,middleTap:Timer?,middleHold:Timer?,hudWatchdog:Timer?
 var middleLastRelease = -100.0,middlePressedAt=0.0,middleDoubleConsumed=false,hudEntryPressStarted=0.0
 var reviewOriginY=0.0,navX=0.0,navY=0.0,navOriginX=0.0,navOriginY=0.0,operationOriginX=0.0,operationOriginY=0.0,middleX=0.0,middleY=0.0
 var navStream=WandAngularStream(),moveStream=WandAngularStream(),legacyHUDStream=WandAngularStream()
 var hudLastUpdate=Date.distantPast,commands:[String]=[]
 var hudDoubleClickInterval:Double {0.3}
 func queue(_ s:String){commands.append(s)}
 func cancelCircleScroll(){}
 func sendReview(_ v:[Int]){}
 func releaseButtons(){}
 init(){${callback}}
 ${['closeHUD','enterPointerMode','handleMiddle','handleMove','handleNavigation','resumeHUDNavigation','handleHUD','startHUDWatchdog','stopHUDWatchdog'].map(method).join('\n')}
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
print("PASS: native full close, stale input rejection, delayed click cancellation, fresh reopen, watchdog teardown")
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
