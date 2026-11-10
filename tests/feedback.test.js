import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { correctExplanation, diagnoseAnswer } from '../site/js/feedback.js';
import { adaptiveBlocks, prepareAdaptiveQuestion } from '../site/js/comparison-blocks.js';
import { assemble, explain, createExperiment, submitTrial, retryTrial, giveUp, advanceTrial, makeReport } from '../site/js/core.js';
import { validSession } from '../site/js/storage.js';

const bank = moduleId => JSON.parse(readFileSync(new URL(`../site/data/${moduleId}-questions.json`, import.meta.url))).questions;
const banks = { adjectives: bank('adjectives'), adverbs: bank('adverbs') };
const all = [...banks.adjectives, ...banks.adverbs];
const get = (base, degree = 'comparative', moduleId = 'adjectives') => prepareAdaptiveQuestion(banks[moduleId].find(question => question.base === base && question.degree === degree));
const idsFor = (question, labels) => labels.map(label => {
  const block = question.blocks.find(item => item.label === label);
  assert.ok(block, `${question.id}: missing test label ${label}`);
  return block.id;
});
const diagnosis = (question, labels) => {
  const ids = idsFor(question, labels);
  const answer = assemble(question, ids).text;
  return { ids, answer, diagnostic: diagnoseAnswer(question, answer, ids) };
};
const freeze = value => { if (value && typeof value === 'object') { Object.freeze(value); Object.values(value).forEach(freeze); } return value; };

function checkDiagnostic(question, ids, answer) {
  const diagnostic = diagnoseAnswer(question, answer, ids);
  assert.deepEqual(Object.keys(diagnostic), ['code', 'title', 'message', 'problemBlockIds', 'missingLabels']);
  for (const key of ['code', 'title', 'message']) assert.ok(typeof diagnostic[key] === 'string' && diagnostic[key].trim(), `${question.id}: ${answer}: ${key}`);
  assert.ok(Array.isArray(diagnostic.problemBlockIds));
  assert.ok(Array.isArray(diagnostic.missingLabels));
  assert.ok(diagnostic.problemBlockIds.every(id => ids.includes(id)), `${question.id}: ${answer}: unrelated highlight`);
  assert.ok(diagnostic.missingLabels.every(label => typeof label === 'string' && label.trim()));
  if (!question.answers.some(expected => expected.toLowerCase() === answer.toLowerCase())) {
    assert.notEqual(diagnostic.code, 'correct', `${question.id}: ${answer}`);
    assert.notEqual(diagnostic.message, correctExplanation(question), `${question.id}: generic correct explanation on wrong answer ${answer}`);
    assert.doesNotMatch(diagnostic.message, /Use .+ to compare two things|Use .+ for the top one in a group|scrambl|check the rule|try again/i);
    for (const correct of question.answers.filter(text => text.trim().includes(' '))) {
      assert.ok(!diagnostic.message.toLowerCase().includes(correct.toLowerCase()), `${question.id}: ${answer}: full corrected phrase revealed: ${diagnostic.message}`);
    }
  }
  return diagnostic;
}

test('correct good explanation is exact and old generic bank text is ignored', () => {
  const source = get('good');
  const expected = 'Good changes its form to better. Use than to introduce the other person, thing or action in the comparison.';
  assert.equal(correctExplanation(source), expected);
  const old = { ...source, explanation: 'Use better than to compare two things. Good changes its form. Use better in this gap.' };
  assert.equal(correctExplanation(old), expected);
  assert.equal(explain(old, 'better than'), expected);
});

test('runtime explanations agree with all 192 authored rules, even in frozen legacy snapshots', () => {
  for (const question of all) {
    const old = freeze({ ...structuredClone(question), explanation: 'Use the answer for the top one in a group.' });
    const snapshot = structuredClone(old);
    assert.equal(correctExplanation(old), question.explanation, question.id);
    assert.deepEqual(old, snapshot, `${question.id}: explanation must not mutate its input`);
    const message = correctExplanation(question);
    assert.doesNotMatch(message, /to compare two things|for the top one in a group|in this gap/);
    assert.equal((message.match(/Use than to introduce/g) ?? []).length, question.degree === 'comparative' ? 1 : 0, question.id);
  }
});

