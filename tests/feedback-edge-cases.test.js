import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assemble } from '../site/js/core.js';
import { prepareAdaptiveQuestion } from '../site/js/comparison-blocks.js';
import { diagnoseAnswer } from '../site/js/feedback.js';

const questions = ['adjectives', 'adverbs'].flatMap(module => JSON.parse(readFileSync(new URL(`../site/data/${module}-questions.json`, import.meta.url), 'utf8')).questions);
const fixture = (base, degree, labels) => {
  const question = prepareAdaptiveQuestion(questions.find(item => item.base === base && item.degree === degree));
  const ids = labels.map(label => question.blocks.find(block => block.label === label).id);
  return { question, ids, answer: assemble(question, ids).text };
};

for (const [base, complete] of [['badly', 'worse'], ['good', 'better'], ['far', 'further']]) {
  test(`${base} + ${complete} + than identifies the extra base, not a missing formation word`, () => {
    const { question, ids, answer } = fixture(base, 'comparative', [base, complete, 'than']);
    const diagnostic = diagnoseAnswer(question, answer, ids);
    assert.equal(diagnostic.code, 'extra-block');
    assert.equal(diagnostic.title, 'Extra block');
    assert.equal(diagnostic.message, `Remove the extra '${base}' block.`);
    assert.deepEqual(diagnostic.problemBlockIds, [ids[0]]);
    assert.deepEqual(diagnostic.missingLabels, []);
    assert.doesNotMatch(diagnostic.message, /Put more|Missing more/);
  });
}

for (const [degree, prefix, wrong, right] of [['comparative', [], '-r', '-ier'], ['superlative', ['the'], '-st', '-iest']]) {
  test(`easy with ${wrong} names the student's actual wrong ending`, () => {
    const labels = [...prefix, 'easy', wrong, ...(degree === 'comparative' ? ['than'] : [])];
    const { question, ids, answer } = fixture('easy', degree, labels);
    const diagnostic = diagnoseAnswer(question, answer, ids);
    assert.equal(diagnostic.code, 'y-spelling');
    assert.ok(diagnostic.message.includes(`Use ${right}, not ${wrong},`));
    assert.deepEqual(diagnostic.missingLabels, [right]);
    assert.deepEqual(diagnostic.problemBlockIds, ids.slice(prefix.length, prefix.length + 2));
  });
}

for (const base of ['much', 'many']) {
  test(`${base}: most alone needs the, not a second most or the base`, () => {
    const { question, ids, answer } = fixture(base, 'superlative', ['most']);
    const diagnostic = diagnoseAnswer(question, answer, ids);
    assert.equal(diagnostic.code, 'missing-the');
    assert.equal(diagnostic.message, 'Add the before the superlative adjective.');
    assert.deepEqual(diagnostic.problemBlockIds, []);
    assert.deepEqual(diagnostic.missingLabels, ['the']);
  });
  test(`${base}: most with a suffix needs that suffix removed, never moved to the base`, () => {
    const { question, ids, answer } = fixture(base, 'superlative', ['the', 'most', '-est']);
    const diagnostic = diagnoseAnswer(question, answer, ids);
    assert.equal(diagnostic.code, 'extra-ending');
    assert.match(diagnostic.message, /'most' is already complete/);
    assert.match(diagnostic.message, /Remove the extra ending/);
    assert.doesNotMatch(diagnostic.message, /after the base|Add a comparison/);
  });
}
