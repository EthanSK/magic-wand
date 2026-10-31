import {fileURLToPath as wandSourcePath} from 'node:url';
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

test('mouse-button double tap always centres and enables follow across prior modes', {skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 function method(name){const start=source.indexOf('    func '+name+'(');assert(start>=0,name);let end=source.indexOf('{',start)+1,depth=1;while(depth){if(source[end]==='{')depth++;if(source[end]==='}')depth--;end++;}return source.slice(start,end);}
 const body=source.slice(source.indexOf('if let marker=line.range(of:"@BOTTOM ")'),source.indexOf('if let marker=line.range(of:"@MIDDLE ")'));
 // Release queues its exit click before recenter consumes it; a double click cancels it.
 const finish=body.indexOf('if controlVersion.usesHeldScroll && value=="0"');
 const recognize=body.indexOf('recognizeMouseButtonRecenter');
 const route=body.indexOf('if controlVersion.usesHeldScroll && !scrollActive');
 assert(finish>=0 && finish<recognize && recognize<route);
 assert(!body.includes('eligible:'));
 const code=`import Foundation
func AXIsProcessTrusted()->Bool {true}
func log(_ v:Any...) {}
var warped=CGPoint.zero
func CGMainDisplayID()->Int {1}
func CGDisplayBounds(_ id:Int)->CGRect {CGRect(x:100,y:-200,width:1200,height:800)}
func CGWarpMouseCursorPosition(_ point:CGPoint){warped=point}
final class Rest {var activated=false;func pointerActivated(){activated=true}}
final class Harness {
 func cancelMouseExitClick(){}
 var actionPause=WandActionPause()
 let pointerRouter=WandPointerRouter(),recenterGesture=WandRecenterGesture(),dwell=WandDwellClick(),motionFilter=WandMotionFilter(),restDetection=Rest()
 let screenshot=WandScreenshotGesture();var pendingRecenter:Timer?
 var ready=true,restoring=false,recenterSuppressButtons=false,deliveryPoint:CGPoint?,commands:[String]=[]
 var pointerOrigin=WandPointerOrigin(),settled:CGPoint?
 func settleRecenteredCursor(at point:CGPoint){settled=point}
 var hud=false,scroll=false,buttons=0,appMode:String?
 func queue(_ text:String){commands.append(text)}
 func closeHUD(reason:String){hud=false;appMode=nil}
 func cancelCircleScroll(){_ = pointerRouter.interrupt()}
 func finishScroll(){scroll=false}
 func releaseButtons(){buttons=0}
 func performPointer(_ actions:[WandPointerRouter.Action]){}
 func scheduleDwell(){}
 ${['recognizeMouseButtonRecenter','recenterPointer'].map(method).join('\n')}
}
for mode in ["off","mouse","hud","scroll","vsCode","drag"] {
 let h=Harness();h.hud=mode=="hud";h.scroll=mode=="scroll";h.appMode=mode=="vsCode" ? "vsCode":nil;h.buttons=mode=="drag" ? 1:0
 h.dwell.follow(mode=="mouse");_=h.pointerRouter.mouseButton(down:true)
 precondition(!h.recognizeMouseButtonRecenter(down:true,now:1))
 precondition(!h.recognizeMouseButtonRecenter(down:false,now:1.08))
 // Mode teardown caused by the first tap must not erase the global gesture.
 h.cancelCircleScroll()
 precondition(!h.recognizeMouseButtonRecenter(down:true,now:1.18))
 warped = .zero
 precondition(h.recognizeMouseButtonRecenter(down:false,now:1.26),mode)
 // Ethan's triple-click shares these clicks: centre once its window passes.
 precondition(warped == .zero && h.pendingRecenter != nil && h.dwell.following == (mode=="mouse"),"no centre before the third-press window "+mode)
 RunLoop.main.run(until:Date().addingTimeInterval(WandTripleClick.window+0.03))
 precondition(h.pendingRecenter==nil && warped==CGPoint(x:700,y:200) && h.deliveryPoint==warped,mode)
 precondition(h.dwell.following && !h.pointerRouter.mouseButtonHeld && h.buttons==0,mode)
 precondition(h.hud==(mode=="hud") && !h.scroll && h.appMode==(mode=="vsCode" ? "vsCode":nil) && h.restDetection.activated,mode)
 precondition(h.recenterSuppressButtons && h.commands.last!.contains("setMouseFollow(true)"))
}
let hold=Harness();_=hold.recognizeMouseButtonRecenter(down:true,now:2);_=hold.recognizeMouseButtonRecenter(down:false,now:2.08);_=hold.recognizeMouseButtonRecenter(down:true,now:2.18)
precondition(!hold.recognizeMouseButtonRecenter(down:false,now:2.6),"long second press remains a hold")
precondition(hold.pendingRecenter==nil)
let busy=Harness();_=busy.screenshot.requestShortcut(now:3);warped = .zero;busy.recenterPointer()
precondition(warped == .zero,"screenshot mode is never recentred")
// Ethan: "It came to the center and then it jumped back." After the centre,
// stale motion state, residuals and a lagging system cursor never restore
// the old position.
do {
 let h=Harness()
 precondition(h.motionFilter.configure([0,0,86.4*1.52425,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,1]));h.motionFilter.path = .direct
 var carried=0
 for _ in 0..<40 {carried+=abs(h.motionFilter.sample(rawX:6000,rawY:-4000,microseconds:9615,held:false,resetState:false)!.x)}
 precondition(carried>0,"the hand was moving fast before the double tap")
 h.recenterPointer()
 let centre=CGPoint(x:700,y:200)
 precondition(warped==centre && h.settled==centre,"the centre is also posted through the input queue")
 let first=h.motionFilter.sample(rawX:0,rawY:0,microseconds:9615,held:false,resetState:false)!
 precondition(first.x==0 && first.y==0,"no smoothed or subpixel residual from before the centre")
 let old=CGPoint(x:1250,y:540)
 var now=10.0;h.pointerOrigin.begin(at:centre,now:now)
 precondition(h.pointerOrigin.origin(system:old,now:now+0.02)==centre,"a lagging or stale old location never becomes the origin")
 h.pointerOrigin.moved(from:centre,to:CGPoint(x:705,y:198),now:now+0.03)
 precondition(h.pointerOrigin.origin(system:old,now:now+0.05)==CGPoint(x:705,y:198),"the next movement chains from the centre")
 precondition(h.pointerOrigin.origin(system:CGPoint(x:705,y:198),now:now+0.08)==CGPoint(x:705,y:198),"once the system agrees, ordinary tracking resumes")
 precondition(h.pointerOrigin.origin(system:CGPoint(x:900,y:400),now:now+0.09)==CGPoint(x:900,y:400),"after it, a physical mouse is adopted at once")
 now=20;h.pointerOrigin.begin(at:centre,now:now)
 precondition(h.pointerOrigin.origin(system:old,now:now+WandPointerOrigin.settle+0.01)==old && h.pointerOrigin.latest==nil,"bounded: never overrides the real cursor indefinitely")
}
print("PASS: global centre/follow (after the triple-click window) from off, mouse, HUD, scrolling, VS Code and drag; holds preserved")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-recenter-'));
 try {writeFileSync(join(dir,'main.swift'),code);const build=spawnSync('swiftc',[wandSourcePath(new URL('../receiver/Sources/WandRunLoop.swift',import.meta.url)),'-O',new URL('../receiver/Sources/WandActionPause.swift',import.meta.url).pathname,new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
