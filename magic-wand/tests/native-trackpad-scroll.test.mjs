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

test('page scrolls use line wheel events; only sideways held output owns a native gesture, ended or cancelled exactly once', {skip:process.platform!=='darwin'},()=>{
 const root=new URL('../receiver/Sources/',import.meta.url).pathname;
 const source=readFileSync(root+'main.swift','utf8');
 const block=(a)=>{assert(a>=0);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);};
 const method=name=>block(source.indexOf('    func '+name+'('));
 const start=source.indexOf('struct WandNativeScrollGesture {'),end=source.indexOf('\nfinal class WandReceiver',start);
 // Record instead of posting: this harness never sends real input. wheelEvents is the
 // receiver's own ordinary line-event builder, unchanged since before native gestures.
 const methods=['postHeldScroll','postNativeScroll','finishNativeScroll','postScroll','finishScroll','finishMouseButtonHold','finishHorizontalStrokeIfNeeded','consumeEarlyHorizontalIntent'].map(method).join('\n')
  .replaceAll('event.post(tap:.cghidEventTap)','posted.append(event)');
 const wheel=block(source.indexOf('    static func wheelEvents('));
 assert.ok(/startDrag\(now:now\) \{finishNativeScroll\(cancelled:true\);transition\(to:1,/.test(source),'drag start cancels the open scroll gesture first');
 assert.ok(/finishNativeScroll\(cancelled:true\)/.test(method('stop')),'receiver stop closes an open gesture');
 const beginHold=method('beginMouseButtonHold');
 assert(beginHold.indexOf('finishNativeScroll(cancelled:true)')>=0 && beginHold.indexOf('finishNativeScroll(cancelled:true)')<beginHold.indexOf('heldScroll.begin('),'a new hold cancels a stale native gesture before beginning');
 // Every held output goes through the router; nothing else starts a native gesture.
 assert.equal((source.match(/postNativeScroll\(/g)||[]).length,2,'only postHeldScroll calls postNativeScroll');
 assert.ok(beginHold.includes('self.postSustainedScroll(x:units.x,y:units.y,at:self.heldScrollAnchor)'),'V3 continuation uses the pixel-aware page router');
 assert.ok(method('handleRaw').includes('postHeldScroll(x:x,y:y,at:heldScrollAnchor)'),'V2 held lines are routed');
 assert.ok(method('handleRaw').includes('finishHorizontalStrokeIfNeeded()'),'every raw held sample promptly consumes the stroke boundary');
 assert.ok(!method('postScroll').includes('postNativeScroll'),'the chord never opens a native gesture');
 const code=`import Cocoa
func log(_ v:Any...) {}
${source.slice(start,end)}
struct PauseStub {var paused=false}
final class Harness {
 var tripleClick=WandTripleClick(),pendingRecenter:Timer?
 let recenterGesture=WandRecenterGesture()
 var scrollFollowBefore=false,ready=true,restoring=false
 let dwell=WandDwellClick()
 let screenshot=WandScreenshotGesture()
 var posted:[CGEvent]=[]
 var nativeScroll=WandNativeScrollGesture(),actionPause=PauseStub()
 final class Rest {func pointerStopped(){}};let restDetection=Rest()
 func scheduleDwell(){}
 var scrollActive=false,scrollAnchor:CGPoint?,circleAnchor:CGPoint?,scrollWatchdog:Timer?,scrollPostedX=0,scrollPostedY=0
 var heldSafetyTimer:Timer?,heldTargetToken=UUID(),heldScrollAnchor:CGPoint?,deliveryPoint:CGPoint?
 let heldScroll=WandHeldScroll();var controlVersion=WandControlVersion.sustainedV3,heldScrollDiagnostics=false,buttons=0
 var mouseOn=0,hudResumed=0
${wheel}
 func currentPointerOrigin()->CGPoint{.zero}
 var physicalDuration:Double?
 func mouseButtonPhysicalTapDuration()->Double?{physicalDuration}
 func transition(to next:Int,at:CGPoint){buttons=next}
 func queue(_ s:String){}
 func setCircleLight(_ on:Bool){}
 func restoreMouseAfterScroll(){mouseOn+=1}
 func resumeHUDNavigation(){hudResumed+=1}
 ${methods}
 func sample(x:Double,y:Double=0,now:Double) {
  heldScroll.confirmHeld(now:now)
  let before=heldScroll.earlyHorizontal
  _=heldScroll.sample(x:x,y:y,dt:0.01,now:now)
  if !before && heldScroll.earlyHorizontal {consumeEarlyHorizontalIntent(now:now)}
  finishHorizontalStrokeIfNeeded()
 }
 func tick(now:Double) {
  let v=heldScroll.continuation(now:now)
  if v.x != 0 || v.y != 0 {postHeldScroll(x:v.x,y:v.y,at:heldScrollAnchor)}
 }
 // "L" an ordinary line event, else the native phase; deltas in lines for both.
 enum Kind:Equatable {case line(x:Int64,y:Int64),native(NSEvent.Phase,x:Int64)}
 func kinds()->[Kind]{posted.map{e in
  let n=NSEvent(cgEvent:e)!
  if !n.hasPreciseScrollingDeltas {
   precondition(n.phase.isEmpty && n.momentumPhase.isEmpty && e.getIntegerValueField(.scrollWheelEventIsContinuous)==0,"line events carry no phase")
   return .line(x:e.getIntegerValueField(.scrollWheelEventDeltaAxis2),y:e.getIntegerValueField(.scrollWheelEventDeltaAxis1))
  }
  precondition(n.scrollingDeltaY==0 && n.momentumPhase.isEmpty,"native events are sideways only, without momentum")
  return .native(n.phase,x:Int64(n.scrollingDeltaX)/10)
 }}
 var nativeCount:Int {kinds().filter{if case .native = $0 {return true};return false}.count}
}
let anchor=CGPoint(x:9,y:9)
// 1. Two-button chord: ordinary line events only, exactly its original transport.
let chord=Harness();chord.scrollActive=true;chord.scrollAnchor=CGPoint(x:5,y:6)
chord.postScroll(x:3,y:0);chord.postScroll(x:2,y:1)
precondition(chord.kinds()==[.line(x:3,y:0),.line(x:2,y:0),.line(x:0,y:1)],"chord posts line events, one axis each")
precondition(chord.posted.allSatisfy{$0.location==CGPoint(x:5,y:6)},"chord keeps its anchor")
chord.finishMouseButtonHold(now:0.1,released:true);chord.finishScroll(released:true);chord.finishScroll(released:true)
precondition(chord.posted.count==3 && chord.scrollPostedX==5 && chord.scrollPostedY==1 && chord.mouseOn==1,"chord end posts no phase and restores follow once")
let lost=Harness();lost.scrollActive=true;lost.scrollAnchor = .zero
lost.postScroll(x:0,y:-2);lost.finishScroll(released:false)
precondition(lost.kinds()==[.line(x:0,y:-2)] && lost.hudResumed==1,"a lost chord posts no phase")
let paused=Harness();paused.scrollActive=true;paused.scrollAnchor = .zero
paused.postScroll(x:1,y:0);paused.actionPause.paused=true;paused.postScroll(x:4,y:0)
precondition(paused.kinds()==[.line(x:1,y:0)],"a pause stops chord scrolling")
// 2. Held vertical page scrolling: line events at the anchor, no gesture to end.
for released in [true,false] {
 let held=Harness();held.heldScroll.begin(now:0,scrollable:true);held.heldScrollAnchor=anchor
 held.postHeldScroll(x:0,y:3,at:held.heldScrollAnchor);held.postHeldScroll(x:0,y:-2,at:held.heldScrollAnchor)
 held.finishMouseButtonHold(now:1,released:released)
 precondition(held.kinds()==[.line(x:0,y:3),.line(x:0,y:-2)] && held.posted.allSatisfy{$0.location==anchor},"vertical held scroll is line events only")
 precondition(held.mouseOn==(released ? 1:0),"a released vertical scroll restores follow; lost telemetry does not")
}
// 3. Diagonal page scrolling keeps both axes as line events.
let diagonal=Harness();diagonal.heldScroll.begin(now:0);diagonal.postHeldScroll(x:3,y:2,at:anchor)
precondition(diagonal.kinds()==[.line(x:3,y:0),.line(x:0,y:2)],"diagonal is line events on both axes")
// 4. Held sideways: one native gesture, began/changed then ended (release) or cancelled (lost).
for (released,phase) in [(true,NSEvent.Phase.ended),(false,.cancelled)] {
 let held=Harness();held.heldScroll.begin(now:0,scrollable:true);held.heldScrollAnchor=anchor
 held.postHeldScroll(x:3,y:0,at:held.heldScrollAnchor);held.postHeldScroll(x:-2,y:0,at:.zero)
 held.finishMouseButtonHold(now:1,released:released)
 precondition(held.kinds()==[.native(.began,x:3),.native(.changed,x:-2),.native(phase,x:0)],"sideways held finish")
 precondition(held.posted.allSatisfy{$0.location==anchor},"sideways gesture anchored")
 held.finishMouseButtonHold(now:2,released:true);precondition(held.posted.count==3,"a second finish posts nothing")
}
// 5. Sideways then page scrolling in one hold: the swipe is cancelled before the first
//    line event, so no history commits; a later sideways stroke begins a fresh gesture.
let turn=Harness();turn.heldScroll.begin(now:0);turn.heldScrollAnchor=anchor
turn.postHeldScroll(x:3,y:0,at:anchor);turn.postHeldScroll(x:2,y:0,at:anchor);turn.postHeldScroll(x:0,y:4,at:anchor)
turn.postHeldScroll(x:0,y:4,at:anchor);turn.postHeldScroll(x:1,y:0,at:anchor);turn.finishMouseButtonHold(now:1,released:true)
precondition(turn.kinds()==[.native(.began,x:3),.native(.changed,x:2),.native(.cancelled,x:0),.line(x:0,y:4),.line(x:0,y:4),
                            .native(.began,x:1),.native(.ended,x:0)],"axis change cancels, then a fresh gesture")
// 6. A physically short tap whose release arrived late must not commit history.
let delayed=Harness();delayed.heldScroll.begin(now:0,scrollable:true);delayed.physicalDuration=0.1
delayed.postHeldScroll(x:3,y:0,at:.zero);delayed.finishMouseButtonHold(now:1,released:true)
precondition(delayed.kinds()==[.native(.began,x:3),.native(.cancelled,x:0)] && delayed.mouseOn==0,"a late tap release cancels")
// 7. A pause mid-swipe cancels at once and sends nothing more.
let hold=Harness();hold.heldScroll.begin(now:0);hold.postHeldScroll(x:2,y:0,at:anchor);hold.actionPause.paused=true
hold.postHeldScroll(x:2,y:0,at:anchor);hold.postHeldScroll(x:0,y:2,at:anchor)
precondition(hold.kinds()==[.native(.began,x:2),.native(.cancelled,x:0)],"pause cancels the swipe and posts nothing more")
// 8. Zero output and idle finishes are silent.
let idle=Harness();idle.postHeldScroll(x:0,y:0,at:anchor);idle.finishNativeScroll(cancelled:true);idle.finishScroll(released:true)
precondition(idle.posted.isEmpty)
func expect(_ ok:Bool,_ message:String) {if !ok {print("FAIL: "+message);fflush(stdout);exit(1)}}
// 9. An abrupt stop ends the native swipe while the physical button stays held.
let stop=Harness();stop.heldScroll.begin(now:0,sustain:true);stop.heldScrollAnchor=anchor
for i in 30...45 {let t=Double(i)*0.01;stop.sample(x:80,now:t);stop.tick(now:t)}
expect(stop.nativeScroll.active,"moving horizontal stroke opens its native gesture")
var endedAt:Double?
for i in 46...70 {
 let t=Double(i)*0.01;stop.sample(x:0,now:t)
 if !stop.nativeScroll.active && endedAt == nil {endedAt=t}
 stop.tick(now:t)
}
expect(endedAt != nil && endedAt!<=0.51,"the existing stroke-end detection ends promptly, with no release wait")
expect(stop.heldScroll.active && stop.kinds().filter{if case .native(.ended,_)=$0{return true};return false}.count==1,"exactly one ended while button remains held")
let countAfterStop=stop.posted.count
for i in 71...120 {let t=Double(i)*0.01;stop.sample(x:0,now:t);stop.tick(now:t)}
expect(stop.posted.count==countAfterStop,"stillness never reopens or synthesizes horizontal continuation")
for i in 121...142 {let t=Double(i)*0.01;stop.sample(x:100,now:t);stop.tick(now:t)}
expect(stop.nativeScroll.active && stop.kinds().filter{if case .native(.began,_)=$0{return true};return false}.count==2,"a fresh deliberate stroke opens a fresh native swipe")
for i in 143...168 {let t=Double(i)*0.01;stop.sample(x:0,now:t);stop.tick(now:t)}
let beforeRelease=stop.posted.count
stop.finishMouseButtonHold(now:1.7,released:true)
expect(stop.posted.count==beforeRelease,"release after stopped swipe sends no duplicate end")
expect(stop.posted.allSatisfy{$0.location==anchor},"every restarted swipe retains the held anchor")
// 10. Reversal cancels the old in-flight swipe before a new one starts.
let reverse=Harness();reverse.heldScroll.begin(now:0,sustain:true);reverse.heldScrollAnchor=anchor
for i in 30...45 {let t=Double(i)*0.01;reverse.sample(x:80,now:t);reverse.tick(now:t)}
for i in 46...75 {let t=Double(i)*0.01;reverse.sample(x:-100,now:t);reverse.tick(now:t)}
expect(reverse.kinds().contains{if case .native(.cancelled,_)=$0{return true};return false},"a turn cancels rather than accepts the old swipe")
expect(reverse.kinds().filter{if case .native(.began,_)=$0{return true};return false}.count==2,"qualified reverse stroke gets its own gesture")
reverse.finishMouseButtonHold(now:0.8,released:false)
expect(reverse.kinds().last == .native(.cancelled,x:0),"lost telemetry cancels the current swipe")
// A missing sample interval cancels an open stroke; it cannot accept history.
let gap=Harness();gap.heldScroll.begin(now:0,sustain:true);gap.heldScrollAnchor=anchor
for i in 30...45 {let t=Double(i)*0.01;gap.sample(x:80,now:t);gap.tick(now:t)}
gap.sample(x:0,now:0.8);gap.tick(now:0.8)
expect(gap.kinds().last == .native(.cancelled,x:0) && !gap.nativeScroll.active,"an input gap cancels the swipe")
// 11. Vertical and diagonal output still continue at the latched speed while still.
for y in [80.0,60.0] {
 let page=Harness();page.heldScroll.begin(now:0,sustain:true)
 let x=y==80 ? 0.0:60.0
 for i in 30...45 {let t=Double(i)*0.01;page.sample(x:x,y:y,now:t);page.tick(now:t)}
 for i in 46...70 {let t=Double(i)*0.01;page.sample(x:0,y:0,now:t);page.tick(now:t)}
 let count=page.posted.count
 for i in 71...90 {let t=Double(i)*0.01;page.sample(x:0,y:0,now:t);page.tick(now:t)}
 expect(page.posted.count>count && !page.nativeScroll.active,"page output continues while still, with line events")
}

// 12. A clear short sideways flick earns output before 220 ms and consumes
// its press, including the receiver's exit click and double/triple recognizers.
for sign in [-1.0,1.0] {
 let h=Harness();h.scrollFollowBefore=true;h.physicalDuration=0.18;h.heldScroll.begin(now:0,sustain:true)
 _=h.recenterGesture.edge(down:true,now:0);_=h.tripleClick.edge(down:true,now:0)
 for i in 6...15 {let t=Double(i)/100;h.sample(x:120*sign,now:t);h.tick(now:t)}
 expect(h.heldScroll.earlyHorizontal && h.nativeScroll.active,"clear horizontal earns early output")
 expect(h.tripleClick.edge(down:false,now:0.18) == .none,"consumed release cannot join triple click")
 h.finishMouseButtonHold(now:0.18)
 expect(!h.recenterGesture.edge(down:false,now:0.18),"consumed release cannot join double click")
 expect(h.mouseOn==1,"short swipe preserves scroll follow restoration without exit click")
 expect(h.kinds().last == .native(.ended,x:0),"accepted short swipe ends instead of cancels")
 expect(h.heldScroll.consumes(buttons:1) && h.heldScroll.consumes(buttons:0),"firmware endpoint click consumed")
 expect(!h.heldScroll.consumes(buttons:1),"next ordinary click remains independent")
 h.heldScroll.begin(now:0.3,sustain:true)
 expect(!h.heldScroll.earlyHorizontal,"fresh hold resets early intent")
 _=h.recenterGesture.edge(down:true,now:0.3);_=h.tripleClick.edge(down:true,now:0.3)
 h.physicalDuration=0.1;h.finishMouseButtonHold(now:0.4)
 expect(!h.dwell.following,"ordinary tap stops follow without a click")
 expect(!h.recenterGesture.edge(down:false,now:0.4),"fresh first tap is not a double")
 _=h.recenterGesture.edge(down:true,now:0.5)
 expect(h.recenterGesture.isSecondPress && h.recenterGesture.edge(down:false,now:0.6),"fresh ordinary double tap works")
}
let earlyLost=Harness();earlyLost.heldScroll.begin(now:0,sustain:true)
for i in 6...15 {let t=Double(i)/100;earlyLost.sample(x:120,now:t);earlyLost.tick(now:t)}
earlyLost.finishMouseButtonHold(now:0.18,released:false)
expect(earlyLost.kinds().last == .native(.cancelled,x:0) && earlyLost.mouseOn==0,"lost early gesture cancels without restoring follow")
for (scrollable,resolving) in [(false,false),(true,true)] {
 let h=WandHeldScroll();h.begin(now:0,scrollable:scrollable,sustain:true,resolving:resolving)
 for i in 5..<20 {let t=Double(i)/100;h.confirmHeld(now:t);_=h.sample(x:150,y:0,dt:0.01,now:t)
  expect(!h.earlyHorizontal && h.continuation(now:t).x==0,"pending target and explicit drag never fast qualify")}
}
let pending=WandHeldScroll();pending.begin(now:0,sustain:true,resolving:true)
for i in 5..<12 {_=pending.sample(x:150,y:0,dt:0.01,now:Double(i)/100)}
expect(pending.setTarget(scrollable:false,now:0.12) && !pending.earlyHorizontal,"early samples cannot steal pending drag target")
expect(!pending.startDrag(now:0.15) && pending.startDrag(now:0.23),"ordinary drag keeps hold timing")

let negatives:[(String,(Double)->(Double,Double))]=[
 ("quiet tap",{t in (0.5*sin(t*100),0.3*cos(t*100))}),
 ("tremor",{t in (8*sin(t*100),6*cos(t*100))}),
 ("slow drift",{_ in (10,0)}),
 ("one-frame knock",{t in (t>=0.1 && t<0.11 ? 500:0,0)}),
 ("two-frame knock",{t in (t>=0.1 && t<0.12 ? 500:0,0)}),
 ("vertical flick",{t in (0,t>=0.06 && t<0.18 ? 120:0)}),
 ("diagonal flick",{t in t>=0.06 && t<0.18 ? (120,100):(0,0)})
]
for (name,rate) in negatives {
 let h=WandHeldScroll();h.begin(now:0,sustain:true)
 for i in 5..<22 {let t=Double(i)/100,(x,y)=rate(t);h.confirmHeld(now:t);_=h.sample(x:x,y:y,dt:0.01,now:t)
  let v=h.continuation(now:t);expect(!h.earlyHorizontal && v.x==0 && v.y==0,name+" retains hold gate")}
}
print("Scroll transports: chord and page lines, sideways native began/changed/ended/cancelled, axis-change cancel, pause, late tap passed")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-native-scroll-life-'));
 try {
  writeFileSync(join(dir,'main.swift'),code);
  const r=spawnSync('swiftc',['-O',root+'WandPointerControl.swift',join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(r.status,0,r.stderr);
  const t=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(t.status,0,t.stdout+t.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});

// Ethan, 2026-10-30: native Back/Forward swipes are "not sensitive enough". Synthetic
// hands on the real V3 held controller plus the real native transport, recorded and
// never posted. Distance alone does not prove Chrome or Codex navigates.
test('horizontal held swipes travel further with unchanged timing, vertical, diagonal and lifecycle', {skip:process.platform!=='darwin'},()=>{
 const root=new URL('../receiver/Sources/',import.meta.url).pathname;
 const source=readFileSync(root+'main.swift','utf8');
 const start=source.indexOf('struct WandNativeScrollGesture {'),end=source.indexOf('\nfinal class WandReceiver',start);
 assert(start>=0 && end>start);
 const dir=mkdtempSync(join(tmpdir(),'wand-trackpad-swipe-'));
 try {
  writeFileSync(join(dir,'gesture.swift'),'import Cocoa\n'+source.slice(start,end));
  writeFileSync(join(dir,'main.swift'),readFileSync(new URL('./fixtures/trackpad-swipe-main.swift',import.meta.url),'utf8'));
  const sim=new URL('./fixtures/sustained-scroll-sim.swift',import.meta.url).pathname;
  const r=spawnSync('swiftc',['-O',root+'WandPointerControl.swift',sim,join(dir,'gesture.swift'),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(r.status,0,r.stderr);
  const t=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(t.status,0,t.stdout+t.stderr);
  console.log(t.stdout.trim());
 } finally {rmSync(dir,{recursive:true,force:true});}
});
