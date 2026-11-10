// Pure comparison projection: authored banks remain the compatibility source.
// This module deliberately does not import the assembly/scoring engine.
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
const normalise = value => String(value ?? '').trim().replace(/\s+/g, ' ').toLowerCase();
const DOUBLING_ID = 'double-final-consonant';

// A y-ending word keeps its y unless a separate operation already removed it.
// Ignore even legacy/malicious transforms for these literal suffix joins.
export function joinComparisonSuffix(text, block) {
  if (['-ier', '-iest'].includes(block.label) && /y$/i.test(text)) return text + block.label.slice(1);
  return block.transforms?.[text] ?? (text + block.label.replace(/^-/, ''));
}

export function normaliseExplicitYQuestion(question) {
  if (!question || !Array.isArray(question.blocks) || question.blocks.some(block => !block || typeof block !== 'object')) return question;
  const prepared = { ...question, blocks: question.blocks.map(block => ({ ...block,
    ...(block.transforms && typeof block.transforms === 'object' && !Array.isArray(block.transforms) ? { transforms: { ...block.transforms } } : {}) })) };
  if (Array.isArray(question.correctSequences)) prepared.correctSequences = question.correctSequences.map(sequence => Array.isArray(sequence) ? [...sequence] : sequence);
  if (typeof question.base !== 'string' || !/^[a-z]+y$/i.test(question.base)) return prepared;
  const sanctioned = new Set();
  for (const block of prepared.blocks) {
    if (block.kind !== 'suffix' || !['-ier', '-iest'].includes(block.label) || !block.transforms
      || Array.isArray(block.transforms) || typeof block.transforms !== 'object') continue;
    if (Object.hasOwn(block.transforms, question.base) && block.transforms[question.base] === question.base.slice(0, -1) + block.label.slice(1)) {
      delete block.transforms[question.base];
      if (!Object.keys(block.transforms).length) delete block.transforms;
      sanctioned.add(block.id);
    }
  }
  if (!sanctioned.size || !Array.isArray(prepared.correctSequences)
    || prepared.correctSequences.some(sequence => !Array.isArray(sequence))) return prepared;
  const lookup = new Map(prepared.blocks.map(block => [block.id, block]));
  const operation = prepared.blocks.find(block => block.kind === 'operation' && block.operation === 'remove-final-y'
    && block.label === 'Remove y' && block.transforms === undefined);
  if (!operation || new Set(lookup.keys()).size !== prepared.blocks.length) return prepared;
  prepared.correctSequences = prepared.correctSequences.filter(sequence => {
    if (sequence.some(id => !lookup.has(id)) || new Set(sequence).size !== sequence.length) return true;
    const index = sequence.findIndex((id, i) => sanctioned.has(id) && lookup.get(sequence[i - 1])?.kind === 'word'
      && lookup.get(sequence[i - 1]).label === question.base);
    if (index < 0) return true;
    const ending = lookup.get(sequence[index]);
    const labels = sequence.map(id => lookup.get(id).label);
    const head = question.base.slice(0, -1) + ending.label.slice(1);
    const expectedLabels = question.degree === 'comparative' ? [question.base, ending.label, 'than'] : labels[0] === 'the' ? ['the', question.base, ending.label] : [question.base, ending.label];
    const expectedAnswer = question.degree === 'comparative' ? head + ' than' : labels[0] === 'the' ? 'the ' + head : head;
    if (JSON.stringify(labels) !== JSON.stringify(expectedLabels) || !Array.isArray(question.answers)
      || !question.answers.some(answer => normalise(answer) === normalise(expectedAnswer))) return true;
    const explicit = [...sequence.slice(0, index), operation.id, ...sequence.slice(index)];
    // Only remove the generator's old duplicate when its explicit twin exists.
    return !prepared.correctSequences.some(recipe => JSON.stringify(recipe) === JSON.stringify(explicit));
  });
  return prepared;
}

// View-only canonical representation: never change the student's saved IDs or result.
export function checkedExplicitYRecipe(session) {
  if (session?.status !== 'correct' || !Array.isArray(session.assembly)) return null;
  const question = session.questions?.[session.index];
  if (!question || typeof question.base !== 'string' || !/y$/i.test(question.base)) return null;
  const lookup = new Map(question.blocks.map(block => [block.id, block]));
  for (const recipe of question.correctSequences ?? []) {
    const index = recipe.findIndex(id => lookup.get(id)?.operation === 'remove-final-y');
    if (index < 1 || lookup.get(recipe[index - 1])?.label !== question.base
      || !['-ier', '-iest'].includes(lookup.get(recipe[index + 1])?.label)) continue;
    if (JSON.stringify(recipe.filter((id, i) => i !== index)) === JSON.stringify(session.assembly)) return [...recipe];
  }
  return null;
}

const currentIrregularForms = (base, degree) => {
  const key = normalise(base);
  const forms = Object.hasOwn(IRREGULAR_COMPARISON_FORMS, key) ? IRREGULAR_COMPARISON_FORMS[key] : [];
  if (normalise(base) === 'far') return degree === 'comparative' ? forms.slice(0, 2) : forms.slice(2);
  return forms.length ? [forms[degree === 'comparative' ? 0 : 1]] : [];
};

