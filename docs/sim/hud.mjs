// The Agentic Mouse side of the wand HUD, for the website demo.
//
// A JavaScript port of Agentic Mouse's wand grid navigator, wheel-detent tracker and persistent
// control state machine (its wand support is in Ethan's local build, not yet published). It keeps
// the same tuning and phases; the cards only report what they would do instead of running it.

const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

/** Continuous outline position over the card grid, with hysteresis and diagonal steps. */
export class WandGridNavigator {
  constructor(rows, start, tuning) {
    this.rows = rows;
    this.tuning = tuning;
    this.row = 0;
    this.column = 0;
    rows.some((cells, rowIndex) => {
      const columnIndex = cells.indexOf(start);
      if (columnIndex < 0) return false;
      this.row = rowIndex;
      this.column = columnIndex;
      return true;
    });
    this.positionX = this.column;
    this.positionY = this.row;
    this.headingX = 0;
    this.headingY = 0;
    this.diagonalHeading = false;
  }

  get focusedCell() { return this.rows[this.row][this.column]; }

  get pointerFocus() {
    const boundary = 0.5 + this.tuning.hysteresis;
    return {
      cell: this.focusedCell,
      pullX: (this.positionX - this.column) / boundary,
      pullY: (this.positionY - this.row) / boundary,
    };
  }

  /** Apply one angular delta in degrees. Returns true when the outlined card changed. */
  apply(deltaX, deltaY) {
    if (!Number.isFinite(deltaX) || !Number.isFinite(deltaY)) return false;
    const width = this.rows[0].length;
    const height = this.rows.length;
    let dx = width > 1 ? deltaX / this.tuning.degreesPerColumn : 0;
    let dy = height > 1 ? deltaY / this.tuning.degreesPerRow : 0;
    this.updateHeading(dx, dy);
    if (!this.diagonalHeading) {
      if (Math.abs(this.headingX) >= Math.abs(this.headingY)) dy *= 1 - this.tuning.minorAxisAttenuation;
      else dx *= 1 - this.tuning.minorAxisAttenuation;
    }
    // Outward travel at an edge is discarded: no wrapping and no hidden overshoot.
    this.positionX = clamp(this.positionX + dx, 0, width - 1);
    this.positionY = clamp(this.positionY + dy, 0, height - 1);
    const before = [this.column, this.row];
    this.resolveSteps(width - 1, height - 1);
    return before[0] !== this.column || before[1] !== this.row;
  }

  updateHeading(dx, dy) {
    const length = Math.hypot(dx, dy);
    if (length <= 0) return;
    const keep = Math.exp(-length / this.tuning.headingMemory);
    this.headingX = this.headingX * keep + dx;
    this.headingY = this.headingY * keep + dy;
    const major = Math.max(Math.abs(this.headingX), Math.abs(this.headingY));
    const minor = Math.min(Math.abs(this.headingX), Math.abs(this.headingY));
    if (Math.hypot(major, minor) < 0.05) return;
    const offAxis = (Math.atan2(minor, major) * 180) / Math.PI;
    const boundary = (Math.atan(1 / this.tuning.dominantAxisRatio) * 180) / Math.PI;
    if (this.diagonalHeading) {
      if (offAxis < boundary - this.tuning.headingHysteresisDegrees) this.diagonalHeading = false;
    } else if (offAxis > boundary + this.tuning.headingHysteresisDegrees) {
      this.diagonalHeading = true;
    }
  }

  resolveSteps(maximumColumn, maximumRow) {
    const boundary = 0.5 + this.tuning.hysteresis;
    const returnLimit = 0.5 - this.tuning.hysteresis;
    for (let guard = 0; guard <= maximumColumn + maximumRow + 1; guard++) {
      const offsetX = this.positionX - this.column;
      const offsetY = this.positionY - this.row;
      const leavesX = Math.abs(offsetX) > boundary;
      const leavesY = Math.abs(offsetY) > boundary;
      if (!leavesX && !leavesY) return;
      let stepX = 0;
      let stepY = 0;
      if (this.diagonalHeading && this.headingX !== 0 && this.headingY !== 0) {
        const signX = this.headingX > 0 ? 1 : -1;
        const signY = this.headingY > 0 ? 1 : -1;
        if (offsetX * signX >= this.tuning.diagonalCommitment && offsetY * signY >= this.tuning.diagonalCommitment) {
          stepX = signX;
          stepY = signY;
        }
      }
      if (stepX === 0 && stepY === 0) {
        if (leavesX && (!leavesY || Math.abs(offsetX) >= Math.abs(offsetY))) stepX = offsetX > 0 ? 1 : -1;
        else stepY = offsetY > 0 ? 1 : -1;
      }
      if (this.column + stepX < 0 || this.column + stepX > maximumColumn) stepX = 0;
      if (this.row + stepY < 0 || this.row + stepY > maximumRow) stepY = 0;
      if (stepX === 0 && stepY === 0) return;
      this.column += stepX;
      this.row += stepY;
      if (stepX !== 0 && (this.positionX - this.column) * stepX < -returnLimit) this.positionX = this.column - stepX * returnLimit;
      if (stepY !== 0 && (this.positionY - this.row) * stepY < -returnLimit) this.positionY = this.row - stepY * returnLimit;
    }
  }
}

/** Vertical tilt into wheel detents while a wheel card is held. */
export class WandAdjustTracker {
  constructor(tuning) {
    this.tuning = tuning;
    this.position = 0;
    this.index = 0;
  }

  get progress() {
    return clamp((this.position - this.index) / (0.5 + this.tuning.hysteresis), -1, 1);
  }

