import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { adaptiveBlocks, prepareAdaptiveQuestion, upgradeAdaptiveSession, doublingConsonant, isControlledDoublingBlock, IRREGULAR_COMPARISON_FORMS } from '../site/js/comparison-blocks.js';
import { assemble, isCorrect, createExperiment, submitTrial, retryTrial, giveUp, advanceTrial, makeReport, wrongQuestions } from '../site/js/core.js';
import { QUESTION_SCHEMA, questionContextIssues } from '../site/js/question-context.js';
import { validSession } from '../site/js/storage.js';

const bank = id => JSON.parse(readFileSync(new URL(`../site/data/${id}-questions.json`, import.meta.url))).questions;
const adjectiveQuestions = bank('adjectives');
const adverbQuestions = bank('adverbs');
const get = (base, degree = 'comparative', moduleId = 'adjectives') => (moduleId === 'adjectives' ? adjectiveQuestions : adverbQuestions).find(question => question.base === base && question.degree === degree);
const idFor = (question, label) => question.blocks.find(block => block.label === label).id;
const operationFor = question => question.blocks.find(block => block.operation === 'double-final-consonant');
const labelsFor = question => adaptiveBlocks(question).map(block => block.label);
const normalise = text => text.trim().replace(/\s+/g, ' ').toLowerCase();
const freeze = value => { if (value && typeof value === 'object') { Object.freeze(value); Object.values(value).forEach(freeze); } return value; };

function syntheticDoubling(base, degree = 'comparative', optionalThe = false) {
  const question = structuredClone(get('big', degree));
  question.id = 'synthetic-' + base + '-' + degree;
  question.base = base;
  question.requiresArticle = degree === 'superlative' && !optionalThe;
  for (const block of question.blocks) {
    if (block.label === 'big') block.label = base;
    if (['-ger', '-gest'].includes(block.label)) block.label = '-' + base.at(-1) + (block.label === '-ger' ? 'er' : 'est');
  }
  const word = base + base.at(-1) + (degree === 'comparative' ? 'er' : 'est');
  question.answers = degree === 'comparative' ? [word + ' than'] : ['the ' + word, ...(optionalThe ? [word] : [])];
  if (optionalThe) question.correctSequences.push(question.correctSequences[0].filter(id => id !== idFor(question, 'the')));
  question.feedback = [];
  return question;
}

