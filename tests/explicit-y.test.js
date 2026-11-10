import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assemble, createExperiment, submitTrial, retryTrial, isCorrect, makeReport } from '../site/js/core.js';
import { prepareAdaptiveQuestion, normaliseExplicitYQuestion, joinComparisonSuffix, upgradeAdaptiveSession, checkedExplicitYRecipe, adaptiveBlocks } from '../site/js/comparison-blocks.js';
import { questionContextIssues } from '../site/js/question-context.js';
import { diagnoseAnswer } from '../site/js/feedback.js';
import { validSession } from '../site/js/storage.js';
const banks = ['adjectives', 'adverbs'].flatMap(moduleId => JSON.parse(readFileSync(new URL(`../site/data/${moduleId}-questions.json`, import.meta.url))).questions);
const affected = banks.filter(q => /y$/.test(q.base) && q.answers.some(answer => answer.includes(q.base.slice(0, -1) + (q.degree === 'comparative' ? 'ier' : 'iest'))));
const get = () => structuredClone(affected.find(q => q.base === 'noisy' && q.degree === 'superlative'));
const ids = (q, labels) => labels.map(label => q.blocks.find(b => b.label === label).id);
const legacy = source => {
  const q = structuredClone(source);
  for (const b of q.blocks.filter(b => b.kind === 'suffix' && ['-ier', '-iest'].includes(b.label))) {
    b.transforms = { ...b.transforms, [q.base]: q.base.slice(0, -1) + b.label.slice(1) };
  }
  const explicit = [...q.correctSequences];
  for (const recipe of explicit) if (recipe.includes('remove-y')) q.correctSequences.push(recipe.filter(id => id !== 'remove-y'));
  return q;
};
const freeze = value => { if (value && typeof value === 'object') { Object.freeze(value); Object.values(value).forEach(freeze); } return value; };

test('all 22 y-change questions join both raw endings literally, with no deleted-y trace or mark', () => {
  assert.equal(affected.length, 22);
  for (const q of affected) for (const ending of ['-ier', '-iest']) {
    const direct = ids(q, [q.base, ending]);
    const built = assemble(q, direct);
    assert.equal(built.text, q.base + ending.slice(1), q.id);
    assert.ok(built.parts.every(part => !part.spellingChanges?.length), q.id);
    assert.equal(isCorrect(q, built.text), false);
    const d = diagnoseAnswer(q, built.text, direct);
    assert.equal(d.code, 'missing-y-operation');
    assert.equal(d.title, 'Missing ×y');
    assert.equal(d.message, `Add ×y after ${q.base} and before ${ending} to remove the final y.`);
    assert.deepEqual(d.problemBlockIds, direct);
    assert.deepEqual(d.missingLabels, ['×y']);
    assert.deepEqual(diagnoseAnswer(q, built.text), d, 'answer-only trace also retains y');
    const s = createExperiment(q.id.startsWith('adj-') ? 'adjectives' : 'adverbs', [q]);
    s.assembly = direct;
    assert.equal(submitTrial(s).correct, false);
    assert.equal(s.score, 0);
  }
});

test('all 192 questions retain every accepted answer through an adaptive correct recipe', () => {
  for (const source of banks) {
    const q = prepareAdaptiveQuestion(source);
    assert.deepEqual(questionContextIssues(q), [], q.id);
    const visible = new Set(adaptiveBlocks(q).map(b => b.id));
    for (const answer of q.answers) assert.ok(q.correctSequences.some(recipe => recipe.every(id => visible.has(id)) && assemble(q, recipe).text === answer), `${q.id}: ${answer}`);
  }
});

test('legacy and malicious direct transforms cannot secretly remove y in either engine or trace', () => {
  const q = legacy(get());
  const direct = ids(q, ['noisy', '-iest']);
  for (const value of ['noisiest', 'the noisiest', 'arbitrary']) {
    q.blocks.find(b => b.label === '-iest').transforms.noisy = value;
    assert.equal(assemble(q, direct).text, 'noisyiest');
    assert.equal(diagnoseAnswer(q, 'noisyiest', direct).code, 'missing-y-operation');
    assert.equal(joinComparisonSuffix('noisy', q.blocks.find(b => b.label === '-iest')), 'noisyiest');
  }
  assert.equal(isCorrect(q, 'the noisiest'), true, 'historical/string lookup remains content-based');
});

test('explicit recipes earn a first mark, while a corrected direct attempt earns zero', () => {
  for (const q of affected) {
    const moduleId = q.id.startsWith('adj-') ? 'adjectives' : 'adverbs';
    const fresh = createExperiment(moduleId, [q]);
    fresh.assembly = [...fresh.questions[0].correctSequences[0]];
    assert.equal(submitTrial(fresh).mark, 1, q.id);
    const retry = createExperiment(moduleId, [q]);
    retry.assembly = retry.questions[0].correctSequences[0].filter(id => id !== 'remove-y');
    assert.equal(submitTrial(retry).correct, false);
    const first = retry.firstAnswer;
    retryTrial(retry);
    retry.assembly = [...retry.questions[0].correctSequences[0]];
    assert.equal(submitTrial(retry).mark, 0);
    assert.equal(retry.results[0].firstAnswer, first);
    assert.equal(validSession(retry, [moduleId]), true);
  }
});

