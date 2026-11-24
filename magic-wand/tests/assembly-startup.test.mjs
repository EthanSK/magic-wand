import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const source = readFileSync(new URL('../hardware/carbon-rod-holders/assembly/viewer-start.js', import.meta.url), 'utf8');

class Element extends EventTarget {
  constructor(tag) {
    super();
    this.tagName = tag;
    this.children = [];
    this.style = {};
    this.hidden = false;
    this.textContent = '';
    this.classList = new Set();
  }
  append(child) { this.children.push(child); }
  replaceChildren(...children) { this.children = children; }
}

function startup() {
  const status = new Element('p');
  const errorBox = new Element('div');
  const body = new Element('body');
  body.dataset = {};
  const window = new EventTarget();
  let reloads = 0;
  window.location = {reload() { reloads++; }};
  const document = {
    currentScript: {dataset: {module: 'viewer.mjs?v=current'}},
    body,
    getElementById: id => ({'startup-status': status, error: errorBox}[id]),
    createElement: tag => new Element(tag),
  };
  runInNewContext(source, {document, window});
  const viewer = body.children[0];
  return {status, errorBox, body, window, viewer, reloads: () => reloads};
}

test('a failed entry module or static dependency has a reload action outside the module graph', () => {
  const page = startup();
  assert.equal(page.body.dataset.ready, 'loading');
  assert.equal(page.viewer.type, 'module');
  assert.equal(page.viewer.src, 'viewer.mjs?v=current');
  page.viewer.dispatchEvent(new Event('error'));
  assert.equal(page.status.hidden, true);
  assert.equal(page.body.dataset.ready, 'error');
  assert.equal(page.errorBox.children[0].textContent, 'Assembly could not be loaded.');
  const reload = page.errorBox.children[1];
  assert.equal(reload.textContent, 'Reload');
  reload.dispatchEvent(new Event('click'));
  assert.equal(page.reloads(), 1);
});

test('an early execution failure is caught before the viewer can install its own error handler', () => {
  const page = startup();
  page.window.dispatchEvent(new Event('error'));
  assert.equal(page.body.dataset.ready, 'error');
  page.viewer.dispatchEvent(new Event('load'));
  assert.equal(page.errorBox.children[0].textContent, 'Assembly could not be loaded.');
  assert.equal(page.errorBox.children.length, 2);
});

test('startup preserves the viewer error when a model request fails', () => {
  const page = startup();
  page.body.dataset.ready = 'error';
  page.errorBox.textContent = 'Assembly versions could not be loaded';
  page.viewer.dispatchEvent(new Event('load'));
  assert.equal(page.errorBox.children[0].textContent, 'Assembly versions could not be loaded');
  assert.equal(page.errorBox.children[1].textContent, 'Reload');
});

test('a completed viewer hides loading feedback and later errors are outside the startup boundary', () => {
  const page = startup();
  page.body.dataset.ready = 'true';
  page.viewer.dispatchEvent(new Event('load'));
  assert.equal(page.status.hidden, true);
  page.window.dispatchEvent(new Event('error'));
  assert.equal(page.body.dataset.ready, 'true');
  assert.deepEqual(page.errorBox.children, []);
});
