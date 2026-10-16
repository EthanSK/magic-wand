// Port of receiver/Sources/WandPointerControl.swift. No input is buffered while
// deciding: only a recognised full loop takes over from ordinary pointing.
export class CircularScroll {
  constructor() { this.reset(); }
  reset() {
    this.samples = []; this.x = 0; this.y = 0; this.lastTime = 0;
    this.active = false; this.remainder = 0; this.lastDirection = 0;
  }
  expire(now) {
    if (this.lastTime > 0 && now - this.lastTime > 0.22) {
      const was = this.active; this.reset(); return was;
    }
    return false;
  }
  update(dx, dy, now, eligible) {
    const pass = { consumesPointer: false, lines: 0 };
    if (!eligible || ![dx, dy, now].every(Number.isFinite)) { this.reset(); return pass; }
    if (dx === 0 && dy === 0) { this.expire(now); return { consumesPointer: this.active, lines: 0 }; }
    this.expire(now);
    if (!this.samples.length && !this.active) this.samples = [{ x: 0, y: 0, t: now }];
    const vy = dy / 1.4;
    this.x += dx; this.y += vy; this.lastTime = now;
    if (this.active) {
      const rx = this.x - this.center.x, ry = this.y - this.center.y;
      const distance = Math.hypot(rx, ry), step = Math.hypot(dx, vy);
      const radial = step > 0 && distance > 0 ? Math.abs((rx * dx + ry * vy) / (distance * step)) : 0;
      const current = Math.atan2(ry, rx), delta = wrap(current - this.angle);
      if (distance < this.radius * 0.4 || distance > this.radius * 1.8 || radial >= 0.8 || Math.abs(delta) >= 1) {
        this.reset(); return pass;
      }
      this.angle = current;
      const direction = delta >= 0 ? 1 : -1;
      if (direction !== this.lastDirection) { this.remainder = 0; this.lastDirection = direction; }
      this.remainder += delta;
      const steps = Math.max(-6, Math.min(6, Math.trunc(this.remainder / (Math.PI / 5))));
      this.remainder -= steps * (Math.PI / 5);
      return { consumesPointer: true, lines: -steps || 0 };
    }
    this.samples.push({ x: this.x, y: this.y, t: now });
    while (this.samples.length > 180 || (this.samples.length > 1 && now - this.samples[0].t > 2.5)) this.samples.shift();
    if (this.samples.length < 13) return pass;
    for (let start = 0; start < this.samples.length - 11; start += 3) {
      const run = this.samples.slice(start), duration = now - run[0].t;
      if (duration < 0.25 || duration > 2.5) continue;
      const xs = run.map(p => p.x), ys = run.map(p => p.y);
      const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
      const w = maxX - minX, h = maxY - minY;
      if (w < 40 || h < 40 || w > 1200 || h > 1200 || w / h < 0.55 || w / h > 1.8 || Math.hypot(this.x - run[0].x, this.y - run[0].y) > Math.min(w, h) * 0.24) continue;
      let length = 0, area = 0, turn = 0, totalTurn = 0, previousHeading = null, largestTurn = 0;
      for (let i = 1; i < run.length; i++) {
        const a = run[i - 1], b = run[i], sx = b.x - a.x, sy = b.y - a.y, segment = Math.hypot(sx, sy);
        length += segment; area += a.x * b.y - b.x * a.y;
        if (segment >= 0.25) {
          const heading = Math.atan2(sy, sx);
          if (previousHeading !== null) {
            const change = wrap(heading - previousHeading); turn += change; totalTurn += Math.abs(change); largestTurn = Math.max(largestTurn, Math.abs(change));
          }
          previousHeading = heading;
        }
      }
      const last = run.at(-1), first = run[0];
      area = (area + last.x * first.y - first.x * last.y) / 2;
      const circularity = length > 0 ? 4 * Math.PI * Math.abs(area) / (length * length) : 0;
      if (Math.abs(turn) < 5.2 || totalTurn <= 0 || Math.abs(turn) / totalTurn < 0.85 || largestTurn >= 1 || circularity < 0.68 || Math.abs(area) / (w * h) < 0.5 || Math.abs(area) / (w * h) > 0.94) continue;
      this.center = { x: (minX + maxX) / 2, y: (minY + maxY) / 2 }; this.radius = (w + h) / 4;
      this.angle = Math.atan2(this.y - this.center.y, this.x - this.center.x); this.remainder = 0;
      this.lastDirection = area > 0 ? 1 : -1; this.active = true; this.samples = [];
      return { consumesPointer: true, lines: area > 0 ? -3 : 3 };
    }
    return pass;
  }
}
function wrap(angle) {
  while (angle > Math.PI) angle -= 2 * Math.PI;
  while (angle < -Math.PI) angle += 2 * Math.PI;
  return angle;
}
