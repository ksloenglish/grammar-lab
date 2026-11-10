import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { validateLearn } from '../scripts/validate.mjs';

const read = path => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const learn = id => JSON.parse(read(`site/data/${id}-learn.json`));
const modules = ['adjectives', 'adverbs'];
const words = text => text.trim().split(/\s+/u).length;
const baseline = {
  adjectives: [
    ['Our school hall is _____ our classroom.', ['larger than', 'largeer than', 'larger'], 'larger than'],
    ['Of three bags, our red bag is _____.', ['the best', 'the goodest', 'the better'], 'the best'],
    ['This is _____ place in our library.', ['the quietest', 'the quieter', 'the quietiest'], 'the quietest'],
  ],
  adverbs: [
    ['Our teacher spoke _____ before.', ['more clearly than', 'clearer than', 'more clearly'], 'more clearly than'],
    ['Of three teams, our blue team played _____.', ['the best', 'goodest', 'more well'], 'the best'],
    ['Among three buses, Bus 2 arrived _____.', ['the earliest', 'the earlier', 'earlyest'], 'the earliest'],
  ],
};
const farSource = { title: 'Cambridge Dictionary Grammar: Farther, farthest or further, furthest?', url: 'https://dictionary.cambridge.org/us/grammar/british-grammar/farther-farthest-or-further-furthest' };
const sources = {
  adjectives: [{ title: 'Cambridge Dictionary Grammar: Comparison: adjectives', url: 'https://dictionary.cambridge.org/us/grammar/british-grammar/comparison-adjectives-bigger-biggest-more-interesting' }, farSource],
  adverbs: [{ title: 'EF English Grammar: Comparative and superlative adverbs', url: 'https://www.ef.com/wwen/english-resources/english-grammar/comparative-and-superlative-adverbs/' }, farSource],
};
const oldExplanations = {
  adjectives: ['Large ends in -e, so add -r and then than: larger than.', 'Good is irregular: good → better → best. A superlative adjective before a noun phrase needs the: the best.', 'Use the quietest. The most quiet is also correct, but it is not an option here.'],
  adverbs: ['Clearly ends in -ly, so use more clearly than.', 'Well is irregular: well → better → best. Best is also natural here; it is not offered as a wrong option.', 'Early changes y to i: early → earlier → earliest. Earliest is also natural here; it is not offered as a wrong option.'],
};
// SHA-256 of complete files in the pre-Learn-refresh commit acc4558. These
// compare exact bytes, not a projection that could hide bank/schema changes.
const frozen = {
  'site/data/adjectives-questions.json': '20c44ca85035975414a830ca3bd626977aad3c606ca1c0e71afba77d0739cd55',
  'site/data/adverbs-questions.json': '00c937d39a5b978463e01f30601f0dee4ec3d0ec378ffb0fd911a3a93ab94904',
  'site/js/core.js': 'f23a90035658e97235ab1fdff95e2b3985bf8263c6383f94b16271ce54a83919',
  'site/js/storage.js': 'f616beaa179590f0f36418a4e08bd8b9ff801b77a46e9b0b9c40b2f992784e77',
  'site/js/question-context.js': '99b28a8f00c96fcdc6730e53a02d749f49452796e9377427782fc02383fda2b3',
};
for (const [path, hash] of Object.entries(frozen)) test(`Learn-only refresh preserves exact acc4558 bytes: ${path}`, () => {
  assert.equal(createHash('sha256').update(read(path)).digest('hex'), hash);
});
for (const id of modules) {
  test(`${id}: concise plain-text Learn schema and six core sections`, () => {
    const data = learn(id);
    validateLearn(data, id);
    assert.equal(data.sections.filter(s => !s.extra).length, 6);
    assert.ok(data.sections.some(s => s.extra), 'optional textbook reading is present');
    assert.ok(words(data.intro) <= 35);
    assert.match(data.scopeNote, /(?:experiment|word.block|question)/i);
    assert.match(data.sourceNote, /(?:chapter\s*6|pages?\s*32\s*[–-]\s*35)/i);
    assert.match(data.sourceNote, /teacher/i);
  });
  test(`${id}: exactly three original mini-check stems/options/answers and original sources`, () => {
    const data = learn(id);
    assert.deepEqual(data.miniCheck.map(q => [q.sentence, q.options, q.answer]), baseline[id]);
    assert.deepEqual(data.sources, sources[id]);
    const currentWords = data.miniCheck.reduce((sum, check) => sum + words(check.explanation), 0);
    const previousWords = oldExplanations[id].reduce((sum, explanation) => sum + words(explanation), 0);
    assert.ok(currentWords < previousWords, `mini-check explanations shortened as a set: ${currentWords} words versus ${previousWords}`);
  });
  test(`${id}: explicit final-y recipes and genuine far alternatives remain core teaching`, () => {
    const core = learn(id).sections.filter(s => !s.extra);
    const text = JSON.stringify(core);
    const recipes = core.flatMap(s => s.recipes ?? []).join('\n');
    assert.match(recipes, /×\s*y/u);
    assert.match(recipes, /×\s*y\s*\+\s*-i(?:er|est)/u);
    for (const form of ['farther', 'further', 'farthest', 'furthest']) assert.ok(text.includes(form), form);
    assert.match(text, /(?:both|either|or)/i);
    assert.ok(!/direct accepted|automatically drop|automatically remove/i.test(text));
  });
  test(`${id}: textbook extras cover lower/equal/stronger comparisons and intended reference`, () => {
    const extra = JSON.stringify(learn(id).sections.filter(s => s.extra));
    for (const pattern of [/\bless\b/i, /\bleast\b/i, /as.{0,45}as/i, /\bnot\b/i, /\bmuch\b/i, /\b(?:slightly|a little|a bit)\b/i]) assert.match(extra, pattern);
    assert.match(extra, /(?:group|among|class|of three|one of)/i);
    assert.match(extra, /(?:reference|same|matching|mine|sister's|did|I do|I run)/i);
  });
  test(`${id}: structured form rows, recipes and labelled mistakes are present`, () => {
    const data = learn(id);
    assert.ok(data.sections.some(s => s.forms?.length));
    assert.ok(data.sections.some(s => s.recipes?.length));
    assert.ok(data.sections.some(s => s.mistakes?.length));
    assert.ok(data.sections.filter(s => !s.extra).some(s => /long|more|most|two forms/i.test(JSON.stringify(s))));
  });
}
test('adjective core describes people/things and uses literal consonant doubling', () => {
  const data = learn('adjectives');
  assert.match(data.intro + JSON.stringify(data.sections.filter(s => !s.extra)), /(?:people|person|thing|noun)/i);
  assert.match(data.sections.flatMap(s => s.recipes ?? []).join(' '), /big\s*\+\s*g\s*\+\s*-(?:er|est)/i);
  const text = JSON.stringify(data.sections);
  assert.match(text, /\bgood\b/i);
});
test('adjective core teaches every amount/number irregular still tested in Lab 01', () => {
  const core = learn('adjectives').sections.filter(section => !section.extra);
  const forms = core.flatMap(section => section.forms ?? []);
  for (const [base, comparative, superlative] of [['little', 'less', 'the least'], ['much', 'more', 'the most'], ['many', 'more', 'the most']]) {
    const row = forms.find(form => form.label.startsWith(base + ':'));
    assert.ok(row, `${base} is core teaching, not just an extra-reading pattern`);
    assert.equal(row.comparative, comparative);
    assert.equal(row.superlative, superlative);
  }
  const note = core.map(section => section.note ?? '').join(' ');
  assert.match(note, /amounts/i);
  assert.match(note, /numbers/i);
  assert.match(note, /noun.*sentence/i);
});
test('adverb core describes actions, distinguishes -ly forms and accepts optional the', () => {
  const data = learn('adverbs');
  const text = data.intro + JSON.stringify(data.sections.filter(s => !s.extra));
  assert.match(text, /action/i);
  assert.match(text, /(?:-ly|clearly|carefully)/i);
  assert.match(text, /(?:optional|with or without|can omit|may omit|can leave out)/i);
  assert.match(text, /\bwell\b/i);
  assert.match(text, /\bbadly\b/i);
  assert.match(text, /good[^.]{0,60}(?:people|things|noun)/i);
  assert.match(text, /well[^.]{0,70}(?:how|action|does)/i);
});

const invalid = (name, mutate, pattern) => test(`Learn validator rejects ${name}`, () => {
  const data = learn('adjectives');
  mutate(data);
  assert.throws(() => validateLearn(data, 'adjectives'), pattern);
});
invalid('mismatched module', d => { d.module = 'wrong'; }, /identity/);
invalid('HTML title', d => { d.sections[0].title = '<b>Rule</b>'; }, /plain text/);
invalid('non-string text', d => { d.sections[0].text = 7; }, /plain-text/);
invalid('non-boolean extra', d => { d.sections[0].extra = 'true'; }, /boolean/);
invalid('missing form field', d => { d.sections[0].forms = [{ label: 'big', comparative: 'bigger' }]; }, /superlative/);
invalid('duplicate form labels', d => { d.sections[0].forms = Array(2).fill({ label: 'big', comparative: 'bigger', superlative: 'biggest' }); }, /unique form/);
invalid('object recipe', d => { d.sections[0].recipes = [{ text: 'big' }]; }, /plain-text/);
invalid('incomplete mistake pair', d => { d.sections[0].mistakes = [{ wrong: 'more big' }]; }, /right/);
invalid('implicit final-y teaching recipe', d => { d.sections[0].recipes = ['noisy + -iest → noisiest']; }, /explicitly include ×y/);
invalid('empty example', d => { d.sections[0].examples = ['']; }, /nonempty/);
invalid('overlong intro', d => { d.intro = Array(36).fill('word').join(' '); }, /maximum 35/);
invalid('overlong core paragraph', d => { d.sections[0].text = Array(41).fill('word').join(' '); }, /maximum 40/);
invalid('overlong extra paragraph', d => { d.sections.find(s => s.extra).text = Array(51).fill('word').join(' '); }, /maximum 50/);
invalid('duplicate options', d => { d.miniCheck[0].options[1] = d.miniCheck[0].options[0]; }, /unique options/);
invalid('prefilled than', d => { d.miniCheck[0].sentence = 'Our hall is _____ than our room.'; }, /supply than/);
invalid('prefilled superlative the', d => { d.miniCheck[1].sentence = 'Our red bag is the _____.'; }, /supply the/);
invalid('four mini-checks', d => { d.miniCheck.push(structuredClone(d.miniCheck[0])); }, /three mini/);
test('Learn validator rejects a valid bare adverb form as a distractor', () => {
  const d = learn('adverbs');
  d.miniCheck[1].options[1] = 'best';
  assert.throws(() => validateLearn(d, 'adverbs'), /optional-the/);
});
test('Learn-only authoring parity calls generator functions without writing banks', () => {
  const root = new URL('../', import.meta.url);
  const output = execFileSync('python3', ['-c', "import importlib.util,json; s=importlib.util.spec_from_file_location('learn_author','scripts/author-content.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(json.dumps(m.learn_files(),ensure_ascii=False))"], { cwd: root, encoding: 'utf8', maxBuffer: 1024 * 1024 });
  assert.deepEqual(JSON.parse(output), modules.map(learn));
});
