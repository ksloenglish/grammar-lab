import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import vm from 'node:vm';
import { assemble, createExperiment } from '../site/js/core.js';
import { QUESTION_SCHEMA } from '../site/js/question-context.js';
import { renderIngredients } from '../site/js/ingredients.js';
import { adaptiveBlocks, prepareAdaptiveQuestion } from '../site/js/comparison-blocks.js';

const source = path => readFileSync(new URL(`../site/${path}`, import.meta.url), 'utf8');
const app = source('js/app.js');
const css = source('css/styles.css');
const bank = moduleId => JSON.parse(source(`data/${moduleId}-questions.json`)).questions;
const escape = value => String(value).replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[character]));

test('all reagent buttons explicitly disable dragging, in building and locked states', () => {
  for (const moduleId of ['adjectives', 'adverbs']) {
    for (const raw of bank(moduleId)) {
      const question = prepareAdaptiveQuestion(raw);
      for (const building of [true, false]) {
        const html = renderIngredients(question, question.blocks.map(block => block.id), [], building, escape);
        const buttons = [...html.matchAll(/<button\b[^>]*>/g)].map(match => match[0]);
        assert.equal(buttons.length, adaptiveBlocks(question, []).length, question.id);
        for (const button of buttons) {
          assert.match(button, /draggable="false"/, question.id);
          assert.match(button, /data-action="add-block"/, question.id);
          assert.equal(/\sdisabled(?:\s|>)/.test(button), !building, question.id);
        }
      }
    }
  }
});

test('selected blocks explicitly disable dragging and have only a return button', () => {
  const assembly = app.slice(app.indexOf('function assemblyView('), app.indexOf('function trialView('));
  assert.match(assembly, /draggable="false"/);
  assert.match(assembly, /data-action="return-block"/);
  assert.doesNotMatch(assembly, /move-buttons|move-block|data-direction/);
});