test('normalization is pure/idempotent, retains stem transforms and does not repair arbitrary corruption', () => {
  const old = legacy(get());
  old.blocks.find(b => b.label === '-iest').transforms.nois = 'noisiest';
  const frozen = freeze(old);
  const before = structuredClone(frozen);
  const q = normaliseExplicitYQuestion(frozen);
  assert.deepEqual(frozen, before);
  assert.deepEqual(normaliseExplicitYQuestion(q), q);
  assert.deepEqual(q.blocks.find(b => b.label === '-iest').transforms, { nois: 'noisiest' });
  assert.deepEqual(questionContextIssues(q), []);
  assert.ok(questionContextIssues(frozen).length, 'strict raw context rejects implicit metadata');
  for (const mutate of [
    q => { q.blocks.find(b => b.label === '-iest').transforms.noisy = 'wrong'; },
    q => { q.blocks.find(b => b.label === '-iest').transforms.stranger = 'noisiest'; },
    q => { q.correctSequences.push(['unknown-id']); },
    q => { q.correctSequences = q.correctSequences.filter(recipe => !recipe.includes('remove-y')); },
    q => { q.blocks.find(b => b.operation === 'remove-final-y').operation = 'bad-operation'; }
  ]) {
    const corrupt = legacy(get()); mutate(corrupt);
    assert.ok(questionContextIssues(prepareAdaptiveQuestion(corrupt)).length, 'unsupported metadata remains rejectable');
  }
  const strict = get();
  strict.correctSequences.push(strict.correctSequences[0].filter(id => id !== 'remove-y'));
  assert.ok(questionContextIssues(prepareAdaptiveQuestion(strict)).length, 'new direct recipes without sanctioned transforms stay invalid');
});

test('old building/wrong/correct work keeps raw IDs and all historical scores/results through refresh', () => {
  for (const status of ['building', 'wrong', 'correct']) {
    const q = legacy(get());
    const s = createExperiment('adjectives', [q]);
    s.questions = [q];
    s.trayOrder = q.blocks.map(b => b.id);
    s.assembly = ids(q, status === 'wrong' ? ['noisy', '-iest'] : ['the', 'noisy', '-iest']);
    if (status !== 'building') {
      s.status = status; s.attempts = 1;
      s.firstAnswer = status === 'wrong' ? 'noisiest' : 'the noisiest';
      if (status === 'correct') {
        s.score = 1;
        s.results = [{ questionId: q.id, firstAnswer: s.firstAnswer, finalAnswer: s.firstAnswer, mark: 1, gaveUp: false }];
      }
    }
    s.originalReport = { historical: true, score: 8 };
    const old = structuredClone(s);
    assert.equal(validSession(s, ['adjectives']), true, status);
    const upgraded = upgradeAdaptiveSession(s);
    assert.deepEqual(s, old);
    for (const key of Object.keys(old).filter(key => key !== 'questions')) assert.deepEqual(upgraded[key], old[key], key);
    assert.deepEqual(questionContextIssues(upgraded.questions[0]), []);
    assert.equal(validSession(upgraded, ['adjectives']), true);
    assert.deepEqual(upgradeAdaptiveSession(JSON.parse(JSON.stringify(upgraded))), upgraded);
    if (status === 'correct') {
      const recipe = checkedExplicitYRecipe(upgraded);
      assert.ok(recipe.includes('remove-y'));
      assert.equal(assemble(upgraded.questions[0], recipe).text, 'the noisiest');
      assert.equal(makeReport(upgraded).results[0].firstAnswer, 'the noisiest');
    } else {
      assert.equal(checkedExplicitYRecipe(upgraded), null);
      assert.ok(assemble(upgraded.questions[0], upgraded.assembly).text.includes('noisyiest'));
    }
    if (status === 'wrong') {
      retryTrial(upgraded);
      upgraded.assembly = [...upgraded.questions[0].correctSequences[0]];
      assert.equal(submitTrial(upgraded).mark, 0);
      assert.equal(upgraded.results[0].firstAnswer, 'noisiest');
    }
  }
});

test('storage keeps valid legacy work/reports byte-for-byte and independent best records; corrupt work archives', async () => {
  const memory = new Map();
  globalThis.localStorage = { setItem: (k, v) => memory.set(k, v), getItem: k => memory.get(k) ?? null, removeItem: k => memory.delete(k) };
  const storage = await import('../site/js/storage.js?explicit-y-storage');
  const q = legacy(get());
  const session = createExperiment('adjectives', [q]); session.questions = [q];
  const report = { schema: 2, questions: [structuredClone(q)], results: [{ firstAnswer: 'the noisiest', mark: 1 }], score: 1, count: 1 };
  storage.save('session', session); storage.save('last-report', report); storage.save('best', { 'adjectives:10': { score: 8 } });
  const before = new Map(memory);
  assert.equal(storage.archiveOutdatedWork(), false);
  assert.deepEqual(memory, before);
  q.correctSequences.push(['corrupt-id']); storage.save('session', { ...session, questions: [q] });
  assert.equal(storage.archiveOutdatedWork(), true);
  assert.equal(storage.load('session'), null);
  assert.ok(storage.load('archive:session'));
  assert.deepEqual(storage.load('last-report'), report);
  assert.deepEqual(storage.load('best'), { 'adjectives:10': { score: 8 } });
  delete globalThis.localStorage;
});
