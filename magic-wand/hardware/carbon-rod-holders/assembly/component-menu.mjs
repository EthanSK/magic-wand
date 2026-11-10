// Older model pages keep their own geometry, but expose the same current
// component menu so a guard-only view cannot strand the user away from assembly.
import { legacyR20 } from './legacy-r20.mjs';
const base = new URL('./', import.meta.url);
try {
  const catalog = await fetch(new URL('catalog.json', base), { cache: 'no-store' }).then(response => response.json());
  const versionId = document.body.dataset.assemblyVersion || catalog.current;
  const version = catalog.versions.find(item => item.id === versionId);
  const guide = version.legacy ? await legacyR20() : await fetch(new URL(version.guide, base)).then(response => response.json());
  const label = document.createElement('label'); label.textContent = 'All components';
  const select = document.createElement('select'); select.id = 'all-components'; select.style.width = '100%';
  select.append(new Option('Choose a component', ''), ...Object.entries(guide.modules).map(([id, module]) => new Option(module.label, id)));
  if (version.helper) select.append(new Option('Wipe tower · discard', 'wipe_tower'));
  label.append(select); document.querySelector('aside h1').after(label);
  select.addEventListener('change', () => {
    if (!select.value) return;
    const url = new URL('./', base);
    url.searchParams.set('version', version.id);
    url.searchParams.set('component', select.value);
    location.assign(url);
  });
} catch {
  // An offline or unavailable catalog must not break a frozen model's viewer.
  const link = document.createElement('a'); link.href = base.href; link.textContent = 'All components and assembly';
  document.querySelector('aside h1').after(link);
}
