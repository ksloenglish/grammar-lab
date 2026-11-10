import { adaptiveBlocks } from './comparison-blocks.js';

export function blockDisplayLabel(block) {
  if (block.operation === 'remove-final-y') return 'y';
  if (block.operation === 'double-final-consonant') return block.consonant ?? block.label;
  return block.label;
}

export function blockAccessibleLabel(block) {
  if (block.operation === 'remove-final-y') return 'Remove the final y from the previous word';
  if (block.operation === 'double-final-consonant') return `Double the final ${block.consonant ?? block.label} of the base word`;
  return `Add ${block.label} to the end of your answer`;
}

export function renderIngredients(question, order, selected, building, escape) {
  // Keep the public signature, but saved/random tray order cannot move the base
  // away from first place or change the adaptive pedagogical order.
  const blocks = adaptiveBlocks(question, selected);
  if (!blocks.length) return '<p class="tray-placeholder">All blocks are in your answer.</p>';
  return `<div class="ingredient-grid adaptive-ingredients">${blocks.map(block => {
    const operationClass = block.operation === 'remove-final-y' ? ' remove-y' : block.operation === 'double-final-consonant' ? ' double-consonant' : '';
    return `<button type="button" class="reagent ${escape(block.kind)}${operationClass}" draggable="false" data-action="add-block" data-block="${escape(block.id)}" ${building ? '' : 'disabled'} aria-label="${escape(blockAccessibleLabel(block))}"><span class="block-label">${escape(blockDisplayLabel(block))}</span></button>`;
  }).join('')}</div>`;
}
