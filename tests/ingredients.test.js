import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { COMPARISON_INGREDIENTS } from '../site/js/question-context.js';
import { adaptiveBlocks, prepareAdaptiveQuestion } from '../site/js/comparison-blocks.js';
import { blockDisplayLabel, blockAccessibleLabel, renderIngredients } from '../site/js/ingredients.js';
const bank = id => JSON.parse(readFileSync(new URL(`../site/data/${id}-questions.json`, import.meta.url))).questions;
const escape = value => String(value).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

for (const moduleId of ['adjectives', 'adverbs']) {
  test(`${moduleId}: authored complete banks stay unchanged while all 96 trays render flat adaptive choices`, () => {
    for (const source of bank(moduleId)) {
      const original = JSON.stringify(source);
      const labels = source.blocks.map(block => block.label);
      assert.equal(source.ingredientMode, 'complete', source.id);
      assert.equal(new Set(labels).size, labels.length, source.id);
      for (const ingredient of [...COMPARISON_INGREDIENTS, source.base]) assert.ok(labels.includes(ingredient), `${source.id}: ${ingredient}`);
      const question = prepareAdaptiveQuestion(source);
      const order = question.blocks.map(block => block.id).reverse();
      const visible = adaptiveBlocks(question);
      const html = renderIngredients(question, order, [], true, escape);
      assert.ok(html.startsWith('<div class="ingredient-grid adaptive-ingredients">'), source.id);
      assert.ok(!/tray-group|<h[1-6]|Words<|Other words|Endings &amp; changes/.test(html), source.id);
      assert.equal((html.match(/data-action="add-block"/g) ?? []).length, visible.length, source.id);
      assert.equal((html.match(/draggable="false"/g) ?? []).length, visible.length, source.id);
      assert.equal((html.match(/type="button"/g) ?? []).length, visible.length, source.id);
      assert.deepEqual([...html.matchAll(/data-block="([^"]+)"/g)].map(match => match[1]), visible.map(block => block.id), source.id);
      assert.equal(visible[0].label, source.base, source.id);
      assert.equal(JSON.stringify(source), original, `${source.id}: runtime must not edit the bank`);
      const chosen = visible.slice(0, 2).map(block => block.id);
      const remaining = renderIngredients(question, order, chosen, true, escape);
      assert.ok(chosen.every(id => !remaining.includes(`data-block="${id}"`)), source.id);
      assert.equal((remaining.match(/data-action="add-block"/g) ?? []).length, visible.length - 2, source.id);
    }
  });
}

test('the unselected/returned base stays first regardless of trayOrder without preselecting it', () => {
  const question = prepareAdaptiveQuestion(bank('adjectives').find(question => question.base === 'big'));
  const base = question.blocks.find(block => block.label === question.base);
  const order = question.blocks.map(block => block.id).reverse();
  const selected = [];
  const initial = renderIngredients(question, order, selected, true, escape);
  assert.equal(initial.match(/data-block="([^"]+)"/)[1], base.id);
  assert.deepEqual(selected, []);
  assert.ok(!renderIngredients(question, order, [base.id], true, escape).includes(`data-block="${base.id}"`));
  assert.equal(renderIngredients(question, [], [], true, escape).match(/data-block="([^"]+)"/)[1], base.id);
});

test('y removal and doubling have distinct CSS hooks, concise labels and precise accessible names', () => {
  const yQuestion = bank('adjectives').find(question => question.base === 'happy');
  const doubleQuestion = prepareAdaptiveQuestion(bank('adjectives').find(question => question.base === 'big'));
  const y = yQuestion.blocks.find(block => block.operation === 'remove-final-y');
  const doubling = doubleQuestion.blocks.find(block => block.operation === 'double-final-consonant');
  assert.equal(blockDisplayLabel(y), 'y');
  assert.equal(blockDisplayLabel(doubling), 'g');
  assert.equal(blockDisplayLabel({ label: '-er', kind: 'suffix' }), '-er');
  assert.equal(blockAccessibleLabel(y), 'Remove the final y from the previous word');
  assert.equal(blockAccessibleLabel(doubling), 'Double the final g of the base word');
  const yHtml = renderIngredients(yQuestion, [], [], true, escape);
  assert.match(yHtml, /class="reagent operation remove-y"[^>]*aria-label="Remove the final y from the previous word"><span class="block-label">y<\/span>/);
  const doubleHtml = renderIngredients(doubleQuestion, [], [], true, escape);
  assert.match(doubleHtml, /class="reagent operation double-consonant"[^>]*aria-label="Double the final g of the base word"><span class="block-label">g<\/span>/);
  assert.ok(!doubleHtml.includes('remove-y') && !doubleHtml.includes('×') && !doubleHtml.includes('Remove y'));
});

test('locked trays disable every native button; selecting all adaptive blocks shows the placeholder', () => {
  const question = bank('adverbs')[0];
  const blocks = adaptiveBlocks(question);
  const html = renderIngredients(question, [], [], false, escape);
  assert.equal((html.match(/ disabled /g) ?? []).length, blocks.length);
  assert.equal(renderIngredients(question, [], blocks.map(block => block.id), true, escape), '<p class="tray-placeholder">All blocks are in your answer.</p>');
});

test('renderer escapes text and accessible labels rather than trusting supplied markup', () => {
  const question = { base: '<base>', degree: 'comparative', blocks: [{ id: 'base"', kind: 'word', label: '<base>' }], answers: [] };
  const html = renderIngredients(question, [], [], true, escape);
  assert.ok(html.includes('data-block="base&quot;"'));
  assert.ok(html.includes('aria-label="Add &lt;base&gt; to the end of your answer"'));
  assert.ok(html.includes('>&lt;base&gt;</span>'));
  assert.ok(!html.includes('<base>'));
});
