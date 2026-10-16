// A stand-in for the Mac's cursor and event stream: what Wand Receiver would post to macOS.
// Coordinates are Mac points on one display; the cursor stays on screen like macOS keeps it.

export class MacScreen {
  constructor({ width = 1728, height = 1117 } = {}) {
    this.width = width;
    this.height = height;
    this.cursor = { x: width / 2, y: height / 2 };
    this.buttonDown = false;
    this.listeners = new Set();
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  emit(event) { for (const listener of this.listeners) listener(event); }

  location() { return { ...this.cursor }; }

  clampPoint(point) {
    return {
      x: Math.min(this.width - 1, Math.max(0, point.x)),
      y: Math.min(this.height - 1, Math.max(0, point.y)),
    };
  }

  /** type: "move" | "drag" | "down" | "up" */
  mouse(type, point, clickCount = 1) {
    this.cursor = this.clampPoint(point);
    if (type === "down") this.buttonDown = true;
    if (type === "up") this.buttonDown = false;
    this.emit({ type, x: this.cursor.x, y: this.cursor.y, clickCount });
  }

  /** One wheel event in lines; positive y scrolls down, positive x scrolls right. */
  scroll(dx, dy) { this.emit({ type: "scroll", dx, dy }); }

  reset() {
    this.cursor = { x: this.width / 2, y: this.height / 2 };
    this.buttonDown = false;
    this.emit({ type: "reset", x: this.cursor.x, y: this.cursor.y });
  }
}