test('drag/drop and arrow-move event paths cannot mutate an answer', () => {
  assert.doesNotMatch(app, /addEventListener\(['"](?:dragstart|dragover|dragleave|drop|dragend)['"]/);
  assert.doesNotMatch(app, /\bmoveBlock\b|move-block|draggedId|dragEndedAt|dataTransfer|ArrowLeft|ArrowRight/);
  assert.doesNotMatch(app, /(?:Tap or drag|Drop or tap|also drag|arrow buttons|Next trial|Completed trials|Number of trials|trial count|\bTrial \$\{|\} trials)/i);
});

test('click/keyboard action implementation appends, returns and re-adds only at the end', async () => {
  const question = bank('adjectives').find(item => item.id === 'adj-043');
  const session = createExperiment('adjectives', [question]);
  const ids = question.correctSequences[0];
  const start = app.indexOf('async function changeBlock(');
  const end = app.indexOf('\nasync function ', start + 1);
  assert.ok(start >= 0 && end > start, 'the shared button action implementation exists');
  const context = vm.createContext({
    session, assemble, justPlacedBlock: null, justFused: false,
    refreshTrial: async () => {}, announce: () => {}
  });
  vm.runInContext(`${app.slice(start, end)}\nglobalThis.changeBlockForTest = changeBlock;`, context);
  for (const id of ids) await context.changeBlockForTest(id, 'add');
  assert.deepEqual(session.assembly, ids);
  await context.changeBlockForTest(ids[0], 'add');
  assert.deepEqual(session.assembly, ids, 'adding an already-selected block does not reorder it');
  await context.changeBlockForTest(ids[0], 'return');
  assert.deepEqual(session.assembly, ids.slice(1));
  await context.changeBlockForTest(ids[0], 'add');
  assert.deepEqual(session.assembly, [...ids.slice(1), ids[0]]);
  assert.equal(session.attempts, 0);
  assert.equal(session.firstAnswer, null);
  assert.equal(session.score, 0);
});

test('base hints are inline immediately after the gap, without a separate base-hint row', () => {
  assert.match(app, /class="gap-with-hint"/);
  assert.match(app, /class="gap"/);
  assert.match(app, /class="inline-base-hint"/);
  assert.doesNotMatch(app, /class="base-hint"|Base word: <strong>/);
  assert.match(css, /\.gap-with-hint/);
  assert.match(css, /\.inline-base-hint/);
});

test('inline hints preserve the blank, sentence suffix and escaped long base text', () => {
  const start = app.indexOf('function gapSentence(');
  const end = app.indexOf('\nfunction ', start + 1);
  const context = vm.createContext({ e: escape });
  vm.runInContext(`${app.slice(start, end)}\nglobalThis.renderGapForTest = gapSentence;`, context);
  for (const base of ['interesting', 'comfortable', 'successfully', '<long & "base">']) {
    const markup = context.renderGapForTest('Before & _____ after.', base);
    assert.match(markup, /^Before &amp; <span class="gap-with-hint"><span class="gap">_____<\/span>\s*<span class="inline-base-hint">/);
    assert.ok(markup.includes(`(${escape(base)})</span></span> after.`));
    assert.equal((markup.match(/class="gap"/g) ?? []).length, 1);
    assert.doesNotMatch(markup, /<long|class="base-hint"/);
  }
});

test('setup retains technical trial-count names but visible choices use questions', () => {
  const setup = app.slice(app.indexOf('async function setupView('), app.indexOf('async function learnView('));
  assert.match(setup, /<legend>Number of questions<\/legend>/);
  assert.match(setup, /name="trial-count"/);
  assert.match(setup, /\[10, 20, 30\]/);
  assert.match(setup, /questions/);
  assert.doesNotMatch(setup, />trials<|Number of trials|trial count/i);
  const home = app.slice(app.indexOf('function homeView('), app.indexOf('async function setupView('));
  assert.doesNotMatch(home, /No login needed\.?|hero-footnote/);
});

test('phone selected blocks do not regress to full-width rows', () => {
  for (const rule of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    if (!rule[1].includes('.assembled-block')) continue;
    assert.doesNotMatch(rule[2], /(?:^|;)\s*(?:width|min-width|flex-basis)\s*:\s*100%/);
    assert.doesNotMatch(rule[2], /(?:^|;)\s*flex\s*:\s*1(?:\s|;|$)/);
  }
});

test('explicit-y revision preserves all bank identity except sanctioned metadata and explanations, with schema 2', () => {
  const hashes = {
    adjectives: '516f52b2b43cfa3703ca796046df233addded217daf8cf0087a33f26d74d9194',
    adverbs: '98880152a7ffeb45c0ba0c569ea7cfccb8f02f564d2b295880b2b283e6166389'
  };
  const withoutExplanations = value => ({ ...value, questions: value.questions.map(({ explanation, ...question }) => question) });
  const sanctionedHead = value => {
    const result = structuredClone(withoutExplanations(value));
    for (const question of result.questions) {
      if (!/y$/i.test(question.base)) continue;
      let legacy = false;
      for (const block of question.blocks) {
        if (block.kind !== 'suffix' || !['-ier', '-iest'].includes(block.label)
          || block.transforms?.[question.base] !== question.base.slice(0, -1) + block.label.slice(1)) continue;
        delete block.transforms[question.base];
        legacy = true;
      }
      if (legacy) question.correctSequences = question.correctSequences.filter(sequence => sequence.some(id =>
        question.blocks.find(block => block.id === id)?.operation === 'remove-final-y'));
    }
    return result;
  };
  const canonical = value => JSON.stringify(value, (_, item) => item && typeof item === 'object' && !Array.isArray(item)
    ? Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item);
  for (const [moduleId, hash] of Object.entries(hashes)) {
    const current = JSON.parse(source(`data/${moduleId}-questions.json`));
    const head = JSON.parse(execFileSync('git', ['show', `HEAD:site/data/${moduleId}-questions.json`], { cwd: new URL('../', import.meta.url), encoding: 'utf8' }));
    assert.deepEqual(withoutExplanations(current), sanctionedHead(head), `${moduleId}: only explanations, exact legacy base-y maps and direct implicit-y recipes may differ from HEAD`);
    assert.equal(createHash('sha256').update(canonical(withoutExplanations(current))).digest('hex'), hash, `${moduleId}: pinned identity of all other fields`);
    assert.ok(current.questions.every(question => typeof question.explanation === 'string' && question.explanation.trim()));
    assert.equal(bank(moduleId).length, 96);
  }
  assert.equal(QUESTION_SCHEMA, 2);
  const state = createExperiment('adjectives', bank('adjectives').slice(0, 10));
  assert.equal(state.schema, 2);
  assert.equal(state.count, 10);
  assert.deepEqual(Object.keys(state).sort(), [
    'schema', 'moduleId', 'questions', 'count', 'index', 'score', 'results', 'assembly',
    'trayOrder', 'attempts', 'firstAnswer', 'status', 'feedback', 'practice',
    'originalReport', 'startedAt'
  ].sort());
});
