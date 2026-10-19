import Foundation

// Offline only: no receiver, Bluetooth, pointer events or Better Git transport.
struct TraceFrame: Decodable {
    let schema: Int
    let kind: String
    let t: Double
    let reason: String?
    let run: String?
    let build: String?
    let dx: Double?
    let dy: Double?
    let eligible: Bool?
    let axisGestures: Bool?
    let step: Int?
    let dropped: UInt64?
}
var detector=WandReviewNavigation(),inputs=0,recordedNext=0,recordedPrevious=0,replayedNext=0,replayedPrevious=0
var malformed=0,gaps=0,partialPrefix=true,lastRun:String?,builds=Set<String>(),differences:[[String:Any]]=[]
var first=true,verifiedBoundary=false
for path in CommandLine.arguments.dropFirst() {
    let data=try Data(contentsOf:URL(fileURLWithPath:path))
    for line in data.split(separator:0x0a) {
        guard let frame=try? JSONDecoder().decode(TraceFrame.self,from:Data(line)),
              frame.schema==1,frame.t.isFinite,frame.t>=0 else{malformed+=1;continue}
        if first {partialPrefix = frame.kind != "capture";first=false}
        switch frame.kind {
        case "capture":
            if let run=frame.run,run != lastRun {detector=WandReviewNavigation();lastRun=run}
            if let build=frame.build {builds.insert(build)}
        case "gap":
            gaps+=Int(frame.dropped ?? 1);detector.reset();verifiedBoundary=false
        case "boundary":
            if frame.reason != "legacy review ignored" {
                if let axes=frame.axisGestures {detector.useAxisGestures=axes}
                detector.reset();verifiedBoundary=true
            }
        case "input":
            guard let dx=frame.dx,let dy=frame.dy,dx.isFinite,dy.isFinite,let eligible=frame.eligible,
                  let expected=frame.step,(-12...12).contains(expected) else {
                malformed+=1;continue
            }
            if let axes=frame.axisGestures,axes != detector.useAxisGestures {detector.useAxisGestures=axes;detector.reset()}
            let actual:Int32
            if eligible {actual=detector.sample(dx:dx,dy:dy,now:frame.t)} else {detector.reset();actual=0}
            inputs+=1
            recordedNext+=max(0,expected);recordedPrevious+=max(0,-expected)
            replayedNext+=max(0,Int(actual));replayedPrevious+=max(0,-Int(actual))
            if Int(actual) != expected && differences.count<200 {
                differences.append(["input":inputs,"t":frame.t,"recorded":expected,"replayed":Int(actual),"afterBoundary":verifiedBoundary])
            }
        default:break
        }
    }
}
let report:[String:Any]=["inputPoints":inputs,"recordedNext":recordedNext,"recordedPrevious":recordedPrevious,
    "replayedNext":replayedNext,"replayedPrevious":replayedPrevious,"differences":differences,
    "malformedRecords":malformed,"captureDrops":gaps,"partialPrefix":partialPrefix,"receiverBuilds":builds.sorted(),
    "warning":"Replay uses the current canonical classifier. A rotated prefix, live capture enable, learned noise state or source change can cause differences; these alone do not prove a detector bug."]
let result=try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys])
print(String(data:result,encoding:.utf8)!)
