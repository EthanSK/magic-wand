import Foundation
import CoreFoundation
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

/// Recognise a rough, intentional loop from LOW pointer deltas and turn it into
/// native wheel lines (no trackpad emulation).
///
/// Shape is judged only from how the direction of motion turns. The device's
/// pointer gain changes with speed, but it scales both axes of a sample equally,
/// so headings survive it while closure, circularity and bounding-box fits do not.
/// No closure, fixed centre or circle fit is required: ovals, spirals, radius
/// drift and uneven speed are fine. Corners, reversals, S-curves and noise are not
/// consistent same-direction turning, so ordinary aiming does not qualify.
/// Candidate motion is never consumed; only an established circle consumes it.
final class WandCircularScroll {
    struct Result:Equatable { let consumesPointer:Bool; let lines:Int32 }
    /// Starting values for LOW counts at the device's ~35 Hz pointer rate, not
    /// measured optima. Lengths are pointer counts after undoing `verticalRatio`.
    struct Tuning {
        /// The device's vertical pointer ratio, undone so loops are judged in angle space.
        var verticalRatio=1.4
        /// Travel per heading sample. Smooths one-count integer quantisation.
        var segment=2.0
        /// Consistent same-direction turning that recognises a loop (5 rad ≈ 0.8 turn).
        var recogniseTurn=5.0
        /// Net turning / total turning. Rejects S-curves, zig-zags and noise.
        var consistency=0.6
        /// A bigger direction change between samples is a corner or reversal, not a loop.
        var maxTurn=1.5
        /// The smallest loop: travel inside the window and extent on both axes.
        var minPath=45.0, minExtent=10.0
        /// Loops may be ovals up to 4:1.
        var minAspect=0.25
        /// Turning older than `window` seconds is forgotten; a loop takes at least `minDuration`.
        var window=2.0, minDuration=0.2
        /// Forget a paused heading; an established scroll stays latched until release.
        var idleEnd=0.35
        /// Wheel lines per full loop, the recognition kick and the per-update cap.
        var linesPerTurn=8.0, kick:Int32=2, maxLinesPerUpdate=6
        init(){}
    }
    private struct Segment { let turn:Double; let length:Double; let t:Double; let x:Double; let y:Double }
    let tuning:Tuning
    private var segments:[Segment]=[]
    private var signedTurn=0.0,absoluteTurn=0.0,path=0.0
    private var accX=0.0,accY=0.0,posX=0.0,posY=0.0,lastTime=0.0
    private var heading:Double?
    private var remainder=0.0,loopLength=0.0,windowPath=0.0,windowTurn=0.0,windowSigned=0.0
    private(set) var active=false
    /// Accepted heading change for this sample; zero for jitter or a cusp.
    private(set) var latestTurn=0.0

    init(tuning:Tuning=Tuning()){self.tuning=tuning}

    func reset(){
        segments.removeAll(keepingCapacity:true);signedTurn=0;absoluteTurn=0;path=0
        accX=0;accY=0;posX=0;posY=0;lastTime=0;heading=nil
        remainder=0;loopLength=0;windowPath=0;windowTurn=0;windowSigned=0;active=false;latestTurn=0
    }
    /// Forget candidate motion or a stale heading, never the held scroll latch.
    /// Resuming after a pause must not invent a turn between unrelated headings.
    @discardableResult
    func expire(now:Double)->Bool {
        guard lastTime>0,now-lastTime>tuning.idleEnd else{return false}
        if active {heading=nil;accX=0;accY=0;remainder=0;lastTime=0}
        else {reset()}
        return false
    }
    func update(dx:Double,dy:Double,now:Double,eligible:Bool)->Result {
        latestTurn=0
        let none=Result(consumesPointer:false,lines:0)
        guard eligible,dx.isFinite,dy.isFinite,now.isFinite else{reset();return none}
        expire(now:now)
        guard dx != 0 || dy != 0 else{return .init(consumesPointer:active,lines:0)}
        let vy=dy/tuning.verticalRatio
        lastTime=now;accX+=dx;accY+=vy;posX+=dx;posY+=vy
        let length=hypot(accX,accY)
        guard length>=tuning.segment else{return .init(consumesPointer:active,lines:0)}
        let direction=atan2(accY,accX);accX=0;accY=0
        let turn=heading.map{Self.wrap(direction-$0)} ?? 0
        heading=direction
        latestTurn=abs(turn)<=tuning.maxTurn ? turn:0
        return active ? scroll(turn:turn,length:length) : candidate(turn:turn,length:length,now:now)
    }
    private func candidate(turn:Double,length:Double,now:Double)->Result {
        let none=Result(consumesPointer:false,lines:0)
        let corner=abs(turn)>tuning.maxTurn
        if corner {segments.removeAll(keepingCapacity:true);signedTurn=0;absoluteTurn=0;path=0}
        let kept=corner ? 0 : turn
        segments.append(.init(turn:kept,length:length,t:now,x:posX,y:posY))
        signedTurn+=kept;absoluteTurn+=abs(kept);path+=length
        while let first=segments.first,now-first.t>tuning.window {
            segments.removeFirst();signedTurn-=first.turn;absoluteTurn-=abs(first.turn);path-=first.length
        }
        if segments.isEmpty {signedTurn=0;absoluteTurn=0;path=0}
        guard segments.count>=6,abs(signedTurn)>=tuning.recogniseTurn,absoluteTurn>0,
              abs(signedTurn)/absoluteTurn>=tuning.consistency,path>=tuning.minPath,
              now-segments[0].t>=tuning.minDuration else{return none}
        var minX=Double.infinity,maxX = -Double.infinity,minY=Double.infinity,maxY = -Double.infinity
        for segment in segments {
            minX=min(minX,segment.x);maxX=max(maxX,segment.x);minY=min(minY,segment.y);maxY=max(maxY,segment.y)
        }
        let w=maxX-minX,h=maxY-minY
        guard w>=tuning.minExtent,h>=tuning.minExtent,min(w,h)/max(w,h)>=tuning.minAspect else{return none}
        let clockwise=signedTurn>0
        loopLength=max(24,min(6000,path*2*Double.pi/abs(signedTurn)))
        segments.removeAll(keepingCapacity:true);signedTurn=0;absoluteTurn=0;path=0
        remainder=0;windowPath=0;windowTurn=0;windowSigned=0;active=true
        // Screen y points down, so positive turning is clockwise: clockwise scrolls down.
        return .init(consumesPointer:true,lines:clockwise ? -tuning.kick : tuning.kick)
    }
    private func scroll(turn:Double,length:Double)->Result {
        // A cusp (circling direction reversed) contributes no burst; the turning
        // that follows simply winds the scroll the other way.
        let kept=abs(turn)>tuning.maxTurn ? 0 : turn
        windowPath+=length;windowTurn+=abs(kept);windowSigned+=kept
        if windowPath>=max(tuning.segment*3,loopLength*0.3) {
            if abs(windowSigned)>0.5 {
                loopLength=max(24,min(6000,0.7*loopLength+0.3*windowPath*2*Double.pi/abs(windowSigned)))
            }
            windowPath=0;windowTurn=0;windowSigned=0
        }
        remainder+=kept
        let perLine=2*Double.pi/tuning.linesPerTurn
        let steps=max(-tuning.maxLinesPerUpdate,min(tuning.maxLinesPerUpdate,Int((remainder/perLine).rounded(.towardZero))))
        remainder-=Double(steps)*perLine
        return .init(consumesPointer:true,lines:Int32(-steps))
    }
    private static func wrap(_ angle:Double)->Double {
        var value=angle
        while value>Double.pi {value-=2*Double.pi}
        while value < -Double.pi {value+=2*Double.pi}
        return value
    }
}

/// Pure routing of the device's `@BOTTOM` edges and `@WAND x,y,buttons` frames.
/// The receiver performs the returned actions in order and owns only CGEvent posting.
///
/// LOW is a plain mouse-button hold with no native button down (precision aiming, not a
/// drag). LOW motion is delayed by the explicitly approved `lowDelay`: the device reports
/// the release edge in the same ordered UART stream as motion, so stiff-switch
/// movement in the last instant before release is discarded unseen and the release
/// click lands where the pointer is already shown. HIGH follow and real dragging
/// stay immediate. Loop scrolling is recognised only during LOW. A hold in which a
/// loop was recognised is consumed by scrolling: the endpoint click that the device
/// emits right after that `@BOTTOM 0` (same callback, so before any later frame) is
/// dropped. The drop is disarmed by the next mouse button press, so it can never swallow
/// a later real click. It is decided by stream order, never by a timeout.
final class WandPointerRouter {
    enum Action:Equatable { case move(dx:Int,dy:Int), scroll(lines:Int32), circleLight(Bool) }
    struct Frame:Equatable { let buttons:Int; let actions:[Action] }
    /// Ethan returned held LOW aiming to immediate movement. Do not enable
    /// a buffer again without fresh explicit confirmation.
    let lowDelay:Double
    /// Bounds memory if the drain timer is starved; the oldest motion is then shown, not lost.
    let maxPending:Int
    let circle:WandCircularScroll
    private(set) var mouseButtonHeld=false // Previously bottomHeld.
    private(set) var holdConsumed=false
    private(set) var dropNextClick=false
    private var droppingClick=false
    private var pending:[(due:Double,dx:Int,dy:Int)]=[]
    private var lit=false

    init(lowDelay:Double=0,maxPending:Int=48,circle:WandCircularScroll=WandCircularScroll()) {
        self.lowDelay=max(0,lowDelay);self.maxPending=max(1,maxPending);self.circle=circle
    }
    var nextDue:Double? {pending.first?.due}
    var pendingCount:Int {pending.count}

    /// The device prints a mouse-button edge before the release click it emits for
    /// that edge. Previously bottom(down:); the wire edge is still `@BOTTOM`.
    func mouseButton(down:Bool)->[Action] {
        pending.removeAll(keepingCapacity:true)
        if down {dropNextClick=false;droppingClick=false}
        else {dropNextClick=mouseButtonHeld && holdConsumed}
        holdConsumed=false;mouseButtonHeld=down
        return endCircle()
    }
    /// One device pointer frame. `hud` excludes HUD navigation from LOW handling.
    func frame(dx:Int,dy:Int,buttons:Int,hud:Bool,now:Double)->Frame {
        var bits=buttons
        if dropNextClick || droppingClick {
            if bits & 1 != 0 {dropNextClick=false;droppingClick=true;bits &= ~1}
            else if droppingClick {droppingClick=false}
        }
        var actions:[Action]=[]
        let low=mouseButtonHeld && bits==0 && !hud
        if !low {actions+=endCircle()}
        // A button change lands where the pointer is already shown.
        if bits != 0 {pending.removeAll(keepingCapacity:true)}
        guard dx != 0 || dy != 0 else{return .init(buttons:bits,actions:actions)}
        guard low else{actions.append(.move(dx:dx,dy:dy));return .init(buttons:bits,actions:actions)}
        let wasActive=circle.active
        let result=circle.update(dx:Double(dx),dy:Double(dy),now:now,eligible:true)
        if circle.active && !wasActive {pending.removeAll(keepingCapacity:true);holdConsumed=true}
        if circle.active != lit {lit=circle.active;actions.append(.circleLight(lit))}
        if result.consumesPointer {
            if result.lines != 0 {actions.append(.scroll(lines:result.lines))}
            return .init(buttons:bits,actions:actions)
        }
        if lowDelay == 0 {
            actions.append(.move(dx:dx,dy:dy))
            return .init(buttons:bits,actions:actions)
        }
        actions+=drain(now:now)
        pending.append((due:now+lowDelay,dx:dx,dy:dy))
        while pending.count>maxPending {
            let oldest=pending.removeFirst();actions.append(.move(dx:oldest.dx,dy:oldest.dy))
        }
        return .init(buttons:bits,actions:actions)
    }
    /// Delayed LOW motion now due, in arrival order.
    func drain(now:Double)->[Action] {
        var actions:[Action]=[]
        while let first=pending.first,first.due<=now {
            pending.removeFirst();actions.append(.move(dx:first.dx,dy:first.dy))
        }
        return actions
    }
    /// Periodic: show due motion and forget stale headings, retaining a held scroll.
    func tick(now:Double)->[Action] {
        var actions=drain(now:now)
        circle.expire(now:now)
        if lit && !circle.active {lit=false;actions.append(.circleLight(false))}
        return actions
    }
    /// Another control took over (scroll chord, HUD, speech): drop unshown LOW
    /// motion and any circle. A hold already consumed by scrolling stays consumed.
    func interrupt()->[Action] {pending.removeAll(keepingCapacity:true);return endCircle()}
    /// Disconnect or shutdown: forget everything.
    func cancelAll()->[Action] {
        pending.removeAll(keepingCapacity:true)
        mouseButtonHeld=false;holdConsumed=false;dropNextClick=false;droppingClick=false
        return endCircle()
    }
    private func endCircle()->[Action] {
        circle.reset()
        guard lit else{return []}
        lit=false;return [.circleLight(false)]
    }
}

/// Click sooner only after a coherent, brisk pointer move and fresh evidence
/// that it stopped. Ethan: a larger move should click as soon as it stops;
/// slow precision work keeps its existing pause. This never delays motion.
struct WandFastStopClick {
    static let window=0.12, distance=40.0, speed=500.0, finalSpeed=500.0
    static let quietDuration=0.008, maximumGap=0.04, maximumTail=0.08, slowTail=0.06
    static let maximumDeliveryGap=0.08, maximumContinuousSample=0.02
    private var samples:[(time:Double,dt:Double,x:Double,y:Double)]=[]
    private var lastAt:Double?,lastMotion=0.0,lastBrisk=0.0,quietAt:Double?,quietCount=0,eligible=false
    private(set) var due:Double?
    private var needsRest=false
    mutating func reset(){self=Self()}
    mutating func requireRest(){reset();needsRest=true}
    mutating func sample(stopped:Bool,x:Int,y:Int,now:Double,sampleSeconds:Double?=nil,pointerQuiet:Bool?=nil){
        guard now.isFinite else{reset();return}
        let dt=lastAt.map{now-$0};lastAt=now
        // A short host-delivery gap need not be a sensor gap: Bluetooth may
        // deliver continuous 104 Hz readings together. Preserve the brisk
        // evidence only when sensor time confirms continuity. Still require
        // fresh quiet arrivals afterwards; this never waits or replays motion.
        let continuous=sampleSeconds.map{$0.isFinite && $0>0 && $0<=Self.maximumContinuousSample} ?? false
        guard let dt,dt>0,dt<=Self.maximumGap || (continuous && dt<=Self.maximumDeliveryGap) else{
            samples=[];quietAt=nil;quietCount=0;eligible=false;due=nil;return
        }
        // Radio notifications can deliver adjacent readings in one burst.
        // Judge speed from sensor time, while freshness and a confirmed stop
        // still use real arrival time. Neither path buffers pointer movement.
        let motionDt=sampleSeconds.flatMap { $0.isFinite && $0>0 && $0<=0.05 ? $0:nil } ?? dt
        if needsRest {
            if stopped && x==0 && y==0 {
                if quietAt==nil {quietAt=now;quietCount=1}else{quietCount+=1}
                if quietCount>=2,now-(quietAt ?? now)>=Self.quietDuration {needsRest=false;quietAt=nil;quietCount=0}
            }else{quietAt=nil;quietCount=0}
            return
        }
        if x==0 && y==0 {
            // Ethan's brisk-stop exception uses the pointer he can see. The
            // ordinary precision path still follows the tuned stop guard;
            // hidden residual counts cannot postpone this recent brisk stop.
            // But sub-pixel *accepted* movement is still precision aiming,
            // even between integer cursor steps; it must not count as quiet.
            guard pointerQuiet ?? stopped else {
                quietAt=nil;quietCount=0;due=nil
                if now-lastBrisk>Self.slowTail {eligible=false}
                return
            }
            guard eligible,now-lastMotion<=Self.maximumTail else{quietAt=nil;quietCount=0;due=nil;return}
            if quietAt==nil {quietAt=now;quietCount=1}else{quietCount+=1}
            if due==nil,quietCount>=2,now-(quietAt ?? now)>=Self.quietDuration {due=now}
            return
        }
        due=nil;quietAt=nil;quietCount=0;lastMotion=now
        samples.append((now,motionDt,Double(x),Double(y)))
        samples.removeAll{now-$0.time>Self.window}
        let path=samples.reduce(0){$0+hypot($1.x,$1.y)}
        let elapsed=samples.reduce(0){$0+$1.dt}
        let net=hypot(samples.reduce(0){$0+$1.x},samples.reduce(0){$0+$1.y})
        let brisk=path>=Self.distance && elapsed>0 && path/elapsed>=Self.speed &&
            net>=path*0.8 && hypot(Double(x),Double(y))/motionDt>=Self.finalSpeed
        if brisk {eligible=true;lastBrisk=now}
        // A brief deceleration/settling tail is part of the same brisk stop.
        // Sustained slow aiming still clears the shortcut and uses200 ms.
        else if !eligible || now-lastBrisk>Self.slowTail {eligible=false}
    }
}

