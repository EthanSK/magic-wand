import Foundation
setbuf(stdout, nil)
// Inert click-lane regressions (receiver195): the real WandMotionFilter
// and WandDwellClick in handleRaw's call order (intent, move with the stillness
// gate's rest flag, timer tick, post-click hold). No native input or hardware.
// Ethan (2026-11-01): "it should detect clicks pretty fast always ... at least
// the first click of the batch and then like if I haven't moved at all, then it
// should repeat the click ... If I move a tiny bit to try and point at something
// else nearby, then it should send the click faster as well."
// Later the same day he slowed only the stationary repeat: "every like one
// second or so ... if it hasn't moved ... It should be quite a long delay".
let config=[0,0,86.4*1.1725,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,1]
let hz=Double(CommandLine.arguments.dropFirst().first ?? "104")!
let dt=1/hz
struct Click {let t:Double;let fast:Bool;let settled:Bool;let repeated:Bool}
final class Hand {
 let f=WandMotionFilter();let d:WandDwellClick
 var now=10.0,n=0,clicks:[Click]=[],lastVisible = -Double.infinity
 init(repeats:Bool=true){d=WandDwellClick(repeatInterval:repeats ? WandDwellClick.senseRepeatInterval:nil,fastStops:true);precondition(f.configure(config));f.path = .direct;d.follow(true)}
 /// Pointer-axis rates in filter units/s; `wobble` adds the balanced 4 Hz
 /// ellipse used by the stationary-noise regression ("trying to hold it still").
 func run(_ seconds:Double,_ rate:(Double)->(Double,Double)={_ in (0,0)},wobble:Bool=false,eligible:Bool=true){
  let start=now
  for _ in 0..<Int((seconds*hz).rounded()) {
   var (x,y)=rate(now-start)
   if wobble {let a=Double(n)*2*Double.pi*4/hz;x+=0.6*sin(a);y+=0.5*cos(a)}
   let s=f.sample(rawX:Int((x*134).rounded()),rawY:Int((y*134).rounded()),microseconds:Int((dt*1_000_000).rounded()),held:false,resetState:false)!
   if s.x != 0 || s.y != 0 {lastVisible=now}
   d.intent(s.intent && !s.resting,now:now) // receiver main.swift
   d.move(dx:s.stopX,dy:s.stopY,now:now,eligible:eligible,pointerX:s.x,pointerY:s.y,sampleSeconds:dt,pointerQuiet:s.quietForClick,fineMove:s.fineMoving,resting:s.resting)
   tick(until:now+dt)
   now+=dt;n+=1
  }
 }
 /// The receiver's one-shot timer: due work fires before the next reading.
 func tick(until limit:Double){
  while let due=d.nextDue,due<limit {
   let at=max(due,now)
   guard d.tick(now:at) else{break}
   clicks.append(Click(t:at,fast:d.lastClickWasFast,settled:d.lastClickWasSettled,repeated:d.lastClickWasRepeat));f.holdAfterAutomaticClick()
  }
 }
}

// 1. A real move that slows toward the end, then a held hand. The brisk-stop
// path cannot apply (its last brisk reading is >120 ms before the stop).
// Ethan's recovered correction restores the ordinary 200 ms precision pause.
let slowed=Hand()
slowed.run(0.3,wobble:true)
slowed.run(0.15){_ in (30,0)}
slowed.run(1.0){t in (30*max(0,1-t),0)} // decelerates to a stop over one second
let stop1=slowed.lastVisible
slowed.run(0.25,wobble:true)
let first=slowed.clicks.first
print("slowed approach: first click",first.map{($0.t-stop1,$0.fast,$0.settled)} as Any)
precondition(first != nil && !first!.fast && first!.t-stop1>=0.2-1e-8 && first!.t-stop1<0.45,"slowed stop keeps the precision pause: \(String(describing:first.map{($0.t-stop1,$0.fast,$0.settled)}))")
precondition(slowed.clicks.count==1,"one click for one stop: \(slowed.clicks.map{$0.t-stop1})")

// 2. Remaining still: about one stop-click per second (Ethan's later spacing),
// timed from the actual click; never earlier, and a fresh reading each time.
let spacing=WandDwellClick.senseRepeatInterval
slowed.run(2.2,wobble:true)
let chain=slowed.clicks
print("still after the click",chain.map{($0.t-chain[0].t,$0.repeated)})
precondition(chain.count>=3 && chain.dropFirst().allSatisfy{$0.repeated},"repeats while still: \(chain.map{$0.t-chain[0].t})")
for (a,b) in zip(chain,chain.dropFirst()) {precondition(b.t-a.t>=spacing-0.001 && b.t-a.t<=spacing+0.02,"one-second repeat spacing: \(b.t-a.t)")}