test('all old and visible recipes, far alternatives and optional-the adverbs are accepted', () => {
  let recipes = 0;
  for (const source of all) {
    const question = prepareAdaptiveQuestion(source);
    for (const ids of question.correctSequences) {
      const answer = assemble(question, ids).text;
      const diagnostic = checkDiagnostic(question, ids, answer);
      assert.equal(diagnostic.code, 'correct', `${question.id}: ${answer}`);
      assert.deepEqual(diagnostic.problemBlockIds, []);
      assert.deepEqual(diagnostic.missingLabels, []);
      assert.equal(diagnostic.message, correctExplanation(question));
      recipes++;
    }
  }
  assert.ok(recipes > 300);
  for (const degree of ['comparative', 'superlative']) {
    const question = get('far', degree, 'adverbs');
    for (const answer of question.answers) assert.equal(diagnoseAnswer(question, answer).code, 'correct');
  }
  assert.equal(diagnoseAnswer(get('fast', 'superlative', 'adverbs'), 'fastest').code, 'correct');
  assert.equal(diagnoseAnswer(get('badly', 'superlative', 'adverbs'), 'most badly').code, 'correct');
});

test('the bigg reports the exact missing-ending hint and highlights only bigg', () => {
  const question = get('big', 'superlative');
  const { diagnostic, ids, answer } = diagnosis(question, ['the', 'big', 'g']);
  assert.equal(answer, 'the bigg');
  assert.deepEqual(diagnostic, {
    code: 'missing-ending', title: 'Missing ending',
    message: "'bigg' is unfinished. You have doubled g; add -est to finish the superlative.",
    problemBlockIds: ids.slice(1), missingLabels: ['-est']
  });
  assert.equal(explain(question, answer, ids), diagnostic.message);
  assert.deepEqual(diagnoseAnswer(question, answer), diagnostic, 'old answer-only callers infer the controlled doubling IDs');
  assert.equal(diagnoseAnswer(banks.adjectives.find(item => item.id === question.id), answer).message, diagnostic.message, 'raw old question is prepared without being changed');
});

test('comparative bigg and removed-y happ get unfinished-word hints, not a second spelling change', () => {
  const big = diagnosis(get('big'), ['big', 'g', 'than']);
  assert.equal(big.diagnostic.code, 'missing-ending');
  assert.match(big.diagnostic.message, /You have doubled g; add -er/);
  assert.deepEqual(big.diagnostic.problemBlockIds, big.ids.slice(0, 2));
  const happy = diagnosis(get('happy'), ['happy', 'Remove y', 'than']);
  assert.equal(happy.answer, 'happ than');
  assert.equal(happy.diagnostic.code, 'missing-ending');
  assert.match(happy.diagnostic.message, /You have removed y; add -ier/);
  assert.deepEqual(happy.diagnostic.problemBlockIds, happy.ids.slice(0, 2));
  assert.deepEqual(happy.diagnostic.missingLabels, ['-ier']);
});