for (const [moduleId, questions] of [['adjectives', adjectiveQuestions], ['adverbs', adverbQuestions]]) {
  test(`${moduleId}: every accepted answer in all 96 questions has a recipe made solely from visible adaptive IDs`, () => {
    assert.equal(questions.length, 96);
    assert.equal(new Set(questions.map(question => question.id)).size, 96);
    for (const degree of ['comparative', 'superlative']) assert.equal(questions.filter(question => question.degree === degree).length, 48);
    for (const rule of ['Regular forms', 'Spelling changes', 'Longer forms', 'Irregular forms']) assert.equal(questions.filter(question => question.rule === rule).length, 24);
    for (const source of questions) {
      const original = structuredClone(source);
      const prepared = prepareAdaptiveQuestion(freeze(source));
      assert.deepEqual(source, original, source.id);
      assert.notEqual(prepared, source);
      assert.deepEqual(prepared.answers, source.answers, source.id);
      assert.deepEqual(prepared.blocks.slice(0, source.blocks.length), source.blocks, source.id);
      assert.deepEqual(questionContextIssues(source), [], `${source.id}: legacy bank`);
      assert.deepEqual(questionContextIssues(prepared), [], `${source.id}: adaptive metadata`);
      assert.deepEqual(prepareAdaptiveQuestion(prepared), prepared, `${source.id}: idempotence`);
      const visible = adaptiveBlocks(prepared);
      assert.equal(visible[0].label, source.base, source.id);
      const available = new Set(visible.map(block => block.id));
      assert.equal(available.size, visible.length, source.id);
      for (const answer of source.answers) {
        assert.ok(prepared.correctSequences.some(sequence => sequence.every(id => available.has(id)) && normalise(assemble(prepared, sequence).text) === normalise(answer)), `${source.id}: ${answer}`);
      }
      for (const legacy of source.correctSequences) assert.ok(isCorrect(prepared, assemble(prepared, legacy).text), `${source.id}: legacy ${legacy}`);
      for (const selected of [[], [visible[0].id], visible.slice(0, 3).map(block => block.id)]) {
        assert.deepEqual(adaptiveBlocks(prepared, selected).map(block => block.id), visible.filter(block => !selected.includes(block.id)).map(block => block.id));
      }
    }
  });
  test(`${moduleId}: opposite-degree forms, unrelated irregulars, noun distractors and combined doubling suffixes never appear`, () => {
    for (const question of questions) {
      const visible = adaptiveBlocks(question);
      const labels = visible.map(block => block.label);
      const comparative = question.degree === 'comparative';
      for (const unwanted of comparative ? ['most', 'the', '-est', '-st', '-iest'] : ['more', 'than', '-er', '-r', '-ier']) assert.ok(!labels.includes(unwanted), `${question.id}: ${unwanted}`);
      assert.ok(!visible.some(block => /^-[bcdfghjklmnpqrstvz](?:er|est)$/.test(block.label) && !['-ier', '-iest'].includes(block.label)), question.id);
      const allowedWords = new Set([question.base, ...(comparative ? ['more', 'than'] : ['most', 'the']), ...(IRREGULAR_COMPARISON_FORMS[question.base] ?? [])]);
      assert.ok(visible.filter(block => block.kind === 'word').every(block => allowedWords.has(block.label)), question.id);
      const allIrregular = IRREGULAR_COMPARISON_FORMS[question.base] ?? [];
      const currentIrregular = question.base === 'far' ? (comparative ? allIrregular.slice(0, 2) : allIrregular.slice(2)) : allIrregular.length ? [allIrregular[comparative ? 0 : 1]] : [];
      for (const form of currentIrregular) assert.ok(labels.includes(form), `${question.id}: retain ${form}`);
      for (const form of allIrregular.filter(form => !currentIrregular.includes(form))) assert.ok(!labels.includes(form), `${question.id}: hide ${form}`);
    }
  });
}

test('fixed pedagogical defaults appear in order; base selection hides only the base and never auto-selects', () => {
  assert.deepEqual(labelsFor(get('tall')), ['tall', 'more', 'than', '-er', '-r']);
  assert.deepEqual(labelsFor(get('tall', 'superlative')), ['tall', 'most', 'the', '-est', '-st']);
  assert.deepEqual(labelsFor(get('nice')), ['nice', 'more', 'than', '-er', '-r']);
  const question = prepareAdaptiveQuestion(get('big'));
  const session = createExperiment('adjectives', [question]);
  assert.deepEqual(session.assembly, []);
  assert.equal(adaptiveBlocks(question)[0].label, 'big');
  assert.equal(adaptiveBlocks(question, [idFor(question, 'big')])[0].label, 'more');
  assert.equal(adaptiveBlocks(question)[0].label, 'big');
});

test('all y-ending bases including -ly get remove-y and the matching -ier/-iest, non-y bases do not', () => {
  for (const question of [...adjectiveQuestions, ...adverbQuestions]) {
    const visible = adaptiveBlocks(question);
    const y = visible.find(block => block.operation === 'remove-final-y');
    assert.equal(Boolean(y), /y$/i.test(question.base), question.id);
    assert.equal(visible.some(block => block.label === (question.degree === 'comparative' ? '-ier' : '-iest')), /y$/i.test(question.base), question.id);
  }
  assert.deepEqual(labelsFor(get('slowly', 'comparative', 'adverbs')), ['slowly', 'more', 'than', '-er', '-r', 'Remove y', '-ier']);
  assert.deepEqual(labelsFor(get('happy', 'superlative')), ['happy', 'most', 'the', '-est', '-st', 'Remove y', '-iest']);
  for (const question of [get('happy'), get('early', 'comparative', 'adverbs')]) {
    const prepared = prepareAdaptiveQuestion(question);
    assert.deepEqual(prepared.correctSequences[0], question.correctSequences[0], 'existing explicit y recipes stay preferred');
    assert.ok(prepared.correctSequences[0].includes('remove-y'));
    assert.equal(assemble(prepared, prepared.correctSequences[0]).parts[0].spellingChanges[0].after, question.base.slice(0, -1));
  }
});

