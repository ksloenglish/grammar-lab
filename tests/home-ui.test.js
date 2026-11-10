import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { assemble } from '../site/js/core.js';
import { spellingStepsMarkup } from '../site/js/effects.js';

const site = new URL('../site/', import.meta.url);
const html = readFileSync(new URL('index.html', site), 'utf8');
const app = readFileSync(new URL('js/app.js', site), 'utf8');
const css = readFileSync(new URL('css/styles.css', site), 'utf8');

test('the Lab has no sound control, playback or Web Audio generation', () => {
  assert.doesNotMatch(html, /sound-toggle|<audio\b|<video\b/i);
  for (const name of readdirSync(new URL('js/', site))) {
    if (!name.endsWith('.js')) continue;
    const source = readFileSync(new URL(`js/${name}`, site), 'utf8');
    assert.doesNotMatch(source, /AudioContext|\bnew\s+Audio\s*\(|createOscillator|soundOn|sound-toggle/, name);
  }
});

test('mobile Lab home remains a labelled link rather than an icon-only control', () => {
  assert.match(html, /<a class="home-link" href="#home" data-route="home">Lab home<\/a>/);
  for (const rule of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    if (!rule[1].includes('.home-link')) continue;
    assert.doesNotMatch(rule[2], /font-size:\s*0(?:\s|;|$)/);
    assert.doesNotMatch(rule[1], /\.home-link::before/);
  }
});

test('Home uses a natural heading and an explicit final-y operation', () => {
  assert.match(app, /<h2 class="specimen-label">How to build a word<\/h2>/);
  assert.doesNotMatch(app, /WORD EXAMPLE|BUILD A WORD/);
  assert.match(app, /class="demo-token operation" role="img" aria-label="Remove the final y"/);
  assert.match(app, /class="demo-cross" aria-hidden="true">✕<\/span><span aria-hidden="true">y<\/span>/);
  const homeSource = app.slice(app.indexOf('function homeView()'), app.indexOf('async function setupView('));
  assert.doesNotMatch(homeSource, /spellingStepsMarkup|spelling-change|deleted-letter/);
  assert.match(app, /spellingStepsMarkup\(assembled\.parts, e\)/);
});

test('the Home recipe removes y before joining ier and shows the intermediate stem', () => {
  const demo = assemble({ blocks: [
    { id: 'base', label: 'easy', kind: 'word' },
    { id: 'remove-y', label: 'Remove y', kind: 'operation', operation: 'remove-final-y' },
    { id: 'suffix', label: '-ier', kind: 'suffix' }
  ] }, ['base', 'remove-y', 'suffix']);
  assert.equal(demo.text, 'easier');
  const markup = spellingStepsMarkup(demo.parts, value => value);
  assert.match(markup, /eas<s class="deleted-letter">y<\/s>/);
  assert.match(markup, /class="spelling-word">eas<\/span>/);
  assert.match(markup, /class="spelling-word completed">easier<\/span>/);
});
