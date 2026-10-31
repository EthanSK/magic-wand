import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

test('V3 page scrolling emits precise pixels without swipe phases, integer-line stalls or replay',{skip:process.platform!=='darwin'},()=>{
 const root=new URL('../receiver/Sources/',import.meta.url).pathname;
 const source=readFileSync(root+'main.swift','utf8');
 function method(name){const expression=new RegExp('    (?:static )?func '+name+'\\(');const a=source.search(expression);assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
 const a=source.indexOf('struct WandNativeScrollGesture {'),b=source.indexOf('\nfinal class WandReceiver',a);
 assert(method('beginMouseButtonHold').includes('pageUnitsPerLine:WandSustainedScroll.pagePixelsPerLine'));
 assert(method('beginMouseButtonHold').includes('self.postSustainedScroll('));
 assert(method('handleRaw').includes('postHeldScroll(x:x,y:y,at:heldScrollAnchor)'),'V2 retains its existing route');
 const methods=['postSustainedScroll','postHeldScroll','postNativeScroll','finishNativeScroll','finishHorizontalStrokeIfNeeded','wheelEvents','pagePixelEvent'].map(method).join('\n').replaceAll('event.post(tap:.cghidEventTap)','posted.append(event)');
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
 func tick(_ now:Double){let v=heldScroll.continuation(now:now,pageUnitsPerLine:WandSustainedScroll.pagePixelsPerLine);if v.x != 0 || v.y != 0 {postSustainedScroll(x:v.x,y:v.y,at:anchor)}}
}
func expect(_ ok:Bool,_ message:String){if !ok {print("FAIL: "+message);fflush(stdout);exit(1)}}
func precisePage(_ event:CGEvent)->Bool {let n=NSEvent(cgEvent:event)!;return n.hasPreciseScrollingDeltas && n.phase.isEmpty && n.momentumPhase.isEmpty && event.getIntegerValueField(.scrollWheelEventScrollPhase)==0}
let pixel=Harness.pagePixelEvent(x:1,y:-2,at:CGPoint(x:20,y:30))!
let native=NSEvent(cgEvent:pixel)!
expect(precisePage(pixel) && native.scrollingDeltaX==1 && native.scrollingDeltaY == -2,"pixel builder has exact precise deltas and no swipe phase")
expect(pixel.location==CGPoint(x:20,y:30),"pixel builder preserves the anchor")

// A slow qualified page stroke should reach the existing 20 ms output cadence
// in one/two-pixel increments, instead of waiting ~150 ms for one large line.
let lines=WandHeldScroll(),pixels=WandHeldScroll();lines.begin(now:0,sustain:true);pixels.begin(now:0,sustain:true)
var lineValues:[Int32]=[],pixelValues:[Int32]=[]
for i in 1...100 {
 let t=Double(i)*0.01
 for h in [lines,pixels] {h.confirmHeld(now:t);_=h.sample(x:0,y:i<=50 ? 8:0,dt:0.01,now:t)}
 if i%2==0 {
  let l=lines.continuation(now:t),p=pixels.continuation(now:t,pageUnitsPerLine:10)
  if i>=40 {lineValues.append(l.y);pixelValues.append(p.y)}
 }
}
expect(pixelValues.filter{$0 != 0}.count>lineValues.filter{$0 != 0}.count*4,"small page output no longer stalls on whole lines")
expect(pixelValues.allSatisfy{$0>=1 && $0<=2},"slow page output stays at one/two pixels per existing tick")
expect(lines.sustained.velocityY==pixels.sustained.velocityY,"pixel precision never changes held speed")
expect(abs(Double(pixelValues.reduce(0,+))-10*Double(lineValues.reduce(0,+)))<10,"fractional physical travel is preserved within one former line")
let before=pixels.sustained.velocityY
let capped=pixels.sustained.tick(now:100,pageUnitsPerLine:10)
expect(capped.y<=Int32(ceil(before*10*0.05))+1,"late ticks use the existing 50 ms cap, never replaying a backlog")
_=pixels.end(now:100);expect(pixels.continuation(now:100.02,pageUnitsPerLine:10)==(0,0),"release stops pixel output")

// The production route sends every vertical/diagonal page sample as precise,
// phase-less pixel events. Even a tick whose rounded y is zero remains a page.
for pair in [(0.0,8.0),(12.0,12.0)] {
 let h=Harness();h.heldScroll.begin(now:0,sustain:true)
 for i in 1...100 {let t=Double(i)*0.01;h.sample(x:pair.0,y:pair.1,now:t);if i%2==0 {h.tick(t)}}
 expect(!h.posted.isEmpty && h.posted.allSatisfy(precisePage),"vertical and diagonal pages never open history swipe phases")
 expect(!h.nativeScroll.active && h.posted.allSatisfy{$0.location==h.anchor},"pages retain their anchor without native swipe state")
 h.posted=[];h.postSustainedScroll(x:1,y:0,at:h.anchor)
 expect(h.posted.count==1 && precisePage(h.posted[0]),"a diagonal tick rounding to y=0 stays on the page transport")
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
print("PASS: phase-less precise page pixels, smooth low-speed cadence, unchanged physics/horizontal/V2, release and late-tick limits")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-page-pixels-'));
 try{writeFileSync(join(dir,'main.swift'),code);const c=spawnSync('swiftc',['-O',root+'WandPointerControl.swift',join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(c.status,0,c.stderr);const r=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(r.status,0,r.stdout+r.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
