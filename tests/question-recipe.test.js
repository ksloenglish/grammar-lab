import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { prepareAdaptiveQuestion } from '../site/js/comparison-blocks.js';
import { blockDisplayLabel } from '../site/js/ingredients.js';

const source = readFileSync(new URL('../site/js/app.js', import.meta.url), 'utf8');
const helper = source.slice(source.indexOf('function correctRecipeView('), source.indexOf('function trialView('));
const renderRecipe = runInNewContext(helper + '\ncorrectRecipeView;', {
  blockDisplayLabel,
  e: value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
});
const questions = JSON.parse(readFileSync(new URL('../site/data/adjectives-questions.json', import.meta.url), 'utf8')).questions;
const rawBig = questions.find(question => question.base === 'big' && question.degree === 'comparative');

test('unvalidated legacy snapshot metadata cannot break the revealed canonical recipe', () => {
  const question = prepareAdaptiveQuestion({ ...rawBig, visibleCorrectSequences: [['missing-block']] });
  const recipe = renderRecipe(question);
  assert.match(recipe, /big \+ .*Double the final g.* \+ -er \+ than/);
  assert.doesNotMatch(recipe, /missing-block|-ger/);
});

test('an unvalidated hidden legacy override cannot replace the visible doubling recipe', () => {
  const question = prepareAdaptiveQuestion({ ...rawBig, visibleCorrectSequences: [rawBig.correctSequences[0]] });
  const recipe = renderRecipe(question);
  assert.match(recipe, /Double the final g/);
  assert.match(recipe, / \+ -er \+ than$/);
  assert.doesNotMatch(recipe, /-ger/);
});
