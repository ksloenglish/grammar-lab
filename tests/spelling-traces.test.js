import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assemble } from '../site/js/core.js';
import { prepareAdaptiveQuestion } from '../site/js/comparison-blocks.js';
import { spellingStepsMarkup } from '../site/js/effects.js';

const questions = JSON.parse(readFileSync(new URL('../site/data/adjectives-questions.json', import.meta.url), 'utf8')).questions;
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

test('doubling adds a consonant without marking any letter as deleted', () => {
  for (const degree of ['comparative', 'superlative']) {
    const question = prepareAdaptiveQuestion(questions.find(item => item.base === 'big' && item.degree === degree));
    const answer = assemble(question, question.correctSequences[0]);
    const markup = spellingStepsMarkup(answer.parts, escape);
    assert.match(markup, /class="spelling-word">big<\/span>/);
    assert.match(markup, /class="spelling-word">bigg<\/span>/);
    assert.match(markup, degree === 'comparative' ? /class="spelling-word completed">bigger<\/span>/ : /class="spelling-word completed">biggest<\/span>/);
    assert.doesNotMatch(markup, /deleted-letter|<s\b/);
  }
});

test('final-y deletion still crosses out only the removed y', () => {
  const question = prepareAdaptiveQuestion(questions.find(item => item.base === 'happy' && item.degree === 'comparative'));
  const answer = assemble(question, question.correctSequences[0]);
  const markup = spellingStepsMarkup(answer.parts, escape);
  assert.match(markup, /happ<s class="deleted-letter">y<\/s>/);
  assert.match(markup, /class="spelling-word">happ<\/span>/);
  assert.match(markup, /class="spelling-word completed">happier<\/span>/);
});

test('noisy plus -iest keeps y and cannot display a deletion strip without the operation', () => {
  const question = questions.find(item => item.base === 'noisy' && item.degree === 'superlative');
  const ids = ['noisy', '-iest'].map(label => question.blocks.find(block => block.label === label).id);
  const answer = assemble(question, ids);
  assert.equal(answer.text, 'noisyiest');
  assert.equal(spellingStepsMarkup(answer.parts, escape), '');
});
