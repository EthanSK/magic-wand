import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

test('held scrolling supplies precise two-axis native phases without momentum or stale gesture state', {skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 const start=source.indexOf('struct WandNativeScrollGesture {');
 const end=source.indexOf('\nfinal class WandReceiver',start);
 assert(start>=0 && end>start);
 const code=`import Cocoa
${source.slice(start,end)}
var g=WandNativeScrollGesture()
let a=CGPoint(x:23,y:47)
precondition(g.finish(cancelled:false)==nil)
precondition(g.update(x:0,y:0,at:a)==nil && !g.active)
let first=NSEvent(cgEvent:g.update(x:3,y:-4,at:a)!)!
precondition(first.phase == .began && first.hasPreciseScrollingDeltas)
precondition(first.scrollingDeltaX==30 && first.scrollingDeltaY == -40)
let second=g.update(x:-2,y:5,at:CGPoint(x:100,y:200))!
precondition(second.location==a)
precondition(NSEvent(cgEvent:second)!.phase == .changed)
precondition(NSEvent(cgEvent:second)!.scrollingDeltaX == -20)
let end=NSEvent(cgEvent:g.finish(cancelled:false)!)!
precondition(end.phase == .ended && end.scrollingDeltaX==0 && end.scrollingDeltaY==0)
precondition(!g.active && g.finish(cancelled:true)==nil)
_ = g.update(x:0,y:2,at:.zero)
let cancel=g.finish(cancelled:true)!
precondition(NSEvent(cgEvent:cancel)!.phase == .cancelled && cancel.location == .zero)
let fresh=g.update(x:-1,y:0,at:a)!
precondition(NSEvent(cgEvent:fresh)!.phase == .began && fresh.location==a)
precondition(NSEvent(cgEvent:fresh)!.momentumPhase.isEmpty)
print("Native scroll: precise both axes, phase lifecycle, fixed anchor, no momentum, restart and cancellation passed")

`;
 const dir=mkdtempSync(join(tmpdir(),'wand-native-scroll-'));
 try {
  const file=join(dir,'main.swift');writeFileSync(file,code);
  const result=spawnSync('swift',[file],{encoding:'utf8'});
  assert.equal(result.status,0,result.stdout+result.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});

test('every held and chord scroll ends, cancels or yields its native gesture exactly once', {skip:process.platform!=='darwin'},()=>{
 const root=new URL('../receiver/Sources/',import.meta.url).pathname;
 const source=readFileSync(root+'main.swift','utf8');
 const method=name=>{const a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);};
 const start=source.indexOf('struct WandNativeScrollGesture {'),end=source.indexOf('\nfinal class WandReceiver',start);
 // Record instead of posting: this harness never sends real input.
 const methods=['postNativeScroll','finishNativeScroll','postScroll','finishScroll','finishBottomHold'].map(method).join('\n')
  .replaceAll('event.post(tap:.cghidEventTap)','posted.append(event)');
 // A native drag can never begin inside an open scroll gesture, and a receiver
 // stop (update or SIGTERM) closes any open gesture.
 assert.ok(/startDrag\(now:now\) \{finishNativeScroll\(cancelled:true\);transition\(to:1,/.test(source),'drag start cancels the open scroll gesture first');
 assert.ok(/finishNativeScroll\(cancelled:true\)/.test(method('stop')),'receiver stop closes an open gesture');
 const beginHold=method('beginBottomHold');
 assert(beginHold.indexOf('finishNativeScroll(cancelled:true)')>=0 && beginHold.indexOf('finishNativeScroll(cancelled:true)')<beginHold.indexOf('heldScroll.begin('),'a new hold cancels a stale native gesture before beginning');
 const code=`import Cocoa
func log(_ v:Any...) {}
${source.slice(start,end)}
struct PauseStub {var paused=false}
final class Harness {
 var scrollFollowBefore=false
 var posted:[CGEvent]=[]
 var nativeScroll=WandNativeScrollGesture(),actionPause=PauseStub()
 var scrollActive=false,scrollAnchor:CGPoint?,circleAnchor:CGPoint?,scrollWatchdog:Timer?,scrollPostedX=0,scrollPostedY=0
 var heldSafetyTimer:Timer?,heldTargetToken=UUID(),heldScrollAnchor:CGPoint?,deliveryPoint:CGPoint?
 let heldScroll=WandHeldScroll();var controlVersion=WandControlVersion.sustainedV3,heldScrollDiagnostics=false,buttons=0
 var mouseOn=0,hudResumed=0
 static func wheelEvents(x:Int32,y:Int32,at point:CGPoint?=nil)->[CGEvent]{[]}
 func currentPointerOrigin()->CGPoint{.zero}
 var physicalDuration:Double?
 func bottomPhysicalTapDuration()->Double?{physicalDuration}
 func transition(to next:Int,at:CGPoint){buttons=next}
 func queue(_ s:String){}
 func setCircleLight(_ on:Bool){}
 func restoreMouseAfterScroll(){mouseOn+=1}
 func resumeHUDNavigation(){hudResumed+=1}
 ${methods}
 func phases()->[NSEvent.Phase]{posted.map{NSEvent(cgEvent:$0)!.phase}}
}
// Two-button chord: began, changed, then a physical release ends it.
let chord=Harness();chord.scrollActive=true;chord.scrollAnchor=CGPoint(x:5,y:6)
chord.postScroll(x:3,y:0);chord.postScroll(x:2,y:1)
// Firmware sends @BOTTOM 0 before the chord's @SCROLL E. The held-scroll
// release must not cancel the chord which owns this open native gesture.
chord.finishBottomHold(now:0.1,released:true)
precondition(chord.phases()==[.began,.changed],"Bottom release waits for the chord end marker")
chord.finishScroll(released:true)
precondition(chord.phases()==[.began,.changed,.ended],"chord release ends the gesture")
precondition(chord.posted.allSatisfy{$0.location==CGPoint(x:5,y:6)},"anchored for the whole gesture")
precondition(chord.scrollPostedX==5 && chord.mouseOn==1)
chord.finishScroll(released:true);precondition(chord.posted.count==3,"a second finish posts nothing")
// Chord watchdog or takeover (not a physical release) cancels it.
let lost=Harness();lost.scrollActive=true;lost.scrollAnchor = .zero
lost.postScroll(x:0,y:-2);lost.finishScroll(released:false)
precondition(lost.phases()==[.began,.cancelled] && lost.hudResumed==1)
// A pause mid-gesture cancels it and sends no further scroll.
let paused=Harness();paused.scrollActive=true;paused.scrollAnchor = .zero
paused.postScroll(x:1,y:0);paused.actionPause.paused=true;paused.postScroll(x:4,y:0)
precondition(paused.phases()==[.began,.cancelled] && !paused.nativeScroll.active)
// Held Bottom scroll: a physical release ends it; lost telemetry cancels it.
for (released,phase) in [(true,NSEvent.Phase.ended),(false,.cancelled)] {
 let held=Harness();held.heldScroll.begin(now:0,scrollable:true);held.heldScrollAnchor=CGPoint(x:9,y:9)
 held.postNativeScroll(x:0,y:3,at:held.heldScrollAnchor);held.postNativeScroll(x:0,y:2,at:.zero)
 held.finishBottomHold(now:1,released:released)
 precondition(held.phases()==[.began,.changed,phase],"held finish \\(released)")
 precondition(held.posted.last!.location==CGPoint(x:9,y:9))
 held.finishBottomHold(now:2,released:true);precondition(held.posted.count==3)
}
// A physically short tap whose release arrived late must not commit history.
let delayed=Harness();delayed.heldScroll.begin(now:0,scrollable:true)
delayed.physicalDuration=0.1
delayed.postNativeScroll(x:3,y:0,at:.zero)
delayed.finishBottomHold(now:1,released:true)
precondition(delayed.phases()==[.began,.cancelled] && delayed.mouseOn==0,"a late tap release cancels instead of committing a swipe")
// No open gesture: finishing is silent.
let idle=Harness();idle.finishNativeScroll(cancelled:true);idle.finishScroll(released:true)
precondition(idle.posted.isEmpty)
print("Native scroll lifecycle: chord end/cancel, pause cancel, held end/cancel, single finish passed")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-native-scroll-life-'));
 try {
  writeFileSync(join(dir,'main.swift'),code);
  const r=spawnSync('swiftc',['-O',root+'WandPointerControl.swift',join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(r.status,0,r.stderr);
  const t=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(t.status,0,t.stdout+t.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