// An accepted regular form, not a CVC guess, is the evidence for doubling.
// In particular warm, long, far, low and new must not gain doubling tiles.
export function doublingConsonant(question) {
  const base = normalise(question?.base);
  const consonant = base.at(-1);
  if (!/^[a-z]+$/.test(base) || !/^[bcdfghjklmnpqrstvz]$/.test(consonant ?? '')
    || !['comparative', 'superlative'].includes(question?.degree)) return null;
  const headword = base + consonant + (question.degree === 'comparative' ? 'er' : 'est');
  const expected = question.degree === 'comparative' ? [headword + ' than'] : [headword, 'the ' + headword];
  return Array.isArray(question.answers) && question.answers.some(answer => expected.includes(normalise(answer))) ? question.base.at(-1) : null;
}

export function isControlledDoublingBlock(question, block) {
  const consonant = doublingConsonant(question);
  return Boolean(consonant && block?.kind === 'operation' && block.operation === DOUBLING_ID
    && block.label === consonant && block.consonant === consonant && block.transforms === undefined
    && (block.category === undefined || block.category === 'ending'));
}

export function prepareAdaptiveQuestion(question) {
  // Do not repair corrupt snapshots; keep them rejectable by shared validation.
  if (!question || !Array.isArray(question.blocks) || question.blocks.some(block => !block || typeof block !== 'object')
    || (question.correctSequences !== undefined && (!Array.isArray(question.correctSequences) || question.correctSequences.some(sequence => !Array.isArray(sequence))))) return question;
  question = normaliseExplicitYQuestion(question);
  const prepared = { ...question, blocks: [...question.blocks] };
  const consonant = doublingConsonant(question);
  if (!consonant) {
    if (question.correctSequences) prepared.correctSequences = question.correctSequences.map(sequence => [...sequence]);
    return prepared;
  }
  // Never overwrite an authored ID or its definition. Validation rejects a
  // conflicting/malformed definition rather than repairing it silently.
  if (!prepared.blocks.some(block => block.id === DOUBLING_ID)) {
    prepared.blocks.push({ id: DOUBLING_ID, label: consonant, kind: 'operation', operation: DOUBLING_ID, consonant, category: 'ending' });
  }
  const find = (label, kind) => prepared.blocks.find(block => block.label === label && block.kind === kind);
  const base = find(question.base, 'word');
  const suffix = find(question.degree === 'comparative' ? '-er' : '-est', 'suffix');
  const operation = prepared.blocks.find(block => block.id === DOUBLING_ID);
  const than = find('than', 'word');
  const the = find('the', 'word');
  const canonical = [];
  if (base && suffix && isControlledDoublingBlock(question, operation)) {
    const word = [base.id, operation.id, suffix.id];
    const headword = normalise(question.base + consonant + suffix.label.slice(1));
    for (const answer of question.answers) {
      const text = normalise(answer);
      if (question.degree === 'comparative' && than && text === headword + ' than') canonical.push([...word, than.id]);
      if (question.degree === 'superlative' && the && text === 'the ' + headword) canonical.push([the.id, ...word]);
      if (question.degree === 'superlative' && text === headword) canonical.push([...word]);
    }
  }
  const seen = new Set();
  prepared.correctSequences = [...canonical, ...(question.correctSequences ?? [])].filter(sequence => {
    const key = JSON.stringify(sequence);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).map(sequence => [...sequence]);
  return prepared;
}

export function adaptiveBlocks(question, selected = []) {
  const prepared = prepareAdaptiveQuestion(question);
  const comparative = question.degree === 'comparative';
  const blocks = [];
  const add = (label, kind) => {
    const block = prepared.blocks.find(item => item.label === label && item.kind === kind);
    if (block && !blocks.some(item => item.id === block.id)) blocks.push(block);
  };
  add(question.base, 'word');
  for (const label of comparative ? ['more', 'than', '-er', '-r'] : ['most', 'the', '-est', '-st']) {
    add(label, label.startsWith('-') ? 'suffix' : 'word');
  }
  if (/y$/i.test(question.base)) {
    const operation = prepared.blocks.find(block => block.kind === 'operation' && block.operation === 'remove-final-y');
    if (operation) blocks.push(operation);
    add(comparative ? '-ier' : '-iest', 'suffix');
  }
  const operation = prepared.blocks.find(block => block.id === DOUBLING_ID);
  if (isControlledDoublingBlock(question, operation)) blocks.push(operation);
  for (const label of currentIrregularForms(question.base, question.degree)) add(label, 'word');
  const used = new Set(selected);
  return blocks.filter(block => !used.has(block.id));
}

export function upgradeAdaptiveSession(session) {
  if (!session || !Array.isArray(session.questions)) return session;
  const questions = session.questions.map(prepareAdaptiveQuestion);
  const current = questions[session.index];
  if (!current || !Array.isArray(current.blocks) || current.blocks.some(block => !block || typeof block.id !== 'string')
    || !Array.isArray(session.trayOrder)) return { ...session, questions };
  const trayOrder = [...session.trayOrder];
  const present = new Set(trayOrder);
  for (const block of current.blocks) {
    if (!present.has(block.id)) {
      trayOrder.push(block.id);
      present.add(block.id);
    }
  }
  return { ...session, questions, trayOrder };
}
