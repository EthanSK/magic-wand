import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { findGuides } from '../docs/how-to/gallery.mjs';
const root = new URL('../', import.meta.url);
const index = () => JSON.parse(readFileSync(new URL('docs/how-to/tutorials.json', root)));
test('guide search finds distinct user actions and handles empty and absent matches', () => {
 const guides = index().guides;
 assert.equal(guides.length, 12);
 assert.ok(findGuides(guides,'How do I scroll sideways?').some(g => g.id === 'scroll-sideways'));
 assert.ok(findGuides(guides,'drag').some(g => g.id === 'drag'));
 assert.ok(findGuides(guides,'dictate').some(g => g.id === 'dictate'));
 assert.equal(findGuides(guides,'').length,12);
 assert.equal(findGuides(guides,'unrelated action 123').length,0);
});
test('each guide has public assets, a stable direct link and optional-review guidance', () => {
 for (const guide of index().guides) {
  assert.equal(guide.url, `https://ethansk.github.io/magic-wand/how-to/#${guide.id}`);
  for (const field of ['video','poster','captions','transcript']) assert.ok(existsSync(new URL(guide[field].replace('https://ethansk.github.io/magic-wand/','docs/'),root)));
  if (['review-changes','stage-files'].includes(guide.id)) assert.match(guide.optionNote,/nods and shakes/);
 }
 const html=readFileSync(new URL('docs/how-to/index.html',root),'utf8');
 assert.match(html,/<dialog id="player" aria-labelledby="player-title">/);
 assert.match(html,/<video[^>]*controls[^>]*playsinline/);
 assert.equal((html.match(/class="howto-card"/g)||[]).length,12);
 assert.match(html,/href="videos\/drag.mp4\?v=[0-9a-f]{10}"/);
});
test('tutorial media and storyboards are current', () => {
 const r=spawnSync('python3',['scripts/tutorials_build.py'],{cwd:root,encoding:'utf8'});
 assert.equal(r.status,0,r.stdout+r.stderr);
});
test('drag demonstration keeps the two presses within the actual double-tap window', () => {
 const manifest=JSON.parse(readFileSync(new URL('tutorials/tutorials.json',root)));
 const t=manifest.tutorials.find(t=>t.id==='drag');
 const actions=t.beats[0].actions;
 const window=t.narration.beats[0].seconds+manifest.video.gapSeconds;
 const time=a=>a.at*window+(a.atS||0);
 const tap=actions.find(a=>a.tap==='bottom'),held=actions.find(a=>a.press==='bottom');
 assert.ok(time(held)-time(tap)>.14,'first press must release before second begins');
 assert.ok(time(held)-time(tap)-.14<.3,'second press must begin within the receiver double-tap window');
});
