// Ports of the pure native pointer helpers. Tests compare native and JS traces.
export class CircularScroll {
  constructor(tuning = {}) {
    this.tuning = {
      verticalRatio: 1.4,
      segment: 2,
      recogniseTurn: 5,
      consistency: 0.6,
      maxTurn: 1.5,
      minPath: 45,
      minExtent: 10,
      minAspect: 0.25,
      window: 2,
      minDuration: 0.2,
      idleEnd: 0.35,
      exitFraction: 0.3,
      straightTurn: 0.35,
      linesPerTurn: 8,
      kick: 2,
      maxLinesPerUpdate: 6,
      ...tuning,
    };
    this.reset();
  }
  reset() {
    this.segments = [];
    this.signedTurn = 0;
    this.absoluteTurn = 0;
    this.path = 0;
    this.accX = 0;
    this.accY = 0;
    this.posX = 0;
    this.posY = 0;
    this.lastTime = 0;
    this.heading = null;
    this.remainder = 0;
    this.loopLength = 0;
    this.windowPath = 0;
    this.windowTurn = 0;
    this.windowSigned = 0;
    this.straightWindows = 0;
    this.straightDistance = 0;
    this.active = false;
  }
  expire(now) {
    if (this.lastTime > 0 && now - this.lastTime > this.tuning.idleEnd) {
      const was = this.active;
      this.reset();
      return was;
    }
    return false;
  }
  update(dx, dy, now, eligible) {
    const none = { consumesPointer: false, lines: 0 };
    if (!eligible || ![dx, dy, now].every(Number.isFinite)) {
      this.reset();
      return none;
    }
    this.expire(now);
    if (!dx && !dy) return { consumesPointer: this.active, lines: 0 };
    const vy = dy / this.tuning.verticalRatio;
    this.lastTime = now;
    this.accX += dx;
    this.accY += vy;
    this.posX += dx;
    this.posY += vy;
    const length = Math.hypot(this.accX, this.accY);
    if (length < this.tuning.segment)
      return { consumesPointer: this.active, lines: 0 };
    const direction = Math.atan2(this.accY, this.accX);
    this.accX = 0;
    this.accY = 0;
    const turn = this.heading === null ? 0 : wrap(direction - this.heading);
    this.heading = direction;
    return this.active
      ? this.scroll(turn, length)
      : this.candidate(turn, length, now);
  }
  candidate(turn, length, now) {
    const t = this.tuning,
      none = { consumesPointer: false, lines: 0 },
      corner = Math.abs(turn) > t.maxTurn;
    if (corner) {
      this.segments = [];
      this.signedTurn = 0;
      this.absoluteTurn = 0;
      this.path = 0;
    }
    const kept = corner ? 0 : turn;
    this.segments.push({
      turn: kept,
      length,
      t: now,
      x: this.posX,
      y: this.posY,
    });
    this.signedTurn += kept;
    this.absoluteTurn += Math.abs(kept);
    this.path += length;
    while (this.segments.length && now - this.segments[0].t > t.window) {
      const f = this.segments.shift();
      this.signedTurn -= f.turn;
      this.absoluteTurn -= Math.abs(f.turn);
      this.path -= f.length;
    }
    if (!this.segments.length) {
      this.signedTurn = 0;
      this.absoluteTurn = 0;
      this.path = 0;
    }
    if (
      this.segments.length < 6 ||
      Math.abs(this.signedTurn) < t.recogniseTurn ||
      this.absoluteTurn <= 0 ||
      Math.abs(this.signedTurn) / this.absoluteTurn < t.consistency ||
      this.path < t.minPath ||
      now - this.segments[0].t < t.minDuration
    )
      return none;
    const xs = this.segments.map((s) => s.x),
      ys = this.segments.map((s) => s.y),
      w = Math.max(...xs) - Math.min(...xs),
      h = Math.max(...ys) - Math.min(...ys);
    if (
      w < t.minExtent ||
      h < t.minExtent ||
      Math.min(w, h) / Math.max(w, h) < t.minAspect
    )
      return none;
    const clockwise = this.signedTurn > 0;
    this.loopLength = Math.max(
      24,
      Math.min(6000, (this.path * 2 * Math.PI) / Math.abs(this.signedTurn)),
    );
    this.segments = [];
    this.signedTurn = 0;
    this.absoluteTurn = 0;
    this.path = 0;
    this.remainder = 0;
    this.windowPath = 0;
    this.windowTurn = 0;
    this.windowSigned = 0;
    this.active = true;
    return { consumesPointer: true, lines: clockwise ? -t.kick : t.kick };
  }
  scroll(turn, length) {
    const t = this.tuning,
      kept = Math.abs(turn) > t.maxTurn ? 0 : turn;
    if (Math.abs(kept) < 0.04) this.straightDistance += length;
    else this.straightDistance = 0;
    if (
      this.straightDistance >=
      Math.max(20, Math.min(60, this.loopLength * 0.25))
    ) {
      this.reset();
      return { consumesPointer: false, lines: 0 };
    }
    this.windowPath += length;
    this.windowTurn += Math.abs(kept);
    this.windowSigned += kept;
    if (
      this.windowPath >=
      Math.max(t.segment * 3, this.loopLength * t.exitFraction)
    ) {
      const expected = (2 * Math.PI * this.windowPath) / this.loopLength;
      if (this.windowTurn < expected * t.straightTurn) this.straightWindows++;
      else this.straightWindows = 0;
      if (this.straightWindows >= 2) {
        this.reset();
        return { consumesPointer: false, lines: 0 };
      }
      if (Math.abs(this.windowSigned) > 0.5)
        this.loopLength = Math.max(
          24,
          Math.min(
            6000,
            0.7 * this.loopLength +
              (0.3 * this.windowPath * 2 * Math.PI) /
                Math.abs(this.windowSigned),
          ),
        );
      this.windowPath = 0;
      this.windowTurn = 0;
      this.windowSigned = 0;
    }
    this.remainder += kept;
    const perLine = (2 * Math.PI) / t.linesPerTurn,
      steps = Math.max(
        -t.maxLinesPerUpdate,
        Math.min(t.maxLinesPerUpdate, Math.trunc(this.remainder / perLine)),
      );
    this.remainder -= steps * perLine;
    return { consumesPointer: true, lines: -steps || 0 };
  }
}
function wrap(a) {
  while (a > Math.PI) a -= 2 * Math.PI;
  while (a < -Math.PI) a += 2 * Math.PI;
  return a;
}
export class PointerRouter {
  constructor({lowDelay=0.09,maxPending=48}={}) {
    this.lowDelay=Math.max(0,lowDelay);
    this.maxPending=Math.max(1,maxPending);
    this.circle = new CircularScroll();
    this.bottomHeld = false;
    this.holdConsumed = false;
    this.dropNextClick = false;
    this.droppingClick = false;
    this.pending = [];
    this.lit = false;
  }
  get nextDue() {
    return this.pending[0]?.due;
  }
  endCircle() {
    this.circle.reset();
    if (!this.lit) return [];
    this.lit = false;
    return [{ type: "light", on: false }];
  }
  bottom(down) {
    this.pending = [];
    if (down) {
      this.dropNextClick = false;
      this.droppingClick = false;
    } else this.dropNextClick = this.bottomHeld && this.holdConsumed;
    this.holdConsumed = false;
    this.bottomHeld = down;
    return this.endCircle();
  }
  frame(dx, dy, buttons, hud, now) {
    let bits = buttons;
    if (this.dropNextClick || this.droppingClick) {
      if (bits & 1) {
        this.dropNextClick = false;
        this.droppingClick = true;
        bits &= ~1;
      } else if (this.droppingClick) this.droppingClick = false;
    }
    let actions = [];
    const low = this.bottomHeld && bits === 0 && !hud;
    if (!low) actions.push(...this.endCircle());
    if (bits !== 0) this.pending = [];
    if (!dx && !dy) return { buttons: bits, actions };
    if (!low) {
      actions.push({ type: "move", dx, dy });
      return { buttons: bits, actions };
    }
    const was = this.circle.active,
      r = this.circle.update(dx, dy, now, true);
    if (this.circle.active && !was) {
      this.pending = [];
      this.holdConsumed = true;
    }
    if (this.circle.active !== this.lit) {
      this.lit = this.circle.active;
      actions.push({ type: "light", on: this.lit });
    }
    if (r.consumesPointer) {
      if (r.lines) actions.push({ type: "scroll", lines: r.lines });
      return { buttons: bits, actions };
    }
    if (this.lowDelay === 0) {
      actions.push({type: "move", dx, dy});
      return {buttons: bits, actions};
    }
    actions.push(...this.drain(now));
    this.pending.push({due:now+this.lowDelay,dx,dy});
    while(this.pending.length>this.maxPending) {
      const p=this.pending.shift();actions.push({type:"move",dx:p.dx,dy:p.dy});
    }
    return { buttons: bits, actions };
  }
  drain(now) {
    const actions = [];
    while (this.pending.length && this.pending[0].due <= now) {
      const p = this.pending.shift();
      actions.push({ type: "move", dx: p.dx, dy: p.dy });
    }
    return actions;
  }
  tick(now) {
    const actions = this.drain(now);
    this.circle.expire(now);
    if (this.lit && !this.circle.active) {
      this.lit = false;
      actions.push({ type: "light", on: false });
    }
    return actions;
  }
  interrupt() {
    this.pending = [];
    return this.endCircle();
  }
}
export class DwellClick {
  constructor() {
    this.following = false;
    this.inhibitedUntil = 0;
    this.reset();
  }
  reset() {
    this.x = 0;
    this.y = 0;
    this.armed = false;
    this.lastMotion = 0;
    this.intentUntil = 0;
  }
  follow(on) {
    if (this.following !== on) this.reset();
    this.following = on;
  }
  get nextDue() {
    return this.following && this.armed
      ? Math.max(this.lastMotion + 0.45, this.inhibitedUntil, this.intentUntil)
      : null;
  }
  intent(moving, now) {
    if (!this.following) return;
    if (moving) { this.intentUntil = now + 0.6; this.lastMotion = now; }
    else if (this.intentUntil > 0) { this.intentUntil = 0; this.lastMotion = now; }
  }
  move(dx, dy, now, eligible) {
    if (!this.following || !eligible || now < this.inhibitedUntil) {
      this.reset();
      return;
    }
    if (!dx && !dy) return;
    this.x += dx;
    this.y += dy;
    this.lastMotion = now;
    if (Math.hypot(this.x, this.y) >= 12) this.armed = true;
  }
  tick(now) {
    if (this.nextDue === null || now < this.nextDue) return false;
    this.reset();
    return true;
  }
}
