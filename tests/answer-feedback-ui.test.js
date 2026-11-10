import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { assemble, createExperiment } from '../site/js/core.js';

const app = readFileSync(new URL('../site/js/app.js', import.meta.url), 'utf8');
const css = readFileSync(new URL('../site/css/styles.css', import.meta.url), 'utf8');
const escape = text => String(text ?? '').replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[character]));
const start = app.indexOf('function wrongAnswerPreview(');
const end = app.indexOf('\nfunction ', start + 1);
assert.ok(start >= 0 && end > start, 'production stable preview helper exists');
const context = vm.createContext({ e: escape });
vm.runInContext(`${app.slice(start, end)}\nglobalThis.preview = wrongAnswerPreview;`, context);

const question = (moduleId, id) => JSON.parse(readFileSync(new URL(`../site/data/${moduleId}-questions.json`, import.meta.url), 'utf8')).questions.find(q => q.id === id);
const plainText = markup => markup.replace(/<[^>]*>/g, '').replace(/&amp;/g, '&');

test('stable wrong preview preserves the full phrase and marks only intersecting parts', () => {
  const session = createExperiment('adjectives', [question('adjectives', 'adj-024')]);
  const q = session.questions[0];
  const ids = ['the', 'big', 'g'].map(label => q.blocks.find(b => b.label === label).id);
  const assembled = assemble(q, ids);
  assert.equal(assembled.text, 'the bigg');
  for (const problemBlockIds of [[ids[1]], [ids[2]], [ids[1], ids[2]]]) {
    const markup = context.preview(assembled, { problemBlockIds });
    assert.equal(markup, 'the <mark class="answer-error-part">bigg</mark>');
    assert.equal(plainText(markup), assembled.text);
  }
  assert.equal(context.preview(assembled, { problemBlockIds: [] }), 'the bigg');
  assert.equal(context.preview(assembled, { problemBlockIds: ['not-selected'] }), 'the bigg');
});

test('missing-piece labels do not add phantom letters or duplicate text to the answer', () => {
  const assembled = { text: 'better', parts: [{ text: 'better', ids: ['better'] }] };
  const markup = context.preview(assembled, { problemBlockIds: [], missingLabels: ['than'], title: 'Missing than' });
  assert.equal(markup, 'better');
  assert.doesNotMatch(markup, /than|sr-only|aria-hidden|shatter/);
  const trial = app.slice(app.indexOf('function trialView('), app.indexOf('function reportView('));
  assert.match(trial, /<strong id="assembled-answer">\$\{preview\}<\/strong>\$\{wrong \? `<span class="answer-issue-tag">/);
  assert.match(trial, /class="feedback-message"/);
});

test('production preview escapes malicious markup and invalid operation brackets verbatim', () => {
  const parts = [
    { text: '[<img src=x onerror="alert(1)">]', ids: ['invalid'] },
    { text: 'word & "quoted" <script>bad()</script>', ids: ['word'] },
    { text: "[Remove y] '<b>ending</b>'", ids: ['op'] }
  ];
  const assembled = { text: parts.map(p => p.text).join(' '), parts };
  const markup = context.preview(assembled, { problemBlockIds: ['invalid', 'op'] });
  assert.equal(markup, parts.map(part => ['invalid', 'op'].includes(part.ids[0])
    ? `<mark class="answer-error-part">${escape(part.text)}</mark>` : escape(part.text)).join(' '));
  assert.doesNotMatch(markup, /<img|<script|<b>|onerror="/);
  assert.equal((markup.match(/<mark /g) ?? []).length, 2);
  assert.ok(markup.includes('[&lt;img'));
  assert.ok(markup.includes('[Remove y]'));
});

test('scattered-letter markup and animation cannot return in app or CSS', () => {
  assert.doesNotMatch(app + css, /shatter-word|word-fragment|--dx:|--dy:|--rotation:/);
  assert.match(app, /diagnoseAnswer\(question, assembled\.text, session\.assembly\)/);
  assert.match(app, /problemIds\.has\(id\) \? ' has-answer-error'/);
  assert.match(app, /data-feedback-code/);
  assert.match(app, /e\(diagnostic\.title\)/);
  assert.match(app, /correctExplanation\(question\)/);
});

test('fresh bank explanations keep one concise formation rule and the exact purpose of than', () => {
  const than = 'Use than to introduce the other person, thing or action in the comparison.';
  for (const moduleId of ['adjectives', 'adverbs']) {
    const bank = JSON.parse(readFileSync(new URL(`../site/data/${moduleId}-questions.json`, import.meta.url), 'utf8'));
    for (const q of bank.questions) {
      assert.equal(typeof q.explanation, 'string', q.id);
      assert.doesNotMatch(q.explanation, /Use .+ (?:to compare two things|for the top one in a group|in this gap)\./i, q.id);
      assert.equal(q.explanation.split(than).length - 1, q.degree === 'comparative' ? 1 : 0, q.id);
    }
  }
  assert.equal(question('adjectives', 'adj-073').explanation,
    'Good changes its form to better. Use than to introduce the other person, thing or action in the comparison.');
});