/// HIGH clicks once after travel then a pause, or an eligible clear fast stop.
/// Entry and remaining still never click; mode changes require fresh movement.
final class WandDwellClick {
    let pause:Double
    let travel:Double
    /// Ethan (2026-10-29): after a stop-to-click, "another tab will slide in
    /// and my mouse will still be over the close button but it won't send a
    /// click again ... do it maybe every interval ... 300 milliseconds".
    /// While the pointer stays settled after the first click,
    /// click again every `repeatInterval`. Any movement, intent, ineligible
    /// sample, button or mode change, or stale telemetry ends the repeats.
    /// Nil (screenshot settling) never repeats.
    let repeatInterval:Double?
    private var fastStop:WandFastStopClick?
    private(set) var lastClickWasFast=false
    /// Repeats need live samples: a gap longer than this stops them.
    static let freshness=0.1
    private(set) var following=false
    private var x=0.0,y=0.0,lastMotion=0.0,inhibitedUntil=0.0,intentUntil=0.0
    private(set) var armed=false
    private(set) var repeatDue:Double?
    private var lastSeen = -Double.infinity
    init(pause:Double=0.2,travel:Double=12,repeatInterval:Double?=nil,fastStops:Bool=false){self.pause=pause;self.travel=travel;self.repeatInterval=repeatInterval;fastStop=fastStops ? WandFastStopClick():nil}
    var nextDue:Double? {
        guard following else{return nil}
        if armed {return max(min(max(lastMotion+pause,intentUntil),fastStop?.due ?? .infinity),inhibitedUntil)}
        return repeatDue
    }
    var repeating:Bool {repeatDue != nil}
    func reset(){x=0;y=0;armed=false;lastMotion=0;intentUntil=0;repeatDue=nil;fastStop?.reset();lastClickWasFast=false}
    func follow(_ on:Bool){if following != on {reset()};following=on}
    /// A scroll release may contain wrist recoil. Keep the old click pause
    /// until a quiet hand and a new pointer move establish a fresh gesture.
    func requireFreshFastGesture(){fastStop?.requireRest()}
    func inhibit(until:Double){reset();inhibitedUntil=max(inhibitedUntil,until)}
    /// The device sees sub-pixel motion before integer cursor counts exist.
    /// A bounded heartbeat lease prevents both premature clicks and stuck state.
    func intent(_ moving:Bool,now:Double){
        guard following else{return}
        // This signal vetoes a click while motion continues; it must not erase
        // the cursor travel that qualifies Ethan's faster click when it stops.
        // Slow final approach, pauses and stale samples remain classified by
        // fastStop.sample, using actual motion in the same live call order.
        if moving {intentUntil=now+0.6;lastMotion=now;repeatDue=nil}
        else if intentUntil>0 {intentUntil=0;lastMotion=now}
    }
    func move(dx:Int,dy:Int,now:Double,eligible:Bool,pointerX:Int?=nil,pointerY:Int?=nil,sampleSeconds:Double?=nil,pointerQuiet:Bool?=nil){
        guard following,eligible,now>=inhibitedUntil else{reset();return}
        fastStop?.sample(stopped:dx==0 && dy==0,x:pointerX ?? dx,y:pointerY ?? dy,now:now,sampleSeconds:sampleSeconds,pointerQuiet:pointerQuiet)
        lastSeen=now
        guard dx != 0 || dy != 0 else{return}
        repeatDue=nil
        x+=Double(dx);y+=Double(dy);lastMotion=now
        if hypot(x,y)>=travel {armed=true}
    }
    func tick(now:Double)->Bool {
        guard let due=nextDue,now>=due else{return false}
        if !armed {
            // A repeat: only on a fresh, still settled pointer, never a burst.
            guard now-lastSeen<=Self.freshness, let interval=repeatInterval else{reset();return false}
            repeatDue=now+interval
            return true
        }
        let fast=(fastStop?.due).map{$0<lastMotion+pause} ?? false
        // An overdue quick decision cannot click later at a stale position.
        if fast,now-lastSeen>WandFastStopClick.maximumGap {fastStop?.reset();return false}
        reset();lastClickWasFast=fast
        if let interval=repeatInterval {repeatDue=now+interval}
        return true
    }
}

/// Conservative IMU inference, not a touch sensor. Remember a quiet desk pose,
/// confirm pickup over multiple readings, then require a return/contact followed
/// by sustained very low acceleration variation and gyro rate before put-down.
/// A still hand away from the learned desk pose must not stop dictation.
final class WandRestDetection {
    enum Event:Equatable {case probe,pickedUp,settling,putDown}
    private let cache:URL?
    private var rest:[Double]?,previous:[Double]?,quiet:[Double]?
    private var quietSince=0.0,quietCount=0,pickupCount=0
    private var quietWindow:[(a:[Double],gyro:Double,time:Double)]=[]
    private var contactUntil=0.0,lastTime=0.0,away=false,settling=false
    private(set) var parked=false
    private(set) var deskQuietSince:Double?
    var hasReference:Bool {rest != nil}

    init(cache:URL?=nil){
        self.cache=cache
        if let cache,let attributes=try? FileManager.default.attributesOfItem(atPath:cache.path),
           attributes[.type] as? FileAttributeType == .typeRegular,
           (attributes[.size] as? NSNumber)?.intValue ?? 513 <= 512,
           let data=try? Data(contentsOf:cache),let pose=try? JSONDecoder().decode([Double].self,from:data),
           pose.count==3,pose.allSatisfy({$0.isFinite}),abs(sqrt(pose.reduce(0){$0+$1*$1})-1)<0.15 {rest=pose}
    }
    /// Keep only the confirmed gravity reference across a receiver reconnect.
    /// Timestamps and current held/parked state must always be learned afresh.
    func reset(keepingReference:Bool=false){
        if !keepingReference {rest=nil}
        previous=nil;quiet=nil;quietCount=0;quietWindow.removeAll();pickupCount=0;contactUntil=0;lastTime=0;away=false;settling=false;parked=false;deskQuietSince=nil
    }
    func pointerActivated(){
        parked=false;away=rest != nil;quiet=nil;quietCount=0;quietWindow.removeAll();deskQuietSince=nil
    }
    func pointerStopped(){quiet=nil;quietCount=0;quietWindow.removeAll();settling=false}
    private func remember(_ pose:[Double]){
        rest=pose
        if let cache,let data=try? JSONEncoder().encode(pose){
            try? data.write(to:cache,options:.atomic)
            try? FileManager.default.setAttributes([.posixPermissions:0o600],ofItemAtPath:cache.path)
        }
    }
    private func distance(_ a:[Double],_ b:[Double])->Double {sqrt(zip(a,b).reduce(0){$0+pow($1.0-$1.1,2)})}
    /// Four observations spanning 1.8 seconds work at both 10 Hz and the
    /// sleeping accelerometer's 1.6 Hz. Never require 18 low-rate observations.
    private func isQuiet(_ a:[Double],gyro:Double,magnitude:Double,now:Double)->Bool {
        guard gyro<1.5,abs(magnitude-1)<0.15 else {quietWindow.removeAll();return false}
        quietWindow.append((a,gyro,now))
        // Keep the shortest window spanning 1.8 s (at least four samples).
        // A fixed 2.15 s cutoff has a blind band: at 0.56 s intervals four
        // samples span only 1.68 s, but five span 2.24 s and lose the first.
        while quietWindow.count>4 && now-quietWindow[1].time>=1.8 {quietWindow.removeFirst()}
        if quietWindow.count>256 {quietWindow.removeFirst(quietWindow.count-256)}
        guard quietWindow.count>=4,let first=quietWindow.first,now-first.time>=1.8 else{return false}
        let n=Double(quietWindow.count)
        let mean=(0..<3).map{axis in quietWindow.reduce(0){$0+$1.a[axis]}/n}
        let scatter=sqrt(quietWindow.reduce(0){$0+pow(distance($1.a,mean),2)}/n)
        let rotation=sqrt(quietWindow.reduce(0){$0+$1.gyro*$1.gyro}/n)
        let midTime=quietWindow.reduce(0){$0+$1.time}/n
        let timeVariance=quietWindow.reduce(0){$0+pow($1.time-midTime,2)}
        guard timeVariance>0 else{return false}
        let slope=(0..<3).map{axis in quietWindow.reduce(0){$0+($1.time-midTime)*($1.a[axis]-mean[axis])}/timeVariance}
        // Compare a window's spread and sustained drift, not every sample with
        // one anchor: the live stationary 104 Hz sensor has isolated 0.03 g noise.
        return scatter<0.025 && rotation<0.45 && sqrt(slope.reduce(0){$0+$1*$1})<0.008
    }
    func update(x:Double,y:Double,z:Double,gyro:Double,now:Double,buttons:Bool,idle:Bool)->[Event] {
        let a=[x,y,z],magnitude=sqrt(x*x+y*y+z*z)
        guard a.allSatisfy({$0.isFinite}),gyro.isFinite,now.isFinite,(0.05...4).contains(magnitude) else{quiet=nil;quietCount=0;quietWindow.removeAll();deskQuietSince=nil;return []}
        if lastTime>0 && (now<=lastTime || now-lastTime>2){quiet=nil;quietCount=0;quietWindow.removeAll();pickupCount=0}
        lastTime=now
        let jerk=previous.map{distance(a,$0)} ?? 0;previous=a
        if buttons {quiet=nil;quietCount=0;quietWindow.removeAll();pickupCount=0;deskQuietSince=nil;return []}
        if parked,let pose=rest {
            if jerk>=0.012 || gyro>=0.3 {deskQuietSince=nil}
            else if deskQuietSince==nil {deskQuietSince=now}
            if distance(a,pose)>0.06 || jerk>0.08 || gyro>1.2 || abs(magnitude-sqrt(pose.reduce(0){$0+$1*$1}))>0.06 {
                pickupCount+=1
                if pickupCount==1 {return [.probe]}
                parked=false;deskQuietSince=nil;away=true;quiet=nil;quietCount=0;quietWindow.removeAll();pickupCount=0
                return [.pickedUp]
            }
            pickupCount=0;return []
        }
        // An explicitly inactive pointer may learn its current stable resting
        // orientation, including a new table position. This does not stop audio.
        if idle {
            if isQuiet(a,gyro:gyro,magnitude:magnitude,now:now){
                remember(a);parked=true;deskQuietSince=now;away=false;settling=false;quiet=nil;quietCount=0
            }
            return []
        }
        // A desk placement need not return to the last gravity angle or make
        // an impact. Confirm physical stillness at the new angle instead.
        // IMU-only detection cannot distinguish a perfectly supported hand.
        var events:[Event]=[]
        if isQuiet(a,gyro:gyro,magnitude:magnitude,now:now) {
            remember(a);parked=true;deskQuietSince=now;away=false;settling=false;quiet=nil;quietCount=0;contactUntil=0
            events.append(.putDown)
        }
        return events
    }
}

/// Ethan's "go to sleep after a minute": dark LEDs and low-rate pickup sensing,
/// never a dictation stop or an explicit HUD/review dismissal. The existing rest
/// detector owns the desk classification; this policy only times confirmed rest.
struct WandDeskSleep {
    static let seconds = 60.0
    static let deepSeconds = 300.0
    private(set) var sleeping = false
    private(set) var deepSleeping = false
    private var restSince:Double?,lastSeen:Double?
    mutating func reset(){sleeping=false;deepSleeping=false;restSince=nil;lastSeen=nil}
    /// Reuse the existing confirmed parked/pickup state. Isolated sensor noise
    /// must not postpone sleep forever. A telemetry gap cannot prove rest.
    mutating func sample(parked:Bool,buttons:Bool,now:Double)->Bool? {
        guard now.isFinite else{return nil}
        let was=sleeping
        if let last=lastSeen,now<=last || now-last>2 {restSince=nil}
        lastSeen=now
        if buttons || !parked {sleeping=false;deepSleeping=false;restSince=nil}
        else {
            if restSince==nil {restSince=now}
            if let since=restSince {sleeping=now-since>=Self.seconds;deepSleeping=now-since>=Self.deepSeconds}
        }
        return was==sleeping ? nil:sleeping
    }
}

/// Gesture adapter only. Better Git owns file membership, Git changes and Undo.
final class WandReviewGesture {
    struct Request {let phase:String,id:String,seq:Int,direction:String,mode:String}
    private(set) var files=false
    private var held=false,started=0.0,lastTap = -100.0,lastInput=0.0,lastPulse=0.0
    private var y=0.0,lastY=0.0,travel=0.0,seq=0,id:String?,direction="next"
    var mode:String {files ? "files":"changes"}
    var isHeld:Bool {held}
    func button(down:Bool,now:Double)->[Request] {
        if down {
            guard !held else{return []};held=true;started=now;lastInput=now;travel=0;y=0;lastY=0;return []
        }
        guard held else{return []};held=false
        if id != nil {lastTap = -100;return finish("finish")}
        if now-started<0.22 {
            if now-lastTap<=0.45 {files.toggle();lastTap = -100}else{lastTap=now}
        }else{lastTap = -100}
        return []
    }
    func motion(y absolute:Double,now:Double)->[Request] {
        guard held,absolute.isFinite else{return []}
        // The receiver rebases the absolute NAV value at physical press.
        let delta=absolute-lastY;lastY=absolute;lastInput=now
        guard now-started>=0.22 else{return []}
        y+=delta;travel+=abs(delta)
        var result:[Request]=[],budget=6
        while abs(y)>=7 && budget>0 {
            let step=y>0 ? "next":"previous";y += y>0 ? -7:7;budget-=1
            if id==nil {id=UUID().uuidString;seq=0;direction=step;lastPulse=now;result.append(request("begin",direction:direction))}
            result.append(request("step",direction:step))
        }
        return result
    }
    // The HUD adapter supplies real wheel-sized steps; Better Git still owns staging.
    func beginDetents(mode:String,now:Double) {
        _=cancel();files=mode=="files";held=true;started=now;lastInput=now
    }
    func detents(_ count:Int32,now:Double)->[Request] {
        guard held else{return []};lastInput=now
        guard count != 0 else{return []}
        let step=count>0 ? "next":"previous"
        var result:[Request]=[]
        if id==nil {id=UUID().uuidString;seq=0;direction=step;lastPulse=now;result.append(request("begin",direction:step))}
        for _ in 0..<min(12,abs(Int(count))) {result.append(request("step",direction:step))}
        return result
    }
    /// Ethan's Review/Stage toggle keeps one selection (formerly set). A live Better Git
    /// transaction only switches mode (same ID, next sequence) and adds the
    /// file being viewed; it is never finished, cancelled or begun again.
    /// Without one, begin it in the current mode and then switch, so
    /// the viewed file joins even before any ratchet. No step is sent.
    func changeMode(_ target:String,now:Double)->[Request] {
        guard target=="changes" || target=="files" else{return []}
        let next=target=="files"
        guard next != files else{return []}
        guard held else{files=next;return []}
        var result:[Request]=[]
        if id==nil {id=UUID().uuidString;seq=0;lastPulse=now;result.append(request("begin",direction:direction))}
        files=next;lastInput=now
        result.append(request("mode",direction:direction))
        return result
    }
    func endDetents(commit:Bool)->[Request] {held=false;lastTap = -100;return finish(commit ? "finish":"cancel")}
    func tick(now:Double)->[Request] {
        guard held,id != nil else{return []}
        if now-lastInput>0.9 {held=false;return finish("cancel")}
        if now-lastPulse>=1 {lastPulse=now;return [request("heartbeat",direction:direction)]}
        return []
    }
    func cancel()->[Request] {held=false;lastTap = -100;return finish("cancel")}
    private func request(_ phase:String,direction:String)->Request {seq+=1;return .init(phase:phase,id:id!,seq:seq,direction:direction,mode:mode)}
    private func finish(_ phase:String)->[Request] {guard id != nil else{return []};let r=request(phase,direction:direction);id=nil;return [r]}
}