// 3. A tiny move to a nearby target re-arms and clicks promptly as well, well
// before the next stationary repeat. Start it 0.2 s after a repeat, so that
// repeat deadline is still 0.8 s away and cannot be what clicks.
let lead=slowed.clicks.last!.t+0.2-slowed.now
slowed.run(lead>=0 ? lead:lead+spacing,wobble:true)
precondition(slowed.clicks.last!.repeated && slowed.now-slowed.clicks.last!.t<=0.25,"the re-target starts just after a repeat")
let pendingRepeat=slowed.clicks.last!.t+spacing
let before=slowed.clicks.count
slowed.run(0.2){_ in (0.7,0)}
let stop2=slowed.lastVisible
slowed.run(0.25,wobble:true)
let retarget=slowed.clicks.dropFirst(before).first
print("tiny nearby target",retarget.map{($0.t-stop2,$0.settled,$0.repeated)} as Any)
precondition(retarget != nil && !retarget!.repeated && !retarget!.fast && retarget!.t-stop2>=0.2-1e-8 && retarget!.t-stop2<0.45 && retarget!.t<pendingRepeat,"tiny re-target keeps the precision pause, before the stationary repeat: \(String(describing:retarget.map{($0.t-stop2,$0.settled)}))")

// 4. Random still tremor never invents a first click, even with repeats on.
let tremor=Hand();tremor.run(3,wobble:true)
precondition(tremor.clicks.isEmpty,"tremor alone must not click: \(tremor.clicks.count)")

// 5. Continuous slow aiming and gentle curves still never click mid-aim.
for rate in [0.08,0.15,0.3,0.7,1.5] {
 let aim=Hand();aim.run(3){_ in (rate,0)}
 precondition(aim.clicks.isEmpty,"continuous slow aiming at \(rate) must not click: \(aim.clicks.count)")
 let curve=Hand();curve.run(4){t in (rate*cos(t/4*Double.pi/3),rate*sin(t/4*Double.pi/3))}
 precondition(curve.clicks.isEmpty,"gentle curve at \(rate) must not click: \(curve.clicks.count)")
}
print("PASS: precision first and re-target clicks, one-second repeats while still, no tremor or slow-aim clicks")

// 6. Cancellation ends a pending repeat: follow off, an ineligible reading
// (mouse button, HUD operation, scroll) or a reset never emits afterwards.
for cancel in ["none","follow","ineligible","reset"] {
 let h=Hand();h.run(0.3,wobble:true);h.run(0.15){_ in (30,0)};h.run(0.25,wobble:true)
 precondition(h.clicks.count==1,"\(cancel): one click before cancelling: \(h.clicks.count)")
 switch cancel {
 case "none": h.run(2.2,wobble:true)
 case "follow": h.d.follow(false);h.run(2.2,wobble:true)
 case "ineligible": h.run(2.2,wobble:true,eligible:false)
 default: h.d.reset();h.run(2.2,wobble:true)
 }
 if cancel=="none" {precondition(h.clicks.count>=3 && zip(h.clicks,h.clicks.dropFirst()).allSatisfy{!$1.repeated || $1.t-$0.t>=spacing-0.001},"control: a still pointer repeats once a second: \(h.clicks.map{$0.t})")}
 else {precondition(h.clicks.count==1,"\(cancel) cancels the repeat chain: \(h.clicks.count)")}
}
// 7. Scroll-release recoil cannot earn the settled shortcut: as for brisk
// stops, it needs a quiet hand and then fresh movement first.
let recoil=Hand();recoil.run(0.3,wobble:true);recoil.d.requireFreshFastGesture()
recoil.run(0.12){_ in (30,0)};let recoilStop=recoil.lastVisible;recoil.run(0.5,wobble:true)
precondition(recoil.clicks.first.map{!$0.settled && !$0.fast && $0.t-recoilStop>=0.2} ?? true,"release recoil keeps the ordinary pause: \(recoil.clicks.map{$0.t-recoilStop})")
// 8. Silence never confirms a settled stop: telemetry stops after 30 ms of rest.
let silent=Hand(repeats:false);silent.run(0.3,wobble:true);silent.run(0.15){_ in (30,0)}
let silentStop=silent.lastVisible;silent.run(0.03,wobble:true)
silent.tick(until:silentStop+0.19)
precondition(silent.clicks.allSatisfy{$0.fast},"no settled click without fresh rest readings: \(silent.clicks.map{($0.t-silentStop,$0.settled)})")
print("PASS: cancellation, scroll recoil and missing readings never produce a settled or repeat click")

// A coherent sub-pixel re-target cancels repetition immediately, before its
// first whole pixel exists; it must not click the old target mid-aim.
let fineRestart=WandDwellClick(repeatInterval:0.3);fineRestart.follow(true)
fineRestart.move(dx:12,dy:0,now:40,eligible:true)
precondition(fineRestart.tick(now:40.2) && fineRestart.repeating)
fineRestart.move(dx:0,dy:0,now:40.3,eligible:true,pointerX:0,pointerY:0,fineMove:true)
precondition(!fineRestart.repeating,"accepted fine aiming cancels the old target repeat before a visible step")
print("PASS: coherent sub-pixel restart cancels repetition")

