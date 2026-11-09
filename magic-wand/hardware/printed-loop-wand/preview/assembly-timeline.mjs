// Shared, renderer-independent assembly playback. Model recipes own the order
// and motion; seeking evaluates a pose from time, never from previous frames.
export class AssemblyTimeline {
  constructor(steps, changed = () => {}) {
    this.changed = changed;
    this.speed = 1;
    this.setSteps(steps);
  }

  setSteps(steps) {
    if (!Array.isArray(steps) || !steps.length || steps.some(s => !Number.isFinite(s.duration) || s.duration <= 0)) {
      throw new TypeError('Assembly steps require positive finite durations');
    }
    this.steps = steps;
    this.starts = [];
    this.duration = steps.reduce((total, step) => { this.starts.push(total); return total + step.duration; }, 0);
    this.time = 0;
    this.playing = false;
    this.lastFrame = null;
    this.emit();
  }

  get state() {
    const index = this.starts.findLastIndex(start => this.time >= start);
    const step = this.steps[index];
    return { index, step, fraction: Math.min(1, (this.time - this.starts[index]) / step.duration),
      time: this.time, duration: this.duration, progress: this.time / this.duration, playing: this.playing };
  }

  emit() { this.changed(this.state); }

  seek(time) {
    if (!Number.isFinite(time)) throw new TypeError('Assembly time must be finite');
    this.time = Math.max(0, Math.min(this.duration, time));
    this.lastFrame = null;
    if (this.time === this.duration) this.playing = false;
    this.emit();
  }

  setSpeed(value) {
    if (!Number.isFinite(value) || value <= 0) throw new TypeError('Assembly speed must be positive');
    this.speed = value;
    this.lastFrame = null;
  }

  play() {
    if (this.time === this.duration) this.time = 0;
    this.playing = true;
    this.lastFrame = null;
    this.emit();
  }

  pause() { this.playing = false; this.lastFrame = null; this.emit(); }

  tick(timestamp) {
    if (!this.playing || !Number.isFinite(timestamp)) return;
    const delta = this.lastFrame === null ? 0 : Math.max(0, timestamp - this.lastFrame) / 1000;
    this.lastFrame = timestamp;
    this.time = Math.min(this.duration, this.time + delta * this.speed);
    if (this.time === this.duration) this.playing = false;
    this.emit();
  }
}