/// The same pointing calculation used by the Puck, run on the Mac without
/// queueing or look-ahead. Device sample time controls integration; arrival
/// time is used only to reject stale state after a transport gap.
/// One gravity basis for pointer, HUD, review and scrolling angular deltas.
/// Transform increments before accumulating them: rotating an old total would jump.
final class WandOrientation {
    var enabled=false
    /// Sense only: the program samples gravity from one reading every 100 ms,
    /// so one sample taken during a hand jerk or twist set a wrong roll until
    /// the next. Recorded Sense pointing (firmware c, ~400 s following) had 15
    /// transient basis flips over 30 degrees, from linear acceleration of
    /// 0.83-1.24 g, a twist and a near-vertical roll. This accepts only near-1 g
    /// samples, away from vertical, without fast rotation: 2 flips remained
    /// and 74% of samples were still used. Each sample is judged at once;
    /// nothing waits. The Puck keeps its original bounds.
    var strictGravity=false
    static let strictLength=0.9...1.1,strictAcross=0.4,strictRotation=45.0
    private var rollCos=1.0,rollSin=0.0,yawScale=1.0
    /// `rotation`: the same reading's rotation rate (program units, 134 per deg/s).
    func observeGravity(x:Double,y:Double,z:Double,rotation:Double=0) {
        guard x.isFinite,y.isFinite,z.isFinite,rotation.isFinite else{return}
        let length=sqrt(x*x+y*y+z*z),across=hypot(x,z)
        // Linear acceleration is not gravity. Ignore obvious shocks and retain
        // the last usable basis near vertical, where roll cannot be determined.
        guard (0.75...1.25).contains(length),across>=0.25 else{return}
        if strictGravity {
            guard Self.strictLength.contains(length),across>=Self.strictAcross,rotation<=Self.strictRotation else{return}
        }
        rollCos=z/across;rollSin=x/across
        // Heading speed loses cos(elevation) when projected onto the two
        // axes perpendicular to the shaft. Undo that before the speed curve.
        // Cap at 2x (60 degrees); heading is ill-conditioned near vertical.
        yawScale=min(2,length/across)
    }
    func project(x:Double,y:Double)->(x:Double,y:Double) {
        guard enabled else{return (x,y)}
        return ((x*rollCos+y*rollSin)*yawScale,y*rollCos-x*rollSin)
    }
}

struct WandAngularStream {
    private var lastX=0.0,lastY=0.0
    private(set) var x=0.0,y=0.0
    mutating func reset(){lastX=0;lastY=0;x=0;y=0}
    mutating func update(x rawX:Double,y rawY:Double,using filter:WandMotionFilter,horizontalGain:Double=1)->(x:Double,y:Double) {
        let step=filter.projectSigned(x:(rawX-lastX)/horizontalGain,y:rawY-lastY)
        lastX=rawX;lastY=rawY;x+=step.x*horizontalGain;y+=step.y
        return (x,y)
    }
}

/// Ordinary pointer conversion. `tuned` is the unchanged Puck filter: adaptive
/// 2–8 ms smoothing, 150 ms directional mean with a 250 ms intent gate, 0.2°
/// slack with recentring, and the slow-motion sensitivity curve. `direct` is
/// Ethan's Sense baseline (2026-10-29: "get rid of all the weird, hacky potential
/// noise rejection ... start off like scratch ... just the expected route"):
/// calibrated, orientation-projected gyro rate × time × the same gain, vertical
/// gain and explicit held LOW gain, keeping the subpixel remainder. Its only
/// additions are the ones measured or approved since: Ethan's approved ~8 ms
/// causal smoothing, a continuous tiny-motion stop and a bounded step (see
/// `WandMotionFilter.directSmoothing`). Nothing is buffered, replayed or
/// predicted. Both paths are measured in the same units.
enum WandPointerPath: String {
    case tuned, direct
    static func read(_ value: Any?, default fallback: WandPointerPath) -> WandPointerPath {
        (value as? String).flatMap(WandPointerPath.init(rawValue:)) ?? fallback
    }
}

final class WandMotionFilter {
    // Ethan's Switch App sensitivity means normal mouse HIGH, even while
    // The HUD button is held. Share the unrounded calculation; the mouse button alone owns LOW.
    // stopX/stopY: the tuned filter's counts, used only to decide stop-to-click
    // (dwell) and screenshot settling, so a direct pointer cannot disable or
    // flood those clicks with tremor- or bias-level counts. Equal to x/y when tuned.
    struct Result {let x:Int,y:Int;let intent:Bool;let angularX:Double,angularY:Double;let highX:Double;var stopX=0,stopY=0;var highY=0.0}
    var path:WandPointerPath = .tuned
    private var directX=0.0,directY=0.0,smoothX=0.0,smoothY=0.0
    /// Seconds. Ethan approved "about 8 ms of pointer smoothing delay to reduce
    /// jagged movement" (2026-10-29, "Make it as good as possible"): a causal
    /// exponential average of the calibrated rate in device time. It reduces
    /// per-reading sensor noise only; it is not the Puck's 150 ms intent filter.
    static let directSmoothing=0.008
    /// Tiny-motion stop: the smoothed rate stops the pointer at or below the
    /// existing slow-speed boundary (CONFIG fineSpeed: 2 in the program's
    /// 134-count units, about 2.3 true deg/s on the Sense) and reaches full gain
    /// at twice it. In recorded real pointing (2026-10-29, firmware c) about a
    /// third of readings were at or below 2 deg/s and the hard on/off gate
    /// crossed about 5 times a second; a continuous knee keeps the stop without
    /// those jumps. Faster movement is unchanged.
    static let directKneeFactor=2.0
    /// One reading moves at most this much device time. A longer gap (lost
    /// readings, a radio stall, a dropped stale reading) is skipped, never
    /// caught up from the next reading's rate. One missing reading still fits.
    static let directMaxStep=0.025
    // Ethan: tiny coherent motion means intentional aiming; back-and-forth
    // wobble should cancel. Only this formerly frozen slow band waits for
    // directional evidence (approved 60 ms on 2026-10-29, tiny slow motion
    // only; normal movement keeps the ~8 ms smoothing). Never replay its
    // accumulated displacement: after confirmation, output this reading only.
    private var fineSamples:[(x:Double,y:Double,time:Double)] = []
    private var fineDuration=0.0
    static let fineConfirmation=0.060
    /// Smoothed rate below which nothing counts as aiming, in the program's
    /// 134-count units (0.85 is about 1.0 true deg/s). Replayed over 25 min of
    /// Ethan's real Sense use (2026-10-29, firmware c, gain 1.52425): 0.85
    /// posted nothing while the hand was still (0.2 crept 250 counts), leaked
    /// less wobble than receiver 111, and cut frozen deliberate slow motion
    /// from 66% to 37%. Stop-to-click is unchanged (it judges tuned counts).
    static let fineFloor=0.85
    private var values:[Double] = []
    private var fx=0.0,fy=0.0,ix=0.0,iy=0.0,meanSpeed=0.0,intentTime=0.0
    private var slackX=0.0,slackY=0.0,fractionX=0.0,fractionY=0.0
    let orientation=WandOrientation()
    var orientationCompensation:Bool {
        get {orientation.enabled}
        set {orientation.enabled=newValue}
    }
    func observeGravity(x:Double,y:Double,z:Double,rotation:Double=0){orientation.observeGravity(x:x,y:y,z:z,rotation:rotation)}
    func projectSigned(x:Double,y:Double)->(x:Double,y:Double) {
        let sx=configured ? values[11] : -1,sy=configured ? values[12] : -1
        let result=orientation.project(x:x/sx,y:y/sy)
        return (result.x*sx,result.y*sy)
    }
    var configured:Bool {values.count==13}
    func configure(_ v:[Double])->Bool {
        guard v.count==13,v.allSatisfy({$0.isFinite}),abs(v[0])<=32768,abs(v[1])<=32768,
              (0...1000).contains(v[2]),(0.1...10).contains(v[3]),(0...1).contains(v[4]),
              v[5]>=0,v[6]>v[5],(0...1).contains(v[7]),v[8]>=0,v[9]>0,v[10]>=0,
              abs(v[11])==1,abs(v[12])==1 else{return false}
        values=v;reset();return true
    }
    func reset(){fx=0;fy=0;ix=0;iy=0;meanSpeed=0;intentTime=0;slackX=0;slackY=0;fractionX=0;fractionY=0;directX=0;directY=0;smoothX=0;smoothY=0;fineSamples=[];fineDuration=0}
    func sample(rawX:Int,rawY:Int,microseconds:Int,held:Bool,resetState:Bool)->Result? {
        guard configured,(-65535...65535).contains(rawX),(-65535...65535).contains(rawY),
              (1...50000).contains(microseconds) else{return nil}
        if resetState {reset()}
        let v=values,dt=Double(microseconds)/1_000_000
        let bodyX=(Double(rawX)-v[0])/134,bodyY=(Double(rawY)-v[1])/134
        let projected=orientation.project(x:bodyX,y:bodyY)
        let x=projected.x,y=projected.y
        let speed=sqrt(x*x+y*y),blend=max(0,min(1,(speed-v[5])/(v[6]-v[5])))
        let alpha=1-exp(-dt/(0.008-0.006*blend))
        fx+=alpha*(x-fx);fy+=alpha*(y-fy)
        if slackX==0 && slackY==0 {ix=0;iy=0;meanSpeed=0;intentTime=0}
        let a=1-exp(-dt/0.15)
        ix+=a*(fx-ix);iy+=a*(fy-iy);meanSpeed+=a*(speed-meanSpeed)
        let mean=sqrt(ix*ix+iy*iy)
        intentTime=mean>0.45 && mean>meanSpeed*0.8 ? min(0.3,intentTime+dt) : max(0,intentTime-dt*3)
        let active=speed>0.45 && intentTime>=0.25
        slackX+=fx*dt;slackY+=fy*dt
        var magnitude=sqrt(slackX*slackX+slackY*slackY),stepX=0.0,stepY=0.0
        if !active && (magnitude<=v[8] || speed<=v[10]) {
            let decay=exp(-dt/v[9]);slackX*=decay;slackY*=decay;magnitude*=decay
        }
        if magnitude>v[8] {
            let excess=(magnitude-v[8])/magnitude
            stepX=slackX*excess;stepY=slackY*excess;slackX-=stepX;slackY-=stepY
        }
        var scale=v[4]+(1-v[4])*blend*blend*(3-2*blend)
        let highX=stepX*v[2]*scale*v[11]
        if held {scale*=v[7]}
        fractionX+=stepX*v[2]*scale*v[11];fractionY+=stepY*v[2]*v[3]*scale*v[12]
        let countX=Int(fractionX.rounded(.towardZero)),countY=Int(fractionY.rounded(.towardZero))
        fractionX-=Double(countX);fractionY-=Double(countY)
        let tunedX=max(-4095,min(4095,countX)),tunedY=max(-4095,min(4095,countY))
        guard path == .direct else {
            return .init(x:tunedX,y:tunedY,intent:active,angularX:x*v[11],angularY:y*v[12],highX:highX,stopX:tunedX,stopY:tunedY,
                         highY:stepY*v[2]*v[3]*(v[4]+(1-v[4])*blend*blend*(3-2*blend))*v[12])
        }
        // Direct: the same calibrated, projected rate (x, y), gain, vertical gain
        // and held choice as above, applied to every reading as it arrives.
        let gain=v[2]*(held ? v[7] : 1)
        let smoothing=1-exp(-dt/Self.directSmoothing)
        smoothX+=smoothing*(x-smoothX);smoothY+=smoothing*(y-smoothY)
        // Ethan: keep direct normal movement, restore tiny-motion stopping.
        // Reuse the existing slow-speed boundary; click timing keeps tuned quiet counts.
        let smoothSpeed=sqrt(smoothX*smoothX+smoothY*smoothY)
        let knee=v[5]>0 ? min(1,max(0,(smoothSpeed-v[5])/(v[5]*(Self.directKneeFactor-1)))) : 1
        // The 60 ms fine-motion escape mistook low-level hand drift for aiming.
        // Restore the original quiet-stop floor; normal smoothing and gain stay unchanged.
        // Restore the original speed-based sensitivity curve, not its radial
        // slack or drift decay: fine aiming is precise, broad travel is fast.
        let response=v[4]+(1-v[4])*blend*blend*(3-2*blend)
        let amount=knee
        let step=min(dt,Self.directMaxStep)*response*amount
        if amount==0 {directX=0;directY=0}
        else {
            directX+=smoothX*step*gain*v[11];directY+=smoothY*step*gain*v[3]*v[12]
        }
        let directCountX=Int(directX.rounded(.towardZero)),directCountY=Int(directY.rounded(.towardZero))
        directX-=Double(directCountX);directY-=Double(directCountY)
        return .init(x:max(-4095,min(4095,directCountX)),y:max(-4095,min(4095,directCountY)),intent:active,
                     angularX:x*v[11],angularY:y*v[12],highX:smoothX*step*v[2]*v[11],stopX:tunedX,stopY:tunedY,highY:smoothY*step*v[2]*v[3]*v[12])
    }
    private func fineMovement(speed:Double,knee:Double,dt:Double)->Bool {
        guard knee<1,speed>Self.fineFloor else {fineSamples=[];fineDuration=0;return false}
        fineSamples.append((smoothX*dt,smoothY*dt,dt));fineDuration+=dt
        while fineSamples.count>1,fineDuration-fineSamples[0].time>=Self.fineConfirmation {
            fineDuration-=fineSamples.removeFirst().time
        }
        let x=fineSamples.reduce(0){$0+$1.x},y=fineSamples.reduce(0){$0+$1.y}
        let distance=hypot(x,y),travel=fineSamples.reduce(0){$0+hypot($1.x,$1.y)}
        let aligned=distance>0 && (smoothX*x+smoothY*y)>=0.85*speed*distance
        guard travel>0,distance/travel>=0.85,aligned else {
            fineSamples=[(smoothX*dt,smoothY*dt,dt)];fineDuration=dt;return false
        }
        return fineDuration>=max(0,Self.fineConfirmation-dt)
    }

}


