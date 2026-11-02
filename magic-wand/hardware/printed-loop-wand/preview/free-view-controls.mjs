// Shared immediate mouse/touch bindings and view helpers for the accessory
// viewers. Keep these controls identical across old and current geometry.
export function bindFreeViewControls({ canvas, input, height, width = height, render, wheel, chooseMode, fit, changed = () => {} }) {
  canvas.addEventListener('pointerdown', event => {
    if (![0, 1, 2].includes(event.button)) return;
    event.preventDefault();
    canvas.focus({ preventScroll: true });
    const mode = event.button === 1 || event.button === 2 || event.shiftKey ? 'move' : input.mode;
    input.pointerDown(event.pointerId, event.clientX, event.clientY, mode);
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener('pointermove', event => {
    if (input.pointerMove(event.pointerId, event.clientX, event.clientY, height(), width())) { changed(); render(); }
  });
  for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) canvas.addEventListener(type, event => input.pointerUp(event.pointerId));
  canvas.addEventListener('contextmenu', event => event.preventDefault());
  canvas.addEventListener('auxclick', event => event.preventDefault());
  window.addEventListener('blur', () => input.cancel());
  canvas.addEventListener('wheel', event => {
    const distance = input.distance;
    if (wheel(event)) {
      if (input.distance !== distance && Number.isFinite(event.clientX) && Number.isFinite(event.clientY)) {
        const bounds = canvas.getBoundingClientRect();
        input.keepZoomAnchor(2 * (event.clientX - bounds.left) / bounds.width - 1,
          1 - 2 * (event.clientY - bounds.top) / bounds.height, bounds.width / bounds.height, distance);
      }
      event.preventDefault(); changed(); render();
    }
  }, { passive: false });
  // Toolbar clicks should not disable the viewer shortcuts. Keep ordinary
  // form typing and arrow navigation outside the canvas untouched.
  (canvas.ownerDocument || canvas).addEventListener('keydown', event => {
    if (event.metaKey || event.altKey || event.ctrlKey) return;
    if (event.target?.closest?.('input,select,textarea,[contenteditable="true"]')) return;
    if (event.key.startsWith('Arrow') && event.target && event.target !== canvas) return;
    if (event.key.toLowerCase() === 'f') { event.preventDefault(); fit(); return; }
    const alias = { r: 'turn', p: 'move' }[event.key.toLowerCase()];
    if (alias) { event.preventDefault(); chooseMode(alias); return; }
    const mode = input.mode;
    if (input.key(event, height())) {
      event.preventDefault();
      if (input.mode !== mode) chooseMode(input.mode);
      changed(); render();
    }
  });
}

export function installViewTools({ view, input, fit, render }) {
  const reset = document.getElementById('reset');
  reset.parentElement.style.cssText = 'display:grid;grid-template-columns:36px 36px 1fr 1.4fr;gap:6px';
  const frame = document.createElement('button');
  frame.id = 'frame'; frame.textContent = 'Frame'; frame.title = 'Fit visible parts (F)';
  frame.addEventListener('click', fit); reset.before(frame);
  for (const button of reset.parentElement.children) button.style.padding = '8px 5px';
  const views = document.createElement('div'); views.className = 'row'; views.id = 'standard-views';
  views.style.cssText = 'display:grid;grid-template-columns:repeat(4,1fr);gap:6px';
  for (const [label, name] of [['Front', 'front'], ['Top', 'top'], ['Side', 'right'], ['Iso', 'isometric']]) {
    const button = document.createElement('button'); button.textContent = label;
    button.style.padding = '7px 4px';
    button.setAttribute('aria-label', label + ' view');
    button.addEventListener('click', () => { input.setView(name); fit(); }); views.append(button);
  }
  reset.parentElement.after(views);
  const override = document.getElementById('wand-scroll').closest('label'); views.after(override);
  const help = document.createElement('p'); help.textContent = 'F: frame · 0: reset · R/P/Z: modes';
  help.style.cssText = 'font-size:12px;color:#a9bacb;margin:8px 0'; override.after(help);
  const namespace = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(namespace, 'svg');
  svg.setAttribute('viewBox', '0 0 80 80'); svg.setAttribute('aria-label', 'View orientation');
  svg.setAttribute('role', 'img'); svg.style.cssText = 'position:absolute;right:12px;top:10px;width:80px;height:80px;pointer-events:none';
  const axes = [];
  for (let index = 0; index < 3; index++) for (const sign of [-1, 1]) {
    const group = document.createElementNS(namespace, 'g'), line = document.createElementNS(namespace, 'line');
    const dot = document.createElementNS(namespace, 'circle'), text = document.createElementNS(namespace, 'text');
    const color = ['#f48c83', '#88d2a0', '#8cb9f2'][index];
    line.setAttribute('stroke', color); line.setAttribute('stroke-width', '1.8');
    line.setAttribute('x1', '40'); line.setAttribute('y1', '40');
    dot.setAttribute('r', sign === 1 ? '8' : '3'); dot.setAttribute('fill', color);
    text.setAttribute('fill', '#15202b'); text.setAttribute('text-anchor', 'middle');
    text.setAttribute('dominant-baseline', 'central'); text.setAttribute('font-size', '10');
    text.setAttribute('font-family', 'system-ui'); text.setAttribute('font-weight', '700');
    text.textContent = sign === 1 ? ['X', 'Y', 'Z'][index] : '';
    group.append(line, dot, text); svg.append(group); axes.push({ index, sign, group, line, dot, text });
  }
  view.append(svg);
  const controls = { update() {
    const basis = input.cameraBasis();
    for (const axis of [...axes].sort((a, b) => a.sign*basis.back[a.index] - b.sign*basis.back[b.index])) {
      const x = 40 + axis.sign * basis.right[axis.index] * 26, y = 40 - axis.sign * basis.up[axis.index] * 26;
      axis.line.setAttribute('x2', x); axis.line.setAttribute('y2', y);
      axis.dot.setAttribute('cx', x); axis.dot.setAttribute('cy', y);
      axis.text.setAttribute('x', x); axis.text.setAttribute('y', y);
      axis.group.setAttribute('opacity', axis.sign*basis.back[axis.index] < -.1 ? '.38' : '1');
      svg.append(axis.group);
    }
  } };
  controls.update();
  return controls;
}
