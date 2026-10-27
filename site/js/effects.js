export function labScene() {
  return `<div class="lab-scene" aria-hidden="true">${['teal', 'violet', 'coral'].map((colour, i) => `<div class="lab-flask ${colour}"><span class="flask-neck"></span><span class="flask-body"><span class="flask-liquid"></span>${Array.from({ length: 3 }, (_, j) => `<span class="lab-bubble" style="--bubble:${j};--delay:${i * 65 + j * 55}ms"></span>`).join('')}</span><span class="flask-tag">${['BUILD', 'CHECK', 'LEARN'][i]}</span></div>`).join('')}<span class="scene-spark">+</span><span class="scene-spark second">×</span></div>`;
}

export function beakerMeter(percent, previous = percent, large = false, animate = false) {
  const level = Math.max(0, Math.min(100, percent));
  const prior = Math.max(0, Math.min(100, previous));
  return `<span class="beaker-meter${large ? ' large' : ''}${animate ? ' is-filling' : ''}" style="--fill:${level}%;--previous-fill:${prior}%" aria-hidden="true"><span class="beaker-rim"></span><span class="beaker-body"><span class="beaker-fill"></span><span class="beaker-graduations"></span><span class="beaker-bubble"></span><span class="beaker-bubble second"></span></span></span>`;
}

export function sparkParticles() {
  return `<div class="particles" aria-hidden="true">${Array.from({ length: 16 }, (_, i) => {
    const angle = i * Math.PI * 2 / 16;
    const distance = 48 + i % 3 * 17;
    return `<span class="particle" style="--x:${Math.round(Math.cos(angle) * distance)}px;--y:${Math.round(Math.sin(angle) * distance)}px;--delay:${i % 4 * 18}ms"></span>`;
  }).join('')}</div>`;
}

export function reportConfetti() {
  return `<div class="report-confetti" aria-hidden="true">${Array.from({ length: 24 }, (_, i) => `<span class="confetti-piece" style="--x:${i * 4}%;--delay:${i % 5 * 30}ms;--rotate:${i % 2 ? 35 : -35}deg"></span>`).join('')}</div>`;
}

export function spellingStepsMarkup(parts, escape) {
  return parts.flatMap(part => (part.spellingChanges ?? []).map(step => `<div class="spelling-change" aria-hidden="true"><span class="spelling-word">${escape(step.before.slice(0, -1))}<s class="deleted-letter">${escape(step.before.slice(-1))}</s></span><span class="spelling-arrow">→</span><span class="spelling-word">${escape(step.after)}</span>${part.text !== step.after ? `<span class="spelling-arrow">→</span><span class="spelling-word completed">${escape(part.text)}</span>` : ''}</div>`)).join('');
}
