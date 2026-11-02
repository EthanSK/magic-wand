// Keep one viewer address while archived revisions retain their exact models.
// Returning to this tab checks the generated pointer without polling or
// resetting the camera when the model has not changed.
export function modelURL(record, base) {
  if (!/^carbon-rod-holders-r\d+-[a-z0-9-]+$/.test(record?.revision) ||
      !/^[a-f0-9]{64}$/.test(record?.scene_sha256)) {
    throw new Error('Invalid model revision');
  }
  const url = new URL(`../../${record.revision}/preview/`, base);
  url.searchParams.set('v', record.scene_sha256);
  return url.href;
}

export function followCurrent({ frame, status, base, fetchCurrent }) {
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

if (typeof document !== 'undefined') {
  const refresh = followCurrent({ frame: document.getElementById('model'),
    status: document.getElementById('status'), base: window.location.href,
    fetchCurrent: (...args) => fetch(...args) });
  window.addEventListener('pageshow', refresh);
  window.addEventListener('focus', refresh);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  refresh();
}
