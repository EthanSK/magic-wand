// Inert experiment configuration and native checkbox-action checks; no window or live input.
import Cocoa
let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
defer { try? FileManager.default.removeItem(at: folder) }
let url=folder.appendingPathComponent("experiment.json")
func config(_ rate:Int) throws {
 try JSONSerialization.data(withJSONObject:["version":1,"visible":false,"label":"Refresh rate","sensorHz":rate]).write(to:url,options:.atomic)
}
let experiment=WandExperiment(url:url)
var sent:[String]=[]
func tick(_ t:Double,_ allowed:Bool=true) { experiment.tick(now:t,maySend:allowed,send:{sent.append($0)}) }
try config(6660)
experiment.connection(hz:104,supportsRateControl:false,now:0)
tick(1);precondition(sent.isEmpty,"legacy firmware never receives a new command")
experiment.connection(hz:104,supportsRateControl:true,now:1)
tick(2,false);precondition(sent.isEmpty,"firmware updates gate rate control")
tick(3);precondition(sent==["R6660"])
precondition(experiment.status["sensorHz"] as? Int==104,"requested rate is not readback")
experiment.reply("rate hz=6660 mode=2 ok=1")
tick(4);precondition(sent.count==1 && experiment.status["sensorHz"] as? Int==6660)
experiment.received(readings:3);experiment.received(readings:2);experiment.postedPointerEvent()
tick(5)
precondition(experiment.status["readingsPerSecond"] as? Double==5)
precondition(experiment.status["reportsPerSecond"] as? Double==2)
precondition(experiment.status["pointerEventsPerSecond"] as? Double==1)
try config(104);tick(6);precondition(sent.last=="R104","revert uses the same verified command")
experiment.reply("rate hz=6660 mode=2 ok=0");tick(20)
precondition(sent.count==2 && experiment.status["rejected"] as? Bool==true)
experiment.disconnected(now:21);tick(22);precondition(sent.count==2)
experiment.connection(hz:104,supportsRateControl:true,now:23);tick(24)
precondition(sent.count==2,"baseline reconnect needs no rate command")
try config(833);tick(25);tick(26);tick(27);tick(29);tick(31)
precondition(sent.suffix(3)==["R833","R833","R833"] && sent.count==5,"missing ACKs have bounded retries")
precondition(WandExperimentConfiguration.parse(Data(#"{"version":true,"visible":false,"label":"x"}"#.utf8))==nil)
precondition(WandExperimentConfiguration.parse(Data(#"{"version":1,"visible":1,"label":"x"}"#.utf8))==nil)
print("PASS: reversible rate control, readback, bounded retry and independent counters; no window or input")

// Click-mode requests preserve the already settled416Hz setting. The panel and
// status distinguish the requested mode from the native mode applied at idle.
var changed=0;experiment.onChange={changed+=1}
try JSONSerialization.data(withJSONObject:["version":1,"visible":false,"label":"Tap to click","sensorHz":416,"manualClick":true]).write(to:url,options:.atomic)
experiment.connection(hz:416,supportsRateControl:true,now:32);let sentBefore=sent.count;tick(33)
precondition(experiment.manualClick && changed==1 && sent.count==sentBefore,"click experiment never changes416Hz")
precondition(experiment.status["manualClickDesired"] as? Bool==true && experiment.status["manualClickApplied"] as? Bool==false,"requested mode stays pending until native input is idle")
experiment.setManualClickSupport(true,reason:"Use Control V2 or V3 for Tap to click")
experiment.setAppliedManualClick(true)
precondition(experiment.status["manualClick"] as? Bool==true,"active status reflects actual native mode")
try JSONSerialization.data(withJSONObject:["version":1,"visible":false,"label":"Tap to click","sensorHz":416,"manualClick":false]).write(to:url,options:.atomic);tick(34)
precondition(!experiment.manualClick && changed==2 && sent.count==sentBefore)
precondition(WandExperimentConfiguration.parse(Data(#"{"version":1,"visible":false,"label":"x","manualClick":1}"#.utf8))==nil)
print("PASS: manual click desired/applied state is reversible and preserves416Hz")

// Send the real Cocoa checkbox action to the real production target. Keeping the
// private configuration invisible makes this a window-free test, never a click
// on Ethan's live panel or a change to his settings.
let application=NSApplication.shared;_=application.setActivationPolicy(.prohibited)
let checkbox=NSButton(checkboxWithTitle:"Enable experiment",target:experiment,action:NSSelectorFromString("toggleManualClick:"))
checkbox.state = .off;checkbox.performClick(nil)
precondition(experiment.manualClick && changed==3,"the actual checkbox action enables the requested experiment")
var stored=try JSONSerialization.jsonObject(with:Data(contentsOf:url)) as? [String:Any]
precondition(stored?["manualClick"] as? Bool==true && stored?["sensorHz"] as? Int==416,"checkbox persists only click mode and preserves416Hz")
checkbox.performClick(nil)
precondition(!experiment.manualClick && changed==4,"the actual checkbox action disables the request")
stored=try JSONSerialization.jsonObject(with:Data(contentsOf:url)) as? [String:Any]
precondition(stored?["manualClick"] as? Bool==false && stored?["sensorHz"] as? Int==416)
print("PASS: actual native checkbox action persists reversible mode without window or input")
