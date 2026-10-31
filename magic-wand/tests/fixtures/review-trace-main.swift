import Foundation
import Darwin
let root=URL(fileURLWithPath:CommandLine.arguments[1],isDirectory:true)
let fm=FileManager.default,config=root.appendingPathComponent("review-trace.json"),directory=root.appendingPathComponent("traces")
var wall=1000.0
func configure(_ enabled:Bool) throws {
    try Data("{\"enabled\":\(enabled),\"captureUntil\":1600,\"deleteAfter\":8800}".utf8).write(to:config,options:.atomic)
    try fm.setAttributes([.posixPermissions:0o600],ofItemAtPath:config.path)
}
let trace=WandReviewTrace(directory:directory,configuration:config,build:"test",maximumBytes:1024,fileCount:3,wallClock:{wall})
trace.synchronize();precondition(!trace.enabled && !fm.fileExists(atPath:directory.path),"off by default, no disk capture")
try configure(true);trace.synchronize();precondition(trace.enabled)
let base=ProcessInfo.processInfo.systemUptime
for batch in 0..<12 {
    for i in 0..<100 {trace.record(.init(kind:"input",t:base+Double(batch*100+i)*0.03,dx:0.02,dy:0.03,eligible:true,step:0))}
    trace.synchronize()
}
let files=try fm.contentsOfDirectory(at:directory,includingPropertiesForKeys:nil)
precondition(files.count==3,"only the bounded rotation set survives")
for file in files {
    let attributes=try fm.attributesOfItem(atPath:file.path)
    precondition((attributes[.size] as! NSNumber).intValue<=1024,"strict byte cap")
    precondition((attributes[.posixPermissions] as! NSNumber).intValue==0o600,"private trace files")
    for line in try String(contentsOf:file,encoding:.utf8).split(separator:"\n") {
        _=try JSONSerialization.jsonObject(with:Data(line.utf8))
    }
}
for i in 0..<10000 {trace.record(.init(kind:"input",t:base+Double(i),step:0))}
precondition((trace.status["buffered"] as! Int)<=512,"bounded memory when writer falls behind")
trace.synchronize()
try configure(false);trace.synchronize();precondition(!trace.enabled)
trace.record(.init(kind:"input",t:base,step:999));trace.synchronize()
for f in try fm.contentsOfDirectory(at:directory,includingPropertiesForKeys:nil) {
    let lines=try String(contentsOf:f,encoding:.utf8).split(separator:"\n")
    for line in lines {
        let value=try JSONSerialization.jsonObject(with:Data(line.utf8)) as! [String:Any]
        precondition(value["step"] as? Int != 999,"disabled input is not captured")
    }
}
// A symlinked config cannot silently enable capture.
let link=root.appendingPathComponent("linked-config.json")
try fm.createSymbolicLink(at:link,withDestinationURL:config)
try configure(true)
let linked=WandReviewTrace(directory:root.appendingPathComponent("linked-traces"),configuration:link,build:"test",wallClock:{wall})
linked.synchronize();precondition(!linked.enabled)
// A failed writer must neither follow a symlink nor throw into input processing.
let bad=root.appendingPathComponent("bad")
try fm.createDirectory(at:bad,withIntermediateDirectories:false,attributes:[.posixPermissions:0o700])
let victim=root.appendingPathComponent("victim");try Data("unchanged".utf8).write(to:victim)
try fm.createSymbolicLink(at:bad.appendingPathComponent("trace.jsonl"),withDestinationURL:victim)
let failed=WandReviewTrace(directory:bad,configuration:config,build:"test",wallClock:{wall})
failed.synchronize();failed.record(.init(kind:"input",t:base,step:1));failed.synchronize()
let contents=try String(contentsOf:victim,encoding:.utf8)
precondition((failed.status["diskError"] as! Bool) && contents=="unchanged")
// Absolute persisted deadlines survive restarts and sleeping past cleanup.
wall=1601;trace.synchronize();precondition(!trace.enabled)
let late=WandReviewTrace(directory:root.appendingPathComponent("late"),configuration:config,build:"late",wallClock:{wall})
late.synchronize();precondition(!late.enabled && !fm.fileExists(atPath:root.appendingPathComponent("late").path))
let unrelated=directory.appendingPathComponent("keep-reference.txt");try Data("keep".utf8).write(to:unrelated)
wall=8801;trace.synchronize()
let remaining=try fm.contentsOfDirectory(atPath:directory.path)
precondition(remaining==["keep-reference.txt"],"only owned temporary traces expire")
late.synchronize();precondition(!late.enabled,"restart never renews an expired lease")
print("PASS private bounded trace rotation, live switch, symlinks and failed writer")
