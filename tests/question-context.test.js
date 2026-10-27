import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { QUESTION_SCHEMA, questionContextIssues } from '../site/js/question-context.js';
import { assemble, createExperiment, submitTrial } from '../site/js/core.js';
import { validSession } from '../site/js/storage.js';
const bank = id => JSON.parse(readFileSync(new URL(`../site/data/${id}-questions.json`, import.meta.url))).questions;

for (const moduleId of ['adjectives', 'adverbs']) {
  test(`${moduleId}: all 96 stems omit than, all trays include -er, all alternatives fit their sentence gaps`, () => {
    const questions = bank(moduleId);
    assert.equal(questions.length, 96);
    for (const question of questions) {
      assert.deepEqual(questionContextIssues(question), [], question.id);
      for (const sequence of question.correctSequences) {
        const answer = assemble(question, sequence).text;
        const complete = question.sentence.replace('_____', answer);
        assert.equal((complete.match(/\bthan\b/gi) ?? []).length, question.degree === 'comparative' ? 1 : 0, `${question.id}: ${complete}`);
        assert.ok(!/\bthe\s+the\b/i.test(complete), complete);
      }
    }
  });
  test(`${moduleId}: comparative answers without than are not marked correct`, () => {
    for (const question of bank(moduleId).filter(question => question.degree === 'comparative')) {
      const session = createExperiment(moduleId, [question]);
      session.assembly = question.correctSequences[0].filter(id => question.blocks.find(block => block.id === id).label !== 'than');
      assert.equal(submitTrial(session).correct, false, question.id);
    }
  });
}

test('regression: a supplied than remote from the gap is rejected', () => {
  const question = structuredClone(bank('adjectives').find(question => question.base === 'happy' && question.degree === 'comparative'));
  question.sentence = 'Tom was _____ after the game than before it.';
  assert.ok(questionContextIssues(question).some(message => message.includes('must not supply than')));
  const session = createExperiment('adjectives', [question]);
  assert.equal(validSession(session, ['adjectives']), false);
});

test('regression: a wrong -st block cannot hide behind a transform for a non-e word', () => {
  const question = structuredClone(bank('adjectives').find(question => question.base === 'quiet' && question.degree === 'superlative'));
  const correctSuffix = question.blocks.find(block => question.correctSequences.flat().includes(block.id) && block.kind === 'suffix');
  correctSuffix.label = '-st';
  assert.ok(questionContextIssues(question).some(message => message.includes('requires a base ending in e')));
});

test('old question snapshots cannot be resumed as current experiments', () => {
  const session = createExperiment('adjectives', bank('adjectives').slice(0, 10));
  assert.equal(session.schema, QUESTION_SCHEMA);
  assert.equal(validSession({ ...session, schema: 1 }, ['adjectives']), false);
});

for (const moduleId of ['adjectives', 'adverbs']) {
  test(`${moduleId}: superlatives never prefill the and always offer it as a block`, () => {
    for (const question of bank(moduleId).filter(question => question.degree === 'superlative')) {
      assert.ok(!/\bthe\b/i.test(question.sentence), question.id);
      assert.ok(question.blocks.some(block => block.label === 'the'), question.id);
      if (moduleId === 'adjectives') {
        assert.ok(question.requiresArticle, question.id);
        assert.ok(question.answers.every(answer => /^the\s/.test(answer)), question.id);
        const session = createExperiment(moduleId, [question]);
        session.assembly = question.correctSequences[0].filter(id => question.blocks.find(block => block.id === id).label !== 'the');
        assert.equal(submitTrial(session).correct, false, `${question.id}: missing the`);
      }
    }
  });
}

test('regression: a prefilled superlative article is rejected', () => {
  const question = structuredClone(bank('adjectives').find(question => question.degree === 'superlative'));
  question.sentence = 'This is the _____ bus route home.';
  assert.ok(questionContextIssues(question).some(message => message.includes('must not supply the')));
});
