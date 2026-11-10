import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { QUESTION_SCHEMA, IRREGULAR_COMPARISON_FORMS, questionContextIssues } from '../site/js/question-context.js';
import { assemble, createExperiment, submitTrial, advanceTrial } from '../site/js/core.js';
import { validSession } from '../site/js/storage.js';

// Exact pre-update adj-089 snapshot. The browser migration test reads this same
// JSON fixture, so a future regenerated bank cannot erase the reported defect.
const OLD_ADJ089_JSON = String.raw`{
  "id": "adj-089",
  "sentence": "This cup holds _____ that cup.",
  "base": "much",
  "degree": "comparative",
  "rule": "Irregular forms",
  "requiresArticle": false,
  "ingredientMode": "complete",
  "blocks": [
    {"id":"b0","label":"more","kind":"word","category":"structure"},
    {"id":"b1","label":"tea","kind":"word","category":"word"},
    {"id":"b2","label":"than","kind":"word","category":"structure"},
    {"id":"b3","label":"much","kind":"word","category":"word"},
    {"id":"b4","label":"-er","kind":"suffix","category":"ending"},
    {"id":"b5","label":"most","kind":"word","category":"structure"},
    {"id":"b6","label":"-est","kind":"suffix","category":"ending"},
    {"id":"b7","label":"-r","kind":"suffix","category":"ending"},
    {"id":"b8","label":"-st","kind":"suffix","category":"ending"},
    {"id":"b9","label":"-ier","kind":"suffix","category":"ending"},
    {"id":"b10","label":"-iest","kind":"suffix","category":"ending"},
    {"id":"b11","label":"the","kind":"word","category":"structure"},
    {"id":"remove-y","label":"Remove y","kind":"operation","category":"ending","operation":"remove-final-y"}
  ],
  "answers": ["more tea than"],
  "correctSequences": [["b0","b1","b2"]],
  "feedback": [
    {"answers":["much tea than"],"message":"Much tea than is not right here. Much changes its form. Use more tea than in this gap. Use more tea than to compare two things."},
    {"answers":["mucher tea than"],"message":"Mucher tea than is not right here. Much changes its form. Use more tea than in this gap. Use more tea than to compare two things."},
    {"answers":["most tea than"],"message":"Most tea than is not right here. Much changes its form. Use more tea than in this gap. Use more tea than to compare two things."},
    {"message":"Use more tea than to compare two things."}
  ],
  "explanation": "Use more tea than to compare two things. Much changes its form. Use more tea than in this gap."
}`;
export const OLD_ADJ089 = JSON.parse(OLD_ADJ089_JSON);
const bank = id => JSON.parse(readFileSync(new URL(`../site/data/${id}-questions.json`, import.meta.url))).questions;
const goodComparative = () => structuredClone(bank('adjectives').find(question => question.base === 'good' && question.degree === 'comparative'));
const hasAnswerIssue = question => questionContextIssues(question).some(issue => issue.includes('answer must be noun-free'));
const hasIngredientIssue = question => questionContextIssues(question).some(issue => issue.includes('unrelated word ingredient'));

test('exact old adj-089 fixture rejects both its tea ingredient and more tea than answer', () => {
  assert.equal(OLD_ADJ089.id, 'adj-089');
  assert.equal(OLD_ADJ089.base, 'much');
  assert.equal(OLD_ADJ089.sentence, 'This cup holds _____ that cup.');
  assert.deepEqual(OLD_ADJ089.answers, ['more tea than']);
  assert.equal(assemble(OLD_ADJ089, OLD_ADJ089.correctSequences[0]).text, 'more tea than');
  assert.ok(hasIngredientIssue(OLD_ADJ089));
  assert.ok(hasAnswerIssue(OLD_ADJ089));
});

test('noun ingredients are rejected without a hardcoded six-noun blacklist', () => {
  for (const noun of ['tea', 'water', 'rice', 'time', 'books', 'chairs', 'pencils', 'sand']) {
    const question = goodComparative();
    question.blocks.push({ id: 'noun', label: noun, kind: 'word', category: 'word' });
    assert.ok(hasIngredientIssue(question), noun);
    assert.ok(!hasAnswerIssue(question), 'The unchanged better than answer remains noun-free');
  }
});

