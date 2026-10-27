import test from 'node:test';
import assert from 'node:assert/strict';
import { beakerMeter, labScene, sparkParticles, reportConfetti } from '../site/js/effects.js';

test('score beakers use the actual percentage and prior percentage', () => {
  const markup = beakerMeter(40, 30, false, true);
  assert.ok(markup.includes('--fill:40%'));
  assert.ok(markup.includes('--previous-fill:30%'));
  assert.ok(markup.includes('is-filling'));
  assert.ok(markup.includes('aria-hidden="true"'));
  assert.ok(beakerMeter(-10).includes('--fill:0%'));
  assert.ok(beakerMeter(150).includes('--fill:100%'));
});
test('decorative scenes and celebrations have fixed, bounded particle counts', () => {
  assert.equal((labScene().match(/class="lab-flask /g) ?? []).length, 3);
  assert.equal((sparkParticles().match(/class="particle"/g) ?? []).length, 16);
  assert.equal((reportConfetti().match(/class="confetti-piece"/g) ?? []).length, 24);
  for (const markup of [labScene(), sparkParticles(), reportConfetti()]) assert.ok(markup.includes('aria-hidden="true"'));
});