const cases = [
  ['good', 'comparative', 'adjectives', ['good', 'than'], 'irregular-formation', /Good changes its form to better/],
  ['good', 'comparative', 'adjectives', ['more', 'good', 'than'], 'irregular-formation', /Remove more/],
  ['good', 'comparative', 'adjectives', ['good', '-er'], 'irregular-formation', /Remove the added ending/],
  ['good', 'comparative', 'adjectives', ['better'], 'missing-than', /Add than after better/],
  ['good', 'comparative', 'adjectives', ['than', 'good'], 'misplaced-than', /Put than after/],
  ['happy', 'comparative', 'adjectives', ['happy', '-er', 'than'], 'y-spelling', /Change the final y to i/],
  ['easy', 'comparative', 'adjectives', ['easy', '-er'], 'y-spelling', /Use -ier, not -er/],
  ['big', 'comparative', 'adjectives', ['big', '-er', 'than'], 'missing-doubling', /only one g/],
  ['big', 'superlative', 'adjectives', ['the', 'big', '-est'], 'missing-doubling', /Double g before -est/],
  ['big', 'comparative', 'adjectives', ['big', 'g', '-ger', 'than'], 'extra-doubling', /already doubled g/],
  ['big', 'comparative', 'adjectives', ['big', 'g', '-r', 'than'], 'wrong-ending', /already doubled g/],
  ['happy', 'comparative', 'adjectives', ['happy', 'Remove y', '-er', 'than'], 'wrong-ending', /already removed y/],
  ['fast', 'comparative', 'adverbs', ['more', 'fast', '-er', 'than'], 'double-formation', /Remove more/],
  ['fast', 'superlative', 'adverbs', ['most', 'fast', '-est'], 'double-formation', /Remove most/],
  ['fast', 'comparative', 'adverbs', ['more', 'fast', 'than'], 'unnecessary-formation-word', /Remove more/],
  ['careful', 'comparative', 'adjectives', ['careful', '-er', 'than'], 'wrong-formation', /Keep careful unchanged/],
  ['careful', 'comparative', 'adjectives', ['careful', 'than'], 'missing-formation-word', /Put more before careful/],
  ['careful', 'comparative', 'adjectives', ['careful', 'more', 'than'], 'misplaced-formation-word', /Put more before careful, not after/],
  ['carefully', 'superlative', 'adverbs', ['carefully', 'Remove y', '-iest'], 'wrong-formation', /Keep carefully unchanged/],
  ['quiet', 'comparative', 'adjectives', ['more', 'quiet'], 'missing-than', /Add than after more quiet/],
  ['simple', 'comparative', 'adjectives', ['more', 'simple'], 'missing-than', /Add than after more simple/],
  ['far', 'comparative', 'adjectives', ['farther'], 'missing-than', /Add than after farther/],
  ['far', 'comparative', 'adjectives', ['further'], 'missing-than', /Add than after further/],
  ['far', 'superlative', 'adjectives', ['farthest'], 'missing-the', /Add the before/],
  ['many', 'superlative', 'adjectives', ['the', 'most', 'many'], 'extra-base', /Keep that irregular block and remove the extra 'many'/],
  ['much', 'superlative', 'adjectives', ['the', 'most', 'much'], 'extra-base', /Keep that irregular block and remove the extra 'much'/],
  ['badly', 'superlative', 'adverbs', ['most', 'badly', '-est'], 'wrong-formation', /Keep badly unchanged after most/],
  ['tall', 'comparative', 'adjectives', ['tall', '-est', 'than'], 'wrong-degree', /needs a comparative, not a superlative/],
  ['tall', 'superlative', 'adjectives', ['the', 'tall', '-er'], 'wrong-degree', /needs a superlative, not a comparative/],
  ['careful', 'comparative', 'adjectives', ['most', 'careful', 'than'], 'wrong-degree', /Replace most with more/],
  ['fast', 'superlative', 'adverbs', ['more', 'fast'], 'wrong-degree', /Remove more. Add -est to fast/],
  ['fast', 'comparative', 'adverbs', ['most', 'fast', '-er'], 'wrong-degree', /Remove most; the comparison word already/],
  ['good', 'superlative', 'adjectives', ['good', '-er'], 'wrong-degree', /Remove '-er'. Good changes its form to best/],
  ['good', 'superlative', 'adjectives', ['the', 'better'], 'wrong-degree', /Choose the superlative form/],
  ['good', 'comparative', 'adjectives', ['better', '-er', 'than'], 'extra-ending', /already complete/],
  ['tall', 'superlative', 'adjectives', ['the', 'tall', '-est', '-er'], 'extra-ending', /Remove the extra ending/],
  ['nice', 'comparative', 'adjectives', ['nice', '-er', 'than'], 'wrong-ending', /already ends in e/],
  ['tall', 'superlative', 'adjectives', ['tall', '-est'], 'missing-the', /Add the before/],
  ['tall', 'superlative', 'adjectives', ['tall', '-est', 'the'], 'misplaced-the', /Put the before the whole/],
  ['tall', 'superlative', 'adjectives', ['the', 'tall', '-est', 'than'], 'extra-than', /Remove than/],
  ['tall', 'comparative', 'adjectives', ['the', 'tall', '-er', 'than'], 'extra-the', /Remove the/],
  ['good', 'comparative', 'adjectives', ['than'], 'missing-base', /only structure words/],
  ['big', 'comparative', 'adjectives', ['-er', 'big', 'g', 'than'], 'ending-position', /straight after/],
  ['big', 'comparative', 'adjectives', ['g', 'big', '-er', 'than'], 'invalid-doubling-operation', /straight after/],
  ['big', 'comparative', 'adjectives', ['big', '-ger', 'g', 'than'], 'invalid-doubling-operation', /already doubled g/],
  ['happy', 'comparative', 'adjectives', ['Remove y', 'happy', '-ier', 'than'], 'invalid-y-operation', /word ending in y/],
  ['big', 'comparative', 'adjectives', ['big', 'Remove y', '-er', 'than'], 'invalid-y-operation', /word ending in y/],
  ['tall', 'comparative', 'adjectives', ['tall', 'than', '-er'], 'ending-position', /Do not attach an ending to 'than'/]
];
for (const [base, degree, moduleId, labels, code, message] of cases) {
  test(`${moduleId} ${base} ${degree}: ${labels.join(' + ')} diagnoses ${code}`, () => {
    const question = get(base, degree, moduleId);
    const { diagnostic, ids, answer } = diagnosis(question, labels);
    checkDiagnostic(question, ids, answer);
    assert.equal(diagnostic.code, code);
    assert.match(diagnostic.message, message);
    assert.ok(diagnostic.problemBlockIds.every(id => ids.includes(id)));
  });
}

