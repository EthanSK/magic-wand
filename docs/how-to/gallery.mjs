import { filterGuides, parseLocation } from './guides.mjs';
export const findGuides = (guides, query) => filterGuides(guides, query);

if (typeof document !== 'undefined') {
  const guides = JSON.parse(document.getElementById('guide-data').textContent);
  const input = document.getElementById('howto-q');
  const dialog = document.getElementById('player');
  const video = document.getElementById('player-video');
  const cards = [...document.querySelectorAll('.howto-card')];
  let opener = null;
  function filter() {
    const visible = new Set(findGuides(guides, input.value).map(g => g.id));
    cards.forEach(card => { card.hidden = !visible.has(card.dataset.id); });
    document.getElementById('howto-count').textContent = `${visible.size} ${visible.size === 1 ? 'video' : 'videos'}`;
    document.getElementById('howto-empty').hidden = visible.size !== 0;
    const url = new URL(location.href);
    input.value.trim() ? url.searchParams.set('q', input.value.trim()) : url.searchParams.delete('q');
    history.replaceState(null, '', url);
  }
  function openGuide(guide, autoplay = false) {
    if (!guide || typeof dialog.showModal !== 'function') return false;
    opener = document.activeElement;
    document.getElementById('player-title').textContent = guide.question;
    document.getElementById('player-summary').textContent = [guide.summary, guide.optionNote].filter(Boolean).join(' ');
    document.getElementById('player-steps').replaceChildren(...guide.steps.map(text => { const li = document.createElement('li'); li.textContent = text; return li; }));
    for (const [id, field] of [['player-transcript','transcript'],['player-download','video']]) document.getElementById(id).href = guide[field];
    document.getElementById('player-link').href = `#${guide.id}`;
    video.pause(); video.src = guide.video; video.poster = guide.poster;
    video.replaceChildren();
    const track = document.createElement('track'); Object.assign(track, {kind:'captions',label:'English',srclang:'en',src:guide.captions,default:true});video.append(track);
    video.load();
    if (!dialog.open) dialog.showModal();
    history.replaceState(null, '', `${location.pathname}${location.search}#${guide.id}`);
    if (autoplay) video.play().catch(() => {});
    return true;
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-guide]');
    if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    if (openGuide(guides.find(g => g.id === link.dataset.guide), true)) event.preventDefault();
  });
  dialog.addEventListener('close', () => {
    video.pause();video.removeAttribute('src');video.load();
    history.replaceState(null, '', `${location.pathname}${location.search}`);
    if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
  });
  input.addEventListener('input', filter);
  document.querySelector('.howto-search').addEventListener('submit', e => e.preventDefault());
  document.querySelector('.howto-search').addEventListener('reset', () => {input.value = '';filter();input.focus();});
  const fromHash = () => openGuide(guides.find(g => g.id === parseLocation(location.href, guides).id), false);
  input.value = new URL(location.href).searchParams.get('q') || '';filter();fromHash();
  window.addEventListener('hashchange', fromHash);
}
