import Foundation

// Ethan's Review/Stage double-click keeps one set: the live Better Git
// transaction switches mode in place; with none, begin then mode, no step.
var failures=0
func check(_ ok:Bool,_ message:String,line:Int=#line) {
    if !ok {failures+=1;print("FAIL \(line): \(message)")}
}

do {
    let review=WandReviewGesture()
    review.beginDetents(mode:"changes",now:0)
    let begun=review.detents(2,now:0.1)
    check(begun.map{$0.phase}==["begin","step","step"],"ratchets begin the set")
    let id=begun.first?.id ?? ""
    let switched=review.changeMode("files",now:0.2)
    check(switched.map{$0.phase}==["mode"],"an existing set only changes mode")
    check(switched.first?.id==id && switched.first?.seq==4,"same transaction, next sequence")
    check(switched.first?.mode=="files" && review.mode=="files","new mode")
    check(review.changeMode("files",now:0.3).isEmpty,"repeated same mode sends nothing")
    let step=review.detents(1,now:0.4)
    check(step.map{$0.phase}==["step"] && step.first?.id==id && step.first?.seq==5 && step.first?.mode=="files","later ratchets stay in the new mode")
    let pulse=review.tick(now:1.2)
    check(pulse.map{$0.phase}==["heartbeat"] && pulse.first?.id==id && pulse.first?.mode=="files","heartbeat keeps the session")
    let back=review.changeMode("changes",now:1.3)
    check(back.map{$0.phase}==["mode"] && back.first?.id==id && back.first?.seq==7 && back.first?.mode=="changes","toggling back")
    let done=review.endDetents(commit:true)
    check(done.map{$0.phase}==["finish"] && done.first?.id==id && done.first?.mode=="changes","hold commit finishes once")
    check(review.endDetents(commit:true).isEmpty,"no second finish")
}
do {
    let review=WandReviewGesture()
    review.beginDetents(mode:"changes",now:0)
    let switched=review.changeMode("files",now:0.1)
    check(switched.map{$0.phase}==["begin","mode"],"no set yet: begin then mode, no step")
    check(Set(switched.map{$0.id}).count==1 && switched.map{$0.seq}==[1,2],"one ordered transaction")
    check(switched.map{$0.mode}==["changes","files"],"begin in the old mode, then switch")
    check(review.changeMode("files",now:0.2).isEmpty,"repeat sends nothing")
    let lost=review.tick(now:1.1)
    check(lost.map{$0.phase}==["cancel"] && lost.first?.mode=="files","safety teardown still cancels")
}
do {
    let review=WandReviewGesture()
    review.beginDetents(mode:"files",now:0)
    check(review.changeMode("eyes",now:0.1).isEmpty && review.mode=="files","invalid target ignored")
    let idle=WandReviewGesture()
    check(idle.changeMode("files",now:0).isEmpty && idle.mode=="files","no live session sends nothing")
}
if failures>0 {exit(1)}
print("review mode ok")