test('extra nouns in accepted answers are rejected even when no noun ingredient is offered', () => {
  for (const answer of ['better tea than', 'better pencils than', 'better than tea', 'the better tea than', 'better best than', 'better better than']) {
    const question = goodComparative();
    question.answers = [answer];
    assert.ok(!question.blocks.some(block => ['tea', 'pencils'].includes(block.label)));
    assert.ok(hasAnswerIssue(question), answer);
    assert.ok(!hasIngredientIssue(question), 'All offered words are still genuine ingredients');
  }
  const oldWithoutTea = structuredClone(OLD_ADJ089);
  oldWithoutTea.blocks = oldWithoutTea.blocks.filter(block => block.label !== 'tea');
  assert.ok(hasAnswerIssue(oldWithoutTea), 'more tea than must not rely on tea being offered');
});

test('unrelated irregular families and prebuilt regular comparison word tiles are rejected', () => {
  for (const label of ['farther', 'worst', 'taller', 'worser']) {
    const question = goodComparative();
    question.blocks.push({ id: 'unrelated', label, kind: 'word' });
    assert.ok(hasIngredientIssue(question), label);
  }
  const question = goodComparative();
  question.answers = ['farther than'];
  assert.ok(hasAnswerIssue(question));
});

test('suffix transforms cannot smuggle a noun or arbitrary headword into the answer allow-list', () => {
  for (const answer of ['better tea', 'tea']) {
    const question = goodComparative();
    question.blocks.find(block => block.label === '-er').transforms = { good: answer };
    question.answers = [`${answer} than`];
    assert.ok(hasAnswerIssue(question), answer);
  }
});

test('genuine relevant irregular families match the generator families', () => {
  assert.deepEqual(IRREGULAR_COMPARISON_FORMS, {
    good: ['better', 'best'], bad: ['worse', 'worst'],
    well: ['better', 'best'], badly: ['worse', 'worst'],
    far: ['farther', 'further', 'farthest', 'furthest'],
    little: ['less', 'least'], much: ['more', 'most'], many: ['more', 'most']
  });
  const source = readFileSync(new URL('../scripts/author-content.py', import.meta.url), 'utf8');
  for (const [base, forms] of Object.entries(IRREGULAR_COMPARISON_FORMS)) {
    const line = source.split('\n').find(line => line.trim().startsWith(`"${base}": (`));
    assert.ok(line, base);
    assert.deepEqual([...line.matchAll(/"([a-z]+)"/g)].map(match => match[1]).slice(1), forms, base);
  }
});

test('quantity superlatives the least and the most remain valid noun-free answers', () => {
  const questions = bank('adjectives').filter(question => ['adj-086', 'adj-088', 'adj-090', 'adj-092', 'adj-094', 'adj-096'].includes(question.id));
  assert.equal(questions.length, 6);
  for (const question of questions) {
    assert.ok(question.answers.every(answer => ['the least', 'the most'].includes(answer)), question.id);
    assert.deepEqual(questionContextIssues(question), [], question.id);
    for (const sequence of question.correctSequences) assert.ok(question.answers.includes(assemble(question, sequence).text), question.id);
  }
});

test('all optional-the adverb superlatives and far alternatives remain accepted', () => {
  for (const question of bank('adverbs').filter(question => question.degree === 'superlative')) {
    assert.ok(question.answers.some(answer => answer.startsWith('the ')), question.id);
    assert.ok(question.answers.some(answer => !answer.startsWith('the ')), question.id);
    assert.deepEqual(questionContextIssues(question), [], question.id);
  }
  for (const moduleId of ['adjectives', 'adverbs']) {
    for (const question of bank(moduleId).filter(question => question.base === 'far')) {
      for (const stem of question.degree === 'comparative' ? ['farther', 'further'] : ['farthest', 'furthest']) {
        assert.ok(question.answers.some(answer => answer.split(' ').includes(stem)), `${question.id}: ${stem}`);
      }
      assert.deepEqual(questionContextIssues(question), [], question.id);
    }
  }
});

test('direct suffix and explicit final-y deletion alternatives remain noun-free', () => {
  for (const moduleId of ['adjectives', 'adverbs']) {
    for (const question of bank(moduleId).filter(question => /y$/.test(question.base) && question.rule === 'Spelling changes')) {
      assert.ok(question.correctSequences.some(sequence => sequence.includes('remove-y')), question.id);
      assert.ok(question.correctSequences.some(sequence => !sequence.includes('remove-y')), question.id);
      assert.deepEqual(questionContextIssues(question), [], question.id);
      for (const sequence of question.correctSequences) assert.ok(question.answers.includes(assemble(question, sequence).text), question.id);
    }
  }
});