for (const base of ['big', 'hot', 'thin', 'wet', 'stop', 'slim', 'red', 'fat', 'rob']) {
  test(`${base}: actual doubling supplies a literal final letter and prefers explicit flat recipes in both degrees`, () => {
    for (const degree of ['comparative', 'superlative']) {
      const source = get(base, degree) ?? syntheticDoubling(base, degree);
      const question = prepareAdaptiveQuestion(source);
      const operation = operationFor(question);
      assert.deepEqual(operation, { id: 'double-final-consonant', label: base.at(-1), kind: 'operation', operation: 'double-final-consonant', consonant: base.at(-1), category: 'ending' });
      assert.equal(doublingConsonant(question), base.at(-1));
      assert.ok(adaptiveBlocks(question).some(block => block.id === operation.id));
      const recipe = degree === 'comparative' ? [idFor(question, base), operation.id, idFor(question, '-er'), idFor(question, 'than')] : [idFor(question, 'the'), idFor(question, base), operation.id, idFor(question, '-est')];
      assert.deepEqual(question.correctSequences[0], recipe);
      assert.equal(assemble(question, recipe).text, source.answers[0]);
      const part = assemble(question, recipe).parts.find(part => part.spellingChanges?.length);
      assert.deepEqual(part.spellingChanges, [{ before: base, after: base + base.at(-1) }]);
      const beforeEnding = recipe.slice(0, recipe.indexOf(operation.id) + 1);
      assert.equal(assemble(question, beforeEnding).parts.at(-1).text, base + base.at(-1));
      assert.deepEqual(questionContextIssues(question), []);
      assert.ok(source.correctSequences.every(legacy => question.correctSequences.some(recipe => JSON.stringify(recipe) === JSON.stringify(legacy))));
    }
  });
}

test('doubling is inferred from accepted regular answers, never just CVC shape, old endings or opposite degree', () => {
  for (const base of ['far', 'warm', 'long', 'low', 'near', 'good']) {
    const question = get(base) ?? get(base, 'comparative', 'adverbs');
    if (!question) continue;
    assert.equal(doublingConsonant(question), null, base);
    assert.ok(!adaptiveBlocks(question).some(block => block.operation === 'double-final-consonant'), base);
  }
  const question = structuredClone(get('big'));
  question.answers = ['more big than'];
  assert.equal(doublingConsonant(question), null, 'even existing combined endings are not evidence');
  question.base = 'fun';
  question.answers = ['more fun than'];
  assert.equal(doublingConsonant(question), null, 'CVC alone is not evidence');
  question.base = 'big';
  question.answers = ['the biggest'];
  assert.equal(doublingConsonant(question), null, 'opposite-degree answer is not evidence');
  for (const base of ['new', 'box', 'happy']) {
    question.base = base;
    question.answers = [base + base.at(-1) + 'er than'];
    assert.equal(doublingConsonant(question), null, `${base}: w/x/y never doubled`);
  }
});

test('farther/further, farthest/furthest, quantity irregulars and all optional-the recipes remain available', () => {
  assert.deepEqual(labelsFor(get('far')), ['far', 'more', 'than', '-er', '-r', 'farther', 'further']);
  assert.deepEqual(labelsFor(get('far', 'superlative')), ['far', 'most', 'the', '-est', '-st', 'farthest', 'furthest']);
  for (const base of ['little', 'much', 'many']) {
    const question = prepareAdaptiveQuestion(get(base, 'superlative'));
    for (const answer of question.answers) assert.ok(question.correctSequences.some(recipe => recipe.every(id => adaptiveBlocks(question).some(block => block.id === id)) && assemble(question, recipe).text === answer));
  }
  const source = syntheticDoubling('stop', 'superlative', true);
  const question = prepareAdaptiveQuestion(source);
  assert.deepEqual(questionContextIssues(question), []);
  assert.equal(question.correctSequences.length, source.correctSequences.length + 2);
  for (const answer of source.answers) assert.ok(question.correctSequences.slice(0, 2).some(recipe => assemble(question, recipe).text === answer));
  const badly = prepareAdaptiveQuestion(get('badly', 'superlative', 'adverbs'));
  assert.deepEqual(badly.answers, ['the worst', 'worst', 'the most badly', 'most badly']);
  assert.ok(labelsFor(badly).includes('worst'));
  assert.ok(!labelsFor(badly).includes('worse'));
});

