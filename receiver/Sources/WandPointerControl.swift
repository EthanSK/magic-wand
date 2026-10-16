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
        /// No motion for this long ends an established circle.
        var idleEnd=0.35
        /// Over `exitFraction` of a loop's length, turning below `straightTurn` of a
        /// loop's expected turning is a deliberate straight move: scrolling ends and
        /// that movement passes through as pointer motion.
        var exitFraction=0.3, straightTurn=0.35
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
    private var straightWindows=0,straightDistance=0.0
    private(set) var active=false

    init(tuning:Tuning=Tuning()){self.tuning=tuning}

    func reset(){
        segments.removeAll(keepingCapacity:true);signedTurn=0;absoluteTurn=0;path=0
        accX=0;accY=0;posX=0;posY=0;lastTime=0;heading=nil
        remainder=0;loopLength=0;windowPath=0;windowTurn=0;windowSigned=0;straightWindows=0;straightDistance=0;active=false
    }
    /// A pause ends an established circle and forgets candidate turning, so slow
    /// aiming broken by pauses can never add up to a loop.
    @discardableResult
    func expire(now:Double)->Bool {
        guard lastTime>0,now-lastTime>tuning.idleEnd else{return false}
        let was=active;reset();return was
    }
    func update(dx:Double,dy:Double,now:Double,eligible:Bool)->Result {
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
        if abs(kept)<0.04 {straightDistance+=length}else{straightDistance=0}
        if straightDistance>=max(20,min(60,loopLength*0.25)) {reset();return .init(consumesPointer:false,lines:0)}
        windowPath+=length;windowTurn+=abs(kept);windowSigned+=kept
        if windowPath>=max(tuning.segment*3,loopLength*tuning.exitFraction) {
            let expected=2*Double.pi*windowPath/loopLength
            if windowTurn<expected*tuning.straightTurn {straightWindows+=1}else{straightWindows=0}
            if straightWindows>=2 {reset();return .init(consumesPointer:false,lines:0)}
            // Follow radius drift: re-estimate the loop length from recent turning.
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
/// LOW is a plain Bottom hold with no mouse button down (precision aiming, not a
/// drag). LOW motion is immediate by default. An optional nonzero `lowDelay`
/// can defer it: the device reports
/// the release edge in the same ordered UART stream as motion, so stiff-switch
/// movement in the last instant before release is discarded unseen and the release
/// click lands where the pointer is already shown. Normal operation does not
/// buffer or roll back movement. HIGH follow and real dragging
/// stay immediate. Loop scrolling is recognised only during LOW. A hold in which a
/// loop was recognised is consumed by scrolling: the endpoint click that the device
/// emits right after that `@BOTTOM 0` (same callback, so before any later frame) is
/// dropped. The drop is disarmed by the next Bottom press, so it can never swallow
/// a later real click. It is decided by stream order, never by a timeout.
final class WandPointerRouter {
    enum Action:Equatable { case move(dx:Int,dy:Int), scroll(lines:Int32), circleLight(Bool) }
    struct Frame:Equatable { let buttons:Int; let actions:[Action] }
    /// Disabled by default: stillness recognition does not require delaying
    /// visible pointer movement. Retained as an explicit opt-in for diagnostics.
    let lowDelay:Double
    /// Bounds memory if the drain timer is starved; the oldest motion is then shown, not lost.
    let maxPending:Int
    let circle:WandCircularScroll
    private(set) var bottomHeld=false
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

    /// The device prints a Bottom edge before the release click it emits for that edge.
    func bottom(down:Bool)->[Action] {
        pending.removeAll(keepingCapacity:true)
        if down {dropNextClick=false;droppingClick=false}
        else {dropNextClick=bottomHeld && holdConsumed}
        holdConsumed=false;bottomHeld=down
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
        let low=bottomHeld && bits==0 && !hud
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
    /// Periodic: show due motion and end an idle circle.
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
        bottomHeld=false;holdConsumed=false;dropNextClick=false;droppingClick=false
        return endCircle()
    }
    private func endCircle()->[Action] {
        circle.reset()
        guard lit else{return []}
        lit=false;return [.circleLight(false)]
    }
}

/// HIGH clicks once after travel then a pause. Entry and remaining still never
/// click; every button/mode transition requires a fresh deliberate movement.
final class WandDwellClick {
    let pause:Double
    let travel:Double
    private(set) var following=false
    private var x=0.0,y=0.0,lastMotion=0.0,inhibitedUntil=0.0,intentUntil=0.0
    private(set) var armed=false
    init(pause:Double=0.45,travel:Double=12){self.pause=pause;self.travel=travel}
    var nextDue:Double? {following && armed ? max(lastMotion+pause,inhibitedUntil,intentUntil) : nil}
    func reset(){x=0;y=0;armed=false;lastMotion=0;intentUntil=0}
    func follow(_ on:Bool){if following != on {reset()};following=on}
    func inhibit(until:Double){reset();inhibitedUntil=max(inhibitedUntil,until)}
    /// The device sees sub-pixel motion before integer cursor counts exist.
    /// A bounded heartbeat lease prevents both premature clicks and stuck state.
    func intent(_ moving:Bool,now:Double){
        guard following else{return}
        if moving {intentUntil=now+0.6;lastMotion=now}
        else if intentUntil>0 {intentUntil=0;lastMotion=now}
    }
    func move(dx:Int,dy:Int,now:Double,eligible:Bool){
        guard following,eligible,now>=inhibitedUntil else{reset();return}
        guard dx != 0 || dy != 0 else{return}
        x+=Double(dx);y+=Double(dy);lastMotion=now
        if hypot(x,y)>=travel {armed=true}
    }
    func tick(now:Double)->Bool {
        guard let due=nextDue,now>=due else{return false}
        reset();return true
    }
}

/// Conservative IMU inference, not a touch sensor. Remember a quiet desk pose,
/// confirm pickup over multiple readings, then require a return/contact followed
/// by sustained very low acceleration variation and gyro rate before put-down.
/// A still hand away from the learned desk pose must not stop dictation.
final class WandRestDetection {
    enum Event:Equatable {case probe,pickedUp,settling,putDown}
    private var rest:[Double]?,previous:[Double]?,quiet:[Double]?
    private var quietSince=0.0,quietCount=0,pickupCount=0
    private var contactUntil=0.0,lastTime=0.0,away=false,settling=false
    private(set) var parked=false
    private(set) var deskQuietSince:Double?
    func reset(){rest=nil;previous=nil;quiet=nil;quietCount=0;pickupCount=0;contactUntil=0;lastTime=0;away=false;settling=false;parked=false;deskQuietSince=nil}
    private func distance(_ a:[Double],_ b:[Double])->Double {sqrt(zip(a,b).reduce(0){$0+pow($1.0-$1.1,2)})}
    func update(x:Double,y:Double,z:Double,gyro:Double,now:Double,buttons:Bool,idle:Bool)->[Event] {
        let a=[x,y,z],magnitude=sqrt(x*x+y*y+z*z)
        guard a.allSatisfy({$0.isFinite}),gyro.isFinite,now.isFinite,(0.05...4).contains(magnitude) else{quiet=nil;quietCount=0;deskQuietSince=nil;return []}
        if lastTime>0 && (now<=lastTime || now-lastTime>2){quiet=nil;quietCount=0;pickupCount=0}
        lastTime=now
        let jerk=previous.map{distance(a,$0)} ?? 0;previous=a
        if buttons {quiet=nil;quietCount=0;pickupCount=0;deskQuietSince=nil;return []}
        // Startup/reconnect only learns a baseline while every control is idle.
        guard let pose=rest else {
            guard idle else{quiet=nil;quietCount=0;return []}
            if let anchor=quiet,distance(a,anchor)<0.004,gyro<0.3,abs(magnitude-1)<0.03 {quietCount+=1}
            else {quiet=a;quietSince=now;quietCount=1}
            if quietCount>=4 && now-quietSince>=1.8 {rest=a;parked=true;quiet=nil;deskQuietSince=now}
            return []
        }
        let offset=distance(a,pose)
        if parked {
            if jerk>=0.004 || gyro>=0.3 {deskQuietSince=nil}
            else if deskQuietSince==nil {deskQuietSince=now}
            if offset>0.065 || abs(magnitude-1)>0.08 {
                pickupCount+=1
                if pickupCount==1 {return [.probe]}
                parked=false;deskQuietSince=nil;away=offset>0.18;quiet=nil;quietCount=0;pickupCount=0
                return [.pickedUp]
            }
            pickupCount=0;return []
        }
        if offset>0.18 {away=true}
        if jerk>0.18 {contactUntil=now+4}
        // Either a return to the learned pose after being lifted, or a contact
        // impulse allows a different resting orientation. Plain aim pauses don't.
        let possible=(away && offset<0.065) || now<contactUntil
        guard possible else{quiet=nil;quietCount=0;settling=false;return []}
        var events:[Event]=[]
        if !settling {settling=true;events.append(.settling)}
        if let anchor=quiet,distance(a,anchor)<0.004,gyro<0.3,abs(magnitude-1)<0.03 {quietCount+=1}
        else {quiet=a;quietSince=now;quietCount=1}
        if quietCount>=18 && now-quietSince>=1.8 {
            rest=a;parked=true;deskQuietSince=now;away=false;settling=false;quiet=nil;quietCount=0;contactUntil=0
            events.append(.putDown)
        }
        return events
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
