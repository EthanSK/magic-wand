// Keep the startup error boundary outside the module graph. A failed static import
// prevents viewer.mjs from reaching its own error display at all.
(() => {
  const source = document.currentScript.dataset.module;
  const status = document.getElementById('startup-status');
  const errorBox = document.getElementById('error');
  const viewer = document.createElement('script');
  viewer.type = 'module';
  viewer.src = source;
  let failureShown = false;

  function failed() {
    if (failureShown) return;
    failureShown = true;
    window.removeEventListener('error', executionFailed);
    status.hidden = true;
    document.body.dataset.ready = 'error';
    const message = document.createElement('p');
    message.textContent = errorBox.textContent || 'Assembly could not be loaded.';
    const reload = document.createElement('button');
    reload.type = 'button';
    reload.textContent = 'Reload';
    reload.addEventListener('click', () => window.location.reload());
    errorBox.replaceChildren(message, reload);
    errorBox.classList.add('startup-error');
    errorBox.style.display = 'flex';
  }

  function executionFailed(event) {
    // Resource errors belong to the script's error listener. This listener also
    // covers failures during early evaluation, including WebGL construction.
    if (event.target === window) failed();
  }

  window.addEventListener('error', executionFailed);
  viewer.addEventListener('error', () => {
    // A fresh document can recover a failed module fetch, including a static
    // dependency. Limit recovery to one reload of this history entry so a
    // broken build still gives the reader a usable error and Reload button.
    const history = window.history;
    if (!failureShown && history && !history.state?.assemblyModuleRetried) {
      try {
        history.replaceState({ ...history.state, assemblyModuleRetried: true }, '');
        window.location.reload();
        return;
      } catch {
        // An embedded viewer can disallow history writes.
      }
    }
    failed();
  }, { once: true });
  // The script load event can precede the catalog and mesh requests.
  window.addEventListener('assembly-startup-finished', () => {
    window.removeEventListener('error', executionFailed);
    status.hidden = true;
    if (document.body.dataset.ready !== 'true') {
      failed();
    } else if (window.history?.state?.assemblyModuleRetried) {
      const { assemblyModuleRetried, ...rest } = window.history.state;
      try { window.history.replaceState(rest, ''); } catch { /* The model is ready. */ }
    }
  }, { once: true });
  document.body.dataset.ready = 'loading';
  document.body.append(viewer);
})();
