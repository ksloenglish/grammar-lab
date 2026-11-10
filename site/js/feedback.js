import { adaptiveBlocks, doublingConsonant, isControlledDoublingBlock, prepareAdaptiveQuestion, joinComparisonSuffix, IRREGULAR_COMPARISON_FORMS } from './comparison-blocks.js';

// No scoring, DOM, storage or core dependency. Return plain text; the view escapes it.
const normalise = value => String(value ?? '').trim().replace(/\s+/g, ' ').toLowerCase();
const capitalise = value => value ? value[0].toUpperCase() + value.slice(1) : '';
const THAN_FUNCTION = 'Use than to introduce the other person, thing or action in the comparison.';
const result = (code, title, message, problemBlockIds = [], missingLabels = []) => ({
  code, title, message, problemBlockIds: [...new Set(problemBlockIds)], missingLabels: [...new Set(missingLabels)]
});
const accepted = (question, text) => (question.answers ?? []).some(answer => normalise(answer) === normalise(text));
const headOf = text => normalise(text).replace(/^the\s+/, '').replace(/\s+than$/, '');

function formation(question) {
  const base = normalise(question.base);
  const comparative = question.degree === 'comparative';
  const marker = comparative ? 'more' : 'most';
  const suffix = comparative ? '-er' : '-est';
  const heads = [...new Set((question.answers ?? []).map(headOf))];
  const irregular = (IRREGULAR_COMPARISON_FORMS[base] ?? []).filter(word => heads.includes(word));
  const analytic = heads.includes(`${marker} ${base}`);
  const regular = heads.filter(word => !word.includes(' ') && !irregular.includes(word));
  const doubled = doublingConsonant(question);
  const y = Boolean(base.endsWith('y') && regular.includes(base.slice(0, -1) + 'i' + suffix.slice(1)));
  const e = Boolean(base.endsWith('e') && regular.includes(base + suffix.slice(2)));
  const ending = y ? (comparative ? '-ier' : '-iest') : e ? (comparative ? '-r' : '-st') : suffix;
  const requiresArticle = question.degree === 'superlative' && (question.requiresArticle === true
    || (question.requiresArticle !== false && question.id?.startsWith('adj-')));
  return { base, comparative, marker, suffix, heads, irregular, analytic, regular, doubled, y, e, ending, requiresArticle };
}

function formationRule(info) {
  const { base, irregular, analytic, regular, marker, suffix, doubled, y, e, ending } = info;
  if (!base) return 'Use the comparison form made by the accepted ingredients.';
  let rule;
  if (irregular.length) rule = `${capitalise(base)} changes its form to ${irregular.join(' or ')}.`;
  else if (doubled) rule = `Double the final ${doubled}, then add ${suffix} to ${base}.`;
  else if (y) rule = `Remove the final y, then add ${ending} to ${base}.`;
  else if (e) rule = `The word already ends in e. Add ${ending} to ${base}.`;
  else if (regular.length) rule = `Add ${suffix} to ${base}.`;
  else rule = `Put ${marker} before ${base}. Do not add ${suffix}.`;
  if (analytic && (regular.length || irregular.length)) rule += ` ${capitalise(marker)} ${base} is also accepted here.`;
  return rule;
}

function mistakeRule(info) {
  // State a formation action, not a complete optional-article accepted phrase.
  return formationRule(info).replace(` ${capitalise(info.marker)} ${info.base} is also accepted here.`,
    ` You can also put ${info.marker} before ${info.base}.`);
}

export function correctExplanation(question) {
  const info = formation(question ?? {});
  const rule = formationRule(info);
  if (question?.degree === 'comparative') return `${rule} ${THAN_FUNCTION}`;
  if (question?.degree === 'superlative') return `${rule} ${info.requiresArticle
    ? 'Use the before the superlative.' : 'This adverb can be used with or without the.'}`;
  return rule;
}

