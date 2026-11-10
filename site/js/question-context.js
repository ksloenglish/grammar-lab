import { doublingConsonant, isControlledDoublingBlock, IRREGULAR_COMPARISON_FORMS } from './comparison-blocks.js';
export { IRREGULAR_COMPARISON_FORMS } from './comparison-blocks.js';

export const QUESTION_SCHEMA = 2;
export const COMPARISON_INGREDIENTS = ['more', 'most', 'than', 'the', '-er', '-est', '-r', '-st', '-ier', '-iest'];
const STRUCTURE_WORDS = ['more', 'most', 'than', 'the'];
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const isText = value => typeof value === 'string' && value.trim().length > 0;
const irregularForms = base => Object.hasOwn(IRREGULAR_COMPARISON_FORMS, base) ? IRREGULAR_COMPARISON_FORMS[base] : [];

// Only real comparison endings extend this allow-list. Arbitrary transform
// values must never introduce a noun or another lexical word into it.
function comparisonHeadwords(question) {
  const base = question.base.toLowerCase();
  const words = new Set([base, ...irregularForms(base)]);
  for (const block of question.blocks.filter(block => block.kind === 'suffix')) {
    const ending = block.label.toLowerCase();
    if (['-er', '-est'].includes(ending)) words.add(base + ending.slice(1));
    else if (['-r', '-st'].includes(ending) && base.endsWith('e')) words.add(base + ending.slice(1));
    else if (['-ier', '-iest'].includes(ending) && base.endsWith('y')) words.add(base.slice(0, -1) + ending.slice(1));
    else if (/^-[b-df-hj-np-tv-z](?:er|est)$/.test(ending) && ending[1] === base.at(-1)) words.add(base + ending.slice(1));
  }
  const consonant = doublingConsonant(question);
  if (consonant && question.blocks.some(block => isControlledDoublingBlock(question, block))) {
    words.add(base + consonant.toLowerCase() + (question.degree === 'comparative' ? 'er' : 'est'));
  }
  return words;
}

function isNounFreeAnswer(question, answer, headwords) {
  const words = answer.trim().toLowerCase().split(/\s+/);
  if (question.degree === 'comparative' && words.at(-1) === 'than') words.pop();
  if (words[0] === 'the') words.shift();
  if (words.length === 2 && ['more', 'most'].includes(words[0])) return words[1] === question.base.toLowerCase();
  return words.length === 1 && headwords.has(words[0]);
}

function legitimateTransform(question, block, from, to) {
  const base = question.base;
  const ending = block.label;
  if (block.kind !== 'suffix') return false;
  if (['-ier', '-iest'].includes(ending) && /y$/i.test(base)) {
    return from === base.slice(0, -1) && to === base.slice(0, -1) + ending.slice(1);
  }
  if (from !== base) return false;
  if (['-er', '-est'].includes(ending)) return to === base + ending.slice(1);
  if (['-r', '-st'].includes(ending) && /e$/i.test(base)) return to === base + ending.slice(1);
  return /^-[bcdfghjklmnpqrstvz](?:er|est)$/.test(ending) && ending[1] === base.at(-1)
    && to === base + ending.slice(1);
}