/// Where the wand's next pointer event starts.
///
/// Posted CGEvents reach the cursor asynchronously, so `CGEvent(source:nil)`
/// can still report a point the wand already moved away from. Separate rapid
/// `receiveText` batches each read it afresh: on 2026-10-30 a batch 0.1 ms
/// after two moves read the pre-move origin (2103,746) again and its +9,-8
/// move landed at 2112,738, 22 px back ("it's jumping back to its original
/// position"). The receiver remembers the points it just posted (and the
/// origin they started from). When the system reports one of those, that is
/// only our own lag: continue from the latest posted point. Anything else (a
/// physical mouse, a warp, another app) is adopted at once. After a recenter
/// warp, the centre wins until macOS reports it or `settle` passes
/// (2026-10-29: "It came to the center and then it jumped back").
/// Nothing is delayed, buffered or replayed; it only chooses the origin.
struct WandPointerOrigin {
    /// Own posted points older than this are forgotten; the system is then trusted.
    static let horizon=0.25
    static let settle=0.5
    static let tolerance:CGFloat=1
    static let maximumTrail=128
    private var trail:[(point:CGPoint,time:Double)]=[]
    private var forcedUntil = -Double.infinity
    /// The last point the wand posted, while it is still remembered.
    var latest:CGPoint? {trail.last?.point}
    private static func near(_ a:CGPoint,_ b:CGPoint)->Bool {abs(a.x-b.x)<=tolerance && abs(a.y-b.y)<=tolerance}
    /// A recenter warp: the centre is the origin until macOS reports it.
    mutating func begin(at center:CGPoint,now:Double){trail=[(center,now)];forcedUntil=now+Self.settle}
    /// The point the next pointer event starts from.
    mutating func origin(system:CGPoint,now:Double)->CGPoint {
        if now<=forcedUntil, let centre=trail.last {
            if Self.near(system,centre.point) {forcedUntil = -.infinity}
            return centre.point
        }
        trail.removeAll {now-$0.time>Self.horizon}
        guard let latest=trail.last, trail.contains(where:{Self.near($0.point,system)}) else {
            trail.removeAll()
            return system
        }
        return latest.point
    }
    /// One posted move, from where it started to where it put the pointer.
    mutating func moved(from start:CGPoint,to end:CGPoint,now:Double) {
        if !(trail.last.map {Self.near($0.point,start)} ?? false) {trail.append((start,now))}
        trail.append((end,now))
        if trail.count>Self.maximumTrail {trail.removeFirst(trail.count-Self.maximumTrail)}
    }
    mutating func cancel(){trail.removeAll();forcedUntil = -.infinity}
}

/// The single eligibility rule for stop-to-click, named so a no-click report
/// says which state blocks it. Nil means clicks may arm.
enum WandClickGate {
    static func blocker(recordingPaused:Bool,mouseButtonHeld:Bool,buttons:Int,hudSession:Bool,hudShown:Bool,scrollActive:Bool,hudOperating:Bool=false)->String? {
        if recordingPaused {return "recording"}
        // Legacy status.json/log value for the mouse button (formerly Bottom);
        // kept so existing readers and recorded logs still match.
        if mouseButtonHeld {return "bottom held"}
        if buttons != 0 {return "button down"}
        // Ethan: follow-on clicking is independent of an open HUD. Suppress
        // clicks only while the HUD button is actually operating its selected card.
        if hudSession && hudOperating {return "hud operating"}
        if scrollActive {return "scroll"}
        return nil
    }
}

/// Short second release recenters; a held second press remains a real drag.
final class WandRecenterGesture {
    private var pressedAt:Double?,lastRelease:Double?,second=false
    /// Ethan's "double click with the second one held" is a deliberate drag.
    /// A short second release still belongs to the existing recenter gesture.
    var isSecondPress:Bool {pressedAt != nil && second}
    func cancel(){pressedAt=nil;lastRelease=nil;second=false}
    func edge(down:Bool,now:Double,eligible:Bool=true)->Bool {
        guard eligible else{cancel();return false}
        if down {
            guard pressedAt==nil else{return false}
            second=lastRelease.map{now-$0>=0 && now-$0<=0.3} ?? false
            pressedAt=now;return false
        }
        guard let start=pressedAt else{return false}
        pressedAt=nil
        guard now-start>=0 && now-start<0.22 else{lastRelease=nil;second=false;return false}
        if second {lastRelease=nil;second=false;return true}
        lastRelease=now;return false
    }
}

/// Ethan's mouse-button triple-click screenshot shortcut. A click is the existing
/// short press (under 220 ms) and each further press follows the previous
/// release within the double click's 300 ms window. A held press is never a
/// click, so tap-then-hold remains the explicit drag. A gap under 30 ms is
/// switch bounce and starts a fresh run instead. The third press is recognised
/// on its down edge; the caller consumes its release. Nothing here moves,
/// buffers or delays the pointer.
struct WandTripleClick {
    enum Event {case none,first,third}
    static let window=0.3,tapSeconds=0.22,bounceSeconds=0.03
    private var clicks=0
    private var pressedAt:Double?,lastRelease:Double?
    mutating func cancel(){clicks=0;pressedAt=nil;lastRelease=nil}
    /// `.first` marks the press that starts a possible run, before any of its
    /// side effects; `.third` is the shortcut itself.
    mutating func edge(down:Bool,now:Double)->Event {
        if down {
            guard pressedAt==nil else{return .none}
            let gap=lastRelease.map{now-$0} ?? -1
            let continues=gap>=Self.bounceSeconds && gap<=Self.window
            if continues && clicks==2 {cancel();return .third}
            pressedAt=now
            if continues {return .none}
            clicks=0;lastRelease=nil;return .first
        }
        guard let start=pressedAt else{return .none}
        pressedAt=nil
        let held=now-start
        if held>=0 && held<Self.tapSeconds {clicks+=1;lastRelease=now}
        else {clicks=0;lastRelease=nil}
        return .none
    }
}

/// Ethan's screenshot mode: "the mouse should move around, even if I wasn't in
/// mouse mode ... you click the bottom button once ... that starts the hold ...
/// when you stop moving it ... that's when we end the drag of the screenshot".
/// Pure ownership state for the receiver. It owns the pointer and the mouse button only
/// while Agentic Mouse's native selection is active, or while a triple-click
/// start waits for it, and never changes the ordinary mouse-follow choice.
///
/// `settle` is a separately owned WandDwellClick: the same stop-to-click
/// algorithm and timing (0.2 s pause after 12 counts of travel), so ending the
/// selection adds no new delay, and the ordinary dwell, which may already be
/// armed, can never end it. A latched drag ends exactly once: by `settle`, by a
/// fresh mouse button press, or by any cancellation (`end`). Physical release of the
/// latching tap never ends it.
/// Ethan (2026-10-30): "triple click enters like normal screenshot mode and
/// it just like enters native macOS screenshot mode and then I just click and
/// hold the mouse button to drag and drop the area naturally". While macOS's
/// own selector is up, the wand aims the pointer (even with mouse follow off)
/// and the wand's mouse button is the native mouse button: down presses, held motion drags, up lets go
/// and macOS captures. Nothing is pressed, finished or repeated automatically.
final class WandScreenshotGesture {
    enum Phase {case idle,pending,aiming,dragging,done}
    /// Previously Bottom.
    enum MouseButton {case pass,consumed,press,release}
    /// Agentic Mouse must report its native selection this soon after a
    /// triple-click request; the wand's motion telemetry must keep arriving.
    static let startSeconds=2.0,telemetrySeconds=0.8
    private(set) var phase:Phase = .idle
    private(set) var shortcut=false
    /// The mouse button is physically down inside screenshot mode, waiting for the
    /// selector before it presses.
    private(set) var pressHeld=false
    /// The press that entered screenshot mode (the triple-click's third, or
    /// one held as the selection started). Its release is never an ordinary
    /// mouse-button edge, even after the mode has ended.
    private(set) var consumeRelease=false
    private(set) var since=0.0,lastTelemetry=0.0
    var ownsPointer:Bool {phase == .pending || phase == .aiming || phase == .dragging}
    var dragging:Bool {phase == .dragging}
    /// Triple-click: the native selection was requested. The third press is
    /// consumed; a fresh press drags.
    func requestShortcut(now:Double)->Bool {
        guard phase == .idle else{return false}
        phase = .pending;shortcut=true;pressHeld=false;consumeRelease=true;since=now;lastTelemetry=now
        return true
    }
    /// Agentic Mouse reports an active native selection. Its repeated heartbeat
    /// never resets progress; a spent (`done`) selection is never re-entered.
    /// True when this call hands the pointer to screenshot aiming.
    func contextActive(now:Double,pressed:Bool)->Bool {
        switch phase {
        case .idle:
            phase = .aiming;shortcut=false;pressHeld=false;consumeRelease=consumeRelease || pressed
        case .pending:
            phase = .aiming
        default: return false
        }
        since=now;lastTelemetry=now;return true
    }
    func telemetry(now:Double){if ownsPointer {lastTelemetry=now}}
    /// Why screenshot mode must return the pointer now, if it must.
    func expired(now:Double)->String? {
        if phase == .pending && now-since>Self.startSeconds {return "native start timed out"}
        if ownsPointer && now-lastTelemetry>Self.telemetrySeconds {return "telemetry lost"}
        return nil
    }
    /// The release of a consumed triple-click press that could not start.
    func holdRelease(){consumeRelease=true}
    /// One mouse-button edge. Down asks to press (once the selector shows); up
    /// lets go of a drag. Everything else in screenshot mode is consumed.
    /// Previously bottom(down:).
    func mouseButton(down:Bool)->MouseButton {
        guard ownsPointer else {
            if !down && consumeRelease {consumeRelease=false;return .consumed}
            if down {consumeRelease=false}
            return .pass
        }
        if down {
            consumeRelease=false
            guard phase != .dragging else{return .consumed}
            pressHeld=true;return .press
        }
        if consumeRelease {consumeRelease=false;pressHeld=false;return .consumed}
        pressHeld=false
        return phase == .dragging ? .release : .consumed
    }
    /// macOS shows the selector and the mouse button is down: the receiver presses at the shown pointer.
    func latch(now:Double)->Bool {
        guard phase == .aiming,pressHeld else{return false}
        phase = .dragging;since=now
        return true
    }
    /// Return the pointer. True when a native button-down must be lifted.
    /// While the native selection is still active the mode is spent (`done`).
    @discardableResult
    func end(contextActive:Bool,forgetPress:Bool=false)->Bool {
        let wasDragging=phase == .dragging
        // A press still down when the mode ends: its release stays consumed.
        if wasDragging || pressHeld {consumeRelease=true}
        phase = contextActive && phase != .idle ? .done : .idle
        shortcut=false;pressHeld=false
        if forgetPress {consumeRelease=false}
        return wasDragging
    }
}

/// A fast upward cue followed by its slow return scrolls up in released-button
/// HIGH mode. No sample buffer: only the recognised gesture owns the pointer.
final class WandFlickScroll {
    struct Result {let consumesPointer:Bool;let lines:Int32}
    private enum Phase {case idle, flick, armed, scrolling}
    private var phase:Phase = .idle
    private var start=0.0,lastMotion=0.0,travel=0.0,fraction=0.0
    var active:Bool {phase != .idle}
    func reset(){phase = .idle;start=0;lastMotion=0;travel=0;fraction=0}
    func sample(x:Double,y:Double,dt:Double,now:Double,eligible:Bool)->Result {
        let none=Result(consumesPointer:false,lines:0)
        guard eligible,x.isFinite,y.isFinite,dt>0,dt<=0.05,now.isFinite else{reset();return none}
        let upward=y < -55 && abs(y)>abs(x)*1.5
        if upward {
            if phase != .flick {phase = .flick;start=now;travel=0;fraction=0}
            travel += -y*dt;lastMotion=now
            return .init(consumesPointer:true,lines:0)
        }
        guard phase != .idle else{return none}
        if abs(x)>max(15,abs(y)*1.5) || y>55 {reset();return none}
        if phase == .flick {
            if y < -12 && now-start<=0.35 {travel += -y*dt;lastMotion=now;return .init(consumesPointer:true,lines:0)}
            guard travel>=3,now-start<=0.35 else{reset();return none}
            phase = .armed;lastMotion=now
        }
        if y>=1.5 && y<=40 {
            // Begin on the first deliberate return sample, without waiting for
            // enough fractional travel to fill the first native wheel line.
            if phase != .scrolling {fraction=1}
            phase = .scrolling;lastMotion=now
            fraction += y*dt*1.6
            let lines=Int32(min(12,fraction.rounded(.towardZero)))
            fraction -= Double(lines)
            return .init(consumesPointer:true,lines:lines)
        }
        let timeout=phase == .armed ? 0.6 : 0.25
        if now-lastMotion>timeout {reset();return none}
        return .init(consumesPointer:true,lines:0)
    }
}

/// The menu and file watcher use this same store. Unrelated flags survive edits.
final class WandUserOptions {
    let url:URL
    init(url:URL){self.url=url}
    func read()->[String:Any] {
        guard let data=try? Data(contentsOf:url),data.count<4096,
              let value=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return [:]}
        return value
    }
    func enabled(_ key:String)->Bool {(read()[key] as? Bool)==true}
    func set(_ key:String,_ enabled:Bool)throws {try setValue(key,enabled)}
    func setValue(_ key:String,_ setting:Any)throws {
        var value=read();value[key]=setting
        let data=try JSONSerialization.data(withJSONObject:value,options:[.sortedKeys])
        try data.write(to:url,options:.atomic)
    }
}

/// Control schemes are independent of the hardware prototype. Unknown persisted
/// values fall back to V1 so an older installation retains its known behavior.
enum WandControlVersion:Int {
    case pointerV1=1,scrollV2=2,sustainedV3=3
    var usesHeldScroll:Bool {self != .pointerV1}
    static func read(_ value:Any?)->WandControlVersion {
        guard let n=value as? NSNumber,CFGetTypeID(n) != CFBooleanGetTypeID(),let v=WandControlVersion(rawValue:n.intValue),n.doubleValue==Double(n.intValue) else{return .pointerV1}
        return v
    }
}