// Mirror the ingredient fusion rules, without importing core (which consumes this API).
// Retaining provenance lets the UI highlight the actual fused part, not every tile.
function trace(question, ids) {
  const blocks = new Map((question.blocks ?? []).map(block => [block.id, block]));
  const parts = [];
  for (const id of ids) {
    const block = blocks.get(id);
    if (!block) { parts.push({ text: String(id), ids: [id], orphan: true }); continue; }
    const previous = parts.at(-1);
    const doubling = block.operation === 'double-final-consonant' || block.id === 'double-final-consonant';
    if (block.kind === 'operation' || doubling) {
      if (!doubling && block.operation === 'remove-final-y' && previous && !previous.orphan && /y$/i.test(previous.text)) {
        previous.text = previous.text.slice(0, -1);
        previous.ids.push(id);
      } else if (isControlledDoublingBlock(question, block) && previous && !previous.orphan
        && previous.text === question.base && previous.ids.length === 1 && blocks.get(previous.ids[0])?.kind === 'word') {
        previous.text += block.consonant;
        previous.ids.push(id);
      } else parts.push({ text: `[${block.label}]`, ids: [id], orphan: true });
    } else if (block.kind === 'suffix' && previous && !previous.orphan) {
      previous.text = joinComparisonSuffix(previous.text, block);
      previous.ids.push(id);
    } else parts.push({ text: block.label, ids: [id], orphan: block.kind === 'suffix' });
  }
  return parts;
}

// explain(question, answer) also supports old callers without IDs. Infer only
// genuine tile combinations; no guessed fake operation or new question fields.
function inferIds(question, answer) {
  const blocks = question.blocks ?? [];
  const words = blocks.filter(block => block.kind === 'word');
  const changes = blocks.filter(block => block.kind !== 'word');
  const inferred = [];
  for (const token of String(answer ?? '').match(/\[[^\]]+\]|\S+/g) ?? []) {
    const exact = blocks.find(block => normalise(block.label) === normalise(token)
      || (block.kind === 'operation' && normalise(`[${block.label}]`) === normalise(token)));
    if (exact) { inferred.push(exact.id); continue; }
    let found;
    for (const word of words) {
      if (!normalise(token).startsWith(normalise(word.label).replace(/y$/, ''))) continue;
      for (const first of changes) {
        const one = [word.id, first.id];
        if (normalise(trace(question, one).map(part => part.text).join(' ')) === normalise(token)) { found = one; break; }
        for (const second of changes) {
          const two = [...one, second.id];
          if (normalise(trace(question, two).map(part => part.text).join(' ')) === normalise(token)) { found = two; break; }
        }
        if (found) break;
      }
      if (found) break;
    }
    if (!found) return [];
    inferred.push(...found);
  }
  return inferred;
}

function editPath(selected, target) {
  const table = Array.from({ length: selected.length + 1 }, () => Array(target.length + 1).fill(0));
  for (let i = selected.length; i >= 0; i--) for (let j = target.length; j >= 0; j--) {
    if (i === selected.length) table[i][j] = target.length - j;
    else if (j === target.length) table[i][j] = selected.length - i;
    else table[i][j] = selected[i] === target[j] ? table[i + 1][j + 1]
      : 1 + Math.min(table[i + 1][j], table[i][j + 1], table[i + 1][j + 1]);
  }
  const edits = [];
  let i = 0, j = 0;
  while (i < selected.length || j < target.length) {
    if (i < selected.length && j < target.length && selected[i] === target[j]) { i++; j++; continue; }
    if (i < selected.length && table[i][j] === 1 + table[i + 1][j]) edits.push({ type: 'remove', id: selected[i++], at: j });
    else if (j < target.length && table[i][j] === 1 + table[i][j + 1]) edits.push({ type: 'add', id: target[j++], at: j - 1 });
    else { edits.push({ type: 'replace', id: selected[i++], with: target[j++], at: j - 1 }); }
  }
  return { distance: table[0][0], edits };
}

