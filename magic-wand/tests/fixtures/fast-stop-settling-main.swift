import Foundation
// Proposed regressions. Profiles are synthetic but shaped on measured 2026-10-31
// Sense stops: brisk travel, a 70-110 ms decelerating tail (visible 1-8 px steps
// then sub-pixel residual), then a quiet pointer.
var failures=0
func expect(_ c:@autoclosure ()->Bool,_ t:String){print((c() ? "ok   ":"FAIL ")+t);if !c(){failures+=1}}
func sweep(px:Int,frames:Int)->WandDwellClick {
 let d=WandDwellClick(fastStops:true);d.follow(true);d.move(dx:0,dy:0,now:0,eligible:true,sampleSeconds:0.01)
 for i in 1...frames {d.move(dx:px,dy:0,now:Double(i)*0.01,eligible:true,sampleSeconds:0.01,pointerQuiet:false)}
 return d
}
/// Feed tail steps (px; 0 = sub-pixel residual, not yet quiet), then quiet frames. Returns (clickTime, fast).
func finish(_ d:WandDwellClick,from:Double,tail:[Int],quiet:Int=30)->(Double?,Bool) {
 var t=from
 for s in tail {t+=0.01;d.move(dx:s,dy:0,now:t,eligible:true,sampleSeconds:0.01,pointerQuiet:false);if d.tick(now:t){return (t,d.lastClickWasFast)}}
 for _ in 0..<quiet {t+=0.01;d.move(dx:0,dy:0,now:t,eligible:true,sampleSeconds:0.01,pointerQuiet:true);if d.tick(now:t){return (t,d.lastClickWasFast)}}
 return (nil,false)
}
let decel=[8,5,3,2,2,1,1,0,0]   // 90 ms: visible steps then sub-pixel residual
// 1. Fast large move with a natural ~90 ms deceleration clicks promptly.
let a=sweep(px:25,frames:10); let ra=finish(a,from:0.10,tail:decel)
expect(ra.1 && (ra.0 ?? 9) <= 0.10+0.09+0.03,"2500 px/s move + 90 ms deceleration clicks within 30 ms of quiet (got \(ra))")
// 2. Sub-pixel residual only (12:31:07.9 shape): counts stop, accepted residual for 90 ms.
let b=sweep(px:25,frames:10); let rb=finish(b,from:0.10,tail:[3,1,0,0,0,0,0,0,0])
expect(rb.1,"fast move whose sub-pixel residual decays over 90 ms still clicks fast (got \(rb))")
// 3. Moderate brisk move keeps the original 60 ms allowance (precision guard unchanged).
let c=sweep(px:6,frames:8); let rc=finish(c,from:0.08,tail:decel)
expect(!rc.1,"600 px/s move with the same 90 ms tail keeps the 200 ms precision pause (got \(rc))")
// 4. After a fast move, a slow approach longer than the cap keeps precision.
let e=sweep(px:25,frames:10); let re=finish(e,from:0.10,tail:Array(repeating:1,count:20))
expect(!re.1,"fast move then 200 ms slow approach is not accelerated (got \(re))")
// 5. Peak evidence does not survive a sensor gap into a later moderate move.
let g=sweep(px:25,frames:10)
g.move(dx:6,dy:0,now:0.16,eligible:true,sampleSeconds:0.045,pointerQuiet:false) // 50 ms real gap
for i in 1...8 {g.move(dx:6,dy:0,now:0.16+Double(i)*0.01,eligible:true,sampleSeconds:0.01,pointerQuiet:false)}
let rg=finish(g,from:0.24,tail:decel)
expect(!rg.1,"a gap clears the fast peak; a later moderate move keeps 60 ms (got \(rg))")
// 6. Scroll-release recoil still needs rest before any fast click, extended or not.
let h=sweep(px:25,frames:10);h.reset();h.requireFreshFastGesture()
for i in 1...10 {h.move(dx:25,dy:0,now:0.2+Double(i)*0.01,eligible:true,sampleSeconds:0.01,pointerQuiet:false)}
let rh=finish(h,from:0.30,tail:decel)
expect(!rh.1,"release recoil cannot earn the extended fast click (got \(rh))")
// 7. Exactly one click per stop.
let k=sweep(px:25,frames:10); _=finish(k,from:0.10,tail:decel)
var extra=0;for i in 1...40 {let t=0.3+Double(i)*0.01;k.move(dx:0,dy:0,now:t,eligible:true,sampleSeconds:0.01,pointerQuiet:true);if k.tick(now:t){extra+=1}}
expect(extra==0,"no second click while still")
// 8. Live pipeline: 40 deg/s sweep, then a linear deceleration to rest over 100 ms.
func live(rate:Double,ramp:Int)->(Double,Bool,Int) {
 let f=WandMotionFilter();f.path = .direct
 precondition(f.configure([0,0,86.4*1.3,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,1]))
 let d=WandDwellClick(fastStops:true);d.follow(true)
 let dt=0.009615;var count=0,delay=Double.infinity,fast=false
 let brisk=42,stop=Double(brisk+ramp)*dt
 for i in 0..<(brisk+ramp+60) {
  let r=i<brisk ? rate : (i<brisk+ramp ? rate*Double(brisk+ramp-i)/Double(ramp+1) : 0)
  let s=f.sample(rawX:Int((r/0.00875).rounded()),rawY:0,microseconds:9615,held:false,resetState:false)!
  let now=Double(i)*dt
  d.intent(s.intent,now:now)
  d.move(dx:s.stopX,dy:s.stopY,now:now,eligible:true,pointerX:s.x,pointerY:s.y,sampleSeconds:dt,pointerQuiet:s.highX==0 && s.highY==0)
  if d.tick(now:now){count+=1;delay=now-stop;fast=d.lastClickWasFast}
 }
 return (delay,fast,count)
}
let lv=live(rate:40,ramp:10)
expect(lv.1 && lv.0<0.06 && lv.2==1,"live 40 deg/s move with 100 ms linear stop clicks fast once (got \(lv))")
let ls=live(rate:4,ramp:10)
expect(!ls.1 && ls.2==1,"live slow 4 deg/s move with the same ramp keeps precision timing (got \(ls))")

let hidden=sweep(px:25,frames:10)
var hiddenClicks=0
for i in 11...42 {
 let t=Double(i)*0.01
 hidden.intent(true,now:t)
 hidden.move(dx:1,dy:0,now:t,eligible:true,pointerX:0,pointerY:0,sampleSeconds:0.01,pointerQuiet:true)
 if hidden.tick(now:t) {hiddenClicks+=1}
}
hidden.intent(false,now:0.43)
for i in 43...85 {
 let t=Double(i)*0.01
 hidden.move(dx:0,dy:0,now:t,eligible:true,pointerX:0,pointerY:0,sampleSeconds:0.01,pointerQuiet:true)
 if hidden.tick(now:t) {hiddenClicks+=1}
}
expect(hiddenClicks==1,"invisible settling after a fast click never rearms another click")
for i in 86...90 {hidden.move(dx:4,dy:0,now:Double(i)*0.01,eligible:true,pointerX:4,pointerY:0,sampleSeconds:0.01,pointerQuiet:false)}
let visibleAgain=finish(hidden,from:0.90,tail:[])
expect(visibleAgain.0 != nil,"real visible movement rearms the next normal click")

print(failures==0 ? "ALL PASS":"\(failures) FAILED")
exit(failures==0 ? 0:1)
