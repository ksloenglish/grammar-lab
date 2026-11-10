import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assemble, isCorrect } from '../site/js/core.js';
import { questionContextIssues } from '../site/js/question-context.js';
import { adaptiveBlocks, prepareAdaptiveQuestion } from '../site/js/comparison-blocks.js';
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
    assert.deepEqual(questionContextIssues(question), [], `${label}: noun-free answers/ingredients, gap, connector, suffix and feedback context`);
    assert.equal(question.sentence.split('_____').length, 2, `${label}: one gap`);
    assert.ok(question.base && question.explanation && question.rule);
    assert.equal(typeof question.explanation, 'string', `${label}: plain explanation text`);
    assert.ok(!/Use .+ (?:to compare two things|for the top one in a group|in this gap)\./i.test(question.explanation), `${label}: remove redundant generic correct-answer copy`);
    const thanPurpose = 'Use than to introduce the other person, thing or action in the comparison.';
    assert.equal(question.explanation.split(thanPurpose).length - 1, question.degree === 'comparative' ? 1 : 0, `${label}: exactly one purpose-of-than sentence for comparatives only`);
    assert.ok(question.degree in counts, `${label}: degree`);
    assert.equal(question.requiresArticle, module.id === 'adjectives' && question.degree === 'superlative', `${label}: explicit article policy`);
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
    const prepared = prepareAdaptiveQuestion(question);
    assert.deepEqual(questionContextIssues(prepared), [], `${label}: controlled adaptive operations and recipes`);
    assert.deepEqual(prepareAdaptiveQuestion(prepared), prepared, `${label}: idempotent adaptive preparation`);
    assert.deepEqual(prepared.answers, question.answers, `${label}: accepted answers must not change`);
    assert.deepEqual(prepared.blocks.slice(0, question.blocks.length), question.blocks, `${label}: authored ingredients must not change`);
    const visible = adaptiveBlocks(prepared);
    const visibleIds = new Set(visible.map(block => block.id));
    assert.equal(visible[0]?.label, question.base, `${label}: unselected base must be first`);
    assert.equal(visibleIds.size, visible.length, `${label}: unique adaptive choices`);
    assert.ok(!visible.some(block => /^-[bcdfghjklmnpqrstvz](?:er|est)$/.test(block.label) && !['-ier', '-iest'].includes(block.label)), `${label}: no combined doubling suffixes in visible choices`);
    for (const sequence of prepared.correctSequences) assert.ok(isCorrect(prepared, assemble(prepared, sequence).text), `${label}: adaptive sequence must remain accepted`);
    for (const answer of question.answers) {
      assert.ok(prepared.correctSequences.some(sequence => sequence.every(id => visibleIds.has(id))
        && assemble(prepared, sequence).text.toLowerCase() === answer.toLowerCase()), `${label}: adaptive choices cannot construct accepted alternative ${answer}`);
    }
    if (/y$/i.test(question.base) && prepared.correctSequences.some(sequence => sequence.some(id =>
      prepared.blocks.find(block => block.id === id)?.operation === 'remove-final-y'))) {
      const operation = prepared.blocks.find(block => block.operation === 'remove-final-y');
      for (const sequence of prepared.correctSequences) {
        assert.ok(sequence.includes(operation.id), `${label}: every accepted y-change recipe requires explicit ×y`);
        const direct = sequence.filter(id => id !== operation.id);
        const literal = assemble(prepared, direct);
        assert.ok(!isCorrect(prepared, literal.text), `${label}: omitting ×y must not produce an accepted answer`);
        assert.ok(literal.parts.some(part => part.text.includes(question.base)), `${label}: omitting ×y must retain the final y`);
        assert.ok(literal.parts.every(part => !part.spellingChanges?.length), `${label}: no spelling trace without an operation`);
        const invalidRecipe = structuredClone(question);
        invalidRecipe.correctSequences = [direct];
        assert.ok(questionContextIssues(invalidRecipe).length, `${label}: strict context rejects accepted recipes without ×y`);
      }
      for (const ending of ['-ier', '-iest']) {
        const suffix = prepared.blocks.find(block => block.kind === 'suffix' && block.label === ending);
        assert.ok(!Object.hasOwn(suffix.transforms ?? {}, question.base), `${label}: ${ending} cannot silently transform the base`);
        const invalidTransform = structuredClone(question);
        const poisoned = invalidTransform.blocks.find(block => block.id === suffix.id);
        poisoned.transforms = { ...poisoned.transforms, [question.base]: question.base.slice(0, -1) + ending.slice(1) };
        assert.ok(questionContextIssues(invalidTransform).length, `${label}: strict context rejects implicit base-y transform`);
      }
    }
    const used = new Set(question.correctSequences.flat());
    const distractors = question.blocks.filter(block => !used.has(block.id));
    assert.equal(question.ingredientMode, 'complete', `${label}: complete ingredient tray`);
    assert.ok(distractors.length >= 2, `${label}: choices must include unused alternatives`);
    assert.ok(question.feedback.length >= 3, `${label}: targeted feedback`);
    for (const feedback of question.feedback) if (feedback.pattern) new RegExp(feedback.pattern);
  }
  assert.ok(Math.abs(counts.comparative - counts.superlative) <= 4, `${module.id}: degree balance`);
  assert.ok(Object.keys(rules).length >= 3, 'Rule variety');
  assert.equal(learn.module, module.id);
  assert.equal(learn.miniCheck.length, 3);
  for (const check of learn.miniCheck) {
    assert.ok(check.options.includes(check.answer));
    assert.ok(!/\bthan\b/i.test(check.sentence), 'Mini-check stem must not supply than');
    if (!/\bthan\b/i.test(check.answer)) assert.ok(!/\bthe\b/i.test(check.sentence), 'Superlative mini-check must not supply the');
    assert.equal(new Set(check.options).size, check.options.length);
    assert.ok(check.explanation);
  }
  console.log(`${module.id}: ${bank.questions.length} questions; degrees ${JSON.stringify(counts)}; rules ${JSON.stringify(rules)}; 3 mini-checks. PASS`);
}
console.log('All noun-free answers/ingredients, question stems, complete authored trays, controlled operations, legacy recipes and every adaptive visible-answer reachability check passed.');