  /** Returns "physicalUp" / "physicalDown" steps; surplus travel is dropped, never queued. */
  apply(deltaY) {
    if (!Number.isFinite(deltaY) || deltaY === 0) return [];
    const limit = this.tuning.maximumStepsPerUpdate;
    this.position += deltaY / this.tuning.degreesPerStep;
    const steps = [];
    while (steps.length < limit && this.position > this.index + 0.5 + this.tuning.hysteresis) {
      this.index += 1;
      steps.push("physicalDown");
    }
    while (steps.length < limit && this.position < this.index - 0.5 - this.tuning.hysteresis) {
      this.index -= 1;
      steps.push("physicalUp");
    }
    if (steps.length === limit) this.position = this.index;
    return steps;
  }
}

/**
 * Persistent wand HUD: open, navigate/park the outline, press/release the outlined card,
 * dismiss. Mirrors Agentic Mouse's WandPersistentController phases and watchdog.
 */
export class HudModel {
  constructor({ layout, hud, timers, onChange = () => {}, onContext = () => {} }) {
    this.layout = layout;
    this.config = hud;
    this.timers = timers;
    this.onChange = onChange;
    this.onContext = onContext;
    this.cards = new Map(layout.cards.map((card) => [card.cell, card]));
    this.open = false;
    this.selected = hud.startCell;
    this.focus = { cell: hud.startCell, pullX: 0, pullY: 0 };
    this.hold = null;
    this.lastFinished = null;
    this.watchdog = null;
    this.action = null;
  }

  card(cell) { return this.cards.get(cell); }

  snapshot() {
    const hold = this.hold;
    return {
      open: this.open,
      cell: this.focus.cell,
      pullX: this.focus.pullX || 0,
      pullY: this.focus.pullY || 0,
      pressed: Boolean(hold && !hold.navigation),
      adjusting: hold && hold.wheel ? { progress: hold.tracker.progress, netSteps: hold.netSteps } : null,
      action: this.action,
    };
  }

  emit() { this.onChange(this.snapshot()); }

  setFocus(focus) { this.focus = { pullX: 0, pullY: 0, ...focus }; }

  reset() {
    const wasOpen = this.open;
    this.hold = null;
    this.open = false;
    this.stopWatchdog();
    this.onContext(false);
    if (wasOpen) this.emit();
  }

  report(text, kind = "use") {
    this.action = { text, kind, at: this.timers.now() };
  }

  handle({ phase, id, seq = 0, x = 0, y = 0 }) {
    if (phase === "dismiss") { this.reset(); return; }
    if (phase === "open") {
      if (!this.open) {
        this.selected = this.config.startCell;
        this.setFocus({ cell: this.selected });
        this.open = true;
        this.action = null;
      }
      this.startWatchdog();
      this.onContext(true);
      this.emit();
      return;
    }
    if (!this.open) return;
    const now = this.timers.now();
    switch (phase) {
      case "navigate":
      case "press": {
        if (id === this.lastFinished) return;
        if (this.hold) {
          if (this.hold.id === id) return;
          this.reset();
          return;
        }
        this.selected = this.focus.cell;
        const card = this.card(this.selected);
        const wheel = phase === "press" && card && card.wheel && this.config.adjustableWheels.includes(card.wheel.id) ? card.wheel : null;
        this.hold = {
          id, seq, last: { x: 0, y: 0 }, received: now, started: now, cell: this.selected,
          navigation: phase === "navigate" ? new WandGridNavigator(this.layout.rows, this.selected, this.config.navigation) : null,
          wheel, tracker: new WandAdjustTracker(this.config.adjust), netSteps: 0, sentSteps: 0,
        };
        break;
      }
      case "motion": {
        const hold = this.hold;
        if (!hold || hold.id !== id || seq <= hold.seq) return;
        const dx = x - hold.last.x;
        const dy = y - hold.last.y;
        hold.seq = seq;
        hold.last = { x, y };
        hold.received = now;
        if (hold.navigation) {
          hold.navigation.apply(dx, dy);
          this.selected = hold.navigation.focusedCell;
          this.setFocus(hold.navigation.pointerFocus);
        } else if (hold.wheel) {
          for (const step of hold.tracker.apply(dy)) {
            // Agentic Mouse feeds a physical upward tilt to the wheel resolver as "down".
            const label = step === "physicalUp" ? hold.wheel.down : hold.wheel.up;
            hold.sentSteps += 1;
            hold.netSteps += step === "physicalUp" ? 1 : -1;
            if (label) this.report(label, "wheel");
          }
        }
        break;
      }
      case "park":
      case "release": {
        const hold = this.hold;
        if (!hold || hold.id !== id || seq <= hold.seq) return;
        this.hold = null;
        this.lastFinished = hold.id;
        if (!hold.navigation && !hold.sentSteps) {
          const card = this.card(hold.cell);
          if (card) this.report(card.opens ? `Opens ${card.title}` : card.title);
        }
        this.selected = hold.navigation ? hold.navigation.focusedCell : hold.cell;
        this.setFocus({ cell: this.selected });
        break;
      }
      default:
        return;
    }
    this.emit();
  }

  startWatchdog() {
    if (this.watchdog !== null) return;
    this.watchdog = this.timers.setInterval(() => {
      if (!this.open) { this.stopWatchdog(); return; }
      const hold = this.hold;
      const now = this.timers.now();
      if (hold && (now - hold.received > 1 || now - hold.started > 30)) { this.reset(); return; }
      this.onContext(true);
    }, 250);
  }

  stopWatchdog() {
    if (this.watchdog !== null) this.timers.clearInterval(this.watchdog);
    this.watchdog = null;
  }
}