test('formation takes one priority over a missing connector and highlights only the actual word', () => {
  const question = get('good');
  const selected = diagnosis(question, ['good', 'than']);
  assert.deepEqual(selected.diagnostic.problemBlockIds, selected.ids.slice(0, 1));
  assert.equal(selected.diagnostic.message, 'Good changes its form to better.');
  assert.doesNotMatch(selected.diagnostic.message, /than/);
  const partial = diagnosis(get('big'), ['big', 'g']);
  assert.equal(partial.diagnostic.code, 'missing-ending');
  assert.doesNotMatch(partial.diagnostic.message, /than|Double g/);
});

test('minimum-edit fallback removes real extra words and respects accepted alternatives', () => {
  const question = get('far');
  const { diagnostic, ids } = diagnosis(question, ['further', 'than', 'farther']);
  assert.equal(diagnostic.code, 'extra-block');
  assert.match(diagnostic.message, /Remove the extra 'farther'/);
  assert.deepEqual(diagnostic.problemBlockIds, ids.slice(2));
  assert.doesNotMatch(diagnostic.message, /further than|farther than/);
  const other = diagnosis(get('quiet'), ['more', 'quiet', 'than', '-er']);
  assert.equal(other.diagnostic.code, 'ending-position');
  const optional = diagnosis(get('far', 'superlative', 'adverbs'), ['furthest', 'farthest']);
  assert.equal(optional.diagnostic.code, 'extra-block');
  assert.doesNotMatch(optional.diagnostic.message, /Add the/);
});

test('minimal reusable questions without base or degree get concrete, safe nearest-recipe hints', () => {
  const question = { blocks: [{ id: 'a', label: 'alpha', kind: 'word' }, { id: 'b', label: 'beta', kind: 'word' }, { id: 'x', label: 'extra', kind: 'word' }], answers: ['alpha beta'], correctSequences: [['a', 'b']], explanation: 'Generic old explanation.' };
  assert.equal(diagnoseAnswer(question, 'alpha extra beta', ['a', 'x', 'b']).code, 'extra-block');
  assert.equal(diagnoseAnswer(question, 'beta alpha', ['b', 'a']).code, 'block-order');
  assert.equal(diagnoseAnswer(question, 'alpha', ['a']).code, 'missing-block');
  assert.match(explain(question, 'alpha extra beta', ['a', 'x', 'b']), /Remove the extra 'extra'/);
  assert.doesNotThrow(() => diagnoseAnswer(question, 'unknown', ['unknown']));
  assert.doesNotThrow(() => diagnoseAnswer({}, '', null));
  const suffixQuestion = { ...question, blocks: [...question.blocks, { id: 'er', label: '-er', kind: 'suffix' }] };
  assert.doesNotMatch(diagnoseAnswer(suffixQuestion, 'alphaer', ['a', 'er']).message, /undefined/);
});

