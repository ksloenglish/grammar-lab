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
