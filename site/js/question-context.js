export const QUESTION_SCHEMA = 2;
export const COMPARISON_INGREDIENTS = ['more', 'most', 'than', 'the', '-er', '-est', '-r', '-st', '-ier', '-iest'];

export function questionContextIssues(question) {
  const issues = [];
  if (!question || typeof question.sentence !== 'string' || !Array.isArray(question.answers) || !Array.isArray(question.blocks)) return ['Invalid question structure'];
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
  for (const answer of question.answers) {
    if (typeof answer !== 'string') { issues.push('Answer must be text'); continue; }
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
