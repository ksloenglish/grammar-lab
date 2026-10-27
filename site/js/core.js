export function normalise(value) {
  return String(value ?? '').trim().replace(/\s+/g, ' ').toLowerCase();
}

export function shuffle(items, random = Math.random) {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

export function sampleQuestions(questions, count, random = Math.random) {
  if (!Number.isInteger(count) || count < 1 || count > questions.length) {
    throw new Error('The question bank does not contain enough distinct trials.');
  }
  return shuffle(questions, random).slice(0, count);
}

export function assemble(question, ids) {
  const parts = [];
  for (const id of ids) {
    const block = question.blocks.find(item => item.id === id);
    if (!block) throw new Error('An answer block is missing.');
    if (block.kind === 'suffix' && parts.length && !parts.at(-1).orphan) {
      const previous = parts.at(-1);
      previous.text = block.transforms?.[previous.text] ?? (previous.text + block.label.replace(/^-/, ''));
      previous.ids.push(id);
    } else {
      parts.push({ text: block.label, ids: [id], orphan: block.kind === 'suffix' });
    }
  }
  return { text: parts.map(part => part.text).join(' '), parts };
}

export function isCorrect(question, answer) {
  return question.answers.some(item => normalise(item) === normalise(answer));
}

export function explain(question, answer) {
  for (const feedback of question.feedback ?? []) {
    if (feedback.answers?.some(item => normalise(item) === normalise(answer))) return feedback.message;
    if (feedback.pattern) {
      try {
        if (new RegExp(feedback.pattern, 'i').test(normalise(answer))) return feedback.message;
      } catch { /* A malformed teacher-edited pattern cannot interrupt practice. */ }
    }
  }
  return question.explanation;
}

export function createExperiment(moduleId, questions, practice = false, originalReport = null) {
  return {
    schema: 1, moduleId, questions, count: questions.length, index: 0, score: 0,
    results: [], assembly: [], trayOrder: shuffle(questions[0].blocks.map(block => block.id)),
    attempts: 0, firstAnswer: null, status: 'building', feedback: '',
    practice, originalReport, startedAt: new Date().toISOString()
  };
}

export function submitTrial(session) {
  if (session.status !== 'building' || !session.assembly.length) return null;
  const question = session.questions[session.index];
  const answer = assemble(question, session.assembly).text;
  const correct = isCorrect(question, answer);
  if (session.attempts === 0) session.firstAnswer = answer;
  session.attempts += 1;
  session.feedback = correct ? question.explanation : explain(question, answer);
  if (correct) {
    const mark = session.attempts === 1 ? 1 : 0;
    session.score += mark;
    session.status = 'correct';
    session.results.push({ questionId: question.id, firstAnswer: session.firstAnswer, finalAnswer: answer, mark, gaveUp: false });
  } else {
    session.status = 'wrong';
  }
  return { correct, answer, mark: correct && session.attempts === 1 ? 1 : 0 };
}

export function retryTrial(session) {
  if (session.status !== 'wrong') return false;
  session.status = 'building';
  session.feedback = '';
  return true;
}

export function giveUp(session) {
  if (!['wrong', 'building'].includes(session.status)) return false;
  const question = session.questions[session.index];
  const current = assemble(question, session.assembly).text;
  if (session.firstAnswer === null) session.firstAnswer = current || '(No answer)';
  session.status = 'revealed';
  session.feedback = question.explanation;
  session.results.push({ questionId: question.id, firstAnswer: session.firstAnswer, finalAnswer: question.answers[0], mark: 0, gaveUp: true });
  return true;
}

export function advanceTrial(session) {
  if (!['correct', 'revealed'].includes(session.status)) return false;
  session.index += 1;
  if (session.index >= session.count) return 'complete';
  session.assembly = [];
  session.trayOrder = shuffle(session.questions[session.index].blocks.map(block => block.id));
  session.attempts = 0;
  session.firstAnswer = null;
  session.status = 'building';
  session.feedback = '';
  return 'next';
}

export function makeReport(session) {
  return {
    schema: 1, moduleId: session.moduleId, questions: session.questions,
    results: session.results, count: session.count, score: session.score,
    percentage: Math.round(session.score / session.count * 100),
    practice: session.practice, originalReport: session.originalReport,
    finishedAt: new Date().toISOString()
  };
}

export function ruleBreakdown(report) {
  const rules = {};
  report.questions.forEach((question, i) => {
    const rule = question.rule;
    rules[rule] ??= { correct: 0, total: 0 };
    rules[rule].total += 1;
    rules[rule].correct += report.results[i]?.mark ?? 0;
  });
  return rules;
}

export function wrongQuestions(report) {
  return report.questions.filter((question, i) => !report.results[i]?.mark);
}

export function scoreComment(percentage) {
  if (percentage >= 90) return 'Excellent reactions. Your grammar is looking precise and confident.';
  if (percentage >= 70) return 'Strong work. A little revision will make your reactions even more reliable.';
  if (percentage >= 50) return 'You are finding the patterns. Revisit the rules, then try the missed trials.';
  return 'Every experiment teaches you something. Start with Learn, then test one rule at a time.';
}
