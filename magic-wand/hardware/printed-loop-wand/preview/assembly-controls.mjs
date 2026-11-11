// Optional assembly player for every shared Three.js viewer. It owns playback
// only; each model supplies its own verified assembly order and pose function.
import { AssemblyTimeline } from './assembly-timeline.mjs';

export function installAssemblyControls({ host, playbackHost, steps, onFrame }) {
  const doc = host.ownerDocument;
  const section = doc.createElement('section'); section.className = 'assembly-controls';
  const heading = doc.createElement('h2'); heading.textContent = 'Assembly';
  const actions = doc.createElement('div'); actions.className = 'row assembly-actions';
  const button = label => { const b = doc.createElement('button'); b.type = 'button'; b.textContent = label; return b; };
  const previous = button('Previous'), play = button('Play'), next = button('Next');
  const speed = doc.createElement('select'); speed.setAttribute('aria-label', 'Playback speed');
  for (const value of [.5, 1, 2]) { const option = doc.createElement('option'); option.value = value; option.textContent = value + '×'; option.selected = value === 1; speed.append(option); }
  actions.append(previous, play, next, speed);
  const seek = doc.createElement('input'); seek.type = 'range'; seek.min = 0; seek.max = 1000; seek.step = 1; seek.value = 0;
  seek.setAttribute('aria-label', 'Assembly progress'); seek.className = 'assembly-progress';
  const progress = doc.createElement('output'); progress.className = 'assembly-count';
  const choices = doc.createElement('div'); choices.className = 'assembly-steps';
  const title = doc.createElement('h3'), caption = doc.createElement('p');
  caption.className = 'assembly-caption';
  if (playbackHost) {
    playbackHost.append(actions, seek, progress);
    section.append(heading, choices, title, caption);
  } else {
    section.append(heading, actions, seek, progress, choices, title, caption);
  }
  host.append(section);
  let raf = 0, disposed = false, lastIndex = -1;
  const timeline = new AssemblyTimeline(steps);
  const frame = now => { raf = 0; if (disposed) return; timeline.tick(now); schedule(); };
  const schedule = () => { if (!disposed && timeline.playing && !raf) raf = requestAnimationFrame(frame); };
  const pause = () => { cancelAnimationFrame(raf); raf = 0; timeline.pause(); };
  timeline.changed = state => {
    onFrame(state);
    seek.value = Math.round(state.progress * 1000);
    progress.textContent = `${state.index + 1} / ${timeline.steps.length}`;
    play.textContent = state.playing ? 'Pause' : state.time === state.duration ? 'Replay' : 'Play';
    previous.disabled = state.time === 0;
    next.disabled = state.time === state.duration;
    for (const [index, b] of [...choices.children].entries()) b.setAttribute('aria-current', index === state.index ? 'step' : 'false');
    if (lastIndex !== state.index) {
      title.textContent = state.step.title; caption.textContent = state.step.caption; lastIndex = state.index;
    }
  };
  const choose = index => { pause(); timeline.seek(timeline.starts[Math.max(0, Math.min(timeline.steps.length - 1, index))]); };
  const rebuild = () => {
    choices.replaceChildren(); lastIndex = -1;
    timeline.steps.forEach((step, index) => { const b = button(`${index + 1}. ${step.title}`); b.addEventListener('click', () => choose(index)); choices.append(b); });
    timeline.emit();
  };
  play.addEventListener('click', () => { if (timeline.playing) pause(); else { timeline.play(); schedule(); } });
  previous.addEventListener('click', () => choose(timeline.state.index - 1));
  next.addEventListener('click', () => {
    if (timeline.state.index === timeline.steps.length - 1) { pause(); timeline.seek(timeline.duration); }
    else choose(timeline.state.index + 1);
  });
  seek.addEventListener('input', () => {
    const time = Number(seek.value) / 1000 * timeline.duration;
    pause(); timeline.seek(time);
  });
  speed.addEventListener('change', () => timeline.setSpeed(Number(speed.value)));
  const visibility = () => { if (doc.hidden) pause(); };
  doc.addEventListener('visibilitychange', visibility);
  rebuild();
  return {
    timeline,
    setSteps(value) { cancelAnimationFrame(raf); raf = 0; timeline.setSteps(value); rebuild(); },
    play() { timeline.play(); schedule(); },
    pause,
    dispose() { pause(); disposed = true; doc.removeEventListener('visibilitychange', visibility); actions.remove(); seek.remove(); progress.remove(); section.remove(); },
  };
}
