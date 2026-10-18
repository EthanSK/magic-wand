import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { CircularScroll } from "../docs/sim/pointer.mjs";

function trace(clockwise, hz = 35, radius = 80, loops = 3) {
  let x = radius, y = 0;
  return Array.from({ length: hz * loops }, (_, i) => {
    const t = (i + 1) / hz, a = t * 2 * Math.PI * (clockwise ? 1 : -1);
    const nx = radius * Math.cos(a), ny = radius * Math.sin(a);
    const step = [nx - x, (ny - y) * 1.4, t + 10]; x = nx; y = ny; return step;
  });
}

test("circular scrolling has both directions, passes initial motion immediately and stays latched on pause", () => {
  for (const hz of [20, 35, 104]) for (const clockwise of [false, true]) {
    const detector = new CircularScroll();
    const reports = trace(clockwise, hz).map(p => detector.update(...p, true));
    assert(!reports[0].consumesPointer);
    assert(reports.slice(0, Math.floor(hz * 0.7)).every(r => r.lines === 0));
    const lines = reports.reduce((sum, r) => sum + r.lines, 0);
    assert(clockwise ? lines < -10 : lines > 10);
    assert(!detector.expire(14));
    assert(detector.active);
    assert(detector.update(2, 0, 14.01, true).consumesPointer);
  }
});

test("jitter, incomplete curves, straight motion, ineligible modes never scroll", () => {
  for (const eligible of [true, false]) {
    const detector = new CircularScroll();
    assert(trace(true, 35, eligible ? 3 : 80).every(p => !detector.update(...p, eligible).consumesPointer));
  }
  const straight = new CircularScroll();
  for (let i = 0; i < 180; i++) assert.equal(straight.update(3, 0, 20 + i / 35, true).lines, 0);
  const detector = new CircularScroll(); trace(true).forEach(p => detector.update(...p, true));
  assert(detector.active);
  detector.update(0, 0, 13.01, false); assert(!detector.active);
});

test("native geometry clamps all screen edges and gaps; Swift and demo circle traces agree", { skip: process.platform !== "darwin" }, () => {
  const dir = mkdtempSync(join(tmpdir(), "wand-pointer-"));
  try {
    const reports = [true, false].flatMap(clockwise => {
      const c = new CircularScroll(); return trace(clockwise).map(p => c.update(...p, true));
    });
    writeFileSync(join(dir, "main.swift"), `import Foundation
let screen=CGRect(x:0,y:0,width:100,height:100)
for edge in [CGPoint(x:0,y:50),CGPoint(x:99,y:50),CGPoint(x:50,y:0),CGPoint(x:50,y:99)] {
 var p=edge
 let direction=CGPoint(x:edge.x==0 ? -20 : edge.x==99 ? 20 : 0,y:edge.y==0 ? -20 : edge.y==99 ? 20 : 0)
 for _ in 0..<200 {p=WandPointerBounds.clamp(CGPoint(x:p.x+direction.x,y:p.y+direction.y),to:[screen])}
 precondition(p==edge)
 let reverse=WandPointerBounds.clamp(CGPoint(x:p.x-direction.x/10,y:p.y-direction.y/10),to:[screen])
 precondition(reverse != edge,"outward motion cannot accumulate behind an edge")
}
let screens=[screen,CGRect(x:-100,y:50,width:100,height:100),CGRect(x:150,y:-100,width:100,height:100)]
let recovered=WandPointerBounds.clamp(CGPoint(x:50,y:10000),to:screens)
precondition(recovered.y<150)
let gap=WandPointerBounds.clamp(CGPoint(x:120,y:30),to:screens)
precondition(screens.contains{$0.contains(gap)})
var output:[[String:Any]]=[]
for clockwise in [true,false] {
 let c=WandCircularScroll();var x=80.0,y=0.0
 for i in 1...105 {
  let t=Double(i)/35,a=t*2*Double.pi*(clockwise ? 1 : -1),nx=80*cos(a),ny=80*sin(a)
  let r=c.update(dx:nx-x,dy:(ny-y)*1.4,now:t+10,eligible:true);x=nx;y=ny
  output.append(["consumesPointer":r.consumesPointer,"lines":r.lines])
 }
}
print(String(data:try! JSONSerialization.data(withJSONObject:output),encoding:.utf8)!)
`);
    const source = fileURLToPath(new URL("../receiver/Sources/WandPointerControl.swift", import.meta.url));
    const built = spawnSync("swiftc", ["-O", source, join(dir, "main.swift"), "-o", join(dir, "check")], { encoding: "utf8" });
    assert.equal(built.status, 0, built.stderr);
    const run = spawnSync(join(dir, "check"), [], { encoding: "utf8" });
    assert.equal(run.status, 0, run.stderr);
    const native=JSON.parse(run.stdout);assert.equal(native.length,reports.length);
    let nativeLines=0,demoLines=0;
    native.forEach((actual,i)=>{
      assert.equal(actual.consumesPointer,reports[i].consumesPointer,`routing at ${i}`);
      nativeLines+=actual.lines;demoLines+=reports[i].lines;
      // Floating point atan2 can put one wheel line on either side of an exact boundary.
      assert(Math.abs(nativeLines-demoLines)<=1,`wheel quantisation at ${i}`);
    });
    assert(Math.abs(nativeLines-demoLines)<=1);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});


test("native wheel axes retain the same fixed scroll target", {skip:process.platform!=="darwin"}, () => {
 const dir=mkdtempSync(join(tmpdir(),"wand-wheel.noindex-"));
 try {
  const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
  const start=source.indexOf('    static func wheelEvents('),end=source.indexOf('    func postScroll(',start);
  writeFileSync(join(dir,'main.swift'),`import Foundation
import ApplicationServices
enum Wheel {
${source.slice(start,end)}
}
let point=CGPoint(x:-321,y:654)
let events=Wheel.wheelEvents(x:3,y:-4,at:point)
precondition(events.count==2)
precondition(events.allSatisfy{$0.location==point},"wheel events stay at their original target")
precondition(events[0].getIntegerValueField(.scrollWheelEventDeltaAxis2)==3)
precondition(events[1].getIntegerValueField(.scrollWheelEventDeltaAxis1)==(-4))
`);
  const build=spawnSync('swiftc',[join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
