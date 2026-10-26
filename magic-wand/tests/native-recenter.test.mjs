import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

test('Bottom double tap always centres and enables follow across prior modes', {skip:process.platform!=='darwin'},()=>{
 const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
 function method(name){const start=source.indexOf('    func '+name+'(');assert(start>=0,name);let end=source.indexOf('{',start)+1,depth=1;while(depth){if(source[end]==='{')depth++;if(source[end]==='}')depth--;end++;}return source.slice(start,end);}
 const body=source.slice(source.indexOf('if let marker=line.range(of:"@BOTTOM ")'),source.indexOf('if let marker=line.range(of:"@MIDDLE ")'));
 assert(body.indexOf('recognizeBottomRecenter')<body.indexOf('if controlVersion'));
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
 let pointerRouter=WandPointerRouter(),recenterGesture=WandRecenterGesture(),dwell=WandDwellClick(),motionFilter=WandMotionFilter(),restDetection=Rest()
 let screenshot=WandScreenshotGesture();var pendingRecenter:Timer?
 var ready=true,restoring=false,recenterSuppressButtons=false,deliveryPoint:CGPoint?,commands:[String]=[]
 var hud=false,scroll=false,buttons=0,appMode:String?
 func queue(_ text:String){commands.append(text)}
 func closeHUD(reason:String){hud=false;appMode=nil}
 func cancelCircleScroll(){_ = pointerRouter.interrupt()}
 func finishScroll(){scroll=false}
 func releaseButtons(){buttons=0}
 func performPointer(_ actions:[WandPointerRouter.Action]){}
 func scheduleDwell(){}
 ${['recognizeBottomRecenter','recenterPointer'].map(method).join('\n')}
}
for mode in ["off","mouse","hud","scroll","vsCode","drag"] {
 let h=Harness();h.hud=mode=="hud";h.scroll=mode=="scroll";h.appMode=mode=="vsCode" ? "vsCode":nil;h.buttons=mode=="drag" ? 1:0
 h.dwell.follow(mode=="mouse");_=h.pointerRouter.bottom(down:true)
 precondition(!h.recognizeBottomRecenter(down:true,now:1))
 precondition(!h.recognizeBottomRecenter(down:false,now:1.08))
 // Mode teardown caused by the first tap must not erase the global gesture.
 h.cancelCircleScroll()
 precondition(!h.recognizeBottomRecenter(down:true,now:1.18))
 warped = .zero
 precondition(h.recognizeBottomRecenter(down:false,now:1.26),mode)
 // Ethan's triple-click shares these clicks: centre once its window passes.
 precondition(warped == .zero && h.pendingRecenter != nil && h.dwell.following == (mode=="mouse"),"no centre before the third-press window "+mode)
 RunLoop.main.run(until:Date().addingTimeInterval(WandTripleClick.window+0.03))
 precondition(h.pendingRecenter==nil && warped==CGPoint(x:700,y:200) && h.deliveryPoint==warped,mode)
 precondition(h.dwell.following && !h.pointerRouter.bottomHeld && h.buttons==0,mode)
 precondition(h.hud==(mode=="hud") && !h.scroll && h.appMode==(mode=="vsCode" ? "vsCode":nil) && h.restDetection.activated,mode)
 precondition(h.recenterSuppressButtons && h.commands.last!.contains("setMouseFollow(true)"))
}
let hold=Harness();_=hold.recognizeBottomRecenter(down:true,now:2);_=hold.recognizeBottomRecenter(down:false,now:2.08);_=hold.recognizeBottomRecenter(down:true,now:2.18)
precondition(!hold.recognizeBottomRecenter(down:false,now:2.6),"long second press remains a hold")
precondition(hold.pendingRecenter==nil)
let busy=Harness();_=busy.screenshot.requestShortcut(now:3);warped = .zero;busy.recenterPointer()
precondition(warped == .zero,"screenshot mode is never recentred")
print("PASS: global centre/follow (after the triple-click window) from off, mouse, HUD, scrolling, VS Code and drag; holds preserved")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-recenter-'));
 try {writeFileSync(join(dir,'main.swift'),code);const build=spawnSync('swiftc',['-O',new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
