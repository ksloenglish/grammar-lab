import { isCorrect } from './core.js';
import { QUESTION_SCHEMA, questionContextIssues } from './question-context.js';

const PREFIX = 'kslo-grammar-lab:';
let available = true;
try {
  localStorage.setItem(PREFIX + 'probe', '1');
  localStorage.removeItem(PREFIX + 'probe');
} catch { available = false; }

export function storageAvailable() { return available; }
export function load(key, fallback = null) {
  if (!available) return fallback;
  try { return JSON.parse(localStorage.getItem(PREFIX + key) ?? 'null') ?? fallback; }
  catch { return fallback; }
}
export function save(key, value) {
  if (!available) return false;
  try {
    // Only defined application state is passed here; report identity fields never are.
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
    return true;
  } catch { available = false; return false; }
}
export function remove(key) {
  if (!available) return;
  try { localStorage.removeItem(PREFIX + key); }
  catch { available = false; }
}
export function archiveOutdatedWork() {
  let changed = false;
  for (const key of ['session', 'last-report']) {
    const value = load(key);
    if (!value) continue;
    if (value.schema !== QUESTION_SCHEMA || value.questions?.some(question => questionContextIssues(question).length)) {
      // Preserve the previous work in this browser; never alter the independent best-score key.
      if (save(`archive:${key}`, value)) remove(key);
      changed = true;
    }
  }
  return changed;
}
export function saveBest(report) {
  if (report.practice || ![10, 20, 30].includes(report.count) || report.results.length !== report.count) return false;
  const all = load('best', {});
  const key = `${report.moduleId}:${report.count}`;
  if (!all[key] || report.score > all[key].score) {
    all[key] = { score: report.score, count: report.count, percentage: report.percentage, date: report.finishedAt };
    return save('best', all);
  }
  return false;
}

export function validSession(value, moduleIds) {
  try {
    if (!value || value.schema !== QUESTION_SCHEMA || !moduleIds.includes(value.moduleId)) return false;
    if (!Array.isArray(value.questions) || value.count !== value.questions.length || value.count < 1 || value.count > 30) return false;
    if (!value.questions.every(question => question && typeof question.id === 'string' && typeof question.sentence === 'string' && Array.isArray(question.blocks) && question.blocks.length && Array.isArray(question.answers) && question.answers.length && question.answers.every(answer => typeof answer === 'string'))) return false;
    if (value.questions.some(question => questionContextIssues(question).length)) return false;
    if (new Set(value.questions.map(question => question.id)).size !== value.count) return false;
    if (!Number.isInteger(value.index) || value.index < 0 || value.index >= value.count) return false;
    if (!Array.isArray(value.results) || !Array.isArray(value.assembly) || !Array.isArray(value.trayOrder)) return false;
    if (!['building', 'wrong', 'correct', 'revealed'].includes(value.status)) return false;
    if (!Number.isInteger(value.attempts) || value.attempts < 0) return false;
    const completed = ['correct', 'revealed'].includes(value.status);
    if (value.results.length !== value.index + Number(completed)) return false;
    if (value.attempts === 0 && value.status !== 'revealed' && (value.status !== 'building' || value.firstAnswer !== null)) return false;
    if ((value.attempts > 0 || value.status === 'wrong' || value.status === 'correct') && (value.attempts < 1 || typeof value.firstAnswer !== 'string' || !value.firstAnswer.trim())) return false;
    if (!value.results.every((result, i) => {
      const question = value.questions[i];
      return result && result.questionId === question.id && [0, 1].includes(result.mark) && typeof result.firstAnswer === 'string' && typeof result.finalAnswer === 'string' && typeof result.gaveUp === 'boolean' && isCorrect(question, result.finalAnswer) && result.mark === Number(!result.gaveUp && isCorrect(question, result.firstAnswer));
    })) return false;
    if (value.score !== value.results.reduce((sum, result) => sum + result.mark, 0)) return false;
    const question = value.questions[value.index];
    if (value.status === 'wrong' && isCorrect(question, value.firstAnswer)) return false;
    if (completed) {
      const result = value.results.at(-1);
      if (result.firstAnswer !== value.firstAnswer || result.gaveUp !== (value.status === 'revealed')) return false;
      if (value.status === 'correct' && result.mark !== Number(value.attempts === 1)) return false;
    }
    const ids = question.blocks.map(block => block.id);
    return value.assembly.every(id => ids.includes(id)) && new Set(value.assembly).size === value.assembly.length && value.trayOrder.length === ids.length && new Set(value.trayOrder).size === ids.length && value.trayOrder.every(id => ids.includes(id));
  } catch { return false; }
}
