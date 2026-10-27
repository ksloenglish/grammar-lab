import { assemble, createExperiment, submitTrial, retryTrial, giveUp, advanceTrial, makeReport, ruleBreakdown, wrongQuestions, sampleQuestions, scoreComment } from './core.js';
import { load, save, remove, storageAvailable, saveBest, validSession, archiveOutdatedWork } from './storage.js';
import { QUESTION_SCHEMA, questionContextIssues } from './question-context.js';
import { labScene, beakerMeter, sparkParticles, reportConfetti, spellingStepsMarkup } from './effects.js';
import { renderIngredients } from './ingredients.js';
import { VERSION } from '../version.js';

const app = document.querySelector('#app');
const dialog = document.querySelector('#confirm-dialog');
const announcer = document.querySelector('#announcer');
const dataCache = new Map();
let modules = [];
let session = null;
let report = null;
let selectedCount = 10;
let currentRoute = 'home';
let navigationIndex = 0;
let renderId = 0;
let dialogPending = false;
let ignorePop = false;
let draggedId = null;
let dragEndedAt = 0;
let audioContext;
let soundOn = false;
let bankUpdateNotice = false;
let justPlacedBlock = null;
let justFused = false;
const e = text => String(text ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const moduleById = id => modules.find(item => item.id === id && item.available);
const actionButton = (label, action, style = 'primary', attrs = '') => `<button type="button" class="button ${style}" data-action="${action}" ${attrs}>${label}</button>`;
const routeLink = (label, route, style = 'secondary') => `<a class="button ${style}" href="#${e(route)}" data-route="${e(route)}">${label}</a>`;
const storageCopy = () => storageAvailable()
  ? 'Your scores and unfinished experiment are saved only in this browser, on this device. If you clear the browser data or reset the browser, you will lose them.'
  : 'This browser cannot save your progress. You can still practise, but you will lose your scores and progress if you leave or refresh the page.';

function announce(message) {
  announcer.textContent = '';
  setTimeout(() => { announcer.textContent = message; }, 30);
}
function updateStorageNotice() { document.querySelector('#storage-notice').textContent = storageCopy() + ' No account or personal data is collected by this app.'; }
function persist() { if (session) save('session', session); updateStorageNotice(); }
async function jsonFile(file) {
  if (!dataCache.has(file)) {
    const response = await fetch(`./data/${file}`, { cache: 'no-cache' });
    if (!response.ok) throw new Error('The learning content could not be loaded. Please check your connection and try again.');
    const data = await response.json();
    dataCache.set(file, data);
  }
  return dataCache.get(file);
}
function gapSentence(sentence, value = '_____') {
  const pieces = sentence.split('_____');
  return `${e(pieces[0])}<span class="gap">${e(value)}</span>${e(pieces.slice(1).join('_____'))}`;
}
function focusMain() { app.focus({ preventScroll: true }); window.scrollTo({ top: 0, behavior: 'instant' }); }
function questionHeading(module, eyebrow, text) {
  return `<header class="page-heading"><a href="#home" data-route="home" class="back-link">← Lab home</a><p class="eyebrow">${e(eyebrow)} / ${e(module.shortTitle)}</p><h1>${e(text)}</h1></header>`;
}
function getSavedSession() {
  const saved = load('session');
  return validSession(saved, modules.filter(item => item.available).map(item => item.id)) ? saved : null;
}

async function confirmLeave(discard = false) {
  if (!session) return true;
  if (dialogPending) return false;
  dialogPending = true;
  const previousFocus = document.activeElement;
  document.querySelector('#dialog-title').textContent = discard ? 'End this experiment?' : 'Leave this experiment?';
  document.querySelector('#dialog-message').textContent = discard
    ? 'Your unfinished experiment will be removed. It will not count towards your best score. Do you want to end it?'
    : (storageAvailable() ? 'Your progress will stay in this browser. You can continue later. Your best score will not change until you finish.' : 'This browser cannot save your progress. If you leave, you will lose this unfinished experiment.');
  dialog.querySelector('[value="leave"]').textContent = discard ? 'End experiment' : 'Save and leave';
  if (!storageAvailable() && !discard) dialog.querySelector('[value="leave"]').textContent = 'Leave experiment';
  dialog.returnValue = 'cancel';
  dialog.showModal();
  return new Promise(resolve => {
    dialog.addEventListener('close', () => {
      dialogPending = false;
      if (dialog.returnValue === 'leave') {
        if (discard) remove('session'); else persist();
        session = null;
        resolve(true);
      } else {
        if (previousFocus?.isConnected) previousFocus.focus();
        resolve(false);
      }
    }, { once: true });
  });
}
async function navigate(route, { replace = false, guard = true } = {}) {
  if (guard && session && route !== 'experiment' && !(await confirmLeave())) return;
  currentRoute = route;
  navigationIndex += replace ? 0 : 1;
  const url = new URL(location.href);
  url.hash = route;
  if (route === 'home') url.search = '';
  history[replace ? 'replaceState' : 'pushState']({ lab: true, index: navigationIndex, route }, '', url);
  await render(route);
  focusMain();
}
window.addEventListener('popstate', async event => {
  if (ignorePop) { ignorePop = false; return; }
  const target = event.state?.route ?? (location.hash.slice(1) || 'home');
  const targetIndex = event.state?.index ?? navigationIndex - 1;
  if (session && target !== 'experiment') {
    const delta = targetIndex - navigationIndex;
    if (delta) {
      ignorePop = true;
      history.go(-delta);
      // Wait for history restoration before allowing the dialog's decision to change routes.
      await new Promise(resolve => setTimeout(resolve, 80));
    }
    if (!(await confirmLeave())) return;
    if (delta) {
      history.go(delta);
      return;
    }
  }
  navigationIndex = targetIndex;
  currentRoute = target;
  await render(target);
  focusMain();
});
window.addEventListener('beforeunload', event => {
  if (!session) return;
  persist();
  event.preventDefault();
  event.returnValue = '';
});
window.addEventListener('pagehide', persist);

function homeView() {
  const best = load('best', {});
  const saved = getSavedSession();
  const available = modules.filter(item => item.available);
  return `<section class="hero">
    <div class="hero-copy"><p class="eyebrow"><span class="status-dot"></span> LEARN · BUILD · TRY AGAIN</p><h1>Mix words.<br><em>Make it work.</em></h1><p class="hero-description">Move word blocks, build your answer and see what happens. Make mistakes, learn the rules and try again.</p><div class="hero-actions"><a class="button primary" href="#modules">Pick a grammar challenge <span class="arrow" aria-hidden="true">↗</span></a><span class="hero-footnote">No login needed.</span></div></div>
    <aside class="hero-demo" aria-label="Example: easy plus ier forms easier"><div class="specimen-label"><span>WORD EXAMPLE</span><span>BUILD A WORD</span></div><div class="demo-equation"><span class="demo-token">easy</span><span class="demo-plus">+</span><span class="demo-token suffix">-ier</span></div><div class="demo-flow" aria-hidden="true">↓</div><div class="demo-result">easier<span class="demo-tick" aria-hidden="true">✓</span></div><p class="demo-caption">Change <strong>y → i</strong>. Add <strong>-er</strong>.<br>You have made the correct word.</p>${labScene()}<div class="glassware" aria-hidden="true"></div></aside>
  </section>
  ${saved ? `<section class="resume-banner"><div><strong>You have an unfinished experiment.</strong><p>${e(moduleById(saved.moduleId)?.shortTitle)} · ${saved.practice ? 'Wrong-answer practice' : `${saved.count} trials`} · ${saved.results.length} completed</p></div>${actionButton('Resume experiment →', 'resume')}${actionButton('Discard', 'discard-saved', 'ghost')}</section>` : ''}
  <section id="modules" aria-labelledby="modules-heading"><div class="section-heading"><span class="section-index">01 /</span><div><h2 id="modules-heading">Choose a grammar topic.</h2><p>Read the rules first, or try some questions.</p></div><span class="available-count">${available.length} CHALLENGES READY</span></div><div class="modules-grid">${available.map((module, i) => `<article class="module-card ${e(module.accent)}"><div class="module-top"><span class="module-status">LAB ${String(i + 1).padStart(2, '0')} · READY</span></div><h3>${e(module.title)}</h3><p>${e(module.description)}</p><div class="module-preview"><span>${i === 0 ? 'big → bigger → biggest' : 'well → better → best'}</span><span aria-hidden="true">↗</span></div><div class="module-actions">${routeLink('Learn the rules', `learn/${module.id}`)}${routeLink('Experiment →', `setup/${module.id}`, 'primary')}</div><div class="best-scores">${[10, 20, 30].map(n => { const record = best[`${module.id}:${n}`]; return `<span class="best-chip">${n} trials: ${record ? `best ${record.score}/${n}` : 'not yet tested'}</span>`; }).join('')}</div></article>`).join('')}</div></section>
  <section class="future-section" aria-labelledby="future-heading"><div class="section-heading"><span class="section-index">02 /</span><div><h2 id="future-heading">More topics to come</h2><p>More ways to practise grammar.</p></div></div><div class="coming-grid">${modules.filter(item => !item.available).map(module => `<article class="coming-card"><span class="coming-symbol" aria-hidden="true">${e(module.symbol ?? '…')}</span><div><h3>${e(module.title)}</h3><p>Coming soon</p></div></article>`).join('')}</div></section>
  <aside class="privacy-notice"><strong>Your scores stay in this browser.</strong><p>${e(storageCopy())} Best scores are kept separately for 10, 20 and 30 trials. You can add your name and class to a printed report. They are not saved or sent.</p></aside>`;
}

async function setupView(module) {
  const bank = await jsonFile(module.bank);
  if (bank.questions.length < 30) throw new Error('This module needs at least 30 questions before it can be used.');
  const params = new URLSearchParams(location.search);
  const preset = params.get('module') === module.id && [10, 20, 30].includes(Number(params.get('n')));
  const saved = getSavedSession();
  return `${questionHeading(module, 'EXPERIMENT SETUP', 'Ready to mix?' )}<div class="two-column"><section class="content-panel setup-card"><h2>${e(module.title)}</h2><p>Choose how many questions to try. The questions are chosen at random. No question appears twice in one experiment.</p>${preset ? '<p class="assignment-note">Teacher assignment: your module and trial count are preselected.</p>' : ''}<fieldset class="trial-options"><legend>Number of trials</legend>${[10, 20, 30].map(n => `<label class="choice"><input type="radio" name="trial-count" value="${n}" ${selectedCount === n ? 'checked' : ''}><strong>${n}</strong><span>trials</span></label>`).join('')}</fieldset><div class="setup-summary"><span>${bank.questions.length} questions in this bank</span><span>First attempt = 1 mark</span></div>${actionButton('Start Experiment →', 'start', 'primary', `data-module="${e(module.id)}"`)}${saved ? `<p class="notice">You have an unfinished experiment. We will ask before starting a new one.</p>` : ''}</section><aside class="side-panel"><p class="eyebrow">HOW TO PLAY</p><h2>Build. Check. Learn.</h2><ol class="setup-steps"><li>Read the sentence and the base word.</li><li>Tap or drag word parts into your answer.</li><li>Put your blocks in order, then check your answer.</li><li>Read the message and try again if needed.</li></ol><p>You get one mark if your first answer is correct. After a mistake, you can try again or see the answer.</p>${routeLink('Review the rules first', `learn/${module.id}`, 'secondary')}<p class="privacy-copy">${e(storageCopy())}</p></aside></div>`;
}

async function learnView(module) {
  const learn = await jsonFile(module.learn);
  const checks = load(`learn:${module.id}`, {});
  return `${questionHeading(module, 'LEARN', 'Learn the rules.')}<p class="learn-intro">${e(learn.intro)}</p><div class="learn-layout"><div class="learn-sections">${learn.sections.map((section, i) => `<section class="learn-section" id="rule-${i}"><span class="section-index">${String(i + 1).padStart(2, '0')} /</span><h2>${e(section.title)}</h2><p>${e(section.text)}</p>${section.examples?.length ? `<ul class="example-list">${section.examples.map(example => `<li>${e(example)}</li>`).join('')}</ul>` : ''}${section.note ? `<p class="rule-note">${e(section.note)}</p>` : ''}</section>`).join('')}</div><aside class="learn-sidebar"><p class="eyebrow">LAB NOTES</p><h2>${e(module.shortTitle)}</h2><nav aria-label="Rules on this page">${learn.sections.map((section, i) => `<a href="#rule-${i}">${e(section.title)}</a>`).join('')}</nav>${routeLink('Try an experiment →', `setup/${module.id}`, 'primary')}<p>Other correct forms are accepted if they fit the sentence.</p></aside></div>
  <section class="mini-check" aria-labelledby="mini-title"><p class="eyebrow">TRY A QUICK CHECK</p><h2 id="mini-title">A quick three-question check</h2><form id="mini-form" data-module="${e(module.id)}">${learn.miniCheck.map((question, i) => `<div class="mini-question"><fieldset><legend>${i + 1}. ${e(question.sentence)}</legend><div class="mini-options">${question.options.map(option => `<label><input type="radio" name="mini-${i}" value="${e(option)}" ${checks[i] === option ? 'checked' : ''} required><span>${e(option)}</span></label>`).join('')}</div></fieldset><p class="mini-feedback" id="mini-feedback-${i}" hidden></p></div>`).join('')}<div class="learn-check-actions"><button type="submit" class="button secondary">Check my answers</button>${routeLink('Start an Experiment →', `setup/${module.id}`, 'primary')}</div><p id="mini-result" role="status"></p></form></section><div class="learn-sources"><p>Grammar references: ${learn.sources.map(source => `<a href="${e(source.url)}" target="_blank" rel="noopener noreferrer">${e(source.title)}</a>`).join(' · ')}</p></div>`;
}

function assemblyView(question) {
  const locked = session.status !== 'building';
  return session.assembly.map((id, i) => { const block = question.blocks.find(item => item.id === id); return `<div class="assembled-block${id === justPlacedBlock ? ' just-placed' : ''}" data-block="${e(id)}" draggable="${!locked}"><button class="token-button ${e(block.kind)}" data-action="return-block" data-block="${e(id)}" ${locked ? 'disabled' : ''} aria-label="Move ${e(block.label)} back to the word blocks">${e(block.operation === 'remove-final-y' ? 'y' : block.label)}</button><div class="move-buttons"><button data-action="move-block" data-block="${e(id)}" data-direction="-1" aria-label="Move ${e(block.label)} left" ${locked || i === 0 ? 'disabled' : ''}>←</button><button data-action="move-block" data-block="${e(id)}" data-direction="1" aria-label="Move ${e(block.label)} right" ${locked || i === session.assembly.length - 1 ? 'disabled' : ''}>→</button></div></div>`; }).join('');
}
function trialView() {
  if (!session) return '<section class="error-panel"><h1>No active experiment</h1><p>Resume your saved experiment or start a new one.</p>' + routeLink('Back to Home', 'home') + '</section>';
  const module = moduleById(session.moduleId);
  const question = session.questions[session.index];
  const building = session.status === 'building';
  const completed = ['correct', 'revealed'].includes(session.status);
  const wrong = session.status === 'wrong';
  const assembled = assemble(question, session.assembly);
  const progress = session.results.length / session.count * 100;
  let preview = e(assembled.text || 'Your answer will appear here');
  if (wrong) preview = `<span class="shatter-word" aria-hidden="true">${[...assembled.text].map((char, i) => `<span style="--i:${i};--dx:${(i % 5 - 2) * 7}px;--dy:${(i % 3 - 1) * 9}px;--rotation:${i % 2 ? 9 : -9}deg">${char === ' ' ? '&nbsp;' : e(char)}</span>`).join('')}</span><span class="sr-only">${e(assembled.text)}</span>`;
  if (session.status === 'revealed') preview = e(question.answers[0]);
  return `<div class="experiment-bar"><div class="trial-meta"><p class="eyebrow">${session.practice ? 'REVISION ROUND' : 'EXPERIMENT'} / ${e(module.shortTitle)}</p><strong>Trial ${session.index + 1} of ${session.count}</strong></div><div class="score-display">${beakerMeter(session.score / session.count * 100, (session.score - (session.status === 'correct' && session.attempts === 1 ? 1 : 0)) / session.count * 100, false, session.status === 'correct' && session.attempts === 1)}<span>Score</span><strong>${session.score}<small> / ${session.count}</small></strong></div>${actionButton('End Experiment', 'end', 'ghost end-button')}</div><div class="progress-track" role="progressbar" aria-label="Completed trials" aria-valuenow="${session.results.length}" aria-valuemin="0" aria-valuemax="${session.count}"><div class="progress-fill" style="width:${progress}%"></div></div>
  ${session.practice ? '<p class="practice-notice">This practice has its own score. Your first result and best score will not change.</p>' : ''}
  <section class="trial-card"><div class="trial-label"><span class="eyebrow">QUESTION ${String(session.index + 1).padStart(2, '0')}</span><span>${e(question.degree)} · ${e(question.rule)}</span></div><h1 class="sentence">${gapSentence(question.sentence)}</h1><p class="base-hint">Base word: <strong>${e(question.base)}</strong></p></section>
  <div class="workbench ${session.status === 'correct' ? 'reaction-success' : ''}"><section class="chamber-panel"><div class="panel-label"><h2>Build your answer</h2><span>01 / BUILD</span></div><div class="assembly-zone" id="assembly-zone" data-zone="assembly" aria-label="Answer blocks in order">${session.assembly.length ? assemblyView(question) : '<p class="tray-placeholder">Drop or tap your word parts here</p>'}</div>${spellingStepsMarkup(assembled.parts, e)}<div class="answer-preview ${session.status === 'correct' ? 'success-glow' : ''}${justFused ? ' just-fused' : ''}"><span class="answer-label">YOUR ANSWER</span><strong id="assembled-answer">${preview}</strong>${session.status === 'correct' ? sparkParticles() : ''}</div>
  ${!building ? `<div class="reaction ${wrong ? 'error' : 'success'}" role="region" aria-label="Trial feedback"><span class="reaction-icon" aria-hidden="true">${wrong ? '✗' : session.status === 'revealed' ? '→' : '✓'}</span><div class="reaction-text"><h3>${wrong ? 'Not quite. Try again.' : session.status === 'revealed' ? 'The correct answer' : 'Correct. Well done!'}</h3><p>${e(session.feedback)}</p>${session.status === 'revealed' ? `<p>Correct answer: <strong>${question.answers.map(e).join(' / ')}</strong></p><p class="correct-recipe">${question.correctSequences[0].map(id => e(question.blocks.find(block => block.id === id).label)).join(' + ')}</p>` : ''}${session.status === 'correct' ? `<p class="mark-note">${session.attempts === 1 ? '+1 mark for a correct first answer.' : 'Good try. No mark this time: only your first answer counts.'}</p>` : ''}</div></div>` : ''}
  <div class="trial-actions">${building ? `${actionButton('Check answer →', 'submit', 'primary', session.assembly.length ? '' : 'disabled')}${actionButton('Clear answer', 'clear', 'ghost', session.assembly.length ? '' : 'disabled')}` : wrong ? `<div class="feedback-actions">${actionButton('Retry', 'retry')}${actionButton('Give Up', 'give-up', 'secondary')}</div>` : completed ? actionButton(session.index + 1 === session.count ? 'View Lab Report →' : 'Next trial →', 'next') : ''}</div></section>
  <section class="tray-panel"><div class="panel-label"><h2>Word blocks</h2><span>02 / SELECT</span></div><p class="tray-help">Tap a block to add it. Tap a block in your answer to move it back. You can also drag blocks to put them in order.</p><div class="reagent-tray" id="reagent-tray" data-zone="tray">${renderIngredients(question, session.trayOrder, session.assembly, building, e)}</div><p class="keyboard-help">Keyboard: press Tab to choose a block, then Enter or Space to add it. Use the arrow buttons to change the order, or press Left or Right on a block in your answer.</p><p class="rule-note">An ending joins the word before it. You do not need every block.</p></section></div>`;
}

function reportView() {
  if (!report) report = load('last-report');
  if (!report || report.schema !== QUESTION_SCHEMA || !moduleById(report.moduleId) || report.results?.length !== report.count || report.questions.some(question => questionContextIssues(question).length)) return '<section class="error-panel"><h1>No lab report yet</h1><p>Complete an experiment to see your results.</p>' + routeLink('Back to Home', 'home') + '</section>';
  const module = moduleById(report.moduleId);
  const breakdown = ruleBreakdown(report);
  const wrongCount = wrongQuestions(report).length;
  return `${questionHeading(module, report.practice ? 'REVISION REPORT' : 'LAB REPORT', 'See what you have learnt.')}<section class="report-hero">${reportConfetti()}<div class="report-score">${beakerMeter(report.percentage, 0, true, true)}<strong>${report.score}<span>/${report.count}</span></strong><span>${report.percentage}% correct on the first answer</span></div><div class="report-summary"><p class="eyebrow">${e(module.title)}</p><h2>${e(scoreComment(report.percentage))}</h2><p>${report.practice ? 'This is a practice score. It does not change your best score.' : 'You get marks for correct first answers only. Trying again helps you learn, but does not add marks.'}</p></div></section>${report.practice && report.originalReport ? `<div class="original-report-summary"><strong>Original experiment: ${report.originalReport.score}/${report.originalReport.count} (${report.originalReport.percentage}%) — unchanged.</strong>${actionButton('View original report', 'original-report', 'ghost')}</div>` : ''}
  <div class="report-actions no-print">${actionButton(`Retry Wrong Answers${wrongCount ? ` (${wrongCount})` : ''}`, 'practice', 'primary', wrongCount ? '' : 'disabled')}${routeLink('New Experiment', `setup/${module.id}`)}${routeLink('Back to Home', 'home', 'ghost')}${actionButton('Print / Save as PDF', 'print', 'secondary')}</div>
  <section class="rule-breakdown" aria-labelledby="breakdown-title"><h2 id="breakdown-title">Your results for each rule</h2>${Object.entries(breakdown).map(([rule, value]) => `<div class="rule-row"><div class="rule-name">${e(rule)}</div><span class="rule-stat">${value.correct}/${value.total}</span><div class="rule-track"><div class="rule-fill" style="width:${value.correct / value.total * 100}%"></div></div></div>`).join('')}</section>
  <section class="report-identity no-print"><h2>Add your name to your printed report <span class="optional-label">optional</span></h2><p>These fields are only used for this printout. They are not saved or sent anywhere. In the print dialogue, choose “Save as PDF” to keep a copy.</p><div class="identity-fields"><label>Name <input id="report-name" type="text" maxlength="80" autocomplete="off" placeholder="Optional name"></label><label>Class <input id="report-class" type="text" maxlength="30" autocomplete="off" placeholder="Optional class"></label></div></section><p class="print-identity print-only" id="print-identity"></p>
  <section class="report-list" aria-labelledby="trials-title"><div class="section-heading"><span class="section-index">QUESTIONS /</span><h2 id="trials-title">All ${report.count} trials</h2></div>${report.questions.map((question, i) => { const result = report.results[i]; return `<article class="report-item"><div class="report-item-header"><span class="result-mark ${result.mark ? 'correct' : 'incorrect'}" aria-label="${result.mark ? 'Correct first answer' : 'Incorrect first answer'}">${result.mark ? '✓' : '✗'}</span><strong>Trial ${i + 1}</strong><span>${e(question.rule)} · ${e(question.degree)}</span></div><p class="report-sentence">${e(question.sentence)}</p><div class="answer-comparison"><div class="answer-entry"><span class="answer-label">YOUR FIRST ANSWER</span><span class="answer-value ${result.mark ? 'correct' : 'incorrect'}">${e(result.firstAnswer)}</span></div><div class="answer-entry"><span class="answer-label">CORRECT ANSWER${question.answers.length > 1 ? 'S' : ''}</span><span class="answer-value">${question.answers.map(e).join(' / ')}</span></div></div>${!result.mark ? `<p class="report-explanation">${e(question.explanation)}${result.gaveUp ? ' Answer revealed.' : ' Correct after another try.'}</p>` : ''}</article>`; }).join('')}</section><p class="report-label">K S Lo Grammar Lab · ${e(VERSION)} · ${e(new Date(report.finishedAt).toLocaleString('en-GB', { timeZone: 'Asia/Hong_Kong' }))} HKT</p>`;
}

async function render(route) {
  const ticket = ++renderId;
  app.setAttribute('aria-busy', 'true');
  try {
    const [view, id] = route.split('/');
    let html;
    if (view === 'home' || !view) html = homeView();
    else if (view === 'learn' || view === 'setup') {
      const module = moduleById(id);
      if (!module) throw new Error('This module is not available yet. Please choose a ready module from the homepage.');
      html = view === 'learn' ? await learnView(module) : await setupView(module);
    } else if (view === 'experiment') html = trialView();
    else if (view === 'report') html = reportView();
    else html = homeView();
    if (ticket !== renderId) return;
    app.innerHTML = `${bankUpdateNotice ? '<aside class="notice" role="status">We have updated the questions. Please start a new experiment. Your best scores are still saved.</aside>' : ''}${html}`;
    document.title = `${view === 'home' ? 'K S Lo Grammar Lab' : view === 'report' ? 'Lab Report | K S Lo Grammar Lab' : moduleById(id ?? session?.moduleId)?.shortTitle ?? 'Experiment'} | K S Lo English`;
  } catch (error) {
    if (ticket !== renderId) return;
    app.innerHTML = `<section class="error-panel"><h1>The lab needs a moment.</h1><p>${e(error.message)}</p>${actionButton('Try again', 'reload', 'primary')}${routeLink('Back to Home', 'home')}</section>`;
    announce(error.message);
  } finally { if (ticket === renderId) app.setAttribute('aria-busy', 'false'); }
}

async function refreshTrial(focusSelector) {
  persist();
  await render('experiment');
  if (focusSelector) app.querySelector(focusSelector)?.focus({ preventScroll: true });
}
function sound(correct) {
  if (!soundOn) return;
  try {
    audioContext ??= new (window.AudioContext || window.webkitAudioContext)();
    audioContext.resume();
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    oscillator.connect(gain); gain.connect(audioContext.destination);
    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(correct ? 520 : 190, audioContext.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(correct ? 780 : 100, audioContext.currentTime + 0.18);
    gain.gain.setValueAtTime(0.04, audioContext.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.25);
    oscillator.start(); oscillator.stop(audioContext.currentTime + 0.26);
  } catch { /* Unsupported audio must not affect marking. */ }
}
async function changeBlock(id, mode, targetId) {
  if (!session || session.status !== 'building') return;
  const question = session.questions[session.index];
  const block = question.blocks.find(item => item.id === id);
  if (!block) return;
  justPlacedBlock = mode === 'return' ? null : id;
  const current = session.assembly.indexOf(id);
  if (mode === 'return') {
    if (current >= 0) session.assembly.splice(current, 1);
  } else {
    if (current >= 0) session.assembly.splice(current, 1);
    const target = targetId ? session.assembly.indexOf(targetId) : -1;
    if (target >= 0) session.assembly.splice(target, 0, id); else session.assembly.push(id);
  }
  justFused = mode !== 'return' && assemble(question, session.assembly).parts.some(part => part.ids.includes(id) && part.ids.length > 1);
  await refreshTrial(mode === 'return' ? `[data-action="add-block"][data-block="${id}"]` : `[data-action="return-block"][data-block="${id}"]`);
  announce(`${block.label} ${mode === 'return' ? 'returned to the word blocks' : 'added to your answer'}. Answer: ${assemble(question, session.assembly).text || 'empty'}.`);
}
async function moveBlock(id, direction) {
  if (!session || session.status !== 'building') return;
  const from = session.assembly.indexOf(id);
  const to = from + direction;
  if (from < 0 || to < 0 || to >= session.assembly.length) return;
  [session.assembly[from], session.assembly[to]] = [session.assembly[to], session.assembly[from]];
  justPlacedBlock = id;
  justFused = assemble(session.questions[session.index], session.assembly).parts.some(part => part.ids.includes(id) && part.ids.length > 1);
  await refreshTrial(`[data-action="return-block"][data-block="${id}"]`);
  announce(`Block moved. Answer: ${assemble(session.questions[session.index], session.assembly).text}.`);
}

async function handleAction(button) {
  const action = button.dataset.action;
  if (!['add-block', 'return-block', 'move-block'].includes(action)) { justPlacedBlock = null; justFused = false; }
  if (action === 'reload') { dataCache.clear(); if (!modules.length) return initialise(); return render(currentRoute); }
  if (action === 'resume') {
    session = getSavedSession();
    if (session) await navigate('experiment', { guard: false });
    return;
  }
  if (action === 'discard-saved') {
    session = getSavedSession();
    if (session && await confirmLeave(true)) await render('home');
    else if (session) session = null;
    return;
  }
  if (action === 'start') {
    const module = moduleById(button.dataset.module);
    const existing = getSavedSession();
    if (existing) {
      session = existing;
      const accepted = await confirmLeave(true);
      if (!accepted) { session = null; return; }
    }
    button.disabled = true;
    try {
      const bank = await jsonFile(module.bank);
      session = createExperiment(module.id, sampleQuestions(bank.questions, selectedCount));
      bankUpdateNotice = false;
      persist();
      await navigate('experiment', { guard: false });
      announce(`Experiment started. ${selectedCount} trials. Only correct first answers earn marks.`);
    } catch (error) { announce(error.message); button.disabled = false; }
    return;
  }
  if (action === 'practice') {
    const questions = wrongQuestions(report);
    if (!questions.length) return;
    const original = report.practice ? report.originalReport : report;
    const saved = getSavedSession();
    if (saved) {
      session = saved;
      if (!(await confirmLeave(true))) { session = null; return; }
    }
    session = createExperiment(report.moduleId, questions, true, original);
    persist();
    await navigate('experiment', { guard: false });
    announce('A separately scored wrong-answer practice round has started.');
    return;
  }
  if (action === 'original-report') { report = report.originalReport; await render('report'); focusMain(); return; }
  if (action === 'print') {
    const name = document.querySelector('#report-name')?.value.trim();
    const className = document.querySelector('#report-class')?.value.trim();
    document.querySelector('#print-identity').textContent = [name ? `Name: ${name}` : '', className ? `Class: ${className}` : ''].filter(Boolean).join(' · ');
    window.print();
    return;
  }
  if (!session) return;
  if (action === 'end') { if (await confirmLeave(true)) await navigate('home', { guard: false }); return; }
  if (action === 'add-block') return changeBlock(button.dataset.block, 'add');
  if (action === 'return-block') return changeBlock(button.dataset.block, 'return');
  if (action === 'move-block') return moveBlock(button.dataset.block, Number(button.dataset.direction));
  if (action === 'clear' && session.status === 'building') {
    session.assembly = []; await refreshTrial('[data-action="add-block"]'); announce('Answer cleared.'); return;
  }
  if (action === 'submit') {
    const result = submitTrial(session);
    if (!result) return;
    sound(result.correct);
    await refreshTrial(result.correct ? '[data-action="next"]' : '[data-action="retry"]');
    announce(`${result.correct ? 'Correct.' : 'Not correct yet.'} ${session.feedback} ${result.correct ? result.mark ? 'One mark awarded.' : 'No mark: this was a retry.' : 'No mark will be awarded for this trial. Retry or give up.'}`);
    return;
  }
  if (action === 'retry' && retryTrial(session)) { await refreshTrial('[data-action="return-block"]'); announce('Try again. Rearrange or return the blocks.'); return; }
  if (action === 'give-up' && giveUp(session)) { await refreshTrial('[data-action="next"]'); announce(`Correct answer: ${session.questions[session.index].answers.join(' or ')}. ${session.feedback}`); return; }
  if (action === 'next') {
    const next = advanceTrial(session);
    if (next === 'complete') {
      report = makeReport(session);
      saveBest(report); save('last-report', report); remove('session'); session = null;
      updateStorageNotice();
      await navigate('report', { guard: false });
      announce(`Lab report. Score ${report.score} out of ${report.count}, ${report.percentage} per cent.`);
    } else if (next) { await refreshTrial('[data-action="add-block"]'); window.scrollTo({ top: 0, behavior: 'instant' }); announce(`Trial ${session.index + 1} of ${session.count}.`); }
  }
}

document.addEventListener('click', event => {
  const route = event.target.closest('[data-route]');
  if (route) { event.preventDefault(); if (route.dataset.route.startsWith('setup/')) selectedCount = 10; void navigate(route.dataset.route); return; }
  const anchor = event.target.closest('a[href^="#"]');
  if (anchor) {
    const target = document.getElementById(anchor.getAttribute('href').slice(1));
    if (target) { event.preventDefault(); target.scrollIntoView({ block: 'start' }); if (target === app) app.focus({ preventScroll: true }); return; }
  }
  const button = event.target.closest('[data-action]');
  if (!button || button.disabled || Date.now() - dragEndedAt < 160) return;
  void handleAction(button).catch(error => announce(error.message));
});
app.addEventListener('change', event => {
  if (event.target.name === 'trial-count') selectedCount = Number(event.target.value);
});
app.addEventListener('submit', async event => {
  if (event.target.id !== 'mini-form') return;
  event.preventDefault();
  const module = moduleById(event.target.dataset.module);
  const learn = await jsonFile(module.learn);
  const values = {};
  let correct = 0;
  learn.miniCheck.forEach((question, i) => {
    const answer = new FormData(event.target).get(`mini-${i}`);
    values[i] = answer;
    const accepted = answer === question.answer;
    if (accepted) correct++;
    const feedback = document.querySelector(`#mini-feedback-${i}`);
    feedback.hidden = false;
    feedback.className = `mini-feedback ${accepted ? 'success' : 'error'}`;
    feedback.textContent = `${accepted ? 'Correct. ' : `Correct answer: ${question.answer}. `}${question.explanation}`;
  });
  save(`learn:${module.id}`, values); updateStorageNotice();
  document.querySelector('#mini-result').textContent = `${correct}/3 correct. ${correct === 3 ? 'Ready for the workbench.' : 'Review the explanations, then try an experiment.'}`;
  announce(`${correct} of 3 mini-check answers correct. Feedback is displayed below each question.`);
});
app.addEventListener('keydown', event => {
  const block = event.target.closest('[data-action="return-block"]');
  if (block && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
    event.preventDefault(); void moveBlock(block.dataset.block, event.key === 'ArrowLeft' ? -1 : 1);
  }
});
app.addEventListener('dragstart', event => {
  if (!session || session.status !== 'building') { event.preventDefault(); return; }
  const target = event.target.closest('[data-block]');
  if (!target) return;
  draggedId = target.dataset.block;
  event.dataTransfer.setData('text/plain', draggedId);
  event.dataTransfer.effectAllowed = 'move';
});
app.addEventListener('dragover', event => {
  const zone = event.target.closest('[data-zone]');
  if (zone && draggedId) { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; zone.classList.add('drag-over'); }
});
app.addEventListener('dragleave', event => {
  const zone = event.target.closest('[data-zone]');
  if (zone && !zone.contains(event.relatedTarget)) zone.classList.remove('drag-over');
});
app.addEventListener('drop', event => {
  const zone = event.target.closest('[data-zone]');
  if (!zone || !draggedId) return;
  event.preventDefault();
  const id = draggedId;
  const targetId = event.target.closest('.assembled-block')?.dataset.block;
  draggedId = null; dragEndedAt = Date.now();
  if (id === targetId) { zone.classList.remove('drag-over'); return; }
  void changeBlock(id, zone.dataset.zone === 'tray' ? 'return' : 'add', targetId);
});
app.addEventListener('dragend', () => {
  draggedId = null; dragEndedAt = Date.now();
  app.querySelectorAll('.drag-over').forEach(zone => zone.classList.remove('drag-over'));
});
document.querySelector('#sound-toggle').addEventListener('click', event => {
  soundOn = !soundOn;
  event.currentTarget.textContent = `Sound ${soundOn ? 'on' : 'off'}`;
  event.currentTarget.setAttribute('aria-pressed', String(soundOn));
  event.currentTarget.setAttribute('aria-label', `Turn sound ${soundOn ? 'off' : 'on'}`);
  if (soundOn) sound(true);
});

async function initialise() {
  try {
    const manifest = await jsonFile('modules.json');
    modules = manifest.modules;
    bankUpdateNotice = archiveOutdatedWork();
    const params = new URLSearchParams(location.search);
    const assigned = moduleById(params.get('module'));
    const requestedCount = Number(params.get('n'));
    selectedCount = [10, 20, 30].includes(requestedCount) ? requestedCount : 10;
    currentRoute = location.hash.slice(1) || (assigned ? `setup/${assigned.id}` : 'home');
    if (currentRoute === 'experiment') {
      session = getSavedSession();
      if (!session) currentRoute = 'home';
    }
    navigationIndex = history.state?.index ?? 0;
    history.replaceState({ lab: true, index: navigationIndex, route: currentRoute }, '', `#${currentRoute}`);
    document.querySelector('#version-label').textContent = VERSION;
    updateStorageNotice();
    await render(currentRoute);
  } catch (error) {
    app.setAttribute('aria-busy', 'false');
    app.innerHTML = `<section class="error-panel"><h1>The lab is temporarily offline.</h1><p>${e(error.message)}</p>${actionButton('Try again', 'reload')}</section>`;
  }
}
void initialise();
