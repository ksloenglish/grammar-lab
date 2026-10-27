import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { COMPARISON_INGREDIENTS } from '../site/js/question-context.js';
import { ingredientGroups, renderIngredients } from '../site/js/ingredients.js';
const bank = id => JSON.parse(readFileSync(new URL(`../site/data/${id}-questions.json`, import.meta.url))).questions;

for (const moduleId of ['adjectives', 'adverbs']) {
  test(`${moduleId}: every question has a complete, uniquely labelled ingredient tray`, () => {
    for (const question of bank(moduleId)) {
      const labels = question.blocks.map(block => block.label);
      assert.equal(question.ingredientMode, 'complete', question.id);
      assert.equal(new Set(labels).size, labels.length, question.id);
      for (const ingredient of [...COMPARISON_INGREDIENTS, question.base]) assert.ok(labels.includes(ingredient), `${question.id}: ${ingredient}`);
      const order = question.blocks.map(block => block.id).reverse();
      const selected = question.correctSequences[0];
      const remaining = ingredientGroups(question, order, selected).flatMap(group => group.blocks.map(block => block.id));
      assert.equal(remaining.length, order.length - selected.length, question.id);
      assert.ok(selected.every(id => !remaining.includes(id)), question.id);
      const html = renderIngredients(question, order, [], true, String);
      assert.equal((html.match(/data-action="add-block"/g) ?? []).length, question.blocks.length, question.id);
      assert.ok(html.includes('tray-group-title'));
    }
  });
}
