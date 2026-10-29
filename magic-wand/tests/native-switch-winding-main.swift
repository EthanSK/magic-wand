import Foundation
setbuf(stdout, nil)
// Switch App winding and ordered HUD delivery. Pure: no sockets, input or hardware.
let perApp = WandSwitchAppWinding.countsPerApp
func circle(_ w: WandSwitchAppWinding, turns: Double, clockwise: Bool, radius: Double = 900, start: Double = 0, t0: Double = 0) -> (sum: Double, t: Double) {
    var sum = 0.0, t = t0, last = (x: radius, y: 0.0)
    let steps = Int(turns * 104)                      // one turn per second at 104 Hz
    for i in 1...steps {
        let a = Double(i) / 104 * 2 * Double.pi * (clockwise ? 1 : -1)
        let p = (x: radius * cos(a), y: radius * sin(a) * 1.4)
        t += 1.0 / 104
        sum += w.update(dx: p.x - last.x, dy: p.y - last.y, now: t)
        last = p
    }
    return (sum, t)
}
// 1. Straight left/right passes through unchanged (the native detents step apps).
let straight = WandSwitchAppWinding()
var passed = 0.0
for i in 1...52 { passed += straight.update(dx: 30, dy: 0, now: Double(i) / 104) }
precondition(abs(passed - 52 * 30) < 1e-9 && !straight.winding, "straight travel is ordinary mouseX: \(passed)")
// 2. Rightward choice, then winding either way continues right.
for clockwise in [true, false] {
    let w = WandSwitchAppWinding()
    var t = 0.0, total = 0.0
    for _ in 0..<20 { t += 1.0 / 104; total += w.update(dx: 40, dy: 0, now: t) }   // ~1.3 apps right
    let first = circle(w, turns: 3, clockwise: clockwise, t0: t)
    precondition(w.winding, "a deliberate circle is recognised")
    precondition(first.sum > 6 * perApp, "three turns keep going right (\(clockwise ? "clockwise" : "anticlockwise")): \(first.sum / perApp) apps")
}
// 3. Leftward choice continues left whichever way the circle winds.
let left = WandSwitchAppWinding()
var lt = 0.0
for _ in 0..<20 { lt += 1.0 / 104; _ = left.update(dx: -40, dy: 0, now: lt) }
precondition(circle(left, turns: 3, clockwise: true, t0: lt).sum < -6 * perApp, "left stays left")
// 4. A long straight stroke after winding returns to ordinary left/right.
let back = WandSwitchAppWinding()
var bt = 0.0
for _ in 0..<20 { bt += 1.0 / 104; _ = back.update(dx: 40, dy: 0, now: bt) }
bt = circle(back, turns: 2, clockwise: true, t0: bt).t
var out = 0.0
for _ in 0..<120 { bt += 1.0 / 104; out += back.update(dx: -40, dy: 0, now: bt) }
precondition(!back.winding && out < 0, "straight leftward motion steps left again: \(out)")
// 5. Tremor never latches.
let still = WandSwitchAppWinding()
for i in 1...520 { _ = still.update(dx: 3 * sin(Double(i)), dy: 2 * cos(Double(i) * 1.7), now: Double(i) / 104) }
precondition(!still.winding, "hand tremor is not a circle")
print("PASS: straight travel passes through; a circle continues the chosen direction either way; straight resumes; tremor ignored")

// Ordered delivery of state-changing HUD packets.
let transport = WandControlTransport(agenticPath: "/nonexistent/agentic.sock", speechPath: "/nonexistent/speech.sock")
var refuse = 3, sent: [String] = []
transport.deliver = { packet, _, _ in
    if refuse > 0 { refuse -= 1; return false }
    sent.append(packet["phase"] as? String ?? "?"); return true
}
transport.retryDelay = 0.001
transport.persistent("park")
transport.persistent("motion", x: 1)          // never queued behind a refused terminal
transport.persistent("choose")
let until = Date().addingTimeInterval(1)
while transport.pendingPackets > 0 && Date() < until { RunLoop.main.run(until: Date().addingTimeInterval(0.005)) }
precondition(sent == ["park", "choose"], "terminals arrive once, in order: \(sent)")
precondition(transport.droppedPackets == 0)
transport.persistent("motion", x: 2)
precondition(sent.last == "motion", "motion is sent directly when nothing is pending")
refuse = Int.max
transport.persistent("activate")
let giveUp = Date().addingTimeInterval(2)
while transport.pendingPackets > 0 && Date() < giveUp { RunLoop.main.run(until: Date().addingTimeInterval(0.01)) }
precondition(transport.pendingPackets == 0 && transport.droppedPackets == 1, "a refused packet is abandoned after one second, never later")
print("PASS: refused HUD terminals resend in order for at most one second; motion is never queued")

// Every part of the initial circle preserves the chosen direction, not just its net total.
for radius in [900.0,1500.0] {for clockwise in [true,false] {
 let w=WandSwitchAppWinding();var t=100.0,last=(x:radius,y:0.0)
 for _ in 0..<20 {t+=1.0/104;_=w.update(dx:40,dy:0,now:t)}
 for i in 1...104 {let a=Double(i)/104*2*Double.pi*(clockwise ? 1:-1),p=(x:radius*cos(a),y:radius*sin(a)*1.4);t+=1.0/104
 let output=w.update(dx:p.x-last.x,dy:p.y-last.y,now:t);precondition(output>=0,"circle acquisition cannot reverse the chosen direction");last=p}
}}
let paused=WandControlTransport(agenticPath:"/nonexistent",speechPath:"/nonexistent")
var permit=false,pausedSent:[String]=[]
paused.deliver={p,_,_ in if !permit{return false};pausedSent.append(p["phase"] as? String ?? "?");return true};paused.retryDelay=0.001
paused.persistent("choose");paused.suspended=true;permit=true
RunLoop.main.run(until:Date().addingTimeInterval(0.02))
precondition(pausedSent.isEmpty && paused.pendingPackets==0,"Pause cancels refused actions")
let expired=WandControlTransport(agenticPath:"/nonexistent",speechPath:"/nonexistent")
var clock=0.0,expiredSent:[String]=[],canDeliver=false
expired.monotonicNow={clock};expired.deliver={p,_,_ in if !canDeliver{return false};expiredSent.append(p["phase"] as? String ?? "?");return true};expired.retryDelay=0.001
expired.persistent("activate");clock=2;canDeliver=true
RunLoop.main.run(until:Date().addingTimeInterval(0.02))
precondition(expiredSent.isEmpty && expired.pendingPackets==0,"a delayed retry checks age before sending")
print("PASS: circle entry never reverses, Pause cancels queued actions, and expired actions never send")

let cancelled=WandControlTransport(agenticPath:"/nonexistent",speechPath:"/nonexistent")
var canSend=false,cancelledSent:[String]=[]
cancelled.deliver={p,_,_ in if !canSend{return false};cancelledSent.append(p["phase"] as? String ?? "?");return true};cancelled.retryDelay=0.001
cancelled.persistent("choose");cancelled.cancel();canSend=true
RunLoop.main.run(until:Date().addingTimeInterval(0.02))
precondition(cancelledSent == ["dismiss"],"session teardown drops old selection and keeps only dismissal")