test('invalid doubling placements remain visibly bracketed and never receive credit', () => {
  const question = prepareAdaptiveQuestion(get('big'));
  const base = idFor(question, 'big'), operation = operationFor(question).id, er = idFor(question, '-er'), than = idFor(question, 'than');
  const invalid = [
    [operation, base, er, than],
    [base, er, operation, than],
    [base, operation, operation, er, than],
    [base, idFor(question, '-ger'), operation, than],
    [idFor(question, 'more'), operation, base, er, than],
    [base, 'remove-y', operation, er, than]
  ];
  for (const assembly of invalid) {
    const built = assemble(question, assembly);
    assert.ok(built.text.includes('[g]'), assembly.join(','));
    assert.equal(isCorrect(question, built.text), false);
    const session = createExperiment('adjectives', [question]);
    session.assembly = assembly;
    assert.equal(submitTrial(session).correct, false);
    assert.equal(session.score, 0);
    assert.ok(/straight after|word ending in y/.test(session.feedback));
  }
});

test('malformed, mismatched and non-doubling operation definitions are rejected in validation and assembly', () => {
  const mutations = [
    operation => { operation.consonant = 't'; },
    operation => { operation.label = 't'; },
    operation => { delete operation.consonant; },
    operation => { operation.label = operation.consonant = 'gg'; },
    operation => { operation.transforms = { big: 'bigger' }; },
    operation => { operation.category = 'word'; },
    operation => { operation.kind = 'suffix'; },
    operation => { operation.kind = 'word'; },
    operation => { delete operation.operation; },
    operation => { operation.operation = 'replace-word'; }
  ];
  for (const mutate of mutations) {
    const question = structuredClone(prepareAdaptiveQuestion(get('big')));
    const operation = operationFor(question);
    mutate(operation);
    assert.equal(isControlledDoublingBlock(question, operation), false);
    assert.ok(questionContextIssues(question).length);
    const result = assemble(question, question.correctSequences[0]);
    assert.ok(result.text.includes('['));
    assert.equal(isCorrect(question, result.text), false);
    const session = createExperiment('adjectives', [question]);
    session.assembly = question.correctSequences[0];
    assert.equal(submitTrial(session).correct, false);
    assert.equal(session.score, 0);
  }
  const question = structuredClone(get('tall'));
  question.blocks.push({ id: 'double-final-consonant', label: 'l', kind: 'operation', operation: 'double-final-consonant', consonant: 'l', category: 'ending' });
  assert.ok(questionContextIssues(question).length);
  const assembly = [idFor(question, 'tall'), 'double-final-consonant', idFor(question, '-er'), idFor(question, 'than')];
  assert.ok(assemble(question, assembly).text.includes('[l]'));
  assert.equal(isCorrect(question, assemble(question, assembly).text), false);
});

test('accepted metadata rejects repeated, orphan, suffix-fused and wrong-position doubling operations', () => {
  const baseQuestion = prepareAdaptiveQuestion(get('big'));
  const base = idFor(baseQuestion, 'big'), operation = operationFor(baseQuestion).id, er = idFor(baseQuestion, '-er'), than = idFor(baseQuestion, 'than');
  for (const sequence of [[operation, base, er, than], [base, er, operation, than], [base, operation, operation, er, than], [base, operation, idFor(baseQuestion, '-ger'), than], [base, operation, than], [base, 'remove-y', operation, er, than]]) {
    const question = { ...baseQuestion, correctSequences: [sequence] };
    assert.ok(questionContextIssues(question).length, sequence.join(','));
  }
  for (const suffix of ['-r', '-st', '-ier', '-iest']) {
    const question = { ...baseQuestion, correctSequences: [[base, operation, idFor(baseQuestion, suffix), than]] };
    assert.ok(questionContextIssues(question).length, suffix);
  }
  assert.deepEqual(questionContextIssues(get('big')), [], 'legacy authored bank does not have to carry the new operation');
});

