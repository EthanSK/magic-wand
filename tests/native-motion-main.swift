import Foundation
let filter=WandMotionFilter()
let config:[Double]=[0,0,86.4,1.4,0.35,2,18,1.0/3,0.2,0.35,1,-1,-1]
precondition(filter.configure(config))
precondition(!filter.configure([Double.nan]))
precondition(filter.sample(rawX:40000,rawY:0,microseconds:10000,held:false,resetState:false)==nil)
let rows=try JSONDecoder().decode([[Int]].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
var totalX=0,totalY=0,expectedX=0,expectedY=0
for (index,r) in rows.enumerated(){
 let s=filter.sample(rawX:r[1],rawY:r[2],microseconds:r[0],held:r[3]==1,resetState:r[4]==1)!
 precondition(abs(s.x-r[5])<=1 && abs(s.y-r[6])<=1,"sample \(index) got \(s.x),\(s.y), expected \(r[5]),\(r[6])")
 precondition(s.intent == (r[7]==1),"intent \(index)")
 totalX+=s.x;totalY+=s.y;expectedX+=r[5];expectedY+=r[6]
}
precondition(abs(totalX-expectedX)<=2 && abs(totalY-expectedY)<=2)
print("PASS: \(rows.count) native motion samples match device filter, signs, precision gain and intent")
