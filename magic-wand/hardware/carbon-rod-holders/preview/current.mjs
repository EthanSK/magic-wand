// Keep one viewer address while archived revisions retain their exact models.
// Watch the generated pointer while the page is visible, including when it
// stays open beside the chat. Unchanged geometry never resets the camera.
export function modelURL(record, base) {
  if (!/^carbon-rod-holders-r\d+-[a-z0-9-]+$/.test(record?.revision) ||
      !/^[a-f0-9]{64}$/.test(record?.scene_sha256)) {
    throw new Error('Invalid model revision');
  }
  const url = new URL(`../../${record.revision}/preview/`, base);
  url.searchParams.set('v', record.scene_sha256);
  return url.href;
}

export function followCurrent({ frame, status, base, fetchCurrent, reload }) {
  let pending = null;
  let displayed = null;
  function refresh() {
    if (pending) return pending;
    pending = (async () => {
      try {
        const response = await fetchCurrent(new URL('current.json', base), { cache: 'no-store' });
        if (!response.ok) throw new Error(`Model request failed (${response.status})`);
        const url = modelURL(await response.json(), base);
        if (url !== displayed) {
          // A changed model gets a fresh page at this same permanent address.
          // Changing an existing embedded document's src left its old model
          // painted during the live check. An unchanged hash keeps the view.
          if (displayed !== null) {
            displayed = url;
            reload();
            return;
          }
          frame.src = url;
          displayed = url;
        }
        frame.hidden = false;
        status.hidden = true;
      } catch (error) {
        // Preserve a previously loaded working model if a refresh fails.
        status.textContent = `Unable to load model: ${error.message}`;
        status.hidden = false;
      } finally {
        pending = null;
      }
    })();
    return pending;
  }
  return refresh;
}

export function watchCurrent(refresh, browserWindow, browserDocument) {
  let timer = null;
  function stop() {
    if (timer !== null) browserWindow.clearInterval(timer);
    timer = null;
  }
  function start() {
    if (browserDocument.hidden) return;
    refresh();
    // This observes completed file updates; it never delays model controls.
    // Focus alone misses an already-open viewer or focus inside its iframe.
    if (timer === null) timer = browserWindow.setInterval(refresh, 1000);
  }
  browserWindow.addEventListener('pageshow', start);
  browserWindow.addEventListener('pagehide', stop);
  browserWindow.addEventListener('focus', start);
  browserDocument.addEventListener('visibilitychange', () => {
    if (browserDocument.hidden) stop(); else start();
  });
  start();
}

if (typeof document !== 'undefined') {
  const refresh = followCurrent({ frame: document.getElementById('model'),
    status: document.getElementById('status'), base: window.location.href,
    fetchCurrent: (...args) => fetch(...args), reload: () => window.location.reload() });
  watchCurrent(refresh, window, document);
}
