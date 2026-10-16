import Foundation
import CoreGraphics

/// Discard outward excess at the actual display edge so reversal responds at once.
/// A union bounding box is insufficient: it includes gaps between staggered screens.
enum WandPointerBounds {
    static func clamp(_ point:CGPoint,to displays:[CGRect])->CGPoint {
        guard point.x.isFinite,point.y.isFinite else{return displays.first?.origin ?? .zero}
        let valid=displays.filter{!$0.isEmpty && !$0.isNull && !$0.isInfinite}
        guard !valid.isEmpty else{return point}
        var closest=point,best=CGFloat.infinity
        for rect in valid {
            let candidate=CGPoint(x:max(rect.minX,min(rect.maxX-1,point.x)),y:max(rect.minY,min(rect.maxY-1,point.y)))
            let dx=candidate.x-point.x,dy=candidate.y-point.y,distance=dx*dx+dy*dy
            if distance<best {closest=candidate;best=distance}
        }
        return closest
    }
}

/// Recognise an intentional closed loop from existing pointer deltas. Candidate
/// motion is never buffered: only an established circle consumes pointer input.
/// Native wheel lines preserve normal Mac scrolling; no trackpad emulation.
final class WandCircularScroll {
    struct Result { let consumesPointer:Bool; let lines:Int32 }
    private struct Sample {let x:Double;let y:Double;let t:Double}
    private var samples:[Sample]=[]
    private var x=0.0,y=0.0,lastTime=0.0
    private var center=CGPoint.zero,radius=0.0,angle=0.0,remainder=0.0,lastDirection=0.0
    private(set) var active=false
    func reset(){samples.removeAll(keepingCapacity:true);x=0;y=0;lastTime=0;active=false;remainder=0;lastDirection=0}
    func expire(now:Double)->Bool {
        if lastTime>0 && now-lastTime>0.22 {let was=active;reset();return was}
        return false
    }
    func update(dx:Double,dy:Double,now:Double,eligible:Bool)->Result {
        guard eligible,dx.isFinite,dy.isFinite,now.isFinite else{reset();return .init(consumesPointer:false,lines:0)}
        if dx==0 && dy==0 {_ = expire(now:now);return .init(consumesPointer:active,lines:0)}
        _ = expire(now:now)
        if samples.isEmpty && !active {samples=[.init(x:0,y:0,t:now)]}
        let vy=dy/1.4 // Undo only the existing vertical pointer ratio when judging shape.
        x+=dx;y+=vy;lastTime=now
        if active {
            let rx=x-Double(center.x),ry=y-Double(center.y),distance=hypot(rx,ry),step=hypot(dx,vy)
            let radial=step>0 && distance>0 ? abs((rx*dx+ry*vy)/(distance*step)) : 0
            let current=atan2(ry,rx),delta=Self.wrap(current-angle)
            guard distance>=radius*0.4,distance<=radius*1.8,radial<0.8,abs(delta)<1.0 else {
                reset();return .init(consumesPointer:false,lines:0)
            }
            angle=current
            let direction=delta>=0 ? 1.0 : -1.0
            if direction != lastDirection {remainder=0;lastDirection=direction}
            remainder+=delta
            let steps=max(-6,min(6,Int(remainder/(Double.pi/5))))
            remainder-=Double(steps)*(Double.pi/5)
            return .init(consumesPointer:true,lines:Int32(-steps))
        }
        samples.append(.init(x:x,y:y,t:now))
        while samples.count>180 || (samples.count>1 && now-samples[0].t>2.5){samples.removeFirst()}
        guard samples.count>=13 else{return .init(consumesPointer:false,lines:0)}
        for start in stride(from:0,to:samples.count-11,by:3) {
            let run=Array(samples[start...]),duration=now-run[0].t
            guard duration>=0.25,duration<=2.5 else{continue}
            let xs=run.map(\.x),ys=run.map(\.y)
            let minX=xs.min()!,maxX=xs.max()!,minY=ys.min()!,maxY=ys.max()!,w=maxX-minX,h=maxY-minY
            guard w>=40,h>=40,w<=1200,h<=1200,w/h>=0.55,w/h<=1.8,
                  hypot(x-run[0].x,y-run[0].y)<=min(w,h)*0.24 else{continue}
            var length=0.0,area=0.0,turn=0.0,totalTurn=0.0,previousHeading:Double?,largestTurn=0.0
            for i in 1..<run.count {
                let a=run[i-1],b=run[i],sx=b.x-a.x,sy=b.y-a.y,segment=hypot(sx,sy)
                length+=segment;area+=a.x*b.y-b.x*a.y
                if segment>=0.25 {
                    let heading=atan2(sy,sx)
                    if let previousHeading {let change=Self.wrap(heading-previousHeading);turn+=change;totalTurn+=abs(change);largestTurn=max(largestTurn,abs(change))}
                    previousHeading=heading
                }
            }
            area+=run.last!.x*run[0].y-run[0].x*run.last!.y;area/=2
            let circularity=length>0 ? 4*Double.pi*abs(area)/(length*length) : 0
            guard abs(turn)>=5.2,totalTurn>0,abs(turn)/totalTurn>=0.85,largestTurn<1.0,
                  circularity>=0.68,abs(area)/(w*h)>=0.5,abs(area)/(w*h)<=0.94 else{continue}
            center=CGPoint(x:(minX+maxX)/2,y:(minY+maxY)/2);radius=(w+h)/4
            angle=atan2(y-Double(center.y),x-Double(center.x));remainder=0
            lastDirection=area>0 ? 1 : -1;active=true;samples.removeAll(keepingCapacity:true)
            return .init(consumesPointer:true,lines:area>0 ? -3 : 3)
        }
        return .init(consumesPointer:false,lines:0)
    }
    private static func wrap(_ angle:Double)->Double {
        var value=angle
        while value>Double.pi {value-=2*Double.pi}
        while value < -Double.pi {value+=2*Double.pi}
        return value
    }
}
