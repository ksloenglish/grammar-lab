const structureWords = new Set(['more', 'most', 'than', 'the']);

export function ingredientGroups(question, order, selected = []) {
  const used = new Set(selected);
  const byId = new Map(question.blocks.map(block => [block.id, block]));
  const groups = [
    { category: 'word', title: 'Words', blocks: [] },
    { category: 'structure', title: 'Other words', blocks: [] },
    { category: 'ending', title: 'Endings & changes', blocks: [] }
  ];
  for (const id of order) {
    if (used.has(id)) continue;
    const block = byId.get(id);
    if (!block) continue;
    const category = block.category ?? (['suffix', 'operation'].includes(block.kind) ? 'ending' : structureWords.has(block.label) ? 'structure' : 'word');
    (groups.find(group => group.category === category) ?? groups[0]).blocks.push(block);
  }
  return groups.filter(group => group.blocks.length);
}

export function renderIngredients(question, order, selected, building, escape) {
  const groups = ingredientGroups(question, order, selected);
  if (!groups.length) return '<p class="tray-placeholder">All blocks are in your answer.</p>';
  return groups.map(group => `<section class="tray-group"><h3 class="tray-group-title">${escape(group.title)}</h3><div class="ingredient-grid">${group.blocks.map(block => `<button class="reagent ${escape(block.kind)}" draggable="${building}" data-action="add-block" data-block="${escape(block.id)}" ${building ? '' : 'disabled'} aria-label="${block.operation === 'remove-final-y' ? 'Remove the final y from the previous word' : `Add ${escape(block.label)} to your answer`}"><span class="block-label">${escape(block.operation === 'remove-final-y' ? 'y' : block.label)}</span></button>`).join('')}</div></section>`).join('');
}
