import { watchCurrent } from '../preview/watch-current.mjs';

// The catalog's "current" is the default build. A newer trial can already be available.
function revisionNumber(id) {
  return /^r\d+$/.test(id) ? Number(id.slice(1)) : 0;
}

function newestRevision(catalog) {
  let latest;
  for (const { id } of catalog.versions) {
    if (revisionNumber(id) > revisionNumber(latest)) latest = id;
  }
  return latest;
}

export async function readCatalog() {
  const response = await fetch(new URL('catalog.json', import.meta.url), { cache: 'no-store' });
  if (!response.ok) throw new Error('Assembly versions could not be loaded');
  return response.json();
}

export function watchAssemblyVersions(catalog, button) {
  let latest = newestRevision(catalog);
  let displayed;
  let checking = false;

  function render() {
    button.hidden = !displayed || revisionNumber(displayed) >= revisionNumber(latest);
  }

  async function refresh() {
    if (document.hidden || checking) return;
    checking = true;
    try {
      latest = newestRevision(await readCatalog());
      render();
    } catch {
      // Keep the last successful check when the viewer server is briefly unavailable.
    } finally {
      checking = false;
    }
  }

  button.addEventListener('click', () => {
    const url = new URL(window.location.href);
    url.searchParams.set('version', latest);
    window.location.assign(url.href);
  });
  watchCurrent(refresh, window, document, 5_000);

  return version => {
    displayed = version;
    render();
  };
}