function recipeHint(question, answer, selected) {
  const lookup = new Map((question.blocks ?? []).map(block => [block.id, block]));
  const labelOf = id => lookup.get(id)?.label ?? String(id);
  const visible = question.base && question.degree ? new Set(adaptiveBlocks(question).map(block => block.id)) : new Set(lookup.keys());
  const recipes = (question.correctSequences ?? []).filter(sequence => sequence.every(id => lookup.has(id))
    && accepted(question, trace(question, sequence).map(part => part.text).join(' ')));
  if (recipes.length && selected.length) {
    const ranked = recipes.map((target, index) => {
      let prefix = 0;
      while (prefix < Math.min(target.length, selected.length) && target[prefix] === selected[prefix]) prefix++;
      return { target, index, prefix, visible: target.every(id => visible.has(id)), ...editPath(selected, target) };
    }).sort((a, b) => a.distance - b.distance || Number(b.visible) - Number(a.visible) || b.prefix - a.prefix
      || a.edits.filter(edit => edit.type !== 'remove').length - b.edits.filter(edit => edit.type !== 'remove').length || a.index - b.index);
    const { target, edits } = ranked[0];
    // The same blocks in a different order: name one block to return/re-add.
    if (selected.length === target.length && [...selected].sort().join('\0') === [...target].sort().join('\0')) {
      const index = selected.findIndex((id, i) => id !== target[i]);
      const id = selected[index];
      const position = target.indexOf(id);
      const neighbour = target[position - 1] ?? target[position + 1];
      return result('block-order', 'Block order', `Move '${labelOf(id)}' ${position ? 'after' : 'before'} '${labelOf(neighbour)}'. Return it to the tray, then add it in that order.`, [id]);
    }
    const extra = edits.find(edit => edit.type === 'remove' && !target.includes(edit.id)) ?? edits[0];
    if (extra?.type === 'remove') return result('extra-block', 'Extra block', `Remove the extra '${labelOf(extra.id)}' block.`, [extra.id]);
    if (extra?.type === 'replace') return result('wrong-block', 'Wrong block', `Replace '${labelOf(extra.id)}' with '${labelOf(extra.with)}'.`, [extra.id], [labelOf(extra.with)]);
    if (extra?.type === 'add') {
      const before = target[extra.at + 1], after = target[extra.at - 1];
      return result('missing-block', 'Missing block', `Add '${labelOf(extra.id)}'${after ? ` after '${labelOf(after)}'` : before ? ` before '${labelOf(before)}'` : ''}.`, [], [labelOf(extra.id)]);
    }
  }
  // Minimal synthetic questions and unknown raw text still get a concrete edit.
  const tokens = normalise(answer).split(' ').filter(Boolean);
  const targets = (question.answers ?? []).map(value => normalise(value).split(' ').filter(Boolean));
  const nearest = targets.map(target => ({ target, ...editPath(tokens, target) })).sort((a, b) => a.distance - b.distance)[0];
  const edit = nearest?.edits[0];
  if (edit?.type === 'remove') return result('extra-word', 'Extra word', `Remove the extra '${edit.id}'.`);
  if (edit?.type === 'replace') return result('wrong-word', 'Wrong word', `Replace '${edit.id}' with '${edit.with}'.`);
  if (edit?.type === 'add') return result('missing-word', 'Missing word', `Add '${edit.id}'${edit.at ? ` after '${nearest.target[edit.at - 1]}'` : ' at the start'}.`, [], [edit.id]);
  return result('unrecognised-block', 'Unrecognised block', `Return '${String(answer ?? '').trim() || 'the selected block'}' to the tray and select a word block for this gap.`, selected);
}

