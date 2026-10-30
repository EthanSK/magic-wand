import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
const root=new URL('../receiver/Sources/',import.meta.url).pathname;
const source=readFileSync(root+'/main.swift','utf8');
function method(name){const a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
test('physical release clears an orphan drag and stale device frames cannot relatch it',{skip:process.platform!=='darwin'},()=>{
const code=`import Foundation
func log(_ v:Any...) {}
final class CGEvent {var location=CGPoint.zero;init?(source:Int?) {}}
final class Harness {
 var scrollFollowBefore=false
 func finishNativeScroll(cancelled:Bool){}

 let screenshot=WandScreenshotGesture();var screenshotRaw=0;func handleScreenshotRaw(_ v:[Int],now:Double){screenshotRaw+=1}
 let heldScroll=WandHeldScroll(),pointerRouter=WandPointerRouter(),dwell=WandDwellClick()
 var heldSafetyTimer:Timer?,heldTargetToken=UUID(),heldScrollAnchor:CGPoint?,deliveryPoint:CGPoint?
 var pointerOrigin=WandPointerOrigin();func currentPointerOrigin()->CGPoint{pointerOrigin.origin(system:CGEvent(source:nil)?.location ?? .zero,now:ProcessInfo.processInfo.systemUptime)}
 var controlVersion=WandControlVersion.sustainedV3,heldScrollDiagnostics=false,buttons=0,recenterSuppressButtons=false
 var physicalTapDuration:Double?=nil;func mouseButtonPhysicalTapDuration()->Double?{physicalTapDuration}
 var reportCount=0,pointerDisplays=[CGRect(x:0,y:0,width:1920,height:1080)],recordingPointerPaused=false,hudSession=false,scrollActive=false
 var transitions:[Int]=[]
 final class Ctx {var isActive=false};let context=Ctx();var hudButtonHeld=false,hudEntryPress=false,pointerInHUD=false,hudOpenedAt=0.0,clickGate:String?
 func closeHUD(reason:String,notifyNative:Bool=true){hudSession=false}
 func noteClickGate(_ gate:String?){clickGate=gate}
 func transition(to next:Int,at:CGPoint){buttons=next;transitions.append(next)}
 func queue(_ s:String){}
 func scheduleDwell(){}
 func setCircleLight(_ on:Bool){}
 func restoreMouseAfterScroll(){}
 func performPointer(_ actions:[WandPointerRouter.Action]){}
 ${['finishMouseButtonHold','reconcileMouseButtonHold','handleFrame'].map(method).join('\n')}
}
let legacy=Harness();legacy.controlVersion = .pointerV1
_=legacy.pointerRouter.mouseButton(down:true);legacy.buttons=1
legacy.reconcileMouseButtonHold(down:false,now:1,reason:"early raw sample")
precondition(legacy.buttons==1,"V1 does not cut a still-held drag on a pre-debounce sample")
_=legacy.pointerRouter.mouseButton(down:false)
legacy.reconcileMouseButtonHold(down:false,now:2,reason:"released raw sample")
precondition(legacy.buttons==0,"V1 releases an orphan after its physical up edge")
legacy.handleFrame(x:0,y:0,b:1);legacy.handleFrame(x:0,y:0,b:0)
precondition(legacy.transitions.suffix(2)==[1,0],"ordinary V1 click pairs remain intact")
for version in [WandControlVersion.scrollV2,.sustainedV3] {
 let h=Harness();h.controlVersion=version
 h.buttons=1 // A native down survived an earlier state cancellation.
 h.reconcileMouseButtonHold(down:false,now:10,reason:"physical release")
 precondition(h.buttons==0,"physical up must release even with no active hold")
 // Once a consumed hold's normal down/up was discarded, a delayed/repeated
 // firmware drag frame must not create a second, unleased OS button-down.
 h.heldScroll.begin(now:20,scrollable:false)
 _=h.heldScroll.startDrag(now:21)
 h.finishMouseButtonHold(now:21)
 precondition(!h.heldScroll.dragging,"ended hold clears the native dragging flag")
 h.handleFrame(x:0,y:0,b:1);h.handleFrame(x:0,y:0,b:0)
 h.handleFrame(x:0,y:0,b:1)
 precondition(h.buttons==0,"legacy device report cannot relatch a V2/V3 drag")
 h.reconcileMouseButtonHold(down:false,now:22,reason:"repeat up")
 precondition(h.buttons==0)
}
print("PASS orphan physical release and stale firmware down")
`;
const dir=mkdtempSync(join(tmpdir(),'wand-orphan-'));
try{writeFileSync(join(dir,'main.swift'),code);const r=spawnSync('swiftc',['-O',root+'/WandPointerControl.swift',join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);const t=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(t.status,0,t.stdout+t.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
