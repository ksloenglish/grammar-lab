import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assemble, sampleQuestions, createExperiment, submitTrial, retryTrial, giveUp, advanceTrial, makeReport, wrongQuestions, ruleBreakdown } from '../site/js/core.js';
import { validSession } from '../site/js/storage.js';
const bank = id => JSON.parse(readFileSync(new URL(`../site/data/${id}-questions.json`, import.meta.url))).questions;

for (const id of ['adjectives', 'adverbs']) {
  test(`${id}: ten complete 10-trial experiments; no repeats, accurate reports`, () => {
    const questions = bank(id);
    for (let run = 0; run < 10; run++) {
      const selected = sampleQuestions(questions, 10);
      assert.equal(new Set(selected.map(q => q.id)).size, 10);
      const session = createExperiment(id, selected);
      for (let i = 0; i < 10; i++) {
        const question = selected[i];
        session.assembly = question.correctSequences[run % question.correctSequences.length];
        const result = submitTrial(session);
        assert.equal(result.correct, true);
        assert.equal(result.mark, 1);
        assert.equal(submitTrial(session), null, 'double-submit must not award again');
        assert.equal(validSession(session, ['adjectives', 'adverbs']), true);
        assert.equal(advanceTrial(session), i === 9 ? 'complete' : 'next');
      }
      const report = makeReport(session);
      assert.equal(report.score, 10);
      assert.equal(report.percentage, 100);
      assert.equal(report.results.length, 10);
      assert.equal(wrongQuestions(report).length, 0);
      assert.equal(Object.values(ruleBreakdown(report)).reduce((sum, x) => sum + x.total, 0), 10);
    }
  });
  test(`${id}: every answer alternative is accepted when assembled`, () => {
    for (const question of bank(id)) {
      for (const sequence of question.correctSequences) {
        const session = createExperiment(id, [question]);
        session.assembly = sequence;
        assert.equal(submitTrial(session).correct, true, `${question.id}: ${assemble(question, sequence).text}`);
      }
    }
  });
  test(`${id}: wrong first attempt, retry, give-up and practice preserve marking`, () => {
    const questions = sampleQuestions(bank(id), 10);
    const session = createExperiment(id, questions);
    for (let i = 0; i < 10; i++) {
      const question = questions[i];
      assert.equal(submitTrial(session), null, 'empty submission ignored');
      assert.equal(session.attempts, 0);
      const used = new Set(question.correctSequences.flat());
      session.assembly = [question.blocks.find(block => !used.has(block.id)).id];
      assert.equal(submitTrial(session).correct, false);
      const firstAnswer = session.firstAnswer;
      if (i % 2 === 0) {
        retryTrial(session);
        session.assembly = question.correctSequences[0];
        assert.equal(submitTrial(session).correct, true);
        assert.equal(session.results[i].mark, 0);
      } else {
        assert.equal(giveUp(session), true);
        assert.equal(giveUp(session), false, 'cannot give up twice');
      }
      assert.equal(session.results[i].firstAnswer, firstAnswer);
      assert.equal(session.score, 0);
      assert.equal(validSession(JSON.parse(JSON.stringify(session)), ['adjectives', 'adverbs']), true);
      advanceTrial(session);
    }
    const report = makeReport(session);
    assert.equal(report.score, 0);
    const practice = createExperiment(id, wrongQuestions(report), true, report);
    for (const question of practice.questions) {
      practice.assembly = question.correctSequences[0]; submitTrial(practice); advanceTrial(practice);
    }
    assert.equal(makeReport(practice).score, 10);
    assert.equal(report.score, 0, 'original stays unchanged');
  });
  test(`${id}: 20 and 30 trials sample without repetitions`, () => {
    for (const n of [20, 30]) for (let i = 0; i < 10; i++) assert.equal(new Set(sampleQuestions(bank(id), n).map(q => q.id)).size, n);
  });
}

test('invalid saved sessions are rejected safely', () => {
  for (const value of [null, {}, { schema: 1 }, { schema: 1, moduleId: 'adjectives', questions: null }]) assert.equal(validSession(value, ['adjectives']), false);
});
test('sampling rejects insufficient content', () => assert.throws(() => sampleQuestions([], 10)));

test('corrupt wrong states cannot earn a first-attempt mark on resume', () => {
  const question = bank('adjectives')[0];
  const session = createExperiment('adjectives', [question]);
  const used = new Set(question.correctSequences.flat());
  session.assembly = [question.blocks.find(block => !used.has(block.id)).id];
  submitTrial(session);
  assert.equal(validSession(session, ['adjectives']), true);
  const noAttempts = { ...session, attempts: 0 };
  const noFirstAnswer = { ...session, firstAnswer: null };
  assert.equal(validSession(noAttempts, ['adjectives']), false);
  assert.equal(validSession(noFirstAnswer, ['adjectives']), false);
  const malformedQuestion = { ...session, questions: [null] };
  assert.equal(validSession(malformedQuestion, ['adjectives']), false);
  retryTrial(session);
  session.assembly = question.correctSequences[0];
  assert.equal(submitTrial(session).mark, 0);
});
