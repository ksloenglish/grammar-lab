import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assemble, isCorrect } from '../site/js/core.js';
import { questionContextIssues } from '../site/js/question-context.js';
import { adaptiveBlocks, prepareAdaptiveQuestion } from '../site/js/comparison-blocks.js';
const read = path => JSON.parse(readFileSync(new URL(`../site/data/${path}`, import.meta.url), 'utf8'));
const wordCount = text => text.trim().split(/\s+/u).filter(Boolean).length;
const plain = (value, label) => {
  assert.equal(typeof value, 'string', `${label}: plain-text string required`);
  assert.ok(value.trim(), `${label}: nonempty text required`);
  assert.ok(!/<\/?[a-z][^>]*>|```|\*\*|\]\(/i.test(value), `${label}: plain text, not HTML or Markdown`);
};
export function validateLearn(learn, moduleId = learn.module) {
  assert.equal(learn.module, moduleId, `${moduleId}: Learn module identity`);
  plain(learn.intro, `${moduleId}/intro`);
  assert.ok(wordCount(learn.intro) <= 35, `${moduleId}/intro: ${wordCount(learn.intro)} words; maximum 35`);
  for (const key of ['scopeNote', 'sourceNote']) if (Object.hasOwn(learn, key)) plain(learn[key], `${moduleId}/${key}`);
  assert.ok(Array.isArray(learn.sections) && learn.sections.length, `${moduleId}: sections array required`);
  if (['adjectives', 'adverbs'].includes(moduleId)) assert.equal(learn.sections.filter(section => section.extra !== true).length, 6, `${moduleId}: six core sections`);
  const titles = new Set();
  for (const [i, section] of learn.sections.entries()) {
    const label = `${moduleId}/section-${i}`;
    assert.ok(section && typeof section === 'object' && !Array.isArray(section), `${label}: section object`);
    plain(section.title, `${label}/title`);
    assert.ok(!/[\r\n]/u.test(section.title), `${label}: single-line title`);
    assert.ok(!titles.has(section.title.toLowerCase()), `${label}: unique title`);
    titles.add(section.title.toLowerCase());
    plain(section.text, `${label}/text`);
    if (Object.hasOwn(section, 'extra')) assert.equal(typeof section.extra, 'boolean', `${label}/extra: boolean required`);
    const cap = section.extra === true ? 50 : 40;
    assert.ok(wordCount(section.text) <= cap, `${label}/text: ${wordCount(section.text)} words; maximum ${cap}`);
    if (Object.hasOwn(section, 'note')) plain(section.note, `${label}/note`);
    for (const key of ['examples', 'recipes', 'forms', 'mistakes']) {
      if (!Object.hasOwn(section, key)) continue;
      assert.ok(Array.isArray(section[key]) && section[key].length, `${label}/${key}: nonempty array required`);
      if (['examples', 'recipes'].includes(key)) section[key].forEach((text, n) => plain(text, `${label}/${key}-${n}`));
      else {
        const keys = key === 'forms' ? ['label', 'comparative', 'superlative'] : ['wrong', 'right'];
        for (const [n, row] of section[key].entries()) {
          assert.ok(row && typeof row === 'object' && !Array.isArray(row), `${label}/${key}-${n}: row object`);
          keys.forEach(field => plain(row[field], `${label}/${key}-${n}/${field}`));
        }
        if (key === 'forms') assert.equal(new Set(section.forms.map(row => row.label.toLowerCase())).size, section.forms.length, `${label}: unique form labels`);
      }
    }
    for (const recipe of section.recipes ?? []) {
      assert.ok(!/\b[a-z]+y\s*\+\s*-i(?:er|est)\b/i.test(recipe), `${label}: a y-change recipe must explicitly include ×y before -ier/-iest`);
    }
  }
  assert.ok(Array.isArray(learn.sources) && learn.sources.length, `${moduleId}: sources array required`);
  for (const [i, source] of learn.sources.entries()) {
    plain(source.title, `${moduleId}/source-${i}/title`);
    plain(source.url, `${moduleId}/source-${i}/url`);
    assert.ok(['http:', 'https:'].includes(new URL(source.url).protocol), `${moduleId}: navigable source URL`);
  }
  assert.ok(Array.isArray(learn.miniCheck), `${moduleId}: miniCheck array required`);
  assert.equal(learn.miniCheck.length, 3, `${moduleId}: exactly three mini-checks`);
  assert.equal(new Set(learn.miniCheck.map(check => check.sentence)).size, 3, `${moduleId}: unique mini-check stems`);
  for (const [i, check] of learn.miniCheck.entries()) {
    const label = `${moduleId}/mini-${i}`;
    for (const key of ['sentence', 'answer', 'explanation']) plain(check[key], `${label}/${key}`);
    assert.equal(check.sentence.split('_____').length, 2, `${label}: one gap`);
    assert.ok(Array.isArray(check.options) && check.options.length >= 2, `${label}: options array required`);
    check.options.forEach((option, n) => plain(option, `${label}/option-${n}`));
    assert.equal(new Set(check.options).size, check.options.length, `${label}: unique options`);
    assert.ok(check.options.includes(check.answer), `${label}: answer must be a listed option`);
    assert.ok(!/\bthan\b/i.test(check.sentence), `${label}: stem must not supply than`);
    const comparative = /\bthan\b/i.test(check.answer);
    if (comparative) assert.ok(/\bthan$/i.test(check.answer) && check.answer.match(/\bthan\b/gi).length === 1, `${label}: one final than`);
    else {
      assert.ok(!/\bthe\b/i.test(check.sentence), `${label}: superlative stem must not supply the`);
      if (moduleId === 'adjectives') assert.ok(/^the\s/i.test(check.answer), `${label}: adjective superlative requires the`);
      if (moduleId === 'adverbs') {
        const alternate = /^the\s/i.test(check.answer) ? check.answer.replace(/^the\s+/i, '') : `the ${check.answer}`;
        assert.ok(!check.options.includes(alternate), `${label}: valid optional-the adverb form must not be a wrong option`);
      }
    }
  }
  const coreRecipes = learn.sections.filter(section => !section.extra).flatMap(section => section.recipes ?? []).join(' ');
  if (['adjectives', 'adverbs'].includes(moduleId)) assert.match(coreRecipes, /×\s*y/u, `${moduleId}: core recipe must show explicit ×y`);
  assert.ok(!/direct.{0,25}(?:recipe|accept)|(?:recipe|accept).{0,25}direct|(?:automatically|automatic)\s+(?:remove|removal|drop|delet)/i.test(JSON.stringify(learn)), `${moduleId}: no direct accepted recipe or automatic y removal teaching`);
  return learn;
}
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
  validateLearn(learn, module.id);
  console.log(`${module.id}: ${bank.questions.length} questions; degrees ${JSON.stringify(counts)}; rules ${JSON.stringify(rules)}; 3 mini-checks. PASS`);
}
console.log('All noun-free answers/ingredients, question stems, complete authored trays, controlled operations, legacy recipes and every adaptive visible-answer reachability check passed.');
