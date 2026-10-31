// Tests gesture acknowledgement without posting any real keyboard/mouse input.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

test('navigation acknowledgement follows completed sideways gestures and fades without queuing input', {skip:process.platform!=='darwin'},()=>{
 const root=new URL('../receiver/Sources/',import.meta.url);
 const source=readFileSync(new URL('main.swift',root),'utf8');
 const start=source.indexOf('struct WandNativeScrollGesture {'),end=source.indexOf('\nfinal class WandReceiver',start);
 assert(start>=0 && end>start);
 const dir=mkdtempSync(join(tmpdir(),'wand-navigation-feedback-'));
 try {
  writeFileSync(join(dir,'gesture.swift'),'import Cocoa\n'+source.slice(start,end));
  writeFileSync(join(dir,'main.swift'),`import Cocoa
var gesture=WandNativeScrollGesture()
var completed:[Int64]=[]
let point=CGPoint(x:20,y:40)
gesture.onCompletedHorizontal = { delta,anchor in
 precondition(anchor==point);completed.append(delta)
}
_ = gesture.update(x:5,y:0,at:point)
_ = gesture.update(x:2,y:0,at:.zero)
precondition(completed.isEmpty)
_ = gesture.finish(cancelled:false)
precondition(completed == [7])
_ = gesture.finish(cancelled:false)
precondition(completed == [7])
_ = gesture.update(x:-3,y:0,at:point)
_ = gesture.finish(cancelled:true)
precondition(completed == [7])
_ = gesture.update(x:8,y:1,at:point)
_ = gesture.finish(cancelled:false)
precondition(completed == [7])
_ = gesture.update(x:3,y:0,at:point)
_ = gesture.update(x:-3,y:0,at:point)
_ = gesture.finish(cancelled:false)
precondition(completed == [7])
_ = gesture.update(x:-4,y:0,at:point)
_ = gesture.finish(cancelled:false)
precondition(completed == [7,-4])
precondition(WandNavigationDirection(horizontalDelta:7) == .back)
precondition(WandNavigationDirection(horizontalDelta:-4) == .forward)
precondition(WandNavigationDirection(horizontalDelta:0) == nil)
precondition(WandNavigationPulse.opacity(at:0)==0)
precondition(WandNavigationPulse.opacity(at:0.04)>0)
precondition(WandNavigationPulse.opacity(at:0.08)==1)
precondition(WandNavigationPulse.opacity(at:0.45)==1)
precondition(WandNavigationPulse.opacity(at:0.65)>0 && WandNavigationPulse.opacity(at:0.65)<1)
precondition(WandNavigationPulse.opacity(at:0.85)==0)
let visible=CGRect(x:-1200,y:80,width:1100,height:800)
precondition(visible.contains(WandNavigationPulse.frame(in:visible)))
print("Direction, completion, cancellation, reset and fade checks passed")
`);
  const build=spawnSync('swiftc',[new URL('WandNavigationFeedback.swift',root).pathname,join(dir,'gesture.swift'),join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});
  assert.equal(build.status,0,build.stderr);
  const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});
  assert.equal(run.status,0,run.stdout+run.stderr);
 } finally {rmSync(dir,{recursive:true,force:true});}
});
