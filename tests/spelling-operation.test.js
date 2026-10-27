import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assemble, createExperiment, submitTrial, isCorrect } from '../site/js/core.js';
const bank = id => JSON.parse(readFileSync(new URL(`../site/data/${id}-questions.json`, import.meta.url))).questions;

for (const moduleId of ['adjectives', 'adverbs']) {
  test(`${moduleId}: every tray contains a real Remove y operation`, () => {
    for (const question of bank(moduleId)) assert.ok(question.blocks.some(block => block.label === 'Remove y' && block.kind === 'operation' && block.operation === 'remove-final-y'), question.id);
  });
}
for (const [moduleId, base] of [['adjectives', 'happy'], ['adverbs', 'early']]) {
  test(`${base}: explicit removal and direct y-ending alternatives remain correct`, () => {
    const question = bank(moduleId).find(question => question.base === base && question.degree === 'comparative');
    const operation = question.blocks.find(block => block.kind === 'operation');
    const explicit = question.correctSequences.find(sequence => sequence.includes(operation.id));
    const direct = question.correctSequences.find(sequence => !sequence.includes(operation.id));
    assert.ok(explicit && direct);
    for (const sequence of [explicit, direct]) {
      const result = assemble(question, sequence);
      assert.ok(isCorrect(question, result.text));
      assert.equal(result.parts.find(part => part.spellingChanges?.length).spellingChanges[0].before, base);
    }
    const firstTwo = explicit.slice(0, explicit.indexOf(operation.id) + 1);
    assert.equal(assemble(question, firstTwo).text, base.slice(0, -1));
  });
}

test('Remove y cannot silently do nothing on a non-y word or after a finished comparative', () => {
  const question = bank('adjectives').find(question => question.base === 'big' && question.degree === 'comparative');
  const operation = question.blocks.find(block => block.kind === 'operation');
  const base = question.blocks.find(block => block.label === 'big');
  const session = createExperiment('adjectives', [question]);
  session.assembly = [base.id, operation.id, ...question.correctSequences[0].slice(1)];
  assert.ok(assemble(question, session.assembly).text.includes('[Remove y]'));
  assert.equal(submitTrial(session).correct, false);
  assert.equal(session.score, 0);
  assert.ok(session.feedback.includes('word ending in y'));
});
