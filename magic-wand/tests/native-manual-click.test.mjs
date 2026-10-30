import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const source = readFileSync(new URL('../receiver/Sources/main.swift', import.meta.url), 'utf8');
function method(name) {
  const start = source.indexOf('    func ' + name + '('); assert(start >= 0, name);
  let end = source.indexOf('{', start) + 1, depth = 1;
  while (depth) { if (source[end] === '{') depth++; if (source[end] === '}') depth--; end++; }
  return source.slice(start, end);
}

test('explicit left click cancels the hold, posts one ordinary pair and preserves HUD/screenshot ownership', { skip: process.platform !== 'darwin' }, () => {
  assert(source.includes('if actionPause.admit(.middle,down:true) {handleLeftClickChord()}'), 'dashboard admission gates the new input');
  const code = `import Foundation
var trusted=true
func AXIsProcessTrusted()->Bool {trusted}
func log(_ v:Any...) {}
final class Harness {
 var ready=true,restoring=false,scrollActive=false,buttons=0
 var actionPause=WandActionPause()
 let screenshot=WandScreenshotGesture(),pointerRouter=WandPointerRouter(),recenterGesture=WandRecenterGesture(),dwell=WandDwellClick()
 var tripleClick=WandTripleClick(),clickFollowChoice:Bool?=true,pendingRecenter:Timer?
 var deliveryPoint:CGPoint?=CGPoint(x:320,y:240),events:[Int]=[],points:[CGPoint]=[],endedWithRelease:Bool?
 var interrupted=0
 func currentPointerOrigin()->CGPoint {CGPoint(x:1,y:2)}
 func finishBottomHold(now:Double,released:Bool=true){endedWithRelease=released;buttons=0}
 func performPointer(_ actions:[WandPointerRouter.Action]){interrupted+=1}
 func scheduleDwell(){}
 func transition(to next:Int,at point:CGPoint){events.append(next);points.append(point);buttons=next}
 ${method('handleLeftClickChord')}
}
let h=Harness();_=h.pointerRouter.bottom(down:true)
h.pendingRecenter=Timer.scheduledTimer(withTimeInterval:100,repeats:false){_ in fatalError("centering must be cancelled")}
let pending=h.pendingRecenter!
h.handleLeftClickChord()
precondition(h.events==[1,0] && h.buttons==0,"one complete left click")
precondition(h.points.allSatisfy{$0==CGPoint(x:320,y:240)},"click at the latest delivered pointer, never a stale system cursor")
precondition(h.endedWithRelease==false && h.interrupted==1,"stop scroll/drag without treating it as a completed scroll")
precondition(h.pointerRouter.bottomHeld,"the still-held centre continues to block automatic clicks")
precondition(h.clickFollowChoice==nil && h.pendingRecenter==nil && !pending.isValid,"cancel centre double/triple tap ownership")
h.handleLeftClickChord();precondition(h.events==[1,0,1,0],"another explicit press can click during the same hold")
let noHold=Harness();noHold.handleLeftClickChord();precondition(noHold.events.isEmpty)
for mode in 0..<5 {
 let blocked=Harness();_=blocked.pointerRouter.bottom(down:true)
 switch mode {
 case 0: blocked.ready=false
 case 1: blocked.restoring=true
 case 2: _=blocked.actionPause.pause()
 case 3: blocked.scrollActive=true
 case 4: _=blocked.screenshot.requestShortcut(now:10)
 default: fatalError()
 }
 blocked.handleLeftClickChord();precondition(blocked.events.isEmpty && blocked.endedWithRelease==nil,"blocked click must not disturb its current owner")
}
trusted=false;let untrusted=Harness();_=untrusted.pointerRouter.bottom(down:true);untrusted.handleLeftClickChord();precondition(untrusted.events.isEmpty)
print("explicit native click checks passed")
`;
  const dir = mkdtempSync(join(tmpdir(), 'wand-manual-click-'));
  try {
    writeFileSync(join(dir, 'main.swift'), code);
    const built = spawnSync('swiftc', ['-Onone', ...['WandPointerControl.swift', 'WandActionPause.swift'].map(name => fileURLToPath(new URL('../receiver/Sources/' + name, import.meta.url))), join(dir, 'main.swift'), '-o', join(dir, 'check')], { encoding: 'utf8' });
    assert.equal(built.status, 0, built.stderr);
    const run = spawnSync(join(dir, 'check'), [], { encoding: 'utf8' });
    assert.equal(run.status, 0, run.stdout + run.stderr);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
