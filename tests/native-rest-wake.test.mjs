import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

// Ethan: waking from rest must "return to the state it was on before
// sleeping", never enter mouse mode on its own. The real receiver IMU and
// recording methods run with a scripted rest detector and inert transports.
const source=readFileSync(new URL('../receiver/Sources/main.swift',import.meta.url),'utf8');
const pointer=readFileSync(new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url),'utf8');
const ready=pointer.includes('struct WandRestFollowMemory')&&source.includes('restFollow.pickedUp(');

test('pickup restores the pre-rest mouse state; manual choices and recording win',{skip:process.platform!=='darwin'||!ready},()=>{
 function method(name){const a=source.indexOf('    func '+name+'(');assert(a>=0,name);let b=source.indexOf('{',a)+1,depth=1;while(depth){if(source[b]==='{')depth++;if(source[b]==='}')depth--;b++;}return source.slice(a,b);}
 const code=`import Foundation
func log(_ values:Any...){}
struct Filter {var configured=true;func observeGravity(x:Double,y:Double,z:Double){};func reset(){}}
final class Rest {
 var parked=false;var deskQuietSince:Double?;var hasReference=true
 enum Event{case probe,pickedUp,settling,putDown}
 var script:[(parked:Bool,events:[Event])]=[]
 func update(x:Double,y:Double,z:Double,gyro:Double,now:Double,buttons:Bool,idle:Bool)->[Event]{
  guard !script.isEmpty else{return []}
  let next=script.removeFirst();parked=next.parked;return next.events
 }
 func pointerActivated(){parked=false};func pointerStopped(){}
}
final class Controls {var speechEvents=0}
final class Recording {var isRecording=false}
final class Harness {
 var ready=true,restoring=false,scrollActive=false,buttons=0,restDiagnosticsRemaining=0,hudSession=false
 var recordingPointerPaused=false,recordingRestoreFollow:Bool?
 var restFollow=WandRestFollowMemory()
 var motionFilter=Filter();let dwell=WandDwellClick(),restDetection=Rest(),controls=Controls(),recording=Recording()
 var deskSleep=WandDeskSleep()
 var pointerRouter=WandPointerRouter(),deliveryPoint:CGPoint?
 var probeTimer:Timer?,queued:[String]=[],entered=0
 func reconcileBottomHold(down:Bool,now:Double,reason:String){};func scheduleDwell(){};func cancelCircleScroll(){};func releaseButtons(){}
 func performPointer(_ actions:[WandPointerRouter.Action]){};func syncRecordingLight(){};func status(){}
 func enterPointerMode(){entered+=1};func queue(_ text:String){queued.append(text)}
 var mouseOnRequests:Int {queued.filter{ $0.contains("setMouseFollow(true)") }.count}
 /// What the device does for a deliberate Bottom choice: the receiver
 /// marks it manual, then the device's own follow report arrives.
 func bottomChoice(follow:Bool){manualPointerDuringRecording();dwell.follow(follow)}
 func rest(putDown:Bool){restDetection.script=[(true,putDown ? [.putDown]:[])];handleIMU("0,0,8192,0,0,0,0")}
 func pickup(){restDetection.script=[(false,[.pickedUp])];handleIMU("0,0,8192,0,0,0,0")}
 ${['handleIMU','recordingChanged','manualPointerDuringRecording'].map(method).join('\n')}
}

// Pure memory contract.
var memory=WandRestFollowMemory()
memory.cameToRest(following:true);precondition(memory.pickedUp(recordingPaused:false))
precondition(!memory.pickedUp(recordingPaused:false),"a pickup restores once, then forgets")
memory.cameToRest(following:true);precondition(!memory.pickedUp(recordingPaused:true),"recording keeps pointing off")
memory.cameToRest(following:true);memory.manualChoice();precondition(!memory.pickedUp(recordingPaused:false))
memory.cameToRest(following:false);precondition(!memory.pickedUp(recordingPaused:false))
memory.cameToRest(following:true);memory.reset();precondition(memory.remembered==nil)

// Rest after OFF stays OFF: dangling still in the hand, then moving again.
let off=Harness();off.dwell.follow(false)
off.rest(putDown:false);off.pickup()
precondition(!off.dwell.following && off.mouseOnRequests==0 && off.entered==0,"waking never enters mouse mode by itself")

// Rest after ON restores ON: the existing put-down turns it off on the table.
let on=Harness();on.dwell.follow(true)
on.rest(putDown:true)
precondition(!on.dwell.following,"table rest still parks the pointer")
on.pickup()
precondition(on.dwell.following && on.mouseOnRequests==1,"pickup returns to mouse mode it had before rest")

// A manual choice while resting wins over the remembered state.
let manualOff=Harness();manualOff.dwell.follow(true);manualOff.rest(putDown:true)
manualOff.bottomChoice(follow:false);manualOff.pickup()
precondition(!manualOff.dwell.following && manualOff.mouseOnRequests==0,"a deliberate switch off survives pickup")
let manualOn=Harness();manualOn.dwell.follow(false);manualOn.rest(putDown:false)
manualOn.bottomChoice(follow:true);manualOn.pickup()
precondition(manualOn.dwell.following && manualOn.mouseOnRequests==0,"a deliberate switch on needs no automatic help")

// Recording during rest wins: pickup while recording keeps pointing off,
// and recording's own end restores the pre-rest choice.
let speech=Harness();speech.dwell.follow(true);speech.rest(putDown:true)
speech.recording.isRecording=true;speech.recordingChanged(true)
speech.pickup()
precondition(!speech.dwell.following && speech.mouseOnRequests==0,"pickup cannot undo the recording pause")
speech.recording.isRecording=false;speech.recordingChanged(false)
precondition(speech.dwell.following && speech.mouseOnRequests==1,"recording end resumes the choice rest was hiding")

// Recording that ends while the wand still rests waits for pickup.
let desk=Harness();desk.dwell.follow(true);desk.rest(putDown:true)
desk.recording.isRecording=true;desk.recordingChanged(true)
desk.recording.isRecording=false;desk.recordingChanged(false)
precondition(!desk.dwell.following && desk.mouseOnRequests==0,"never turn mouse mode on while it lies on the desk")
desk.pickup()
precondition(desk.dwell.following && desk.mouseOnRequests==1,"pickup then restores it once")

// Rest during an active recording: the recording pause still owns pointing.
let during=Harness();during.dwell.follow(true)
during.recording.isRecording=true;during.recordingChanged(true)
during.rest(putDown:false);during.pickup()
precondition(!during.dwell.following && during.mouseOnRequests==0)
during.recording.isRecording=false;during.recordingChanged(false)
precondition(during.dwell.following && during.mouseOnRequests==1,"Codex's one-time recording pause still resumes once")

// A manual choice during recording and rest wins over both.
let both=Harness();both.dwell.follow(true);both.rest(putDown:true)
both.recording.isRecording=true;both.recordingChanged(true)
both.bottomChoice(follow:false)
both.pickup();both.recording.isRecording=false;both.recordingChanged(false)
precondition(!both.dwell.following && both.mouseOnRequests==0,"the manual choice beats rest and recording")

// An open HUD at pickup keeps its own state and forgets the rest memory.
let hud=Harness();hud.dwell.follow(true);hud.rest(putDown:false);hud.hudSession=true;hud.pickup()
precondition(hud.mouseOnRequests==0 && hud.restFollow.remembered==nil)
print("PASS: wake restores pre-rest state; manual and recording win")
`;
 const dir=mkdtempSync(join(tmpdir(),'wand-wake-'));
 try {writeFileSync(join(dir,'main.swift'),code);const build=spawnSync('swiftc',['-Onone',new URL('../receiver/Sources/WandPointerControl.swift',import.meta.url).pathname,join(dir,'main.swift'),'-o',join(dir,'check')],{encoding:'utf8'});assert.equal(build.status,0,build.stderr);const run=spawnSync(join(dir,'check'),[],{encoding:'utf8'});assert.equal(run.status,0,run.stdout+run.stderr);}finally{rmSync(dir,{recursive:true,force:true});}
});