/// Ethan's "drag up or down or left or right ... if I keep it held down ... it
/// keeps scrolling ... ideally at the same speed as the initial drag ... until I
/// let go". Vertical/diagonal page strokes latch their representative speed while
/// the hand rests; another deliberate stroke changes it. Same-direction page
/// flicks add speed. Sideways native gestures instead end with the measured
/// stroke, so the app can accept Back/Forward without waiting for button release.
/// Tremor, slow drift, end-of-stroke recoil, follow-through and one-reading knocks
/// are not new strokes. No circle classifier runs.
///
/// This sets wheel velocity only. The pointer stays at its anchor; nothing here
/// delays, buffers or replays pointer motion. The 40 ms average shapes only how
/// quickly the wheel speed follows the hand during a stroke.
final class WandSustainedScroll {
    struct Tuning {
        /// Seconds: exponential average of the angular rate, for wheel speed only.
        var smoothing=0.04
        /// Averaged degrees per second below which the hand is resting.
        var restSpeed=2.5
        /// Averaged peak degrees per second that a stroke must reach.
        var strokeSpeed=6.0
        /// Degrees of straight travel for the first stroke, then for any stroke
        /// that changes an established velocity.
        var firstTravel=0.6,changeTravel=0.8
        var minimumSeconds=0.03
        /// Net travel / path length: wobble goes back and forth.
        var straightness=0.6
        /// cos(60 degrees): turning further from a stroke's direction ends it.
        var turnCosine=0.5
        /// A stroke ends when its averaged rate falls below this share of its peak.
        var endShare=0.35
        /// A same-direction restroke takes its own speed after passing its peak.
        var settleShare=0.7
        /// A same-direction restroke must rise to this multiple of its starting
        /// rate, so a stroke's decaying or creeping tail never lowers its speed.
        var riseFactor=2.5
        /// A direction change starting this soon after a stroke ends is probably
        /// recoil: it needs this share of that stroke's travel, within a bound.
        var recoilSeconds=0.4,recoilShare=0.55,recoilMaxTravel=3.0
        /// tan(30 degrees): a stroke closer than this to an axis scrolls only that axis.
        var axisSnap=0.577
        /// Output directions this close keep the established direction.
        var sameDirectionCosine=0.9
        /// Averaged motion within this cosine of the scroll direction is its tail.
        var forwardCosine=0.7
        /// Receiver seconds without readings that end the current measurement.
        var gapSeconds=0.25
        /// Base speed mapping: min(ordinaryMaxRate, stroke speed x lines per
        /// degree). Page fine control scales its low end below the plateau.
        var ordinaryMaxRate=120.0
        /// Ethan found page scrolling too fast at low speed after the wheel
        /// transport change. Ease small page strokes in at half gain, reaching
        /// the original mapping by its plateau. Horizontal history gestures
        /// retain their independently tested curve; this adds no input delay.
        var pageLowSpeedGain=0.5
        /// Ethan, 2026-10-31: "sensitivity at low scroll speed or maybe overall
        /// can still be faster". Increase the earlier 1.3 gain to 1.7, including each added flick
        /// and the ceiling, without changing stroke recognition or sideways
        /// history gestures. The gentle low-speed curve keeps the same shape.
        var pageSensitivity=1.7
        /// Ethan, 2026-10-30: "the highest isn't fast enough ... it should be
        /// like much faster if you want to do like a huge scroll", then "I just
        /// wanted to add like extra sensitivity at the faster speeds. Did you
        /// have to change like the normal behavior?" Only strokes faster than
        /// highSpeedFrom (degrees per second) exceed the original mapping. The
        /// extra rate starts flat and grows with the square of the excess,
        /// reaching maxRate at highSpeedFull.
        var highSpeedFrom=120.0,highSpeedFull=240.0
        /// Page (vertical and diagonal) wheel lines per second at highSpeedFull.
        /// Ethan, 2026-10-30: the maximum page scroll was still "not enough",
        /// with no change asked to the normal range: 600 became 1200. Everything up
        /// to highSpeedFrom, including the 120 plateau, is unchanged.
        var maxRate=1200.0
        /// The extension top under the horizontal gain, kept at the validated
        /// Receiver 135 value so sideways swipes keep exactly that strength.
        var horizontalCurveMaxRate=600.0
        /// Ethan, 2026-10-30, on the native Back/Forward edge peek: "it's just
        /// not sensitive enough when doing those trackpad swipes". A stroke that
        /// scrolls only horizontally gets up to this multiple of the vertical
        /// rate above, never beyond horizontalMaxRate, and never below the page
        /// rate. Vertical and diagonal strokes keep the page curve exactly. It scales velocity only: same timing,
        /// no buffer, no catch-up. The receiving app still decides scroll or history.
        /// After the 2.5x build worked in Chrome but needed "extreme swipe radii",
        /// Ethan asked for "maybe five times" more: 12.5, and a ceiling five times
        /// the shared maxRate, so stronger strokes are not clamped back to 600.
        var horizontalGain=12.5
        /// Horizontal-only wheel lines per second (30,000 points per second).
        /// Separate from the page maxRate for vertical and diagonal.
        var horizontalMaxRate=3000.0
        /// Degrees per second: the extra horizontal rate eases in (smoothstep)
        /// from none at horizontalGainFrom to all of it at horizontalGainFull, so
        /// fine horizontal strokes keep the ordinary mapping.
        var horizontalGainFrom=8.0,horizontalGainFull=30.0
        /// tan(20 degrees): a stroke this close to level gets all of it. It fades
        /// to none at the axisSnap boundary, where diagonal scrolling begins, so
        /// the rate is continuous across that boundary.
        var horizontalGainLevelSlope=0.364
    }
    /// Counts for the opt-in per-hold diagnostic line. No positions or coordinates.
    struct Summary:Equatable {
        var strokes=0,directionChanges=0,speedChanges=0,ignoredRecoils=0
        var peakRate=0.0
    }
    /// Native sideways swipes end at the measured stroke's end, while the
    /// physical button can stay held for another distinct swipe.
    enum HorizontalBoundary {case ended,cancelled}
    private var horizontalBoundary:HorizontalBoundary?
    func takeHorizontalBoundary()->HorizontalBoundary? {defer{horizontalBoundary=nil};return horizontalBoundary}
    private(set) var velocityX=0.0,velocityY=0.0
    private(set) var summary=Summary()
    let tuning:Tuning
    static let pagePixelsPerLine=10.0
    private var fractionX=0.0,fractionY=0.0,lastTick=0.0
    // The initial credit is one output unit: a pixel for page output, one line
    // for the existing default/horizontal path. It must not become a page jump.
    private var initialX=0.0,initialY=0.0
    // Averaged angular rate, device-sample clock and last receiver arrival.
    private var rateX=0.0,rateY=0.0,averaging=false,clock=0.0,lastArrival:Double?
    // Candidate movement since it last started, restarted or turned.
    private var moving=false,moveX=0.0,moveY=0.0,movePath=0.0,moveTime=0.0
    private var movePeak=0.0,moveFloor=0.0,moveStart=0.0,moveLargestStep=0.0,moveCountedRecoil=false
    // The committed stroke while the hand is still making it.
    private var stroking=false,settling=false,keepOutput=false
    private var directionX=0.0,directionY=0.0,outputX=0.0,outputY=0.0
    private var strokeX=0.0,strokeY=0.0,peak=0.0,base=0.0
    // The most recent finished stroke, for recoil rejection.
    private var endedAt = -Double.infinity,endedTravel=0.0
    private let linesPerDegree:Double
    init(linesPerDegree:Double=1.6,tuning:Tuning=Tuning()){self.linesPerDegree=linesPerDegree;self.tuning=tuning}
    var started:Bool {velocityX != 0 || velocityY != 0}
    var horizontalStrokeActive:Bool {stroking && velocityX != 0 && velocityY == 0}
    func reset(now:Double=0){
        velocityX=0;velocityY=0;summary=Summary();fractionX=0;fractionY=0;initialX=0;initialY=0;lastTick=now;horizontalBoundary=nil
        rateX=0;rateY=0;averaging=false;clock=0;lastArrival=nil
        moving=false;stroking=false;settling=false;keepOutput=false;strokeX=0;strokeY=0;peak=0;base=0
        endedAt = -Double.infinity;endedTravel=0
    }
    /// One held reading: screen-corrected angular rate in degrees per second, its
    /// device interval, and optionally the receiver arrival time for gap detection.
    func sample(x:Double,y:Double,dt:Double,now:Double?=nil){
        guard x.isFinite,y.isFinite,dt>0,dt<=0.05 else{return}
        if let now,now.isFinite {
            // Readings missing in transit: do not join motion across the gap.
            if let last=lastArrival,now-last>tuning.gapSeconds {interrupt()}
            lastArrival=now
        }
        clock+=dt
        if averaging {let a=1-exp(-dt/tuning.smoothing);rateX+=a*(x-rateX);rateY+=a*(y-rateY)}
        else {rateX=x;rateY=y;averaging=true}
        let speed=hypot(rateX,rateY)
        if stroking {
            continueStroke(x:x,y:y,dt:dt,speed:speed)
            if stroking {return}
        }
        track(x:x,y:y,dt:dt,speed:speed)
    }
    private func interrupt(){
        if stroking {finishStroke(cancelled:true)}
        moving=false;averaging=false
    }
    private func continueStroke(x:Double,y:Double,dt:Double,speed:Double){
        strokeX+=x*dt;strokeY+=y*dt
        var along=rateX*directionX+rateY*directionY
        if along>=peak {
            // Still accelerating: the growing stroke refines a direction that its
            // first fraction of a degree, or slow drift, may have skewed.
            let distance=hypot(strokeX,strokeY)
            if distance>0 {
                directionX=strokeX/distance;directionY=strokeY/distance
                along=rateX*directionX+rateY*directionY
                if !keepOutput {
                    let output=snapped(directionX,directionY)
                    if output.x==0 {fractionX=0;initialX=0}
                    if output.y==0 {fractionY=0;initialY=0}
                    outputX=output.x;outputY=output.y
                }
            }
            peak=max(peak,along);apply()
        }
        let turned=speed>tuning.restSpeed && along<tuning.turnCosine*speed
        if along<max(tuning.restSpeed,tuning.endShare*peak) || turned {
            // Use the existing stroke-end test, with no additional timer or delay.
            // The average decelerates before it crosses zero on a reversal.
            // Classify that boundary from the real incoming direction, using
            // the existing stroke-speed/turn thresholds, so reversal cancels.
            let incomingSpeed=hypot(x,y)
            let incomingTurn=incomingSpeed>=tuning.strokeSpeed && x*directionX+y*directionY<tuning.turnCosine*incomingSpeed
            finishStroke(cancelled:turned || incomingTurn);return
        }
        if settling && along<tuning.settleShare*peak {settling=false;apply()}
    }
    private func finishStroke(cancelled:Bool=false){
        stroking=false;endedAt=clock;endedTravel=max(0,strokeX*directionX+strokeY*directionY)
        if settling {settling=false;apply()}
        if velocityX != 0 && velocityY == 0 {
            horizontalBoundary=cancelled ? .cancelled:.ended
            fractionX=0;fractionY=0;initialX=0;initialY=0
        }
    }
    /// Wheel lines per second for a stroke's representative speed. Continuous
    /// and rising; it sets velocity only, so it adds no delay or catch-up.
    func linesPerSecond(peak:Double)->Double {
        let rate=curve(peak:peak,top:tuning.maxRate)
        let full=linesPerDegree>0 ? tuning.ordinaryMaxRate/linesPerDegree : 0
        let u=full>0 ? min(1,max(0,peak/full)):1
        let gentle=min(1,max(0,tuning.pageLowSpeedGain))
        return rate*(gentle+(1-gentle)*u*u*(3-2*u))*tuning.pageSensitivity
    }
    /// Base mapping before the page-only fine-control adjustment.
    private func curve(peak:Double,top:Double)->Double {
        let ordinary=min(tuning.ordinaryMaxRate,max(0,peak)*linesPerDegree)
        guard peak>tuning.highSpeedFrom,tuning.highSpeedFull>tuning.highSpeedFrom,top>ordinary else{return ordinary}
        let excess=min(1,(peak-tuning.highSpeedFrom)/(tuning.highSpeedFull-tuning.highSpeedFrom))
        return ordinary+(top-ordinary)*excess*excess
    }
    /// Wheel lines per second for a stroke whose output is horizontal only.
    /// `slope` is |vertical/horizontal| of the stroke itself. Never below the
    /// page rate for the same speed (so it is continuous with diagonal output at
    /// the snap boundary) and never above horizontalMaxRate (unless the page
    /// rate is); non-decreasing in speed, so it changes no timing and adds no catch-up.
    func horizontalLinesPerSecond(peak:Double,slope:Double=0)->Double {
        // Horizontal tuning retains the pre-page-adjustment floor.
        let page=curve(peak:peak,top:tuning.maxRate)
        guard peak.isFinite,!slope.isNaN,tuning.horizontalGain>1 else{return page}
        let ordinary=curve(peak:peak,top:tuning.horizontalCurveMaxRate)
        let span=tuning.horizontalGainFull-tuning.horizontalGainFrom
        let rise=span>0 ? min(1,max(0,(peak-tuning.horizontalGainFrom)/span)) : (peak>=tuning.horizontalGainFull ? 1:0)
        let edge=tuning.axisSnap-tuning.horizontalGainLevelSlope
        let level=edge>0 ? min(1,max(0,(tuning.axisSnap-abs(slope))/edge)) : (abs(slope)<tuning.axisSnap ? 1:0)
        let gain=1+(tuning.horizontalGain-1)*rise*rise*(3-2*rise)*level
        return max(page,ordinary,min(max(ordinary,tuning.horizontalMaxRate),ordinary*gain))
    }
    private func apply(){
        // Pure horizontal output keeps its separate history-swipe curve;
        // vertical and diagonal page output use gentle low-speed control.
        let horizontal=outputY==0 && outputX != 0
        let rate=horizontal ? horizontalLinesPerSecond(peak:peak,slope:directionX != 0 ? abs(directionY/directionX) : .infinity) : linesPerSecond(peak:peak)
        // Ethan's same-direction flick adds to the held page speed and keeps
        // that increment after its decelerating tail. `base` is captured once
        // per qualified stroke, never once per sample, so noise cannot pump it.
        // Sideways history gestures keep their existing replace-speed semantics.
        let magnitude:Double
        if !horizontal && keepOutput {
            magnitude=min(tuning.maxRate*tuning.pageSensitivity,base+rate)
        } else {
            magnitude=settling ? max(base,rate):rate
        }
        if velocityX != 0 && velocityY == 0 && !horizontal {horizontalBoundary = .cancelled}
        velocityX=outputX*magnitude;velocityY=outputY*magnitude
        summary.peakRate=max(summary.peakRate,magnitude)
    }
    private func track(x:Double,y:Double,dt:Double,speed:Double){
        guard speed>=tuning.restSpeed else{moving=false;return}
        let velocity=hypot(velocityX,velocityY)
        let forward=velocity>0 && rateX*velocityX+rateY*velocityY>=tuning.forwardCosine*speed*velocity
        if moving {
            let distance=hypot(moveX,moveY)
            let turned=distance>0.1 && rateX*moveX+rateY*moveY<tuning.turnCosine*speed*distance
            // Restart at each new low so a candidate measures a fresh rise, not
            // drift banked while resting. Along the current scroll this applies
            // throughout, so the previous stroke's tail never sets a new speed.
            if turned || (speed<moveFloor && (forward || movePeak<tuning.strokeSpeed)) {moving=false}
        }
        if !moving {
            moving=true;moveX=0;moveY=0;movePath=0;moveTime=0;movePeak=0
            moveFloor=speed;moveStart=clock;moveLargestStep=0;moveCountedRecoil=false
        }
        let step=hypot(x,y)*dt
        moveX+=x*dt;moveY+=y*dt;movePath+=step;moveTime+=dt;moveLargestStep=max(moveLargestStep,step)
        let distance=hypot(moveX,moveY)
        guard distance>0 else{return}
        movePeak=max(movePeak,(rateX*moveX+rateY*moveY)/distance)
        guard moveTime>=tuning.minimumSeconds,movePeak>=tuning.strokeSpeed,distance>=tuning.straightness*movePath else{return}
        let unitX=moveX/distance,unitY=moveY/distance
        let output=snapped(unitX,unitY)
        let same=velocity>0 && (output.x*velocityX+output.y*velocityY)/velocity>=tuning.sameDirectionCosine
        if same && movePeak<tuning.riseFactor*moveFloor {return}
        var required=velocity>0 ? tuning.changeTravel : tuning.firstTravel
        let change=velocity>0 && !same
        if change && moveStart-endedAt<=tuning.recoilSeconds {
            required=max(required,min(tuning.recoilMaxTravel,tuning.recoilShare*endedTravel))
        }
        // One reading cannot supply most of a stroke: a knock is not a drag.
        guard distance>=required,distance-moveLargestStep>=0.5*required else{
            if change && distance>=tuning.changeTravel && !moveCountedRecoil {moveCountedRecoil=true;summary.ignoredRecoils+=1}
            return
        }
        moving=false;stroking=true;directionX=unitX;directionY=unitY;strokeX=moveX;strokeY=moveY;peak=movePeak
        summary.strokes+=1
        if same {
            // Same direction: snapshot speed once; page flicks add to it without a dip.
            outputX=velocityX/velocity;outputY=velocityY/velocity;base=velocity;settling=true;keepOutput=true
            summary.speedChanges+=1
        } else {
            if velocity>0 {summary.directionChanges+=1}
            outputX=output.x;outputY=output.y;base=0;settling=false;keepOutput=false
            // A new direction never inherits fractional travel from the old one;
            // the travel already made pays for its first line at the next tick.
            fractionX=0;fractionY=0;initialX=output.x;initialY=output.y
        }
        apply()
    }
    private func snapped(_ x:Double,_ y:Double)->(x:Double,y:Double){
        if abs(x)<abs(y)*tuning.axisSnap {return (0,y<0 ? -1:1)}
        if abs(y)<abs(x)*tuning.axisSnap {return (x<0 ? -1:1,0)}
        return (x,y)
    }
    /// The opt-in diagnostic line: counts and wheel rates only, never positions.
    func report(seconds:Double,ended:String)->String {
        let rate=hypot(velocityX,velocityY)
        let axis=rate==0 ? "none" : velocityX==0 ? "vertical" : velocityY==0 ? "horizontal" : "diagonal"
        return "ms=\(Int((seconds*1000).rounded())) end=\(ended) strokes=\(summary.strokes) directionChanges=\(summary.directionChanges) speedChanges=\(summary.speedChanges) ignoredRecoils=\(summary.ignoredRecoils) peakLinesPerSecond=\(Int(summary.peakRate.rounded())) finalLinesPerSecond=\(Int(rate.rounded())) axis=\(axis)"
    }
    func tick(now:Double,pageUnitsPerLine:Double=1)->(x:Int32,y:Int32){
        guard now.isFinite,now>=lastTick,pageUnitsPerLine.isFinite,pageUnitsPerLine>=1,pageUnitsPerLine<=1024 else{return (0,0)}
        let dt=min(0.05,now-lastTick);lastTick=now
        // Keep the last direction/rate for the existing recoil and restroke
        // classifier, but never manufacture sideways movement while held still.
        // Vertical and diagonal page scrolling retain their latched speed.
        if velocityX != 0 && velocityY == 0 && !stroking {return (0,0)}
        // Fractions stay in physical line units between ticks. Only the final
        // quantization changes: page pixels arrive at the same cadence, without
        // waiting for a whole wheel line or replaying missed timer intervals.
        let scale=velocityY == 0 ? 1:pageUnitsPerLine
        fractionX+=velocityX*dt;fractionY+=velocityY*dt
        let unitsX=fractionX*scale+initialX,unitsY=fractionY*scale+initialY
        let x=Int32(unitsX.rounded(.towardZero)),y=Int32(unitsY.rounded(.towardZero))
        fractionX=(unitsX-Double(x))/scale;fractionY=(unitsY-Double(y))/scale
        initialX=0;initialY=0
        return(x,y)
    }
}