export function diagnoseAnswer(source, answer, ids = []) {
  const question = prepareAdaptiveQuestion(source ?? {}) ?? {};
  if (accepted(question, answer)) return result('correct', 'Correct', correctExplanation(question));
  const info = formation(question);
  const selected = Array.isArray(ids) && ids.length ? [...ids] : inferIds(question, answer);
  const lookup = new Map((question.blocks ?? []).map(block => [block.id, block]));
  const parts = trace(question, selected);
  const chosen = selected.map(id => lookup.get(id)).filter(Boolean);
  const selectedIds = label => chosen.filter(block => normalise(block.label) === label).map(block => block.id);
  const partIds = part => part?.ids ?? [];
  const wordParts = parts.filter(part => !part.orphan && part.ids.some(id => lookup.get(id)?.kind === 'word'
    && (!['more', 'most', 'the', 'than'].includes(normalise(lookup.get(id)?.label))
      || info.irregular.includes(normalise(lookup.get(id)?.label)))));
  const word = wordParts[0];
  const rawHead = headOf(answer);
  const text = normalise(word?.text ?? rawHead.replace(/^(?:more|most)\s+/, '').replace(/\s+(?:more|most|the|than).*$/, ''));
  const suffixes = chosen.filter(block => block.kind === 'suffix');
  const currentSuffixes = suffixes.filter(block => /(?:er|r)$/.test(block.label) === info.comparative);
  const currentMarkers = selectedIds(info.marker);
  const opposite = info.comparative ? 'most' : 'more';
  const hasMarker = currentMarkers.length || new RegExp(`\\b${info.marker}\\b`).test(normalise(answer));
  const issueWordIds = partIds(word);

  // Invalid operations stay visibly invalid and outrank downstream formation.
  for (const part of parts.filter(part => part.orphan)) {
    const block = lookup.get(part.ids[0]);
    if (block?.operation === 'remove-final-y') return result('invalid-y-operation', 'Y change in the wrong place',
      'Put Remove y straight after a word ending in y. You do not need it for other words.', part.ids);
    if (block?.operation === 'double-final-consonant' || block?.id === 'double-final-consonant') {
      const already = parts.some(item => !item.orphan && (item.ids.includes(part.ids[0])
        || (info.doubled && info.heads.includes(normalise(item.text)))));
      return result('invalid-doubling-operation', 'Extra letter in the wrong place', already
        ? `You have already doubled ${block.label}. Remove the extra letter block; it belongs straight after the base word only once.`
        : 'Put the extra letter straight after the base word, before -er or -est. Only double the final consonant when the word needs it.', part.ids);
    }
    if (block?.kind === 'suffix') return result('ending-position', 'Ending in the wrong place',
      `Put '${block.label}' straight after the word it changes, not at the start or after an invalid change.`, part.ids);
  }
  if (/\[Remove y\]/i.test(answer)) return result('invalid-y-operation', 'Y change in the wrong place',
    'Put Remove y straight after a word ending in y. You do not need it for other words.', selectedIds('remove y'));
  if (/\[[a-z]\]/i.test(answer)) return result('invalid-doubling-operation', 'Extra letter in the wrong place',
    'Put the extra letter straight after the base word, before -er or -est. Only double the final consonant when the word needs it.', chosen.filter(block => block.operation === 'double-final-consonant').map(block => block.id));
  for (const part of parts) {
    for (let i = 1; i < part.ids.length; i++) {
      const ending = lookup.get(part.ids[i]);
      const previous = lookup.get(part.ids[i - 1]);
      if (ending?.kind === 'suffix' && ['-ier', '-iest'].includes(ending.label)
        && previous?.kind === 'word' && /y$/i.test(previous.label)) {
        return result('missing-y-operation', 'Missing ×y',
          `Add ×y after ${previous.label} and before ${ending.label} to remove the final y.`, part.ids, ['×y']);
      }
    }
    const first = lookup.get(part.ids[0]);
    if (first?.kind === 'word' && ['more', 'most', 'the', 'than'].includes(normalise(first.label))
      && !info.irregular.includes(normalise(first.label))
      && part.ids.some(id => lookup.get(id)?.kind === 'suffix')) return result('ending-position', 'Ending on the wrong word',
        `Do not attach an ending to '${first.label}'. Put the ending straight after the base word.`, part.ids);
  }
  if (!info.base || !['comparative', 'superlative'].includes(question.degree)) return recipeHint(question, answer, selected);
  if (info.comparative && /^than\b/.test(normalise(answer)) && normalise(answer) !== 'than') return result('misplaced-than', 'Than in the wrong place',
    `Put than after the comparison word or phrase. ${THAN_FUNCTION}`, selectedIds('than'));
  if (info.base && !wordParts.length && selected.length && chosen.every(block => ['more', 'most', 'the', 'than'].includes(normalise(block.label))))
    return result('missing-base', 'Missing comparison word', `You have selected only structure words. Add a comparison form of ${info.base}.`, [], [info.irregular[0] ?? info.base]);

  const extraBase = wordParts.find(part => normalise(part.text).startsWith(info.base));
  if (hasMarker && info.irregular.includes(info.marker) && extraBase) return result('extra-base', 'Extra base word',
    `${capitalise(info.base)} changes its form to ${info.marker}. Keep that irregular block and remove the extra '${info.base}' block${suffixes.length ? ' with its ending' : ''}.`, partIds(extraBase));

  // Several lexical parts need a whole-recipe diagnosis. Looking only at the
  // first base would invent a missing marker when a valid form follows it,
  // for example badly + worse + than needs badly removed, not more added.
  if (wordParts.length > 1) return recipeHint(question, answer, selected);

  if (info.doubled && text === info.base + info.doubled) return result('missing-ending', 'Missing ending',
    `'${text}' is unfinished. You have doubled ${info.doubled}; add ${info.suffix} to finish the ${question.degree}.`, issueWordIds, [info.suffix]);
  if (info.y && text === info.base.slice(0, -1)) return result('missing-ending', 'Missing ending',
    `'${text}' is unfinished. You have removed y; add ${info.ending} to finish the ${question.degree}.`, issueWordIds, [info.ending]);

  const regularForm = info.regular.includes(text);
  if (hasMarker && regularForm) return result('double-formation', 'Two comparison forms',
    `'${text}' already has a ${question.degree} ending. Remove ${info.marker}; do not use both forms together.`, [...currentMarkers, ...issueWordIds]);
  const completePrefix = [...info.heads].sort((a, b) => b.length - a.length).find(head => !head.includes(' ') && text.startsWith(head) && text !== head);
  if (completePrefix) return result('extra-ending', 'Extra ending',
    `'${completePrefix}' is already complete. Remove the extra ending attached after it.`, issueWordIds);
  const otherIrregular = (IRREGULAR_COMPARISON_FORMS[info.base] ?? []).filter(form => !info.irregular.includes(form));
  const wrongMarker = selectedIds(opposite);
  const wrongEnding = suffixes.find(block => !currentSuffixes.includes(block));
  if (wrongMarker.length || wrongEnding || otherIrregular.includes(text)
    || new RegExp(`\\b${opposite}\\b`).test(normalise(answer))) {
    let action;
    if (wrongMarker.length || new RegExp(`\\b${opposite}\\b`).test(normalise(answer))) {
      if (regularForm || info.irregular.includes(text)) action = `Remove ${opposite}; the comparison word already has the required degree.`;
      else if (info.analytic) action = `Replace ${opposite} with ${info.marker}.`;
      else if (info.irregular.length) action = `Remove ${opposite}. ${mistakeRule(info)}${wrongEnding ? ' Remove the added ending.' : ''}`;
      else action = `Remove ${opposite}. ${wrongEnding ? `Change '${wrongEnding.label}' to ${info.ending}.` : mistakeRule(info)}`;
    } else if (wrongEnding) action = info.analytic && !info.regular.length
      ? `Remove '${wrongEnding.label}'. Put ${info.marker} before ${info.base}; keep the base unchanged.`
      : info.irregular.length ? `Remove '${wrongEnding.label}'. ${mistakeRule(info)}` : `Change '${wrongEnding.label}' to ${info.ending}.`;
    else action = `Choose the ${question.degree} form of ${info.base}.`;
    return result('wrong-degree', 'Wrong comparison degree',
      `This gap needs a ${question.degree}, not a ${info.comparative ? 'superlative' : 'comparative'}. ${action}`,
      wrongMarker.length ? wrongMarker : issueWordIds.length ? issueWordIds : wrongEnding ? [wrongEnding.id] : []);
  }

  if (info.irregular.length && (text === info.base || text.startsWith(info.base)) && !info.irregular.includes(text) && !info.analytic)
    return result('irregular-formation', 'Irregular form', `${mistakeRule(info)}${suffixes.length ? ' Remove the added ending.' : ''}${hasMarker ? ` Remove ${info.marker}; it does not go before ${info.base}.` : ''}`,
      [...issueWordIds, ...currentMarkers]);
  if (info.irregular.includes(text) && (suffixes.length || hasMarker)
    && !(info.irregular.includes(info.marker) && text === info.marker && !suffixes.length))
    return result('double-formation', 'Two comparison forms', `This is already an irregular ${question.degree} form. Remove ${hasMarker ? info.marker : 'the added ending'}.`, [...currentMarkers, ...issueWordIds]);
  if (hasMarker && !info.analytic && text === info.base) return result('unnecessary-formation-word', 'Unnecessary comparison word',
    `Remove ${info.marker}. ${mistakeRule(info)}`, [...currentMarkers, ...issueWordIds]);
  if (info.analytic && !info.regular.length && !info.irregular.includes(text) && text && text !== info.base) return result('wrong-formation', 'Unnecessary ending or change',
    `Keep ${info.base} unchanged after ${info.marker}. Remove the ending or spelling change${hasMarker ? '.' : `, then put ${info.marker} before ${info.base}.`}`, issueWordIds.length ? issueWordIds : suffixes.map(block => block.id));

  if (info.y && text.startsWith(info.base) && text !== info.base) return result('y-spelling', 'Final y needs changing',
    `Change the final y to i before adding ${info.suffix}. Use ${info.ending}, not ${suffixes[0]?.label ?? info.suffix}, with the y-ending base.`, issueWordIds, [info.ending]);
  if (info.doubled && text === info.base + info.suffix.slice(1)) return result('missing-doubling', 'Missing doubled letter',
    `'${text}' has only one ${info.doubled}. Double ${info.doubled} before ${info.suffix}.`, issueWordIds, [info.doubled]);
  const appliedDouble = word?.ids.some(id => lookup.get(id)?.operation === 'double-final-consonant');
  if (info.doubled && appliedDouble && !regularForm && suffixes.length) {
    const combined = suffixes.find(block => block.label === '-' + info.doubled + info.suffix.slice(1));
    return result(combined ? 'extra-doubling' : 'wrong-ending', combined ? 'Extra doubled letter' : 'Wrong ending',
      `You have already doubled ${info.doubled}. Replace '${combined?.label ?? suffixes[0].label}' with ${info.suffix}; do not double the letter again.`, issueWordIds, [info.suffix]);
  }
  const removedY = word?.ids.some(id => lookup.get(id)?.operation === 'remove-final-y');
  if (info.y && removedY && !regularForm && suffixes.length) return result('wrong-ending', 'Wrong ending',
    `You have already removed y. Use ${info.ending} after '${info.base.slice(0, -1)}', not '${suffixes[0].label}'.`, issueWordIds, [info.ending]);
  if (info.regular.length && text === info.base && !hasMarker) return result('missing-ending', 'Missing ending',
    `'${info.base}' is still the base word. ${mistakeRule(info)}`, issueWordIds, [info.ending]);
  if (info.analytic && text === info.base && !hasMarker) return result('missing-formation-word', `Missing ${info.marker}`,
    `Put ${info.marker} before ${info.base}; keep the base word unchanged.`, [], [info.marker]);
  if (info.regular.length && text && !regularForm && !info.irregular.includes(text) && !(info.analytic && hasMarker && text === info.base)) return result('wrong-ending', 'Wrong ending',
    `'${text}' does not have the right ending. ${mistakeRule(info)}`, issueWordIds.length ? issueWordIds : suffixes.map(block => block.id), [info.ending]);

  // Formation is complete: now diagnose structure/order, without changing it.
  const withoutStructure = normalise(answer).replace(/\b(?:the|than)\b/g, '').trim().replace(/\s+/g, ' ');
  const rearrangedAnalytic = normalise(answer).replace(/\b(?:the|than)\b/g, '').trim() === `${info.base} ${info.marker}`;
  if (rearrangedAnalytic && info.analytic) return result('misplaced-formation-word', `${capitalise(info.marker)} in the wrong place`,
    `Put ${info.marker} before ${info.base}, not after it.`, currentMarkers);
  if (!info.heads.includes(withoutStructure)) return recipeHint(question, answer, selected);
  const words = normalise(answer).split(' ');
  const thanCount = words.filter(word => word === 'than').length;
  const theCount = words.filter(word => word === 'the').length;
  if (info.comparative) {
    if (theCount) return result('extra-the', 'Unnecessary the', 'Remove the. This gap needs a comparative phrase, not a superlative adjective.', selectedIds('the'));
    if (!thanCount) return result('missing-than', 'Missing than', `Add than after ${withoutStructure}. ${THAN_FUNCTION}`, [], ['than']);
    if (thanCount > 1) return result('extra-than', 'Extra than', 'Use than only once. Remove the extra than block.', selectedIds('than').slice(1));
    if (words.at(-1) !== 'than') return result('misplaced-than', 'Than in the wrong place', `Put than after the complete comparison phrase. ${THAN_FUNCTION}`, selectedIds('than'));
  } else if (question.degree === 'superlative') {
    if (thanCount) return result('extra-than', 'Unnecessary than', 'Remove than. A superlative identifies the top person, thing or action in a group; it does not take than.', selectedIds('than'));
    if (theCount > 1) return result('extra-the', 'Extra the', 'Use the only once. Remove the extra the block.', selectedIds('the').slice(1));
    if (theCount && words[0] !== 'the') return result('misplaced-the', 'The in the wrong place', 'Put the before the whole superlative phrase, not after it.', selectedIds('the'));
    if (info.requiresArticle && !theCount) return result('missing-the', 'Missing the', 'Add the before the superlative adjective.', [], ['the']);
  }
  return recipeHint(question, answer, selected);
}
