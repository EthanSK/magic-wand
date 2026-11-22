export function watchCurrent(refresh, browserWindow, browserDocument, interval = 1000) {
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
    if (timer === null) timer = browserWindow.setInterval(refresh, interval);
  }
  browserWindow.addEventListener('pageshow', start);
  browserWindow.addEventListener('pagehide', stop);
  browserWindow.addEventListener('focus', start);
  browserDocument.addEventListener('visibilitychange', () => {
    if (browserDocument.hidden) stop(); else start();
  });
  start();
}