test('firstAnswer, retry-zero, Give Up, reset and independent practice preserve scoring and schema', () => {
  const session = createExperiment('adjectives', [get('big', 'superlative'), get('good')]);
  const stateKeys = Object.keys(session);
  assert.equal(submitTrial(session), null);
  session.assembly = idsFor(session.questions[0], ['the', 'big', 'g']);
  const assembled = structuredClone(session.assembly);
  assert.deepEqual(submitTrial(session), { correct: false, answer: 'the bigg', mark: 0 });
  assert.equal(session.firstAnswer, 'the bigg');
  assert.equal(session.score, 0);
  assert.deepEqual(session.assembly, assembled, 'wrong submission never scrambles selected blocks');
  assert.deepEqual(Object.keys(session), stateKeys, 'no new persisted diagnostic fields');
  assert.equal(submitTrial(session), null);
  assert.equal(retryTrial(session), true);
  assert.equal(session.feedback, '');
  session.assembly = [...session.questions[0].correctSequences[0]];
  assert.equal(submitTrial(session).mark, 0);
  assert.equal(session.results[0].firstAnswer, 'the bigg');
  assert.equal(session.feedback, correctExplanation(session.questions[0]));
  assert.equal(advanceTrial(session), 'next');
  assert.deepEqual(session.assembly, []);
  assert.equal(session.firstAnswer, null);
  assert.equal(session.attempts, 0);
  assert.equal(session.feedback, '');
  assert.equal(giveUp(session), true);
  assert.equal(session.results[1].mark, 0);
  assert.equal(session.results[1].gaveUp, true);
  assert.equal(session.results[1].firstAnswer, '(No answer)');
  assert.equal(session.feedback, correctExplanation(session.questions[1]));
  assert.equal(giveUp(session), false);
  assert.equal(session.schema, 2);
  assert.equal(validSession(session, ['adjectives']), true);
  const report = makeReport(session);
  const practice = createExperiment('adjectives', [get('good')], true, report);
  practice.assembly = [...practice.questions[0].correctSequences[0]];
  assert.equal(submitTrial(practice).mark, 1);
  assert.equal(practice.score, 1);
  assert.equal(report.score, 0);
});

test('bounded all-bank fuzz: remove each visible recipe block, swap adjacent blocks and append unused visible options', t => {
  let checked = 0;
  let wrong = 0;
  for (const source of all) {
    const question = prepareAdaptiveQuestion(source);
    const visible = adaptiveBlocks(question);
    const visibleIds = new Set(visible.map(block => block.id));
    const recipes = question.correctSequences.filter(sequence => sequence.every(id => visibleIds.has(id)));
    for (const recipe of recipes) {
      const trials = recipe.map((id, index) => recipe.filter((item, i) => i !== index));
      for (let i = 0; i < recipe.length - 1; i++) {
        const swapped = [...recipe];
        [swapped[i], swapped[i + 1]] = [swapped[i + 1], swapped[i]];
        trials.push(swapped);
      }
      for (const block of visible) if (!recipe.includes(block.id)) trials.push([...recipe, block.id]);
      for (const ids of trials) {
        const answer = assemble(question, ids).text;
        const snapshot = structuredClone(question);
        const diagnostic = checkDiagnostic(question, ids, answer);
        assert.deepEqual(question, snapshot, `${question.id}: ${answer}: diagnostic mutation`);
        if (diagnostic.code !== 'correct') wrong++;
        checked++;
      }
    }
  }
  t.diagnostic(`${checked} altered visible recipes checked; ${wrong} incorrect answers got concrete diagnostics.`);
  assert.ok(checked > 2000);
  assert.ok(wrong > 2000);
});

test('bounded unseen permutations are block-specific and deterministic without any author feedback', () => {
  for (const question of [get('big'), get('happy', 'superlative'), get('good'), get('carefully', 'superlative', 'adverbs'), get('far')]) {
    const bare = { ...question, feedback: [], explanation: 'Generic answer explanation that must never be used.' };
    const blocks = adaptiveBlocks(bare).slice(0, 7);
    let checked = 0;
    for (let i = 0; i < blocks.length; i++) for (let j = 0; j < blocks.length; j++) {
      if (i === j) continue;
      const ids = [blocks[i].id, blocks[j].id, blocks[(j + 2) % blocks.length].id];
      const answer = assemble(bare, ids).text;
      const diagnostic = checkDiagnostic(bare, ids, answer);
      assert.deepEqual(diagnoseAnswer(bare, answer, ids), diagnostic);
      assert.doesNotMatch(diagnostic.message, /Generic answer explanation|undefined/);
      checked++;
    }
    assert.ok(checked >= 20);
  }
});
