// The simulated Mac screen: a large light board the wand can click, drag-paint and scroll.
// It only draws what the receiver model posted to the simulated Mac.

const LINE_POINTS = 14; // One wheel line, in Mac points.
const DOCUMENT_SCALE = 3; // The board is three screens wide and tall, so scrolling has room.
const GRID = 96;
const LABEL_GRID = 576;
const COLUMNS = "ABCDEFGHIJKLMNOP";

export class LightBoard {
  constructor(canvas, { mac, reducedMotion = false, onChange = () => {} }) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.mac = mac;
    this.reducedMotion = reducedMotion;
    this.onChange = onChange;
    this.width = mac.width * DOCUMENT_SCALE;
    this.height = mac.height * DOCUMENT_SCALE;
    this.strokes = [];
    this.current = null;
    this.ripples = [];
    this.scrollbarsUntil = 0;
    this.frame = 0;
    this.reset();
    this.unsubscribe = mac.subscribe((event) => this.handle(event));
    this.resize();
  }

  reset() {
    this.scrollX = (this.width - this.mac.width) / 2;
    this.scrollY = (this.height - this.mac.height) / 2;
    this.strokes = [];
    this.current = null;
    this.ripples = [];
    this.request();
  }

  get offset() { return { x: this.scrollX, y: this.scrollY }; }

  documentPoint(event) { return { x: event.x + this.scrollX, y: event.y + this.scrollY }; }

  handle(event) {
    const now = performance.now();
    switch (event.type) {
      case "down":
        this.current = { points: [this.documentPoint(event)], moved: false };
        this.strokes.push(this.current);
        break;
      case "drag":
        if (this.current) {
          this.current.points.push(this.documentPoint(event));
          this.current.moved = true;
        }
        break;
      case "up":
        if (this.current && !this.current.moved && !this.reducedMotion) {
          this.ripples.push({ ...this.documentPoint(event), at: now });
        }
        this.current = null;
        break;
      case "scroll":
        this.scrollX = Math.min(this.width - this.mac.width, Math.max(0, this.scrollX + event.dx * LINE_POINTS));
        this.scrollY = Math.min(this.height - this.mac.height, Math.max(0, this.scrollY + event.dy * LINE_POINTS));
        this.scrollbarsUntil = now + 1100;
        break;
      case "reset":
        this.reset();
        break;
      default:
        break;
    }
    if (this.strokes.length > 400) this.strokes.splice(0, this.strokes.length - 400);
    this.onChange(event);
    this.request();
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    this.canvas.width = Math.max(1, Math.round(rect.width * ratio));
    this.canvas.height = Math.max(1, Math.round(rect.height * ratio));
    this.request();
  }

  request() {
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      this.draw();
    });
  }

  draw() {
    const { context: c, canvas } = this;
    const scale = canvas.width / this.mac.width;
    const now = performance.now();
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.fillStyle = "#0e0d13";
    c.fillRect(0, 0, canvas.width, canvas.height);
    c.setTransform(scale, 0, 0, scale, -this.scrollX * scale, -this.scrollY * scale);

    // Dot grid and coordinates, so scrolling in either direction is visible. Kept quiet so the
    // pointer, strokes and HUD stay the brightest things on the screen.
    const left = Math.floor(this.scrollX / GRID) * GRID;
    const top = Math.floor(this.scrollY / GRID) * GRID;
    c.fillStyle = "rgba(196, 192, 214, 0.16)";
    for (let x = left; x <= this.scrollX + this.mac.width; x += GRID) {
      for (let y = top; y <= this.scrollY + this.mac.height; y += GRID) c.fillRect(x - 2, y - 2, 4, 4);
    }
    c.fillStyle = "rgba(196, 192, 214, 0.24)";
    c.font = "600 34px 'Atkinson Hyperlegible Mono', monospace";
    const labelLeft = Math.floor(this.scrollX / LABEL_GRID) * LABEL_GRID;
    const labelTop = Math.floor(this.scrollY / LABEL_GRID) * LABEL_GRID;
    for (let x = labelLeft; x <= this.scrollX + this.mac.width; x += LABEL_GRID) {
      for (let y = labelTop; y <= this.scrollY + this.mac.height; y += LABEL_GRID) {
        c.fillText(`${COLUMNS[x / LABEL_GRID] || ""}${y / LABEL_GRID + 1}`, x + 18, y + 46);
      }
    }
    c.strokeStyle = "rgba(196, 192, 214, 0.3)";
    c.lineWidth = 3;
    c.strokeRect(0, 0, this.width, this.height);

    // Light painted by drags, and dots stamped by clicks.
    c.lineCap = "round";
    c.lineJoin = "round";
    for (const stroke of this.strokes) {
      c.shadowColor = "rgba(242, 239, 249, 0.75)";
      c.shadowBlur = 18 * scale;
      if (stroke.points.length === 1 || !stroke.moved) {
        const [point] = stroke.points;
        c.fillStyle = "#f2eff9";
        c.beginPath();
        c.arc(point.x, point.y, 11, 0, Math.PI * 2);
        c.fill();
      } else {
        c.strokeStyle = "#f2eff9";
        c.lineWidth = 10;
        c.beginPath();
        stroke.points.forEach((point, index) => (index ? c.lineTo(point.x, point.y) : c.moveTo(point.x, point.y)));
        c.stroke();
      }
    }
    c.shadowBlur = 0;
    this.ripples = this.ripples.filter((ripple) => now - ripple.at < 450);
    for (const ripple of this.ripples) {
      const progress = (now - ripple.at) / 450;
      c.strokeStyle = `rgba(242, 239, 249, ${1 - progress})`;
      c.lineWidth = 4;
      c.beginPath();
      c.arc(ripple.x, ripple.y, 14 + progress * 46, 0, Math.PI * 2);
      c.stroke();
    }

    // macOS-style overlay scrollbars while scrolling.
    c.setTransform(scale, 0, 0, scale, 0, 0);
    if (now < this.scrollbarsUntil) {
      const alpha = Math.min(1, (this.scrollbarsUntil - now) / 300) * 0.55;
      c.fillStyle = `rgba(242, 239, 249, ${alpha})`;
      const barX = (this.scrollX / this.width) * this.mac.width;
      const barY = (this.scrollY / this.height) * this.mac.height;
      roundRect(c, barX, this.mac.height - 16, this.mac.width / DOCUMENT_SCALE, 9, 4.5);
      roundRect(c, this.mac.width - 16, barY + 70, 9, this.mac.height / DOCUMENT_SCALE - 70 / DOCUMENT_SCALE, 4.5);
    }

    drawCursor(c, this.mac.cursor.x, this.mac.cursor.y, this.mac.buttonDown);

    if (this.ripples.length || now < this.scrollbarsUntil) this.request();
  }

  destroy() {
    this.unsubscribe();
    if (this.frame) cancelAnimationFrame(this.frame);
  }
}

function roundRect(c, x, y, width, height, radius) {
  c.beginPath();
  c.roundRect(x, y, width, height, radius);
  c.fill();
}

/** The standard macOS arrow, about 17 × 25 points. */
function drawCursor(c, x, y, pressed) {
  c.save();
  c.translate(x, y);
  if (pressed) c.scale(0.92, 0.92);
  c.beginPath();
  c.moveTo(0, 0);
  c.lineTo(0, 23);
  c.lineTo(5.6, 17.6);
  c.lineTo(9.4, 26.4);
  c.lineTo(13.2, 24.8);
  c.lineTo(9.6, 16.4);
  c.lineTo(17, 16.4);
  c.closePath();
  c.fillStyle = "#000";
  c.strokeStyle = "#fff";
  c.lineWidth = 2.2;
  c.lineJoin = "round";
  c.stroke();
  c.fill();
  c.restore();
}