test('arbitrary transforms cannot disguise an invalid ending or operation, while genuine y transforms remain valid', () => {
  const question = structuredClone(prepareAdaptiveQuestion(get('big')));
  question.blocks.find(block => block.label === '-er').transforms = { bigg: 'better' };
  assert.ok(questionContextIssues(question).some(issue => issue.includes('arbitrary spelling transform')));
  const happy = structuredClone(get('happy'));
  happy.blocks.find(block => block.label === '-er').transforms = { happy: 'happier' };
  assert.ok(questionContextIssues(happy).some(issue => issue.includes('arbitrary spelling transform')));
  assert.deepEqual(questionContextIssues(get('happy')), []);
});

test('preparation is pure, idempotent and deduplicates canonical recipes without overwriting conflicting authored IDs', () => {
  const source = get('big');
  const prepared = prepareAdaptiveQuestion(source);
  const twice = prepareAdaptiveQuestion(prepared);
  assert.deepEqual(twice, prepared);
  assert.equal(twice.blocks.filter(block => block.id === 'double-final-consonant').length, 1);
  assert.equal(new Set(twice.correctSequences.map(sequence => JSON.stringify(sequence))).size, twice.correctSequences.length);
  const conflict = structuredClone(source);
  const authored = { id: 'double-final-consonant', label: 'g', kind: 'word' };
  conflict.blocks.push(authored);
  const projected = prepareAdaptiveQuestion(conflict);
  assert.deepEqual(projected.blocks.at(-1), authored);
  assert.deepEqual(projected.correctSequences, conflict.correctSequences);
  assert.ok(questionContextIssues(projected).length, 'do not silently sanitise malformed author edits');
});

test('first-attempt scoring, lock, retry, Give Up and independent practice remain unchanged with new canonical recipes', () => {
  const question = get('big');
  const first = createExperiment('adjectives', [question]);
  assert.equal(submitTrial(first), null);
  assert.equal(first.attempts, 0);
  first.assembly = [...first.questions[0].correctSequences[0]];
  assert.deepEqual(submitTrial(first), { correct: true, answer: 'bigger than', mark: 1 });
  assert.equal(submitTrial(first), null);
  assert.equal(first.score, 1);
  const retry = createExperiment('adjectives', [question]);
  retry.assembly = [idFor(retry.questions[0], 'big'), idFor(retry.questions[0], 'than')];
  assert.equal(submitTrial(retry).correct, false);
  assert.equal(retry.firstAnswer, 'big than');
  assert.equal(retryTrial(retry), true);
  retry.assembly = [...retry.questions[0].correctSequences[0]];
  assert.equal(submitTrial(retry).mark, 0);
  assert.equal(retry.score, 0);
  assert.equal(retry.results[0].firstAnswer, 'big than');
  assert.equal(validSession(retry, ['adjectives']), true);
  const report = makeReport(retry);
  const practice = createExperiment('adjectives', wrongQuestions(report), true, report);
  assert.ok(practice.questions[0].correctSequences[0].includes('double-final-consonant'));
  practice.assembly = [...practice.questions[0].correctSequences[0]];
  assert.equal(submitTrial(practice).mark, 1);
  assert.equal(report.score, 0);
  assert.equal(practice.originalReport, report);
  const revealed = createExperiment('adjectives', [question]);
  assert.equal(giveUp(revealed), true);
  assert.equal(revealed.score, 0);
  assert.equal(revealed.firstAnswer, '(No answer)');
  assert.equal(giveUp(revealed), false);
});

