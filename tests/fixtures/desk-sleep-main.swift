import Foundation
var sleep=WandDeskSleep()
precondition(sleep.sample(parked:false,buttons:false,now:99)==nil)
for i in 0..<120 {precondition(sleep.sample(parked:true,buttons:false,now:100+Double(i)*0.5)==nil)}
precondition(sleep.sample(parked:true,buttons:false,now:160)==true)
precondition(sleep.sleeping)
precondition(sleep.sample(parked:true,buttons:false,now:161)==nil)
precondition(sleep.sample(parked:false,buttons:false,now:162)==false)
precondition(!sleep.sleeping)
for i in 0...60 {_=sleep.sample(parked:true,buttons:false,now:200+Double(i))}
precondition(sleep.sleeping)
precondition(sleep.sample(parked:true,buttons:true,now:261)==false)
precondition(sleep.sample(parked:true,buttons:false,now:262)==nil)
sleep.reset();precondition(!sleep.sleeping)
_=sleep.sample(parked:true,buttons:false,now:300)
precondition(sleep.sample(parked:true,buttons:false,now:400)==nil,"telemetry gap is not confirmed rest")
precondition(sleep.sample(parked:true,buttons:false,now:.nan)==nil)
sleep.reset()
// Existing detector at the real sleeping rate supplies the timer's evidence.
let rest=WandRestDetection();var now=1.0
for _ in 0..<105 {
 _=rest.update(x:0,y:0,z:1.055,gyro:0,now:now,buttons:false,idle:true)
 _=sleep.sample(parked:rest.parked,buttons:false,now:now)
 now+=0.625
}
precondition(rest.parked && sleep.sleeping)
for _ in 0..<2 {
 _=rest.update(x:0.2,y:0.1,z:1.0,gyro:2,now:now,buttons:false,idle:true);now+=0.625
}
precondition(!rest.parked)
precondition(sleep.sample(parked:rest.parked,buttons:false,now:now)==false)
// No blind band between four-sample rest confirmation and the time window.
for interval in [0.1,0.4,0.5,0.56,0.625,0.7,0.9] {
 let detector=WandRestDetection()
 for i in 0..<40 {_=detector.update(x:0,y:0,z:1.055,gyro:0,now:1+Double(i)*interval,buttons:false,idle:true)}
 precondition(detector.parked,"rest missed at interval \(interval)")
}
print("PASS minute desk sleep, pickup, held buttons, reset and real rest detector")