/// Conservative evidence for a clear sideways flick before the normal hold
/// deadline. Uses the actual angular stream and the existing stroke classifier;
/// peak speed alone would accept the brief switch knocks seen in the private
/// "abrupt-stop swipes" reference. Ordinary taps keep their duration rule.
struct WandEarlyHorizontalIntent {
    private(set) var accepted=false
    private var x=0.0,y=0.0,path=0.0,largest=0.0,strongSamples=0
    mutating func sample(x dx:Double,y dy:Double,dt:Double,horizontal:Bool,eligible:Bool)->Bool {
        guard !accepted,dx.isFinite,dy.isFinite,dt>0,dt<=0.05 else{return false}
        let step=hypot(dx,dy)*dt
        x+=dx*dt;y+=dy*dt;path+=step;largest=max(largest,step)
        if abs(dx)>=40 {strongSamples+=1}
        guard eligible,horizontal,abs(x)>=4,abs(y)<abs(x)*0.577,
              abs(x)>=path*0.85,strongSamples>=4,largest<=path*0.35 else{return false}
        accepted=true;return true
    }
}

/// V2 changes only a mouse button hold. Short taps are still interpreted by the
/// existing device callback; a used/long hold must never emit its old end click.
final class WandHeldScroll {
    /// Continuous signed travel from the shared V2 direction classifier.
    private(set) var directionalTravel=0.0
    var latestTurn:Double {circle.latestTurn}
    private(set) var active=false
    private(set) var dragging=false
    private(set) var scrollable=true
    private(set) var circular=false
    private(set) var horizontal=false
    private(set) var sustaining=false
    /// Disabled by default: Ethan prefers a plain tap to exit without clicking.
    var quietStopEnabled=false
    let sustained:WandSustainedScroll
    private var scrollDirection=0.0,directionTravel=0.0,directionTravelX=0.0,sampleTime=0.0
    private var winding=0.0,windingToScroll=0.0,reverseTurn=0.0,reverseAt=0.0
    private var reverseSegments=0
    private let circle:WandCircularScroll
    private var started=0.0,confirmed=0.0,fraction=0.0,moved=false,dropClick=false,droppingClick=false
    private var earlyIntent=WandEarlyHorizontalIntent()
    var earlyHorizontal:Bool {earlyIntent.accepted}
    /// A qualified movement, not merely elapsed hold time. Even a tiny V3 stroke
    /// counts before its fractional wheel output reaches a whole pixel.
    var hasScrollGesture:Bool {moved || earlyHorizontal || (sustaining ? sustained.summary.strokes > 0 : scrollDirection != 0)}
    // Reuse the existing mouse button tap/hold cutoff; do not add a movement buffer.
    let holdSeconds:Double
    private let linesPerDegree:Double
    init(linesPerDegree:Double=1.6,holdSeconds:Double=0.22,sustainedTuning:WandSustainedScroll.Tuning=WandSustainedScroll.Tuning()){
        self.holdSeconds=holdSeconds;self.linesPerDegree=linesPerDegree
        self.sustained=WandSustainedScroll(linesPerDegree:linesPerDegree,tuning:sustainedTuning)
        var tuning=WandCircularScroll.Tuning()
        // Angular degrees, before sensitivity. Recognise the bend while the
        // wand still travels in its original vertical direction.
        tuning.verticalRatio=1;tuning.segment=0.012
        tuning.recogniseTurn=Double.pi/3;tuning.consistency=0.65
        tuning.minPath=0.18;tuning.minExtent=0.05;tuning.minAspect=0.1
        tuning.minDuration=0.06;tuning.window=1.0;tuning.idleEnd=0.35
        circle=WandCircularScroll(tuning:tuning)
    }
    func reset(){earlyIntent=WandEarlyHorizontalIntent();directionalTravel=0;sustained.reset();sustaining=false;active=false;dragging=false;resolving=false;circular=false;horizontal=false;scrollDirection=0;directionTravel=0;directionTravelX=0;sampleTime=0;winding=0;windingToScroll=0;reverseTurn=0;reverseAt=0;reverseSegments=0;circle.reset();fraction=0;moved=false;dropClick=false;droppingClick=false}
    func begin(now:Double,scrollable:Bool=true,sustain:Bool=false,resolving:Bool=false){reset();active=true;started=now;confirmed=now;self.scrollable=scrollable;self.resolving=resolving && scrollable;sustaining=sustain;sustained.reset(now:now)}
    // A lease is renewed only by actual button samples, never by a timer.
    // Stop rather than keep a native drag or scroll alive after telemetry loss.
    func confirmHeld(now:Double){if active {confirmed=now}}
    func stale(now:Double)->Bool {active && now-confirmed>0.8}
    /// Ethan's smart hold: the pointer target decides scroll or native drag.
    /// While the bounded probe is outstanding the hold behaves as a scroll
    /// (the safe fallback) and can never start a drag. A reply only applies
    /// before the existing tap/hold decision, so a late, cancelled or unknown
    /// answer never flips a hold that is already acting.
    private(set) var resolving=false
    @discardableResult
    func setTarget(scrollable:Bool,now:Double)->Bool {
        guard active,resolving,!dragging,!moved,!qualified(now:now) else{return false}
        resolving=false;self.scrollable=scrollable;return true
    }
    /// The original call shape, with the same safety: only an outstanding
    /// probe at the very start of a hold can be answered.
    @discardableResult
    func setTarget(scrollable:Bool)->Bool {setTarget(scrollable:scrollable,now:started)}
    /// At the tap/hold decision an unanswered probe settles on scrolling.
    func settleTarget(now:Double){if resolving && qualified(now:now) {resolving=false}}
    func qualified(now:Double)->Bool {active && now-started>=holdSeconds}
    func elapsed(now:Double)->Double {now-started}
    func startDrag(now:Double,immediate:Bool=false)->Bool {
        guard active,!scrollable,!resolving,!dragging,(immediate || qualified(now:now)) else{return false}
        dragging=true;return true
    }
    @discardableResult
    func end(now:Double)->Bool {
        guard active else{return false}
        active=false;dragging=false;sustained.reset();dropClick=moved || earlyHorizontal || now-started>=0.22
        fraction=0;circle.reset();circular=false;return dropClick
    }
    func sample(x:Double=0,y:Double,dt:Double,now:Double?=nil)->Int32 {
        directionalTravel=0
        guard active,scrollable,x.isFinite,y.isFinite,dt>0,dt<=0.05 else{return 0}
        // V3 measures a stroke from its first held reading, including the readings
        // before the 220 ms tap/hold decision. Only continuation() emits wheel
        // lines. A clear sideways flick can earn an earlier decision; ordinary
        // taps and every page direction keep the existing hold deadline.
        if sustaining {
            sustained.sample(x:x,y:y,dt:dt,now:now)
            if let now, !qualified(now:now) {
                _=earlyIntent.sample(x:x,y:y,dt:dt,
                    horizontal:sustained.horizontalStrokeActive && sustained.summary.strokes == 1,
                    eligible:!resolving && !dragging)
            }
            return 0
        }
        guard now.map({qualified(now:$0)}) ?? true else{return 0}
        sampleTime=now ?? sampleTime+dt
        // Ethan's "micro circles": smaller geometry below retains the same
        // quiet-rate guard, wheel gain and pointer tuning.
        guard hypot(x,y)>1 else{circle.expire(now:sampleTime);reverseTurn=0;reverseSegments=0;return 0}
        let dx=x*dt,dy=y*dt
        var travel=hypot(dx,dy)
        // Ethan's left/right start is the horizontal equivalent of up/down.
        // The first deliberate stroke chooses one axis for the entire hold;
        // sideways portions of its later circle must not switch scroll axes.
        // The first U-turn maps its winding to that direction; subsequent
        // consistent opposite winding reverses it without releasing.
        if scrollDirection==0 {
            directionTravelX+=dx;directionTravel+=dy
            if hypot(directionTravelX,directionTravel)>=0.12 {
                horizontal=abs(directionTravelX)>abs(directionTravel)
                let initialTravel=horizontal ? directionTravelX:directionTravel
                scrollDirection=initialTravel>0 ? 1:-1
                // Include the acquisition stroke once, on its chosen axis.
                directionalTravel=scrollDirection*hypot(directionTravelX,directionTravel)
                fraction=directionalTravel*linesPerDegree
                travel = 0
            }
        }
        let result=circle.update(dx:dx,dy:dy,now:sampleTime,eligible:scrollDirection != 0)
        if result.consumesPointer && !circular {
            circular=true
            winding=result.lines<0 ? 1:-1
            windingToScroll=scrollDirection*winding
        } else if circular {
            let turn=circle.latestTurn
            if turn*winding < -0.005 {
                if sampleTime-reverseAt>0.25 {reverseTurn=0;reverseSegments=0}
                reverseAt=sampleTime;reverseTurn+=abs(turn);reverseSegments+=1
                if reverseTurn>=Double.pi/6 && reverseSegments>=3 {
                    winding = -winding;scrollDirection=windingToScroll*winding
                    fraction=0;reverseTurn=0;reverseSegments=0
                }
            } else if turn*winding>0.005 {
                reverseTurn=0;reverseSegments=0
            }
        }
        // As soon as the starting direction is known, every part of the U
        // continues it. Use the same distance/gain before and after recognition;
        // the returning leg must never leak an opposite signed vertical delta.
        // Only established circular winding can subsequently reverse direction.
        // No output before axis acquisition; keep that small initial travel
        // so choosing an axis neither loses distance nor leaks onto the other.
        if scrollDirection != 0 {
            directionalTravel += scrollDirection*travel
            fraction += scrollDirection*travel*linesPerDegree
        }
        let lines=Int32(max(-12,min(12,fraction.rounded(.towardZero))))
        fraction -= Double(lines)
        if lines != 0 {moved=true}
        return lines
    }
    func continuation(now:Double,pageUnitsPerLine:Double=1)->(x:Int32,y:Int32){
        guard active,sustaining,scrollable,!stale(now:now) else{return(0,0)}
        // Early intent never opens the page-scrolling lane. Once its horizontal
        // stroke ends, tick() is already silent until another real stroke.
        guard qualified(now:now) || (earlyHorizontal && sustained.velocityX != 0 && sustained.velocityY == 0) else{return(0,0)}
        let result=sustained.tick(now:now,pageUnitsPerLine:pageUnitsPerLine)
        if result.x != 0 || result.y != 0 {moved=true}
        return result
    }
    func consumes(buttons:Int)->Bool {
        if active {return true}
        // Device reports an endpoint click as ordered down/up frames after
        // mouse-button release. Keep dropping it until its up, never the next physical tap.
        if dropClick && buttons & 1 != 0 {dropClick=false;droppingClick=true;return true}
        if droppingClick {
            if buttons & 1 == 0 {droppingClick=false}
            return true
        }
        return false
    }
}


/// What a plain mouse button hold should do with the target under the pointer,
/// judged from the Accessibility roles of the hit element and its ancestors
/// (nearest first). Restored from the earlier contextual hold, with safer
/// failure handling: only a positive answer can produce a native drag.
enum WandHoldTarget:String,Equatable {
    case scroll,drag,unknown
    /// Explicitly draggable controls and notification subroles win inside a scroll area.
    static let draggableRoles:Set<String>=["AXScrollBar","AXValueIndicator","AXSlider","AXSplitter","AXNotificationCenterAlert"]
    /// A real scrolling surface: native scroll views and web documents.
    static let scrollRoles:Set<String>=["AXScrollArea","AXWebArea"]
    /// A window/app boundary ends the search but does not prove a drag target.
    /// Custom message lists can expose AXList -> AXWindow with no AXScrollArea.
    /// Keep their ordinary hold scrolling; tap-then-hold still drags deliberately.
    static let surfaceRoles:Set<String>=["AXWindow","AXSheet","AXDrawer","AXApplication","AXMenuBar"]
    static func ends(at role:String)->Bool {
        draggableRoles.contains(role) || scrollRoles.contains(role) || surfaceRoles.contains(role)
    }
    static func classify(roles:[String])->WandHoldTarget {
        for role in roles {
            if draggableRoles.contains(role) {return .drag}
            if scrollRoles.contains(role) {return .scroll}
            if surfaceRoles.contains(role) {return .unknown}
        }
        // Empty, broken or timed-out chains prove nothing. Keep scrolling:
        // an unknown answer must never select text or move a window.
        return .unknown
    }
}

/// One bounded Accessibility probe, deliberately excluding titles, values and text.
/// The role chain and owner let a failed hold be attributed without recording chats.
struct WandHoldTargetProbe {
    var roles:[String]=[]
    var bundleIdentifier:String="unknown"
    var stop:String="unavailable"
    var error:Int=0
    var milliseconds:Int=0
    var target:WandHoldTarget {WandHoldTarget.classify(roles:roles)}
    var diagnostic:String {
        let chain=roles.prefix(24).map{String($0.prefix(64))}.joined(separator:">")
        return "app=\(bundleIdentifier.prefix(128)) roles=\(chain) stop=\(stop) error=\(error) ms=\(milliseconds)"
    }
}