test('schema-2 old snapshot upgrade preserves unfinished assembled legacy IDs and every scoring/state field', () => {
  const sources = [get('tall'), get('big'), get('big', 'superlative')];
  const session = createExperiment('adjectives', sources);
  session.assembly = [...session.questions[0].correctSequences[0]];
  assert.equal(submitTrial(session).mark, 1);
  advanceTrial(session);
  session.questions = structuredClone(sources); // Simulate saved pre-adaptive metadata.
  session.trayOrder = session.questions[1].blocks.map(block => block.id).reverse();
  session.assembly = [idFor(session.questions[1], 'big'), idFor(session.questions[1], 'than')];
  submitTrial(session);
  retryTrial(session);
  session.assembly = [...sources[1].correctSequences[0].slice(0, -1)];
  session.startedAt = '2026-11-01T12:34:56.000Z';
  session.customState = { retained: true };
  assert.equal(validSession(session, ['adjectives']), true);
  const old = structuredClone(session);
  const upgraded = upgradeAdaptiveSession(session);
  assert.equal(upgraded.schema, QUESTION_SCHEMA);
  assert.equal(upgraded.schema, 2);
  assert.deepEqual(session, old, 'upgrade is not an in-place reset');
  for (const key of Object.keys(old).filter(key => !['questions', 'trayOrder'].includes(key))) assert.deepEqual(upgraded[key], old[key], key);
  assert.deepEqual(upgraded.trayOrder.slice(0, old.trayOrder.length), old.trayOrder);
  assert.deepEqual(upgraded.trayOrder.slice(old.trayOrder.length), ['double-final-consonant']);
  assert.ok(upgraded.questions[1].correctSequences[0].includes('double-final-consonant'));
  assert.ok(upgraded.questions[2].correctSequences[0].includes('double-final-consonant'));
  assert.equal(assemble(upgraded.questions[1], upgraded.assembly).text, assemble(old.questions[1], old.assembly).text);
  assert.equal(validSession(upgraded, ['adjectives']), true);
  assert.deepEqual(upgradeAdaptiveSession(upgraded), upgraded);
  upgraded.assembly.push(idFor(upgraded.questions[1], 'than'));
  assert.equal(submitTrial(upgraded).mark, 0, 'old wrong first attempt cannot become a fresh mark');
  assert.equal(upgraded.score, 1);
  assert.equal(upgraded.results[1].firstAnswer, 'big than');
});

test('upgrade keeps wrong/correct/revealed states, reports and originalReport unchanged, and does not archive all old work', () => {
  for (const status of ['building', 'wrong', 'correct', 'revealed']) {
    const source = get('big');
    const session = createExperiment('adjectives', [source]);
    if (status === 'wrong') { session.assembly = [idFor(source, 'big')]; submitTrial(session); }
    if (status === 'correct') { session.assembly = [...source.correctSequences[0]]; submitTrial(session); }
    if (status === 'revealed') giveUp(session);
    session.questions = [structuredClone(source)];
    session.trayOrder = source.blocks.map(block => block.id);
    session.originalReport = { schema: 2, score: 5, results: [{ mark: 0 }] };
    session.practice = true;
    const upgraded = upgradeAdaptiveSession(session);
    assert.equal(upgraded.status, status);
    assert.deepEqual(upgraded.originalReport, session.originalReport);
    assert.deepEqual(upgraded.results, session.results);
    assert.deepEqual(upgraded.assembly, session.assembly);
    assert.equal(validSession(upgraded, ['adjectives']), true, status);
  }
  const session = createExperiment('adverbs', [get('fast', 'comparative', 'adverbs')]);
  assert.deepEqual(upgradeAdaptiveSession(session), session, 'no forced tray or score changes on unrelated questions');
  assert.equal(upgradeAdaptiveSession(null), null);
  assert.deepEqual(upgradeAdaptiveSession({ schema: 1, questions: [null], index: 0, trayOrder: [] }), { schema: 1, questions: [null], index: 0, trayOrder: [] });
  for (const question of [{}, { blocks: [null] }, { blocks: [{ label: 'big' }] }]) {
    const corrupt = { schema: 2, questions: [question], index: 0, trayOrder: [] };
    assert.doesNotThrow(() => upgradeAdaptiveSession(corrupt));
    assert.deepEqual(upgradeAdaptiveSession(corrupt), corrupt);
  }
});
