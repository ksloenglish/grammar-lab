import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assemble, isCorrect } from '../site/js/core.js';
const read = path => JSON.parse(readFileSync(new URL(`../site/data/${path}`, import.meta.url), 'utf8'));
const manifest = read('modules.json');
assert.equal(new Set(manifest.modules.map(item => item.id)).size, manifest.modules.length, 'Unique module IDs');
for (const module of manifest.modules.filter(item => item.available)) {
  const bank = read(module.bank);
  const learn = read(module.learn);
  assert.equal(bank.module, module.id);
  assert.ok(bank.questions.length >= 60, `${module.id}: at least 60 questions`);
  assert.equal(new Set(bank.questions.map(question => question.id)).size, bank.questions.length);
  assert.equal(new Set(bank.questions.map(question => question.sentence)).size, bank.questions.length, 'Unique sentences');
  const counts = { comparative: 0, superlative: 0 };
  const rules = {};
  for (const question of bank.questions) {
    const label = `${module.id}/${question.id}`;
    assert.equal(question.sentence.split('_____').length, 2, `${label}: one gap`);
    assert.ok(question.base && question.explanation && question.rule);
    assert.ok(question.degree in counts, `${label}: degree`);
    counts[question.degree]++;
    rules[question.rule] = (rules[question.rule] ?? 0) + 1;
    assert.equal(new Set(question.blocks.map(block => block.id)).size, question.blocks.length);
    assert.equal(new Set(question.blocks.map(block => block.label)).size, question.blocks.length, `${label}: duplicate labels`);
    assert.ok(question.answers.length && question.correctSequences.length);
    for (const sequence of question.correctSequences) {
      assert.equal(new Set(sequence).size, sequence.length, `${label}: block reuse`);
      const answer = assemble(question, sequence).text;
      assert.ok(isCorrect(question, answer), `${label}: sequence produces ${answer}`);
    }
    for (const answer of question.answers) assert.ok(question.correctSequences.some(sequence => assemble(question, sequence).text.toLowerCase() === answer.toLowerCase()), `${label}: unreachable ${answer}`);
    const used = new Set(question.correctSequences.flat());
    const distractors = question.blocks.filter(block => !used.has(block.id));
    assert.ok(distractors.length >= 2 && distractors.length <= 3, `${label}: ${distractors.length} distractors (expected 2–3)`);
    assert.ok(question.feedback.length >= 3, `${label}: targeted feedback`);
    for (const feedback of question.feedback) if (feedback.pattern) new RegExp(feedback.pattern);
  }
  assert.ok(Math.abs(counts.comparative - counts.superlative) <= 4, `${module.id}: degree balance`);
  assert.ok(Object.keys(rules).length >= 3, 'Rule variety');
  assert.equal(learn.module, module.id);
  assert.equal(learn.miniCheck.length, 3);
  for (const check of learn.miniCheck) {
    assert.ok(check.options.includes(check.answer));
    assert.equal(new Set(check.options).size, check.options.length);
    assert.ok(check.explanation);
  }
  console.log(`${module.id}: ${bank.questions.length} questions; degrees ${JSON.stringify(counts)}; rules ${JSON.stringify(rules)}; 3 mini-checks. PASS`);
}
console.log('All content and reachable answer checks passed.');
