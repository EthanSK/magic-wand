// Screenshot markup for the assembly viewer. Draw pauses the model and holds
// the view still; moving the view later clears the old screen marks.
// Called by viewer.mjs after its first assembly is ready. GPT-6.1 Sol.

/** Add temporary drawing above the model without editing it. GPT-6.1 Sol. */
export function installDrawingMode({ view, onStart, freezeTargets = [] }) {
  const document = view.ownerDocument, overlay = document.createElement('canvas');
  overlay.className = 'drawing-overlay';
  overlay.setAttribute('aria-label', 'Drawing canvas');
  overlay.tabIndex = 0;
  const context = overlay.getContext('2d'), toolbar = document.createElement('div');
  toolbar.className = 'drawing-tools';
  toolbar.setAttribute('role', 'group');
  toolbar.setAttribute('aria-label', 'Drawing');
  const button = text => {
    const element = document.createElement('button');
    element.type = 'button'; element.textContent = text; toolbar.append(element);
    return element;
  };
  const toggle = button('Draw'), undo = button('Undo'), clearButton = button('Clear');
  view.append(overlay, toolbar);
  let active = false, pointer = null, strokes = [], frozen = [], width = 0, height = 0;
  const refresh = () => {
    toggle.textContent = active ? 'Done' : 'Draw';
    toggle.setAttribute('aria-pressed', String(active));
    overlay.dataset.active = String(active);
    overlay.hidden = !active && !strokes.length;
    undo.hidden = clearButton.hidden = !active && !strokes.length;
    undo.disabled = clearButton.disabled = !strokes.length;
  };
  const paint = points => {
    context.strokeStyle = context.fillStyle = '#ffe072';
    context.lineWidth = 4; context.lineCap = context.lineJoin = 'round';
    context.shadowColor = '#12151c'; context.shadowBlur = 2;
    context.beginPath();
    if (points.length === 1) {
      context.arc(...points[0], 2, 0, Math.PI * 2); context.fill();
    } else {
      context.moveTo(...points[0]);
      for (const point of points.slice(1)) context.lineTo(...point);
      context.stroke();
    }
  };
  const redraw = () => {
    context.clearRect(0, 0, width, height);
    for (const stroke of strokes) paint(stroke);
    refresh();
  };
  const finishStroke = () => {
    const id = pointer; pointer = null;
    if (id !== null && overlay.hasPointerCapture(id)) overlay.releasePointerCapture(id);
  };
  const clear = () => { finishStroke(); strokes = []; redraw(); };
  const setActive = value => {
    finishStroke();
    if (value) {
      onStart();
      frozen = freezeTargets.map(element => [element, element.inert]);
      for (const [element] of frozen) element.inert = true;
    } else {
      for (const [element, wasInert] of frozen) element.inert = wasInert;
      frozen = [];
    }
    active = value; refresh();
    if (active) overlay.focus({ preventScroll: true });
  };
  toggle.addEventListener('click', () => setActive(!active));
  undo.addEventListener('click', () => { finishStroke(); strokes.pop(); redraw(); });
  clearButton.addEventListener('click', clear);
  const point = event => {
    const box = overlay.getBoundingClientRect();
    return [event.clientX - box.left, event.clientY - box.top];
  };
  overlay.addEventListener('pointerdown', event => {
    if (!active || pointer !== null || event.isPrimary === false || event.button !== 0) return;
    event.preventDefault(); pointer = event.pointerId; overlay.setPointerCapture(pointer);
    strokes.push([point(event)]); paint(strokes.at(-1)); refresh();
  });
  overlay.addEventListener('pointermove', event => {
    if (event.pointerId !== pointer) return;
    event.preventDefault();
    const stroke = strokes.at(-1), samples = event.getCoalescedEvents?.();
    for (const sample of samples?.length ? samples : [event]) {
      const next = point(sample); paint([stroke.at(-1), next]); stroke.push(next);
    }
  });
  for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) {
    overlay.addEventListener(name, event => { if (event.pointerId === pointer) finishStroke(); });
  }
  overlay.addEventListener('wheel', event => event.preventDefault(), { passive: false });
  // Shared viewer shortcuts also listen on document. Drawing owns its keys so
  // F/0/arrows cannot shift the model under the pen. GPT-6.1 Sol.
  document.addEventListener('keydown', event => {
    if (!active) return;
    event.stopPropagation();
    if (event.key === 'Escape') {
      event.preventDefault(); setActive(false); toggle.focus();
    } else if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'z') {
      event.preventDefault(); finishStroke(); strokes.pop(); redraw();
    }
  }, true);
  const resize = () => {
    const box = view.getBoundingClientRect();
    if (box.width === width && box.height === height) return;
    // Resizing changes the camera projection. Old ink must not point at another
    // part after the pane changes size. GPT-6.1 Sol.
    finishStroke(); strokes = []; width = box.width; height = box.height;
    const ratio = Math.min(document.defaultView.devicePixelRatio || 1, 2);
    overlay.width = Math.round(width * ratio); overlay.height = Math.round(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0); redraw();
  };
  new ResizeObserver(resize).observe(view);
  resize(); refresh();
  return { clear };
}
