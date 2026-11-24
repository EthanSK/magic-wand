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
  viewer.addEventListener('error', failed, { once: true });
  viewer.addEventListener('load', () => {
    window.removeEventListener('error', executionFailed);
    status.hidden = true;
    if (document.body.dataset.ready !== 'true') failed();
  }, { once: true });
  document.body.dataset.ready = 'loading';
  document.body.append(viewer);
})();