test('all banks remain 96 unique noun-free questions with 48/48 degrees and 24 per rule', () => {
  const expectedRules = ['Regular forms', 'Spelling changes', 'Longer forms', 'Irregular forms'];
  for (const moduleId of ['adjectives', 'adverbs']) {
    const questions = bank(moduleId);
    assert.equal(questions.length, 96, moduleId);
    assert.equal(new Set(questions.map(question => question.id)).size, 96, moduleId);
    for (const degree of ['comparative', 'superlative']) assert.equal(questions.filter(question => question.degree === degree).length, 48, `${moduleId}: ${degree}`);
    for (const rule of expectedRules) assert.equal(questions.filter(question => question.rule === rule).length, 24, `${moduleId}: ${rule}`);
    for (const question of questions) {
      assert.deepEqual(questionContextIssues(question), [], question.id);
      const allowed = new Set([question.base, 'more', 'most', 'than', 'the', ...(IRREGULAR_COMPARISON_FORMS[question.base] ?? [])]);
      for (const block of question.blocks.filter(block => block.kind === 'word')) assert.ok(allowed.has(block.label), `${question.id}: ${block.label}`);
      for (const sequence of question.correctSequences) assert.ok(question.answers.includes(assemble(question, sequence).text), `${question.id}: ${sequence}`);
    }
  }
});

test('the six changed IDs now use good/bad/far comparatives with no lexical extras', () => {
  const replacements = new Map([['adj-085', 'good'], ['adj-087', 'bad'], ['adj-089', 'good'], ['adj-091', 'bad'], ['adj-093', 'far'], ['adj-095', 'far']]);
  for (const [id, base] of replacements) {
    const question = bank('adjectives').find(question => question.id === id);
    assert.ok(question, id);
    assert.equal(question.base, base, id);
    assert.equal(question.degree, 'comparative', id);
    assert.equal(question.rule, 'Irregular forms', id);
    assert.deepEqual(questionContextIssues(question), [], id);
    assert.ok(question.answers.every(answer => /^(?:better|worse|farther|further) than$/.test(answer)), id);
  }
});

test('schema stays 2: validSession excludes the old same-schema snapshot and accepts all current questions', () => {
  assert.equal(QUESTION_SCHEMA, 2);
  const oldSession = createExperiment('adjectives', [OLD_ADJ089]);
  oldSession.assembly = ['b0', 'b1', 'b2'];
  assert.equal(oldSession.schema, 2);
  assert.equal(validSession(oldSession, ['adjectives', 'adverbs']), false);
  for (const moduleId of ['adjectives', 'adverbs']) {
    const questions = bank(moduleId);
    for (let start = 0; start < questions.length; start += 10) {
      assert.equal(validSession(createExperiment(moduleId, questions.slice(start, start + 10)), ['adjectives', 'adverbs']), true, `${moduleId}: ${start}`);
    }
  }
});

test('new compatible snapshots preserve first-attempt scores, retries and unfinished assembly', () => {
  const session = createExperiment('adjectives', bank('adjectives').slice(0, 10));
  session.assembly = session.questions[0].correctSequences[0];
  assert.equal(submitTrial(session).mark, 1);
  assert.equal(advanceTrial(session), 'next');
  session.assembly = [session.questions[1].correctSequences[0][0]];
  const snapshot = JSON.parse(JSON.stringify(session));
  assert.equal(snapshot.score, 1);
  assert.equal(snapshot.results[0].mark, 1);
  assert.equal(validSession(snapshot, ['adjectives', 'adverbs']), true);
  assert.deepEqual(snapshot.assembly, session.assembly);
});

test('corrupt nested snapshots are rejected without throwing during context/archive checks', () => {
  const mutations = [
    question => { question.base = null; },
    question => { question.base = {}; },
    question => { question.base = 'constructor'; },
    question => { question.id = {}; },
    question => { question.degree = null; },
    question => { question.blocks = [null]; },
    question => { question.blocks[0].label = {}; },
    question => { question.blocks[0].transforms = []; },
    question => { question.correctSequences = {}; },
    question => { question.correctSequences = [null]; },
    question => { question.correctSequences = [['missing-block']]; },
    question => { question.feedback = [null]; },
    question => { question.feedback = [{ answers: {} }]; },
    question => { question.answers = [null]; }
  ];
  for (const mutate of mutations) {
    const question = goodComparative();
    mutate(question);
    assert.doesNotThrow(() => questionContextIssues(question));
    assert.ok(questionContextIssues(question).length);
    const snapshot = { schema: 2, moduleId: 'adjectives', questions: [question], count: 1 };
    assert.equal(validSession(snapshot, ['adjectives']), false);
  }
});
