import Foundation
let dt=1.0/104
func prepared(horizontal:Bool=false)->(WandSustainedScroll,Double){
 let s=WandSustainedScroll();var t=0.0
 for i in 0..<64 {t+=dt;let v=i<32 ? 100.0:0;s.sample(x:horizontal ? v:0,y:horizontal ? 0:v,dt:dt,now:t);_=s.tick(now:t,pageUnitsPerLine:10)}
 return(s,t)
}
for sign in [-1.0,1.0] {
 let s=WandSustainedScroll();var t=0.0
 for i in 0..<64 {t+=dt;s.sample(x:0,y:i<32 ? sign*100:0,dt:dt,now:t);_=s.tick(now:t,pageUnitsPerLine:10)}
 var changed=false
 for _ in 0..<6 {t+=dt;s.sample(x:0,y:-sign*100,dt:dt,now:t);let q=s.tick(now:t,pageUnitsPerLine:10);precondition(Double(q.y)*sign<=0,"old direction must not jump before reversal");if Double(q.y)*sign<0 {changed=true}}
 precondition(changed,"existing reversal recognition remains responsive")
}
// Small opposite tremor remains below the existing stroke threshold.
let (quiet,start)=prepared();quiet.sample(x:0,y:-3,dt:dt,now:start+dt)
precondition(quiet.tick(now:start+dt,pageUnitsPerLine:10).y>0,"minor recoil keeps normal held scrolling")
// Skipped old output must never accumulate for a later catch-up.
let (s,start2)=prepared();var t=start2
for _ in 0..<2 {t+=dt;s.sample(x:0,y:-100,dt:dt,now:t);precondition(s.tick(now:t,pageUnitsPerLine:10).y==0)}
t+=dt;s.sample(x:0,y:0,dt:dt,now:t)
precondition(s.tick(now:t,pageUnitsPerLine:10).y<=21,"no delayed replay of withheld scroll")
print("PASS: both vertical reversals reject old output; minor tremor and no catch-up preserved")
