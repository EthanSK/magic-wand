// Check that recentering and mode changes discard only obsolete pointer work.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
const dir=new URL('../receiver/Sources/',import.meta.url);
const src=readFileSync(new URL('main.swift',dir),'utf8');
function method(name,source=src){const a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
function run(code,files=[]){const d=mkdtempSync(join(tmpdir(),'wand-cancel-'));try{writeFileSync(join(d,'main.swift'),code);let b=spawnSync('swiftc',['-Onone',...files.map(x=>new URL(x,dir).pathname),join(d,'main.swift'),'-o',join(d,'test')],{encoding:'utf8'});assert.equal(b.status,0,b.stderr);b=spawnSync(join(d,'test'),[],{encoding:'utf8'});assert.equal(b.status,0,b.stdout+b.stderr);}finally{rmSync(d,{recursive:true,force:true});}}
// Exercise production cancellation against inert input. No native events are posted.
test('reset discards pending movement and click without replaying them after the centre',{skip:process.platform!=='darwin'},()=>{
 run(`import Foundation
struct E {let p:CGPoint;func post(tap:Int){Harness.events.append(p)}}
extension Int {static var cghidEventTap:Int {0}}
final class Virtual {var cancelled=0;func discardPendingPointerMotion(){cancelled+=1}}
final class Harness {
 static var events:[CGPoint]=[]
 static func mouseMovementEvent(buttons:Int,from:CGPoint,to:CGPoint)->E? {E(p:to)}
 var pointerMotionEpoch:UInt64=0,pointerMotionCutoff = -Double.infinity
 let motionFilter=WandMotionFilter()
 let dwell=WandDwellClick();var dwellTimer:Timer?;let senseVirtual:Virtual?=Virtual()
 ${method('invalidatePointerMotion')}
 ${method('settleRecenteredCursor')}
}
let h=Harness();h.dwell.follow(true)
h.motionFilter.path = .direct;h.motionFilter.holdAfterAutomaticClick()
precondition(h.motionFilter.restingAfterClick)
_=h.dwell.move(dx:20,dy:0,now:1,eligible:true)
h.dwellTimer=Timer(timeInterval:1,repeats:false){_ in fatalError("cancelled click fired")}
let timer=h.dwellTimer!,before=ProcessInfo.processInfo.systemUptime
h.invalidatePointerMotion()
precondition(h.pointerMotionEpoch==1 && h.pointerMotionCutoff>=before)
precondition(!h.motionFilter.restingAfterClick,"a new mode must not inherit the old click hold")
precondition(!timer.isValid && h.dwellTimer==nil && h.dwell.following)
precondition(!h.dwell.tick(now:100) && h.senseVirtual?.cancelled==1)
let centre=CGPoint(x:500,y:400);Harness.events.append(centre);h.settleRecenteredCursor(at:centre)
precondition(Harness.events==[centre,centre],"no stale point after the centre")
`,['WandPointerControl.swift']);
 const recenter=method('recenterPointer');assert(recenter.indexOf('invalidatePointerMotion()')<recenter.indexOf('CGWarpMouseCursorPosition'));
 const end=method('endScreenshot');assert(end.indexOf('transition(to:')<end.indexOf('invalidatePointerMotion()'),'finish the final drag before cancellation');
 assert(method('reset').includes('invalidatePointerMotion()'));
 assert(method('recordingChanged').includes('invalidatePointerMotion()'));
 assert(method('deviceFollowChanged').includes('if dwell.following != on {invalidatePointerMotion()}'),'repeated follow status does not reset a live gesture');
 const receive=method('receiveText');assert(receive.includes('pointerEpochAtEntry==pointerMotionEpoch {handleRaw'));
 assert(receive.includes('handle("0,0,"+button)'),'a button release in invalidated text still reaches the receiver');
});
test('virtual program keeps buttons, dictation and new movement when old movement is invalidated',{skip:process.platform!=='darwin'},()=>{
 run(`import Foundation
let host="var WandSenseHost={create:function(g,n){return {repl:function(s){n.text(s);},teardown:function(){}}}};"
let sources=WandVirtualPuck.Sources(shim:"",host:host,base:"",bridge:"",power:"")
let v=WandVirtualPuck(sources:sources)!
var output="";v.onText={output += $0}
v.send("@RAW 9615,500,0,0")
v.send("@BOTTOM 0")
v.send("@WAND 20,10,0")
v.send("@STT 1")
v.send("@MIDDLE 0")
v.discardPendingPointerMotion()
v.send("@RAW 9615,7,0,0")
RunLoop.main.run(until:Date().addingTimeInterval(0.03))
precondition(output=="@BOTTOM 0\\n@WAND 0,0,0\\n@STT 1\\n@MIDDLE 0\\n@RAW 9615,7,0,0\\n",output)
v.teardown()
`,['WandVirtualPuck.swift']);
});
test('late sensor movement cannot cross a pointer reset, but a fresh sample can',{skip:process.platform!=='darwin'},()=>{
 const s=readFileSync(new URL('WandReceiverSense.swift',dir),'utf8');const a=s.indexOf('            func motion(at reading: Double)');assert(a>=0);let b=s.indexOf('{',a)+1,n=1;while(n){if(s[b]==='{')n++;if(s[b]==='}')n--;b++;}
 const protocol=readFileSync(new URL('WandSenseProtocol.swift',dir),'utf8');let c=protocol.indexOf('enum WandSenseStaleness {'),d=protocol.indexOf('{',c)+1,depth=1;while(depth){if(protocol[d]==='{')depth++;if(protocol[d]==='}')depth--;d++;}
 run(`import Foundation
${protocol.slice(c,d)}
let pointerMotionCutoff=10.0,dropLate=false,gyro:[Int]?=[1,2,3],arrival=11.0
var senseStaleReadings=0
${s.slice(a,b)}
precondition(motion(at:9.99)==nil && motion(at:10)==nil)
precondition(motion(at:10.01)==gyro)
`);
});