// 9. Ethan's later stationary spacing, isolated from the motion filter: no
// repeat before one interval, a fresh reading for each repeat, and a starved
// timer clicks once (no catch-up burst). Silence ends the chain.
let spaced=WandDwellClick(repeatInterval:spacing);spaced.follow(true)
spaced.move(dx:12,dy:0,now:50,eligible:true)
let firstDue=spaced.nextDue!
precondition(spaced.tick(now:firstDue) && !spaced.lastClickWasRepeat,"ordinary first click after travel")
let repeatAt=spaced.nextDue!
precondition(abs(repeatAt-firstDue-spacing)<1e-9,"the next stationary repeat is one interval after the click")
var t=firstDue
while t+0.01<repeatAt {t+=0.01;spaced.move(dx:0,dy:0,now:t,eligible:true);precondition(!spaced.tick(now:t),"no stationary repeat before the interval")}
spaced.move(dx:0,dy:0,now:repeatAt,eligible:true)
precondition(spaced.tick(now:repeatAt) && spaced.lastClickWasRepeat,"a still, freshly reported pointer repeats")
t=repeatAt
while t<repeatAt+2.5 {t+=0.01;spaced.move(dx:0,dy:0,now:t,eligible:true)} // timer starved, readings continue
precondition(spaced.tick(now:t) && !spaced.tick(now:t),"a late timer clicks once, never a burst")
precondition(abs(spaced.nextDue!-t-spacing)<1e-9,"the next repeat is timed from the late click")
precondition(!spaced.tick(now:t+1.5) && !spaced.repeating,"no repeat without a fresh reading; the chain ends")
print("PASS: stationary repeats stay one interval apart, need fresh readings and never burst")

// A clicked Sense stroke cannot re-arm from its small unqualified settling tail.
do {
 let d=WandDwellClick(repeatInterval:1,fastStops:true);d.follow(true)
 var now=10.0
 func frame(_ x:Int=0,_ fine:Bool=false,_ rest:Bool=false){now+=0.01;d.move(dx:x,dy:0,now:now,eligible:true,pointerX:x,pointerY:0,sampleSeconds:0.01,pointerQuiet:x==0,fineMove:fine,resting:rest)}
 frame()
 for _ in 0..<6 {frame(8)}
 for _ in 0..<3 {frame(0,false,true)}
 precondition(d.tick(now:now) && d.lastClickWasFast,"the first fast stop stays prompt")
 var duplicates=0
 for _ in 0..<3 {
  for _ in 0..<3 {frame(1)} // Below the original 12-count target gate; no coherent fine intent.
  for _ in 0..<8 {frame(0,false,true);if d.tick(now:now){duplicates+=1}}
 }
 print("Unqualified settling tail extra clicks:",duplicates)
 precondition(duplicates==0,"one stop reused its already-clicked travel")
 frame(1,true)
 for _ in 0..<8 {frame(0,false,true)}
 precondition(!d.tick(now:now),"a fresh one-pixel target must not inherit the brisk click")
 for _ in 0..<14 {frame(0,false,true)}
 precondition(d.tick(now:now) && !d.lastClickWasFast,"a fresh coherent one-pixel target still clicks after the precision pause")
 print("PASS: one stop is consumed once; tiny deliberate re-target keeps precision pause")
}

// The recovered slow-pointer instruction applies to both a short precise move
// and a longer slow approach. Distance alone must never earn a brisk click.
// Use the actual timer boundary at both report rates, including a one-pixel
// accepted target after a previous quick click; no native input is emitted.
for (label,step,count,fine) in [("slow short",1,12,false),("slow long",1,100,false),("one pixel",1,1,true),("brisk",8,6,false)] {
 let d=WandDwellClick(repeatInterval:1,fastStops:true);d.follow(true)
 var t=80.0
 d.move(dx:0,dy:0,now:t,eligible:true,sampleSeconds:dt)
 for _ in 0..<count {
  t+=dt;d.move(dx:fine ? 0:step,dy:0,now:t,eligible:true,pointerX:step,pointerY:0,sampleSeconds:dt,pointerQuiet:false,fineMove:fine)
 }
 let stopped=t
 var clicked:Double?
 while t-stopped<0.3 {
  t+=dt;d.move(dx:0,dy:0,now:t,eligible:true,pointerX:0,pointerY:0,sampleSeconds:dt,pointerQuiet:true,resting:true)
  if let due=d.nextDue,due<=t,d.tick(now:t){clicked=t;break}
 }
 precondition(clicked != nil,"\(label) still clicks")
 let latency=clicked!-stopped
 if label=="brisk" {precondition(d.lastClickWasFast && latency<0.06,"brisk distance and speed keep the fast opportunity: \(latency)")}
 else {precondition(!d.lastClickWasFast && latency>=0.2-1e-8 && latency<0.2+2*dt,"\(label) requires the 200 ms precision pause: \(latency)")}
 print("precision boundary",label,hz,latency)
}
print("PASS: slow short and long strokes plus one-pixel targets keep 200 ms; brisk stops stay fast")
