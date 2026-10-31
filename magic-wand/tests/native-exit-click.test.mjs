import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

// Real receiver release, arbitration and timer methods; all external effects are
// inert. This never posts input or starts a native screenshot.
test('exit follow never clicks; stillness, double/triple shortcuts and quiet hold remain independent',{skip:process.platform!=='darwin'},()=>{
 const root=new URL('../receiver/Sources/',import.meta.url).pathname;
 const source=readFileSync(root+'main.swift','utf8');
 function method(name){const a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
 const a=source.indexOf('            if let marker=line.range(of:"@BOTTOM ")'),b=source.indexOf('            if let marker=line.range(of:"@MIDDLE ")',a);
 const bottom=source.slice(a,b);
 assert(!source.includes('scheduleMouseExitClick'), 'removed click-to-exit cannot queue an OS click');
 const code=`import Foundation
func AXIsProcessTrusted()->Bool {true}
func log(_ parts:Any...) {}
struct Pause {var paused=false;func admit(_ button:Button,down:Bool)->Bool{!paused};enum Button{case mouseButton}}
final class Rest {func pointerActivated(){};func pointerStopped(){}}
final class Harness {
 var actionPause=Pause(),ready=true,restoring=false,scrollActive=false
 let motionFilter=WandMotionFilter()
 var scrollFollowBefore=false,controlVersion=WandControlVersion.sustainedV3
 var dwell=WandDwellClick(),heldScroll=WandHeldScroll(),pointerRouter=WandPointerRouter(),recenterGesture=WandRecenterGesture(),tripleClick=WandTripleClick(),flickScroll=WandFlickScroll()
 var screenshot=WandScreenshotGesture(),restFollow=WandRestFollowMemory(),restDetection=Rest()
 var heldSafetyTimer:Timer?,heldTargetToken=UUID(),heldScrollAnchor:CGPoint?,deliveryPoint:CGPoint?,flickAnchor:CGPoint?
 var pendingRecenter:Timer?
 var clickFollowChoice:(following:Bool,paused:Bool,restore:Bool?,rest:WandRestFollowMemory)?
 var recordingPointerPaused=false,recordingRestoreFollow:Bool?,recenterSuppressButtons=false,heldScrollDiagnostics=false
 var point=CGPoint(x:40,y:70),app:String?="test.app",buttons=0,clicks:[CGPoint]=[],centres=0,screenshots=0
 var hudSession=false,hudButtonHeld=false,hudEntryPress=false,pointerInHUD=false
 var physicalDuration:Double?
 func mouseButtonPhysicalTapDuration()->Double?{physicalDuration}
 func currentPointerOrigin()->CGPoint{point}
  func transition(to next:Int,at point:CGPoint){if next==1 && buttons==0 {clicks.append(point)};buttons=next}
 func releaseButtons(){buttons=0}
 func finishNativeScroll(cancelled:Bool){}
 func setCircleLight(_ on:Bool){}
 func postHeldScroll(x:Int32,y:Int32,at:CGPoint?){}
 func postSustainedScroll(x:Int32,y:Int32,at:CGPoint?){}
 func queue(_ text:String){}
 func scheduleDwell(){}
 func performPointer(_ actions:[WandPointerRouter.Action]){}
 func restoreMouseAfterScroll(){}
 func probeHoldTarget(at:CGPoint,token:UUID){_=heldScroll.setTarget(scrollable:true,now:ProcessInfo.processInfo.systemUptime)}
 func manualPointerDuringRecording(){}
 func recenterPointer(){centres+=1;dwell.follow(true);_=pointerRouter.cancelAll()}
 func startScreenshotShortcut(now:Double){screenshots+=1;pendingRecenter?.invalidate();pendingRecenter=nil;_=screenshot.requestShortcut(now:now)}
 func latchScreenshotIfReady(){}
 func finishScreenshotDrag(reason:String){}
 func edge(_ down:Bool){let line="@BOTTOM "+(down ? "1":"0");for _ in [0] {${bottom}}}
 ${['beginMouseButtonHold','finishMouseButtonHold','reconcileMouseButtonHold','recognizeMouseButtonRecenter','screenshotMouseButton'].map(method).join('\n')}
}
func wait(_ s:Double){RunLoop.main.run(until:Date().addingTimeInterval(s))}
func make(_ following:Bool=true)->Harness {let h=Harness();h.dwell.follow(following);return h}
func tap(_ h:Harness){let entering = !h.dwell.following;h.edge(true);if entering {h.dwell.follow(true)};wait(0.04);h.edge(false)}
func expect(_ ok:Bool,_ message:String){if !ok {print("FAIL: "+message);fflush(stdout);exit(1)}}
let single=make();tap(single)
expect(!single.dwell.following && single.clicks.isEmpty && single.pendingRecenter == nil,"release stops follow immediately without clicking")
wait(0.2);expect(single.clicks.isEmpty,"single click waits for the double/triple window")
wait(0.13);expect(single.clicks.isEmpty,"no deferred exit click appears after 300 ms")
single.edge(false);wait(0.32);expect(single.clicks.isEmpty,"duplicate release cannot click again")
let double=make();tap(double);wait(0.08);tap(double);wait(0.33)
expect(double.clicks.isEmpty && double.centres==1,"double click still centres without posting a click")
let triple=make();tap(triple);wait(0.08);tap(triple);wait(0.08);triple.edge(true);triple.edge(false);wait(0.33)
expect(triple.clicks.isEmpty && triple.centres==0 && triple.screenshots==1,"triple click opens screenshot without any preliminary click")
let entering=make(false);tap(entering);wait(0.33);expect(entering.clicks.isEmpty,"entering follow never clicks")
let held=make();held.edge(true);wait(0.26);expect(held.dwell.following && held.heldScroll.active && held.clicks.isEmpty,"disabled quiet hold does not stop follow or click");held.edge(false);wait(0.33);expect(held.dwell.following && held.clicks.isEmpty,"plain quiet release preserves prior follow when the experiment is off")
let opted=make();opted.heldScroll.quietStopEnabled=true;opted.edge(true);wait(0.26);expect(opted.dwell.following && opted.heldScroll.active && opted.clicks.isEmpty,"the retained opt-in experiment only stops on release");opted.edge(false);wait(0.33);expect(!opted.dwell.following && opted.clicks.isEmpty,"opted-in quiet hold stays off without clicking")
let drag=make();tap(drag);wait(0.08);drag.edge(true);wait(0.23);expect(drag.heldScroll.startDrag(now:ProcessInfo.processInfo.systemUptime),"tap-then-hold is an explicit drag");drag.edge(false);wait(0.33)
expect(drag.clicks.isEmpty,"drag release never queues a click")
for reason in ["next press","pause","disconnect","pointer moved","app changed","screenshot","HUD opens","following again"] {
 let h=make();tap(h)
 switch reason {
 case "next press": h.edge(true)
 case "pause": h.actionPause.paused=true
 case "disconnect": h.ready=false
 case "pointer moved": h.point.x+=30
 case "app changed": h.app="other.app"
 case "screenshot": h.startScreenshotShortcut(now:ProcessInfo.processInfo.systemUptime)
 case "HUD opens": h.hudSession=true
 default: h.dwell.follow(true)
 }
 wait(0.33);expect(h.clicks.isEmpty,reason+" rejects the pending click")
 h.heldSafetyTimer?.invalidate()
}
// Exiting never schedules a click, even if the run loop is busy afterward.
let late=make();tap(late);Thread.sleep(forTimeInterval:0.45);wait(0.02)
expect(late.clicks.isEmpty,"an overdue pending click is discarded")
let still=WandDwellClick();still.follow(true);still.move(dx:15,dy:0,now:0,eligible:true);still.move(dx:0,dy:0,now:0.1,eligible:true)
expect(still.tick(now:0.35),"automatic stillness click stays enabled")
print("PASS: exit without click, stillness click, double/triple shortcuts and quiet hold")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-exit-click-'));
 try{writeFileSync(join(dir,'main.swift'),code);const c=spawnSync('swiftc',['-Onone',root+'WandRunLoop.swift',root+'WandPointerControl.swift',join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(c.status,0,c.stderr);const r=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(r.status,0,r.stdout+r.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
