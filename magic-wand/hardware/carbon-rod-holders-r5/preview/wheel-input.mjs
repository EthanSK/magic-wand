// Mouse scroll zooms independently of the drag mode. A deliberate wand
// override turns scroll into rotation; DOM wheel events carry no device ID.
// Reuse the shared immediate-input controls without retuning their gain/timing.
export function applyViewerWheel(input, event, height, pageHeight, wandRotate = false) {
  const mode = input.mode;
  input.mode = wandRotate && !event.ctrlKey ? 'turn' : 'zoom';
  try { return input.wheel(event, height, pageHeight); }
  finally { input.mode = mode; }
}
