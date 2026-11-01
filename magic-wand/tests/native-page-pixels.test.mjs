// Formerly the pixel transport test: verify restored wheel output with native sideways swipes.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

test('V3 page scrolling restores ordinary wheel events without changing native horizontal swipes',{skip:process.platform!=='darwin'},()=>{
 const root=new URL('../receiver/Sources/',import.meta.url).pathname;
 const source=readFileSync(root+'main.swift','utf8');
 function method(name){const expression=new RegExp('    (?:static )?func '+name+'\\(');const a=source.search(expression);assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
 const a=source.indexOf('struct WandNativeScrollGesture {'),b=source.indexOf('\nfinal class WandReceiver',a);
 assert(method('beginMouseButtonHold').includes('self.heldScroll.continuation(now:now)'));
 assert(!method('beginMouseButtonHold').includes('pageUnitsPerLine:'));
 assert(method('beginMouseButtonHold').includes('self.postSustainedScroll('));
 assert(method('handleRaw').includes('postHeldScroll(x:x,y:y,at:heldScrollAnchor)'),'V2 retains its existing route');
 const methods=['postSustainedScroll','postHeldScroll','postNativeScroll','finishNativeScroll','finishHorizontalStrokeIfNeeded','wheelEvents'].map(method).join('\n').replaceAll('event.post(tap:.cghidEventTap)','posted.append(event)');
 const code=`import Cocoa
func log(_ args:Any...){}
${source.slice(a,b)}
struct Pause {var paused=false}
final class Harness {
 var actionPause=Pause(),nativeScroll=WandNativeScrollGesture()
 let heldScroll=WandHeldScroll()
 var posted:[CGEvent]=[]
 let anchor=CGPoint(x:20,y:30)
 func currentPointerOrigin()->CGPoint{anchor}
 ${methods}
 func sample(x:Double,y:Double,now:Double){heldScroll.confirmHeld(now:now);_=heldScroll.sample(x:x,y:y,dt:0.01,now:now);finishHorizontalStrokeIfNeeded()}
 func tick(_ now:Double){let v=heldScroll.continuation(now:now);if v.x != 0 || v.y != 0 {postSustainedScroll(x:v.x,y:v.y,at:anchor)}}
}
func expect(_ ok:Bool,_ message:String){if !ok {print("FAIL: "+message);fflush(stdout);exit(1)}}
func ordinaryPage(_ event:CGEvent)->Bool {let n=NSEvent(cgEvent:event)!;return !n.hasPreciseScrollingDeltas && n.phase.isEmpty && n.momentumPhase.isEmpty}
let wheel=Harness.wheelEvents(x:1,y:-2,at:CGPoint(x:20,y:30))
expect(wheel.count==2 && wheel.allSatisfy(ordinaryPage),"line builder has no precise deltas or swipe phase")
expect(wheel[0].getIntegerValueField(.scrollWheelEventDeltaAxis2)==1 && wheel[1].getIntegerValueField(.scrollWheelEventDeltaAxis1) == -2,"exact separate wheel line values")
expect(wheel.allSatisfy{$0.location==CGPoint(x:20,y:30)},"wheel builder preserves the anchor")

// The output unit change must preserve the existing stroke-to-speed mapping.
// Fractional wheel travel remains in the controller; late ticks retain their cap.
let lines=WandHeldScroll(),pixels=WandHeldScroll();lines.begin(now:0,sustain:true);pixels.begin(now:0,sustain:true)
var lineTotal:Int32=0,pixelTotal:Int32=0
for i in 1...100 {
 let t=Double(i)*0.01
 for h in [lines,pixels] {h.confirmHeld(now:t);_=h.sample(x:0,y:i<=50 ? 8:0,dt:0.01,now:t)}
 if i%2==0 {lineTotal+=lines.continuation(now:t).y;pixelTotal+=pixels.continuation(now:t,pageUnitsPerLine:10).y}
 expect(lines.sustained.velocityY==pixels.sustained.velocityY,"same speed curve and stroke decisions")
}
expect(abs(Double(pixelTotal)-10*Double(lineTotal))<10,"fractional physical travel preserved within one line")
let before=lines.sustained.velocityY
let capped=lines.sustained.tick(now:100)
expect(capped.y<=Int32(ceil(before*0.05))+1,"late ticks keep the 50 ms cap, never replaying a backlog")
_=lines.end(now:100);expect(lines.continuation(now:100.02)==(0,0),"release stops output")

// Every vertical/diagonal page sample uses ordinary wheel events.
// Even a tick whose rounded y is zero remains a page, never a history swipe.
for pair in [(0.0,8.0),(12.0,12.0)] {
 let h=Harness();h.heldScroll.begin(now:0,sustain:true)
 for i in 1...100 {let t=Double(i)*0.01;h.sample(x:pair.0,y:pair.1,now:t);if i%2==0 {h.tick(t)}}
 expect(!h.posted.isEmpty && h.posted.allSatisfy(ordinaryPage),"vertical and diagonal pages use ordinary wheel events")
 expect(!h.nativeScroll.active && h.posted.allSatisfy{$0.location==h.anchor},"pages retain their anchor without native swipe state")
 h.posted=[];h.postSustainedScroll(x:1,y:0,at:h.anchor)
 expect(h.posted.count==1 && ordinaryPage(h.posted[0]),"a diagonal tick rounding to y=0 stays on the page transport")
}

// Default and explicit pixel-page scaling are identical for horizontal input.
let a=WandHeldScroll(),b=WandHeldScroll();a.begin(now:0,sustain:true);b.begin(now:0,sustain:true)
for i in 1...100 {
 let t=Double(i)*0.01
 for h in [a,b] {h.confirmHeld(now:t);_=h.sample(x:i<60 ? 80:0,y:0,dt:0.01,now:t)}
 expect(a.continuation(now:t)==b.continuation(now:t,pageUnitsPerLine:10),"horizontal native units and stopped-stroke behavior remain identical")
}
let v2=Harness();v2.postHeldScroll(x:0,y:1,at:v2.anchor)
expect(v2.posted.count==1 && !NSEvent(cgEvent:v2.posted[0])!.hasPreciseScrollingDeltas,"V2 still posts its ordinary line wheel event")
let h=Harness();h.heldScroll.begin(now:0,sustain:true)
for i in 1...50 {h.sample(x:80,y:0,now:Double(i)*0.01)}
h.postSustainedScroll(x:2,y:0,at:h.anchor)
expect(NSEvent(cgEvent:h.posted.last!)!.phase == .began && NSEvent(cgEvent:h.posted.last!)!.scrollingDeltaX==20,"horizontal native transport retains its ten-points-per-line scale")
h.posted=[];h.postSustainedScroll(x:1,y:1,at:h.anchor)
expect(h.posted.count==3 && NSEvent(cgEvent:h.posted[0])!.phase == .cancelled && h.posted.dropFirst().allSatisfy(ordinaryPage),"page motion cancels the old native swipe before wheel output")
h.actionPause.paused=true;h.posted=[];h.postSustainedScroll(x:0,y:1,at:h.anchor)
expect(h.posted.isEmpty,"paused debug mode never sends page actions")
print("PASS: ordinary page wheel, existing speed curve, unchanged physics/horizontal/V2, release and late-tick limits")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-page-pixels-'));
 try{writeFileSync(join(dir,'main.swift'),code);const c=spawnSync('swiftc',['-O',root+'WandPointerControl.swift',join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(c.status,0,c.stderr);const r=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(r.status,0,r.stdout+r.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