/// Ethan: waking from rest must "return to the state it was on before
/// sleeping". Remember the mouse-follow choice when the wand comes to rest
/// and restore exactly that on pickup, instead of always entering mouse mode.
/// A manual mouse button choice made meanwhile wins, and the recording pause keeps
/// pointing off until recording or a manual choice ends it.
struct WandRestFollowMemory {
    private(set) var remembered:Bool?
    /// The wand has just come to rest; `following` is the choice it had.
    mutating func cameToRest(following:Bool) {remembered=following}
    /// A deliberate mouse button choice replaces whatever rest remembered.
    mutating func manualChoice() {remembered=nil}
    /// Recording starts while resting: report the choice rest is hiding so
    /// recording can resume it later, and stop rest from also restoring it.
    mutating func handOverToRecording()->Bool {defer{remembered=nil};return remembered==true}
    /// Recording ended while the wand still rests: restore on pickup instead
    /// of starting mouse mode on the desk.
    mutating func restoreOnPickup() {remembered=true}
    /// Pickup: whether to switch mouse follow back on. Always forgets.
    mutating func pickedUp(recordingPaused:Bool)->Bool {
        defer{remembered=nil}
        return !recordingPaused && remembered==true
    }
    mutating func reset() {remembered=nil}
}

/// The HUD button in an active review: tap cancels; a long press stages the working selection.
/// Ethan now calls this the "selection"; former "bucket" / "commit set"
/// mean Better Git's pending staging selection,
/// not a Git commit. Formerly a double-click action. Pointer motion is unbuffered.
struct WandReviewExitGesture {
    // The HUD button in Ethan's selected Review changes / Stage files set. A 0.5 s
    // hold stages and stays. One short click waits out the double-click
    // window (at most 0.3 s) and then exits; a second short press inside it
    // asks Agentic Mouse to toggle the set instead. That second press can
    // still be held to stage: its down alone never toggles.
    enum Release { case none, wait, toggle, commit }
    static let holdSeconds = 0.5
    static let doubleClickSeconds = 0.3
    /// Review navigation waits this long, at most, for the toggle's acknowledgement.
    static let toggleAcknowledgementSeconds = 1.0
    private var pressedAt: Double?
    private var committed = false
    private var secondPress = false
    private var toggledAt: Double?
    /// When one short click exits unless a second press arrives first.
    private(set) var tapDeadline: Double?
    /// The HUD button is down.
    var pending: Bool { pressedAt != nil }
    /// One short click is waiting for a possible second press.
    var awaitingSecond: Bool { tapDeadline != nil }
    func toggling(now: Double) -> Bool {
        guard let toggledAt else { return false }
        return now >= toggledAt && now - toggledAt < Self.toggleAcknowledgementSeconds
    }
    mutating func down(now: Double) {
        guard pressedAt == nil else { return }
        secondPress = tapDeadline.map { now <= $0 } ?? false
        tapDeadline = nil
        pressedAt = now; committed = false
    }
    mutating func commitIfHeld(now: Double) -> Bool {
        guard let pressedAt, !committed, now - pressedAt >= Self.holdSeconds else { return false }
        committed = true; return true
    }
    mutating func up(now: Double, window: Double = WandReviewExitGesture.doubleClickSeconds) -> Release {
        guard let pressedAt else { return .none }
        let second = secondPress, held = committed
        self.pressedAt = nil; committed = false; secondPress = false
        if held { return .none }
        if now - pressedAt >= Self.holdSeconds { return .commit }
        if second { return .toggle }
        tapDeadline = now + max(0, min(Self.doubleClickSeconds, window))
        return .wait
    }
    /// A waiting tap whose window has passed (its timer ran late) ends now.
    mutating func expiredTap(now: Double) -> Bool {
        guard pressedAt == nil, let tapDeadline, now > tapDeadline else { return false }
        self.tapDeadline = nil; return true
    }
    /// The tap timer for `deadline`; a superseded timer finds another or none.
    mutating func tapTimedOut(deadline: Double) -> Bool {
        guard pressedAt == nil, tapDeadline == deadline else { return false }
        tapDeadline = nil; return true
    }
    mutating func cancelTap() -> Bool {
        guard tapDeadline != nil else { return false }
        tapDeadline = nil; return true
    }
    mutating func toggleRequested(now: Double) { toggledAt = now }
    /// Agentic Mouse's change from one set to the other answers our own recent
    /// toggle; presses made since then belong to the new set.
    mutating func acknowledgeToggle(from: String?, to: String?, now: Double) -> Bool {
        guard toggling(now: now), let from, let to, from != to else { return false }
        toggledAt = nil; return true
    }
    mutating func reset() { pressedAt = nil; committed = false; secondPress = false; tapDeadline = nil; toggledAt = nil }
}

/// Ethan's "eyes mode" = Review changes; "bang mode" / "!" = Stage files.
/// Turns rough clockwise/anticlockwise loops, squares, diamonds and single
/// corners into review ratchets. Better Git owns preview and staging.
/// Screen coordinates: positive Y points down, so positive turning is clockwise
/// (next) and negative is anticlockwise (previous).
///
/// Clean 2026-10-19 redesign. Ethan: "each corner of the square... one revolution
/// does four jumps evenly spread" and "if I just wanted to flick in a clockwise
/// direction... it would just do one jump". North->east is next; east->north,
/// including the same arc straight back, is previous; north->west is previous.
/// The former detector summed signed per-packet headings with tolerance boosts,
/// so turnarounds, tremor and slow motion became missed flicks and random
/// back-and-forth. Here:
/// - Headings come only from spatial segments sized to the gesture itself, so
///   speed, Bluetooth bunching and packet count do not change them.
/// - A run counts the unwrapped turn of its travel direction from its opening
///   stroke. Wobble cancels instead of accumulating. The first step needs a rough
///   quarter (45 degrees); each further step a full quarter, so a loop gives four
///   evenly spaced steps at any radius, and turning back by a quarter from the
///   furthest point reached gives one opposite step.
/// - A sharp about-face (a large turn within a short, size-relative path) is a
///   straight reversal, never winding: it starts a fresh run, so a curved arc
///   traced back afterwards counts as its own opposite quarter.
/// - A step also needs sideways travel into the turn, by a fraction of the
///   gesture's size. Tremor or a turnaround hook turns the heading without it.
///   A sharp turn is held until its outgoing stroke leaves the short path in
///   which it could still become an about-face (or the wand settles).
/// - Floors rise with hand noise learned from the packets themselves, so a steady
///   hand keeps tiny gestures and a shaky one cannot invent turns.
/// - A pause does not reset anything by time alone. When movement resumes, a
///   consistent direction continues the run (very slow motion), and a new
///   direction starts a fresh run from the pause point (a separate gesture).
/// Nothing here moves or buffers the pointer.
struct WandReviewCircle {
    enum Event:String {case none,start,segment,pending,cancelled,cusp,resumed,step,settled,rest,gap,jump,invalid}
    struct Snapshot {
        let event:Event,active:Bool,turn:Double,effective:Double,scale:Double,segment:Double
        let pending:Int,direction:Int,runSteps:Int,credit:Double,sideways:Double
        // Read-only diagnostics. `credit` is retired (no return allowance) and always 0.
        let noise:Double,paused:Bool,jitter:Double,wobble:Double
    }
    // Turning of the path's travel direction, in degrees.
    static let firstTurnDegrees = 45.0     // a rough quarter-turn earns a run's first step
    static let quarterTurnDegrees = 90.0   // each further step, and turning back to an opposite step
    static let cuspTurnDegrees = 115.0     // this much turning within a short path is an about-face
    static let straightDegrees = 10.0      // a segment this far off the opening chord ends the opening stroke
    static let continueDegrees = 45.0      // after a pause, a direction within this continues the run
    static let cancelBackDegrees = 20.0    // falling this far back below a threshold cancels it
    static let sharpDegrees = 40.0         // a turn this sharp at one junction may still become an about-face
    // Geometry: degrees of wand angle, or fractions of the gesture's own size.
    static let segmentFraction = 0.12, minimumSegment = 0.03, maximumSegment = 1.0, partialSegment = 0.5
    static let referenceSegments = 2.0     // opening-stroke chord length, in segments, for the reference
    static let reliableNoise = 6.0         // an opening chord shorter than this many noise widths is unreliable
    static let cuspNoise = 4.0             // a partial segment must be this many noise widths to show an about-face
    static let confirmFraction = 0.3       // sideways travel into a turn
    static let cuspFraction = 0.4          // the short path, as a fraction of the gesture's size, of an about-face
    static let settleFraction = 0.15       // smaller sideways travel accepted once the wand settles
    static let strongFraction = 0.6        // sideways travel that confirms even a sharp turn at once
    static let stepPathFraction = 0.5      // path between steps, as a fraction of the gesture's size
    static let minimumSideways = 0.05, minimumPath = 0.1, restTravel = 0.05
    // Learned hand noise raises these floors: packets while still, and sideways
    // scatter of moving packets (the firmware dead zone hides tremor at rest but
    // passes it during motion). A steady hand keeps small gestures; a shaky one
    // cannot invent turns.
    static let noiseSegment = 3.5, noiseTravel = 2.5, wobbleWeight = 1.5, noiseCeiling = 0.4
    // Pause classification only, in seconds; nothing waits on a timer and no
    // minimum speed is imposed. A corner with a short sideways leg is accepted
    // once the wand settles; a longer pause marks where a new gesture may begin.
    static let settleSeconds = 0.12, restSeconds = 0.35, gapSeconds = 1.0
    // Tremor is a fast wobble: only closely spaced packets can show it. Widely
    // spaced packets (slow sparse input) show shape, never noise.
    static let tremorSpan = 0.1

    private(set) var event = Event.none
    private(set) var active = false
    private var x=0.0,y=0.0,lastTime:Double?
    private var jitter=0.0,wobble=0.0,jitterCount=0.0,wobbleCount=0.0
    private var progressX=0.0,progressY=0.0,lastProgress:Double?
    private var settled=false,paused=false,pauseX=0.0,pauseY=0.0
    // Spatial segments: heading is measured only between points a segment apart.
    private var anchorX=0.0,anchorY=0.0,heading:Double?,path=0.0
    // The two previous moving packets, for the sideways-scatter noise estimate.
    private var priorX=0.0,priorY=0.0,olderX=0.0,olderY=0.0,olderTime=0.0,priorTime=0.0,moving=0
    private var lastDX=0.0,lastDY=0.0,lastPacket:Double?
    // The furthest point along the current heading since the last segment:
    // where an about-face actually turned round.
    private var extremeX=0.0,extremeY=0.0,extremeReach=0.0
    // One run, between about-faces and redirected pauses. `turn` is the unwrapped
    // heading change since the run's first segment; `reference` is the direction
    // of its opening stroke.
    private var turn=0.0,firstHeading=0.0,reference=0.0,referenceChord=0.0,referenceLocked=false
    private var window:[(path:Double,turn:Double)]=[]
    private var runX=0.0,runY=0.0,runSteps=0
    // The gesture's size: the furthest distance from where the current step window
    // began (run start or last step). Rotation-invariant, unlike a bounding box.
    private var windowX=0.0,windowY=0.0,spread=0.0,previousExtent=0.0,stepPath=0.0
    private var direction=0.0,next=0.0,peak=0.0,peakX=0.0,peakY=0.0,peakHeading=0.0
    private var refX=0.0,refY=0.0,refHeading=0.0
    private var pendingSign=0.0,pendingThreshold=0.0,pendingX=0.0,pendingY=0.0,pendingHeading=0.0,pendingPartial=false
    private var pendingSharp=false,armX=0.0,armY=0.0,armSideways=0.0,recentTurn=0.0

    // Bounded spatial evidence, cleared on an accepted step or mode reset.
    private var smallerCurve:[(x:Double,y:Double)]=[]
    var isCircling: Bool { direction != 0 }
    /// Keeps the learned noise floors; everything about the gesture starts afresh.
    mutating func reset(){let learned=(jitter,wobble,jitterCount,wobbleCount);self=Self();(jitter,wobble,jitterCount,wobbleCount)=learned}
    /// Replay only: start from noise floors recorded in a trace snapshot.
    mutating func restoreNoise(jitter learnedJitter:Double,wobble learnedWobble:Double) {
        guard learnedJitter.isFinite,learnedWobble.isFinite else{return}
        jitter=max(0,min(0.1,learnedJitter));wobble=max(0,min(0.1,learnedWobble));jitterCount=20;wobbleCount=20
    }

    private static func radians(_ degrees:Double)->Double {degrees*Double.pi/180}
    private static func wrap(_ angle:Double)->Double {
        var value=angle
        while value>Double.pi {value-=2*Double.pi}
        while value < -Double.pi {value+=2*Double.pi}
        return value
    }
    /// Persistent tremor raises a noise estimate within a few packets; one shape
    /// corner among sparse packets barely moves it.
    private static func robust(_ value:Double,_ estimate:Double)->Double {min(value,estimate*3+0.01,0.1)}
    private var extent:Double {spread}
    private var scale:Double {max(extent,previousExtent*0.5)}
    private var noise:Double {max(jitter,wobble*Self.wobbleWeight)}
    private func floor(_ base:Double,_ factor:Double,_ level:Double)->Double {min(Self.noiseCeiling,max(base,level*factor))}
    private var segmentLength:Double {max(floor(Self.minimumSegment,Self.noiseSegment,noise),min(Self.maximumSegment,scale*Self.segmentFraction))}
    /// The short path within which a large turn is an about-face rather than winding.
    private var cuspReach:Double {max(Self.cuspFraction*scale,segmentLength)}
    /// An opening chord a few noise widths long (or locked) can anchor a turn.
    // An unfiltered opening needs a full segment, not a half-segment of tremor.
    private var referenceReliable:Bool {referenceLocked || referenceChord>=max(segmentLength,Self.reliableNoise*noise)}
    /// Turn measured from the run's opening stroke.
    private func effective(_ raw:Double)->Double {raw-Self.wrap(reference-firstHeading)}
    private var sideways:Double {
        guard pendingSign != 0 else{return 0}
        return pendingSign*(-(x-pendingX)*sin(pendingHeading)+(y-pendingY)*cos(pendingHeading))
    }
    var snapshot:Snapshot {
        let degrees=180/Double.pi
        return Snapshot(event:event,active:active,turn:turn*degrees,effective:effective(turn)*degrees,scale:scale,segment:segmentLength,
                        pending:Int(pendingSign),direction:Int(direction),runSteps:runSteps,credit:0,sideways:sideways,
                        noise:noise,paused:paused,jitter:jitter,wobble:wobble)
    }
    private mutating func note(_ next:Event) {
        let rank:[Event:Int]=[.none:0,.segment:1,.start:2,.resumed:2,.pending:3,.cancelled:4,.cusp:5,.rest:6,.gap:6,.step:7,.settled:7,.jump:8,.invalid:8]
        if rank[next,default:0]>=rank[event,default:0] {event=next}
    }

    // MARK: Packets and pauses

