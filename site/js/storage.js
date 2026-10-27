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
  if (!value || value.schema !== 1 || !moduleIds.includes(value.moduleId)) return false;
  if (!Array.isArray(value.questions) || value.count !== value.questions.length || value.count < 1 || value.count > 30) return false;
  if (!Number.isInteger(value.index) || value.index < 0 || value.index >= value.count) return false;
  if (!Array.isArray(value.results) || !Array.isArray(value.assembly) || !Array.isArray(value.trayOrder)) return false;
  if (!['building', 'wrong', 'correct', 'revealed'].includes(value.status)) return false;
  const completed = ['correct', 'revealed'].includes(value.status);
  if (value.results.length !== value.index + Number(completed)) return false;
  if (!value.results.every(result => [0, 1].includes(result.mark))) return false;
  if (value.score !== value.results.reduce((sum, result) => sum + result.mark, 0)) return false;
  if (!Number.isInteger(value.attempts) || value.attempts < 0) return false;
  if (new Set(value.questions.map(question => question.id)).size !== value.count) return false;
  if (!value.questions.every(question => typeof question.sentence === 'string' && Array.isArray(question.blocks) && question.blocks.length && Array.isArray(question.answers) && question.answers.length)) return false;
  const ids = value.questions[value.index].blocks.map(block => block.id);
  return value.assembly.every(id => ids.includes(id)) && new Set(value.assembly).size === value.assembly.length && value.trayOrder.length === ids.length && new Set(value.trayOrder).size === ids.length && value.trayOrder.every(id => ids.includes(id));
}
