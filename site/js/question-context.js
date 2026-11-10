export const QUESTION_SCHEMA = 2;
export const COMPARISON_INGREDIENTS = ['more', 'most', 'than', 'the', '-er', '-est', '-r', '-st', '-ier', '-iest'];
export const IRREGULAR_COMPARISON_FORMS = Object.freeze({
  good: Object.freeze(['better', 'best']),
  bad: Object.freeze(['worse', 'worst']),
  well: Object.freeze(['better', 'best']),
  badly: Object.freeze(['worse', 'worst']),
  far: Object.freeze(['farther', 'further', 'farthest', 'furthest']),
  little: Object.freeze(['less', 'least']),
  much: Object.freeze(['more', 'most']),
  many: Object.freeze(['more', 'most'])
});
const STRUCTURE_WORDS = ['more', 'most', 'than', 'the'];
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const isText = value => typeof value === 'string' && value.trim().length > 0;
const irregularForms = base => Object.hasOwn(IRREGULAR_COMPARISON_FORMS, base) ? IRREGULAR_COMPARISON_FORMS[base] : [];

// Derive comparison headwords independently of accepted answers and word tiles.
// Only real comparison endings can extend the base; arbitrary transform values
// cannot introduce a noun (or another lexical word) into this allow-list.
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
  return words;
}

function isNounFreeAnswer(question, answer, headwords) {
  const words = answer.trim().toLowerCase().split(/\s+/);
  if (question.degree === 'comparative' && words.at(-1) === 'than') words.pop();
  if (words[0] === 'the') words.shift();
  // A longer form contains exactly one lexical headword: the given base.
  if (words.length === 2 && ['more', 'most'].includes(words[0])) return words[1] === question.base.toLowerCase();
  // Irregular quantity forms such as "the most" and "the least" are
  // themselves headwords, so they need no additional adjective or noun.
  return words.length === 1 && headwords.has(words[0]);
}

export function questionContextIssues(question) {
  const issues = [];
  // Saved snapshots are untrusted JSON. Reject malformed nested values before
  // examining them so archiveOutdatedWork can safely exclude corrupt questions.
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
  for (const ingredient of COMPARISON_INGREDIENTS) {
    if (!question.blocks.some(block => block.label === ingredient && block.kind === (ingredient.startsWith('-') ? 'suffix' : 'word'))) issues.push(`The complete tray is missing ${ingredient}`);
  }
  if (!question.blocks.some(block => block.label === 'Remove y' && block.kind === 'operation' && block.operation === 'remove-final-y')) issues.push('Every tray must include the Remove y operation');
  const allowedWords = new Set([question.base.toLowerCase(), ...STRUCTURE_WORDS, ...irregularForms(question.base.toLowerCase())]);
  for (const block of question.blocks) {
    if (block.kind === 'word' && !allowedWords.has(block.label.toLowerCase())) issues.push(`Noun-free comparison tray has an unrelated word ingredient: ${block.label}`);
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
    for (let i = 1; i < sequence.length; i++) {
      const ending = blocks.get(sequence[i]);
      let word = blocks.get(sequence[i - 1]);
      if (ending?.kind === 'operation' && (ending.operation !== 'remove-final-y' || word?.kind !== 'word' || !/y$/i.test(word.label))) issues.push('Accepted Remove y sequence must follow a y-ending word');
      if (word?.kind === 'operation') word = blocks.get(sequence[i - 2]);
      if (ending?.kind !== 'suffix' || !word) continue;
      if (['-r', '-st'].includes(ending.label) && !word.label.endsWith('e')) issues.push(`The ${ending.label} ending requires a base ending in e, not ${word.label}`);
      if (['-ier', '-iest'].includes(ending.label) && !word.label.endsWith('y')) issues.push(`The ${ending.label} ending requires a base ending in y, not ${word.label}`);
    }
  }
  const accepted = new Set(question.answers.map(answer => String(answer).trim().toLowerCase()));
  for (const entry of question.feedback ?? []) {
    for (const answer of entry.answers ?? []) if (accepted.has(String(answer).trim().toLowerCase())) issues.push(`Wrong-answer feedback targets an accepted answer: ${answer}`);
  }
  return issues;
}