    mutating func sample(dx:Double,dy:Double,now:Double)->Int32 {
        event = .none
        guard dx.isFinite,dy.isFinite,now.isFinite else{reset();event = .invalid;return 0}
        guard hypot(dx,dy)<30 else{reset();event = .jump;return 0}
        // A transport gap, or no progress for restSeconds, is a pause at the last
        // position before this packet; this packet's movement then decides how
        // the run resumes.
        if active,!paused {
            if let lastTime,now-lastTime>Self.gapSeconds {pause();note(.gap)}
            else if let lastProgress,now-lastProgress>=Self.restSeconds {pause();note(.rest)}
        }
        lastTime=now;x+=dx;y+=dy
        // The first packet after construction or reset only sets the baseline: it
        // may carry a stale NAV total, and nothing about the hand is known yet.
        if lastProgress==nil {progressX=x;progressY=y;lastProgress=now}
        // Sideways scatter of each moving packet from the chord joining its
        // neighbours: tremor counts, acceleration along the path does not.
        // Review now receives slow motion before the HUD speed floor. Learn
        // sideways noise from the opening packets too, before an apparent
        // first turn can be mistaken for an intentional loop.
        if !settled,dx != 0 || dy != 0 {
            if moving>=2 && now-olderTime<=Self.tremorSpan {
                let cx=x-olderX,cy=y-olderY,chord=hypot(cx,cy)
                if chord>1e-6 {wobbleCount=min(wobbleCount+1,20);wobble+=(Self.robust(abs(cx*(priorY-olderY)-cy*(priorX-olderX))/chord,wobble)-wobble)/wobbleCount}
            }
            olderX=priorX;olderY=priorY;olderTime=priorTime;priorX=x;priorY=y;priorTime=now;moving+=1
        }
        var output:Int32=0
        let travel=floor(Self.restTravel,Self.noiseTravel,noise)
        if hypot(x-progressX,y-progressY)>=travel {
            if !active {active=true;note(.start);startRun(x:progressX,y:progressY,previous:0)}
            progressX=x;progressY=y;lastProgress=now;settled=false
        } else if let lastProgress,now-lastProgress>=Self.settleSeconds {
            // Jitter is the packet-to-packet change while not progressing: random
            // tremor has it, steady very slow motion does not, so slow deliberate
            // movement never raises the floors. Zero packets count as quiet.
            if let lastPacket,now-lastPacket<=Self.tremorSpan/2 {jitterCount=min(jitterCount+1,20);jitter+=(Self.robust(hypot(dx-lastDX,dy-lastDY)/2,jitter)-jitter)/jitterCount}
            if active {
                // Only a corner armed by a completed segment may be accepted on settling.
                if pendingSign != 0 && !pendingPartial {output+=confirm(onSettle:true,value:nil)}
                settled=true;moving=0
            }
        }
        lastDX=dx;lastDY=dy;lastPacket=now
        guard active else{return output}
        return output+advance()
    }
    /// Remember where the wand stopped. Nothing is reset until movement resumes.
    private mutating func pause() {paused=true;pauseX=x;pauseY=y}
    /// Movement after a pause: a consistent direction continues the run (slow
    /// continuous motion); a new direction is a separate gesture from the pause point.
    private mutating func resume(direction resumed:Double) {
        paused=false
        guard let current=heading,abs(Self.wrap(resumed-current))>Self.radians(Self.continueDegrees) else{return}
        startRun(x:pauseX,y:pauseY,previous:knownSize);note(.resumed)
    }
    /// The gesture size a restarted run keeps. Ethan wants the known circle to be
    /// the frame of reference that blocks noise. Slow circles pause at their slow
    /// points and wobble at a near-stop; restarting from zero (after a pause) or
    /// from a tremor-sized about-face let the size the step rules scale by shrink
    /// to hundredths of a degree, so ~0.2° of wobble stepped "previous" in the
    /// middle of slow clockwise circles (2026-10-30 slow reference). A restart now
    /// keeps the size, exactly as an ordinary step already does (half of it, via
    /// `scale`); each later step re-learns it from the new gesture.
    private var knownSize:Double {max(extent,previousExtent)}
    /// A run starts at a point with no heading yet; its first segment sets it.
    private mutating func startRun(x startX:Double,y startY:Double,previous:Double) {
        anchorX=startX;anchorY=startY;heading=nil;extremeX=startX;extremeY=startY;extremeReach=0
        turn=0;firstHeading=0;reference=0;referenceChord=0;referenceLocked=false;window=[]
        runX=startX;runY=startY;runSteps=0
        direction=0;next=0;peak=0;pendingSign=0;pendingPartial=false;stepPath=0
        previousExtent=previous;windowX=startX;windowY=startY;spread=hypot(x-startX,y-startY)
    }

    /// Keep pause wobble from redefining the circle, while allowing a genuine
    /// smaller circle to replace it. Near-full winding, radial fit and noise
    /// clearance must agree; no minimum speed or timed wait is introduced.
    /// A dramatic size reduction may use its first loop to establish the new size.
    private mutating func relearnSmallerCurve()->Bool {
        guard previousExtent>0 else{return false}
        let spacing=floor(Self.minimumSegment,Self.noiseSegment,noise)
        if let p=smallerCurve.last, hypot(x-p.x,y-p.y)<spacing {return false}
        smallerCurve.append((x,y));if smallerCurve.count>96 {smallerCurve.removeFirst()}
        guard smallerCurve.count>=8 else{return false}
        let a=smallerCurve[0],b=smallerCurve[smallerCurve.count/3],c=smallerCurve[2*smallerCurve.count/3]
        let bx=b.x-a.x,by=b.y-a.y,cx=c.x-a.x,cy=c.y-a.y
        let determinant=2*(bx*cy-by*cx)
        guard abs(determinant)>1e-6 else{return false}
        let bb=bx*bx+by*by,cc=cx*cx+cy*cy
        let ux=(bb*cy-cc*by)/determinant,uy=(bx*cc-cx*bb)/determinant
        let radius=hypot(ux,uy)
        guard radius.isFinite,radius>=max(Self.minimumPath*2,10*noise),2*radius<previousExtent*0.8 else{return false}
        let ox=a.x+ux,oy=a.y+uy
        var turn=0.0,absolute=0.0,last:Double?
        for p in smallerCurve {
            guard abs(hypot(p.x-ox,p.y-oy)-radius)<=0.15*radius else{return false}
            let angle=atan2(p.y-oy,p.x-ox)
            if let prior=last {let d=Self.wrap(angle-prior);turn+=d;absolute+=abs(d)}
            last=angle
        }
        guard abs(turn)>=Self.radians(300),abs(turn)>=0.98*absolute else{return false}
        previousExtent=min(previousExtent,2*radius);smallerCurve.removeAll(keepingCapacity:true)
        return true
    }

    // MARK: Segments and turning

    private mutating func advance()->Int32 {
        if paused {
            // Decide only once the new direction is measurable.
            let rx=x-pauseX,ry=y-pauseY
            guard hypot(rx,ry)>=max(Self.partialSegment*segmentLength,Self.noiseTravel*noise) else{return 0}
            resume(direction:atan2(ry,rx))
        }
        var length=segmentLength
        spread=max(spread,hypot(x-windowX,y-windowY))
        if relearnSmallerCurve() {length=segmentLength}
        let ddx=x-anchorX,ddy=y-anchorY,distance=hypot(ddx,ddy),h=atan2(ddy,ddx)
        if let current=heading {
            let reach=ddx*cos(current)+ddy*sin(current)
            if reach>extremeReach {extremeReach=reach;extremeX=x;extremeY=y}
        }
        // A quick flick may be only three or four packets: half a segment can open
        // a run, and stands in for the current heading until a segment completes.
        let partial=distance>=max(Self.partialSegment*length,Self.noiseTravel*noise)
        guard let previous=heading else{
            guard partial else{return 0}
            heading=h;firstHeading=h;reference=h;referenceChord=distance;turn=0;commit(distance:distance)
            window=[(path,0)];refX=runX;refY=runY;refHeading=h
            return 0
        }
        let delta=Self.wrap(h-previous),estimate=turn+delta
        // Turning this sharply within a short, size-relative path is an about-face
        // or a turnaround hook: the stroke reversed. It is never winding; a fresh run
        // starts where the stroke turned round.
        let reach=cuspReach,junction=path
        var sharp=abs(delta)
        for entry in window where junction-entry.path<=reach {sharp=max(sharp,abs(estimate-entry.turn))}
        // A corner is a turn at one junction; a tight arc spreads its turn out.
        recentTurn=abs(delta)
        // A partial segment may reveal an about-face early, but only when it is
        // clearly longer than tremor at a momentary stop.
        if sharp>=Self.radians(Self.cuspTurnDegrees) && (distance>=length || distance>=max(Self.partialSegment*length,Self.cuspNoise*noise)) {
            if pendingSign != 0 {note(.cancelled)}
            let stroke=knownSize
            startRun(x:extremeReach>0 ? extremeX:anchorX,y:extremeReach>0 ? extremeY:anchorY,previous:stroke)
            note(.cusp)
            return advance()
        }
        guard distance>=length else{
            return partial ? count(raw:estimate,heading:h,partial:true) : 0
        }
        window.append((junction,turn))
        while window.count>1,junction-window[0].path>reach {window.removeFirst()}
        heading=h;turn=estimate;commit(distance:distance)
        // Up to two segments of the opening stroke's chord, rather than one short
        // noisy segment, are the run's reference; turning ends the opening stroke.
        // A chord shorter than a few noise widths cannot lock on a turn: under
        // tremor the reference keeps following the opening chord instead.
        if !referenceLocked {
            let chordX=x-runX,chordY=y-runY,chord=hypot(chordX,chordY),chordHeading=atan2(chordY,chordX)
            if referenceReliable && abs(Self.wrap(h-reference))>Self.radians(Self.straightDegrees) {referenceLocked=true}
            else {
                reference=firstHeading+Self.wrap(chordHeading-firstHeading);refHeading=chordHeading;referenceChord=chord
                if chord>=Self.referenceSegments*length {referenceLocked=true}
            }
        }
        return count(raw:turn,heading:h,partial:false)
    }
    private mutating func commit(distance:Double) {
        anchorX=x;anchorY=y;path+=distance;stepPath+=distance
        extremeX=x;extremeY=y;extremeReach=0;note(.segment)
    }

    // MARK: Steps

    private mutating func count(raw:Double,heading now:Double,partial:Bool)->Int32 {
        let value=effective(raw)
        let first=Self.radians(Self.firstTurnDegrees),quarter=Self.radians(Self.quarterTurnDegrees)
        if direction != 0 && (value-peak)*direction>0 {peak=value;peakX=x;peakY=y;peakHeading=now}
        if pendingSign == 0 {
            if direction == 0 {
                // A run whose opening stroke is still tremor-sized has no direction
                // to turn from yet.
                if abs(value)>=first && referenceReliable {arm(value>0 ? 1:-1,threshold:value>0 ? first:-first,x:runX,y:runY,heading:reference)}
            } else if (value-next)*direction>=0 {
                arm(direction,threshold:next,x:refX,y:refY,heading:refHeading)
            } else if (peak-value)*direction>=quarter {
                arm(-direction,threshold:peak-quarter*direction,x:peakX,y:peakY,heading:peakHeading)
            }
            guard pendingSign != 0 else{return 0}
            pendingPartial=partial
        } else if (value-pendingThreshold)*pendingSign < -Self.radians(Self.cancelBackDegrees) {
            pendingSign=0;note(.cancelled);return 0
        } else if !partial {
            pendingPartial=false
        }
        return confirm(onSettle:false,value:value)
    }
    private mutating func arm(_ sign:Double,threshold:Double,x fromX:Double,y fromY:Double,heading h:Double) {
        pendingSign=sign;pendingThreshold=threshold;pendingX=fromX;pendingY=fromY;pendingHeading=h;note(.pending)
        pendingSharp=recentTurn>=Self.radians(Self.sharpDegrees);armX=x;armY=y;armSideways=sideways
    }
    /// A step needs sideways travel into the turn, not just a turned heading.
    private mutating func confirm(onSettle:Bool,value:Double?)->Int32 {
        guard pendingSign != 0 else{return 0}
        let need=max((onSettle ? Self.settleFraction:Self.confirmFraction)*scale,floor(Self.minimumSideways,Self.noiseTravel,noise))
        // Consecutive steps need travel of at least half the gesture's size between
        // them, as every corner of a square or quarter of a loop has.
        guard sideways>=need,stepPath>=max(Self.minimumPath,Self.stepPathFraction*scale) else{return 0}
        // A sharp turn is confirmed once its outgoing stroke has left the short path
        // in which it could still become an about-face, once the wand settles, or
        // when the path had already curved well sideways before it (an arc's last
        // packet). Sideways travel gained after the turn could be a reset stroke.
        if pendingSharp && !onSettle && armSideways<Self.strongFraction*scale && hypot(x-armX,y-armY)<cuspReach {return 0}
        let sign=pendingSign,now=heading ?? 0
        direction=sign;next=pendingThreshold+Self.radians(Self.quarterTurnDegrees)*sign
        peak=value ?? effective(turn);peakX=x;peakY=y;peakHeading=now
        refX=x;refY=y;refHeading=now
        smallerCurve.removeAll(keepingCapacity:true)
        runSteps+=1;stepPath=0;previousExtent=extent;windowX=x;windowY=y;spread=0
        pendingSign=0;note(onSettle ? .settled:.step)
        return Int32(sign)
    }
}

/// Ethan's review "circles" include clockwise/anticlockwise diamonds and squares.
/// Straight up/down flicks do not navigate; the optional yes/no experiment is
/// kept separately. This adapter leaves Better Git's selection lifecycle intact.
struct WandReviewNavigation {
    var useAxisGestures = false
    private var axisGesture = WandAxisReviewGesture()
    private var circle = WandReviewCircle()
    /// Starts a fresh gesture; the default classifier keeps its learned hand noise.
    mutating func reset() { axisGesture.reset();circle.reset() }
    mutating func sample(dx:Double,dy:Double,now:Double)->Int32 {
        if useAxisGestures { return axisGesture.sample(dx:dx,dy:dy,now:now) }
        return circle.sample(dx:dx,dy:dy,now:now)
    }
    /// Diagnostics only: the default classifier's state after the last sample.
    var snapshot: WandReviewCircle.Snapshot { circle.snapshot }
    /// Replay only: seed the default classifier's learned noise from a trace.
    mutating func restoreNoise(jitter:Double,wobble:Double) { circle.restoreNoise(jitter:jitter,wobble:wobble) }
}

/// Ethan's optional "yes/no": an up-and-down nod moves next; a side-to-side
/// shake moves previous. Off by default; replaces only the review gestures.
struct WandAxisReviewGesture {
    static let minimumTravel=0.3, reversalTravel=0.06
    private var x=0.0,y=0.0,extreme=0.0,extremeCross=0.0,strokeStart=0.0,crossStart=0.0,direction=0.0
    private var axis=0
    private var started:Double?,lastMotion:Double?
    mutating func reset(){self=Self()}
    mutating func sample(dx:Double,dy:Double,now:Double)->Int32 {
        guard dx.isFinite,dy.isFinite,now.isFinite else{reset();return 0}
        if let lastMotion,now-lastMotion>0.6 {reset()}
        guard hypot(dx,dy)>=0.003 else{return 0}
        if axis==0,let started,now-started>4 {reset()}
        if started==nil {started=now}
        lastMotion=now;x+=dx;y+=dy
        if axis==0 {
            guard max(abs(x),abs(y))>=Self.minimumTravel else{return 0}
            if abs(y)>=1.6*abs(x) {axis=1;direction=y>0 ? 1:-1}
            else if abs(x)>=1.6*abs(y) {axis=2;direction=x>0 ? 1:-1}
            else{return 0}
            extreme=axis==1 ? y:x;extremeCross=axis==1 ? x:y
        }
        let primary=axis==1 ? y:x,cross=axis==1 ? x:y
        if (primary-extreme)*direction>0 {extreme=primary;extremeCross=cross}
        let travel=abs(extreme-strokeStart)
        // Reject a broad bend rather than mistaking a circle for a yes/no motion.
        if abs(cross-crossStart)>max(0.18,travel*0.65) {reset();return 0}
        // Ethan's "every switching direction" / "corner": use a small confirmed
        // reversal, then track the opposite stroke immediately, without a neutral
        // reset. The travel requirement prevents tremor from adding more ratchets.
        guard travel>=Self.minimumTravel,(extreme-primary)*direction>=Self.reversalTravel else{return 0}
        // A rounded turn keeps travelling sideways; a nod reverses on its axis.
        guard abs(cross-extremeCross)<=0.03+abs(extreme-primary)*0.75 else{reset();return 0}
        let step:Int32=axis==1 ? 1:-1
        strokeStart=extreme;crossStart=cross;direction = -direction;extreme=primary;extremeCross=cross
        return step
    }
}