export function questionContextIssues(question) {
  const issues = [];
  // Saved snapshots are untrusted JSON: guard every nested value first.
  if (!isObject(question) || typeof question.sentence !== 'string' || !isText(question.base) || !/^[a-z]+$/i.test(question.base)
    || !['comparative', 'superlative'].includes(question.degree) || (question.id !== undefined && typeof question.id !== 'string')
    || !Array.isArray(question.answers) || !question.answers.length || !Array.isArray(question.blocks) || !question.blocks.length
    || !question.blocks.every(block => isObject(block) && isText(block.id) && isText(block.label) && ['word', 'suffix', 'operation'].includes(block.kind)
      && (block.transforms === undefined || (isObject(block.transforms) && Object.values(block.transforms).every(isText))))
    || (question.correctSequences !== undefined && (!Array.isArray(question.correctSequences) || !question.correctSequences.every(sequence => Array.isArray(sequence) && sequence.every(isText))))
    || (question.feedback !== undefined && (!Array.isArray(question.feedback) || !question.feedback.every(entry => isObject(entry) && (entry.answers === undefined || (Array.isArray(entry.answers) && entry.answers.every(isText))))))) return ['Invalid question structure'];
  const [before, after, extra] = question.sentence.split('_____');
  if (after === undefined || extra !== undefined) issues.push('The sentence must have exactly one gap');
  if (/\bthan\b/i.test(question.sentence)) issues.push('The question stem must not supply than');
  if (/\b(?:more|most)\b/i.test(question.sentence)) issues.push('The question stem must not supply more or most');
  if (question.degree === 'superlative' && /\bthe\b/i.test(question.sentence)) issues.push('The superlative stem must not supply the');
  if (question.degree === 'superlative' && !question.blocks.some(block => block.label === 'the' && block.kind === 'word')) issues.push('Every superlative tray must include the');
  if (!question.blocks.some(block => block.label === '-er' && block.kind === 'suffix')) issues.push('Every tray must include a literal -er suffix');
  if (!question.blocks.some(block => block.label === question.base && block.kind === 'word')) issues.push('The tray must include the base word');
  // Full authored cores are preserved, even though runtime visible choices are
  // degree-specific. Do not make doubling compulsory in legacy bank snapshots.
  for (const ingredient of COMPARISON_INGREDIENTS) {
    if (!question.blocks.some(block => block.label === ingredient && block.kind === (ingredient.startsWith('-') ? 'suffix' : 'word'))) issues.push(`The complete tray is missing ${ingredient}`);
  }
  if (!question.blocks.some(block => block.label === 'Remove y' && block.kind === 'operation' && block.operation === 'remove-final-y')) issues.push('Every tray must include the Remove y operation');
  if (new Set(question.blocks.map(block => block.id)).size !== question.blocks.length) issues.push('Ingredient IDs must be unique');
  const allowedWords = new Set([question.base.toLowerCase(), ...STRUCTURE_WORDS, ...irregularForms(question.base.toLowerCase())]);
  for (const block of question.blocks) {
    if (block.kind === 'word' && !allowedWords.has(block.label.toLowerCase())) issues.push(`Noun-free comparison tray has an unrelated word ingredient: ${block.label}`);
    if (block.operation === 'double-final-consonant' || block.id === 'double-final-consonant') {
      if (!isControlledDoublingBlock(question, block)) issues.push('Double final consonant must match the base and an accepted regular doubling form');
    } else if (block.kind === 'operation') {
      if (block.operation !== 'remove-final-y' || block.label !== 'Remove y' || block.transforms !== undefined) {
        issues.push('Unknown or malformed spelling operation');
      }
    } else if (block.operation !== undefined) {
      issues.push('Only an operation ingredient may define a spelling operation');
    }
    if (block.kind === 'suffix' && !COMPARISON_INGREDIENTS.filter(label => label.startsWith('-')).includes(block.label)
      && !(/^-[bcdfghjklmnpqrstvz](?:er|est)$/.test(block.label) && block.label[1] === question.base.at(-1))) {
      issues.push(`Unsupported comparison suffix: ${block.label}`);
    }
    if (block.transforms !== undefined && (block.kind !== 'suffix' || Object.entries(block.transforms).some(([from, to]) => !legitimateTransform(question, block, from, to)))) {
      issues.push(`Ingredient has an arbitrary spelling transform: ${block.label}`);
    }
  }
  const headwords = comparisonHeadwords(question);
  for (const answer of question.answers) {
    if (typeof answer !== 'string') { issues.push('Answer must be text'); continue; }
    if (!isNounFreeAnswer(question, answer, headwords)) issues.push(`Comparison gap answer must be noun-free and contain only one relevant headword: ${answer}`);
    const thanCount = (answer.match(/\bthan\b/gi) ?? []).length;
    if (question.degree === 'comparative' && (thanCount !== 1 || !/\bthan\s*$/i.test(answer))) issues.push(`Comparative gap answer must end in exactly one than: ${answer}`);
    if (question.degree === 'superlative' && thanCount) issues.push(`Superlative gap answer must not include than: ${answer}`);
    if ((question.requiresArticle || (question.degree === 'superlative' && question.id?.startsWith('adj-'))) && !/^the\s+/i.test(answer)) issues.push(`Adjective superlative answer must include the: ${answer}`);
    if (/\bthe\s*$/i.test(before) && /^the\b/i.test(answer.trim())) issues.push(`The answer repeats the supplied article: ${answer}`);
    const complete = question.sentence.replace('_____', answer);
    if (/\b(?:than\s+than|the\s+the)\b/i.test(complete)) issues.push(`Duplicated word in completed sentence: ${complete}`);
  }
  const blocks = new Map(question.blocks.map(block => [block.id, block]));
  for (const sequence of question.correctSequences ?? []) {
    if (sequence.some(id => !blocks.has(id))) issues.push('Accepted sequence references a missing ingredient');
    if (new Set(sequence).size !== sequence.length) issues.push('Accepted sequence cannot repeat an ingredient');
    for (let i = 0; i < sequence.length; i++) {
      const ending = blocks.get(sequence[i]);
      const previous = blocks.get(sequence[i - 1]);
      let word = previous;
      if (ending?.kind === 'operation') {
        if (ending.operation === 'remove-final-y') {
          if (previous?.kind !== 'word' || !/y$/i.test(previous.label)) issues.push('Accepted Remove y sequence must follow a y-ending word');
        } else if (ending.operation === 'double-final-consonant') {
          if (!isControlledDoublingBlock(question, ending) || previous?.kind !== 'word' || previous.label !== question.base) {
            issues.push('Accepted doubling sequence must immediately follow the unmodified base word');
          }
          const suffix = blocks.get(sequence[i + 1]);
          if (suffix?.kind !== 'suffix' || !['-er', '-est'].includes(suffix.label)) issues.push('Accepted doubling operation must be followed by -er or -est');
        } else issues.push('Accepted sequence contains an unknown spelling operation');
      }
      if (word?.kind === 'operation') word = blocks.get(sequence[i - 2]);
      if (ending?.kind !== 'suffix') continue;
      if (word?.kind !== 'word') { issues.push('Accepted suffix must follow a word or its controlled spelling operation'); continue; }
      if (previous?.operation === 'double-final-consonant' && !['-er', '-est'].includes(ending.label)) issues.push('A doubled base takes -er or -est, not a combined doubling ending');
      if (['-r', '-st'].includes(ending.label) && !word.label.endsWith('e')) issues.push(`The ${ending.label} ending requires a base ending in e, not ${word.label}`);
      if (['-ier', '-iest'].includes(ending.label) && !word.label.endsWith('y')) issues.push(`The ${ending.label} ending requires a base ending in y, not ${word.label}`);
      if (['-ier', '-iest'].includes(ending.label) && previous?.operation !== 'remove-final-y') issues.push(`Accepted ${ending.label} sequence must immediately follow Remove y`);
    }
  }
  const accepted = new Set(question.answers.map(answer => String(answer).trim().toLowerCase()));
  for (const entry of question.feedback ?? []) {
    for (const answer of entry.answers ?? []) if (accepted.has(String(answer).trim().toLowerCase())) issues.push(`Wrong-answer feedback targets an accepted answer: ${answer}`);
  }
  return issues;
}
