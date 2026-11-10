"""Stable, mistake-specific feedback regression using current engine-created fixtures.

Run GRAMMAR_TEST_URL=http://127.0.0.1:3000/ python3 tests/answer-feedback-check.py.
Chromium 1440px and genuine touch WebKit 360x640/800; no source edits/hooks.
Evidence stays beneath ignored test-results/answer-feedback/. Existing all-192
ordinary-building audit remains in mobile-question-redesign-check.py.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import time
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('GRAMMAR_TEST_URL', 'http://127.0.0.1:3000/').rstrip('/') + '/'
OUT = ROOT / 'test-results/answer-feedback'
OUT.mkdir(parents=True, exist_ok=True)
EVIDENCE = {'url': BASE, 'checks': [], 'cases': [], 'screenshots': [], 'errors': []}
GOOD = 'Good changes its form to better. Use than to introduce the other person, thing or action in the comparison.'
OLD = 'Use better than to compare two things. Good changes its form. Use better than in this gap.'
_spec = importlib.util.spec_from_file_location('feedback_text_metrics', ROOT / 'tests/home-ui-check.py')
_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_metrics)
TEXT_METRICS = _metrics.TEXT_METRICS


def check(condition, message):
    if not condition:
        EVIDENCE['errors'].append(message)
        raise AssertionError(message)
    EVIDENCE['checks'].append(message)


def saved(page):
    return page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session'))")


def activate(locator, mobile):
    locator.tap() if mobile else locator.click()


def screenshot(page, tag, name, viewport=False):
    file = f'{tag}-{name}{"-viewport" if viewport else ""}.png'
    page.evaluate('async()=>{await document.fonts.ready;window.scrollTo(0,0);await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);}')
    page.screenshot(path=str(OUT / file), full_page=not viewport)
    EVIDENCE['screenshots'].append(file)


SEED = """async ({module,id,labels=[],submit=false,legacy=false}) => {
  const {createExperiment,submitTrial}=await import('./js/core.js');
  const bank=(await(await fetch('./data/'+module+'-questions.json')).json()).questions;
  const q=bank.find(q=>q.id===id); if(!q)throw new Error('Missing fixture '+id);
  const state=createExperiment(module,[q]);
  state.assembly=labels.map(label=>{const b=state.questions[0].blocks.find(b=>b.label===label);if(!b)throw new Error('Missing label '+label);return b.id;});
  if(submit)submitTrial(state);
  if(legacy){state.feedback='Use better than to compare two things. Good changes its form. Use better than in this gap.';
    state.questions[0].explanation=state.feedback;}
  const best={'adjectives:10':{score:8,count:10,percentage:80,date:'2026-11-10'}};
  localStorage.clear();localStorage.setItem('kslo-grammar-lab:session',JSON.stringify(state));
  localStorage.setItem('kslo-grammar-lab:best',JSON.stringify(best));return{state,best};
}"""


def seed(page, module, question_id, labels=None, submit=False, legacy=False):
    # Leave the old document before injecting: its pagehide must not overwrite
    # the new fixture, and this is not an app-source test hook.
    page.goto(BASE + '?feedback-fixture=' + str(time.monotonic_ns()), wait_until='domcontentloaded')
    expect(page.locator('.module-card')).to_have_count(2)
    fixture = page.evaluate(SEED, {'module': module, 'id': question_id, 'labels': labels or [], 'submit': submit, 'legacy': legacy})
    page.evaluate("history.replaceState(null,'','#experiment')")
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('.sentence')).to_be_visible()
    check(saved(page) == fixture['state'], f'{question_id}: prepared schema-2 fixture resumes exactly')
    return fixture


def select(page, labels, mobile):
    q = saved(page)['questions'][0]
    ids = [next(b['id'] for b in q['blocks'] if b['label'] == label) for label in labels]
    for block_id in ids:
        activate(page.locator(f'[data-action="add-block"][data-block="{block_id}"]'), mobile)
    return ids


def current_diagnostic(page):
    return page.evaluate("""async () => {
      const {diagnoseAnswer}=await import('./js/feedback.js');const {assemble}=await import('./js/core.js');
      const s=JSON.parse(localStorage.getItem('kslo-grammar-lab:session')),q=s.questions[s.index];
      const a=assemble(q,s.assembly);return {diagnostic:diagnoseAnswer(q,a.text,s.assembly),assembled:a};
    }""")


def layout(page, tag, building=False):
    check(page.evaluate('Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)<=innerWidth'), f'{tag}: no horizontal overflow')
    expect(page.locator('.score-display')).to_be_visible()
    expect(page.locator('.experiment-bar .beaker-meter, .move-buttons, [data-action="move-block"], .shatter-word')).to_have_count(0)
    positions = page.evaluate("""() => {
      const q=document.querySelector('.trial-card'),c=document.querySelector('.chamber-panel'),t=document.querySelector('.tray-panel');
      return {order:!!(q.compareDocumentPosition(c)&Node.DOCUMENT_POSITION_FOLLOWING)&&!!(c.compareDocumentPosition(t)&Node.DOCUMENT_POSITION_FOLLOWING),
        ys:[q,c,t].map(n=>n.getBoundingClientRect().y),score:document.querySelector('.score-display').getBoundingClientRect().height};
    }""")
    check(positions['order'] and positions['score'] <= 32.1, f'{tag}: compact score and Question/Build/Word blocks DOM order remain')
    mobile = page.viewport_size['width'] == 360
    if mobile:
        check(positions['ys'][0] < positions['ys'][1] < positions['ys'][2], f'{tag}: phone vertical reading order remains')
    for node in page.locator('.reagent .block-label, .token-button').all():
        m = node.evaluate(TEXT_METRICS)
        check(m['fonts'] and min(m['fonts']) >= (18 if mobile else 20) and m['rects'] and not m['clipped'] and not m['hidden'],
              f'{tag}: {m["text"]!r} tile label stays readable and unclipped')
    controls = page.locator('.trial-actions button, .reagent, .token-button')
    dimensions = controls.evaluate_all('nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return [r.width,r.height]})')
    target_message = f'{tag}: all controls retain 44px height and phone targets retain 44px width ({dimensions})'
    if dimensions and all(h >= 43.9 and (not mobile or w >= 43.9) for w,h in dimensions):
        check(True, target_message)
    else:
        # Collect remaining independent feedback cases, but never waive this
        # requirement: main() fails if ANY observed layout/runtime error exists.
        EVIDENCE['errors'].append(target_message)
    desktop_targets = page.locator('.trial-actions button, .reagent').evaluate_all('nodes=>nodes.map(n=>n.getBoundingClientRect().width)')
    check(all(w >= 43.9 for w in desktop_targets), f'{tag}: action and tray targets retain 44px width')
    if building and mobile:
        bottom = page.evaluate("Math.max(...[...document.querySelectorAll('.trial-actions button,.reagent')].map(n=>n.getBoundingClientRect().bottom))")
        check(bottom <= page.viewport_size['height'], f'{tag}: representative ordinary building fits actual phone height ({bottom:.1f}px)')


def wrong_assertions(page, tag, expected_text, expected_marks, message_patterns=(), title_pattern=None, announce=True):
    expect(page.locator('.reaction.error')).to_be_visible()
    state = saved(page)
    data = current_diagnostic(page)
    d, assembled = data['diagnostic'], data['assembled']
    check(set(d) == {'code','title','message','problemBlockIds','missingLabels'}, f'{tag}: diagnostic has only the documented fields')
    check(assembled['text'] == expected_text and page.locator('#assembled-answer').text_content() == expected_text,
          f'{tag}: EXACT submitted text and intact spaces, without hidden duplicates')
    check(state['firstAnswer'] == expected_text and state['score'] == 0 and state['attempts'] == 1 and state['results'] == [],
          f'{tag}: first wrong answer is recorded verbatim with zero mark')
    expect(page.locator('.answer-preview.is-incorrect .answer-issue-tag')).to_have_text(d['title'])
    expect(page.locator('.reaction.error h3')).to_have_text(d['title'])
    expect(page.locator('.reaction.error .feedback-message')).to_have_text(d['message'])
    check(page.locator('.reaction.error').get_attribute('data-feedback-code') == d['code'], f'{tag}: reaction exposes actual diagnostic code')
    check(d['title'] not in ['Not quite. Try again.', 'Not correct yet.'], f'{tag}: issue label names the mistake rather than a generic failure')
    marks = page.locator('#assembled-answer mark.answer-error-part').all_text_contents()
    computed_marks = [part['text'] for part in assembled['parts'] if set(part['ids']).intersection(d['problemBlockIds'])]
    check(marks == computed_marks == expected_marks, f'{tag}: highlights ONLY the diagnosed assembled parts ({marks})')
    flagged = page.locator('.token-button.has-answer-error').evaluate_all('nodes=>nodes.map(n=>n.dataset.block)')
    check(set(flagged) == set(state['assembly']).intersection(d['problemBlockIds']), f'{tag}: only diagnosed selected IDs get token error styling')
    check(page.locator('.token-button, .reagent').evaluate_all('nodes=>nodes.every(n=>n.disabled)'), f'{tag}: selection remains locked until Retry')
    if title_pattern:
        check(re.search(title_pattern, d['title'], re.I), f'{tag}: title identifies the expected issue ({d["title"]})')
    for pattern in message_patterns:
        check(re.search(pattern, d['message'], re.I), f'{tag}: actionable message matches {pattern!r}: {d["message"]}')
    check(not re.search(r'Use .+ (?:to compare two things|for the top one in a group|in this gap)', d['message'], re.I),
          f'{tag}: actual wrong answer never falls back to generic correct-answer copy')
    for answer in state['questions'][0]['answers']:
        # A submitted double formation can already CONTAIN a valid phrase,
        # e.g. more faster than. It must stay verbatim; do not forbid its text.
        if answer.lower() not in expected_text.lower():
            check(answer.lower() not in page.locator('.reaction.error').inner_text().lower(), f'{tag}: full corrected phrase {answer!r} is not revealed before Give Up')
    expect(page.locator('.correct-recipe')).to_have_count(0)
    expect(page.locator('.shatter-word, #assembled-answer .sr-only, #assembled-answer [aria-hidden]')).to_have_count(0)
    if announce:
        expect(page.locator('#announcer')).to_contain_text(d['message'])
        check(True, f'{tag}: live announcement includes the actual diagnostic message')
    for node in page.locator('.answer-issue-tag, .answer-error-part, .feedback-message').all():
        m = node.evaluate(TEXT_METRICS)
        check(m['rects'] and not m['clipped'] and not m['hidden'], f'{tag}: issue label/error part/message is readable, not clipped')
    check(not any(key in state for key in ['diagnostic','problemBlockIds','missingLabels']), f'{tag}: diagnostic fields are not added to saved schema')
    check('<mark' not in json.dumps(state) and 'answer-error-part' not in json.dumps(state), f'{tag}: no feedback markup is stored')
    layout(page, tag)
    EVIDENCE['cases'].append({'tag': tag, 'text': expected_text, 'diagnostic': d, 'marks': marks})
    return data


CASES = [
    # module, id, slug, selected labels, exact text, marked parts, message patterns, title pattern
    ('adjectives','adj-073','missing-than',['better'],'better',[],[r'\bthan\b'],r'than'),
    ('adjectives','adj-024','unfinished-bigg',['the','big','g'],'the bigg',['bigg'],[r'-est',r'\bbigg\b',r'already|doubled|double'],r'ending'),
    ('adjectives','adj-023','missing-double-g',['big','-er','than'],'biger than',['biger'],[r'double|twice',r'\bg\b'],r'spelling|double'),
    ('adverbs','adv-001','extra-more',['more','fast','-er','than'],'more faster than',['more','faster'],[r'\bmore\b',r'Remove'],r'forms'),
    ('adverbs','adv-002','extra-most',['most','fast','-est'],'most fastest',['most','fastest'],[r'\bmost\b',r'Remove'],r'forms'),
    ('adjectives','adj-031','y-spelling',['easy','-er','than'],'easyer than',['easyer'],[r'\by\b',r'\bi\b|-ier'],r'spelling|y'),
    ('adverbs','adv-001','connector-order',['than','fast','-er'],'than faster',['than'],[r'\bthan\b',r'end|after'],r'order|than'),
    ('adjectives','adj-024','missing-article',['big','g','-est'],'biggest',[],[r'\bthe\b'],r'the|article'),
    ('adjectives','adj-043','long-word-ending',['interesting','-er','than'],'interestinger than',['interestinger'],[r'\bmore\b'],r'form|ending|long'),
    ('adjectives','adj-077','irregular-bad',['bad','-er','than'],'bader than',['bader'],[r'\bbad\b',r'\bworse\b'],r'irregular|form'),
    ('adjectives','adj-023','invalid-operation',['g','big','-er','than'],'[g] biger than',['[g]'],[r'straight after|after the base|before'],r'order|operation|letter'),
    ('adverbs','adv-081','extra-base-before-irregular',['badly','worse','than'],'badly worse than',['badly'],[r"Remove the extra 'badly' block"],r'extra'),
    ('adjectives','adj-031','actual-wrong-r-ending',['easy','-r','than'],'easyr than',['easyr'],[r'Use -ier, not -r'],r'y'),
    ('adjectives','adj-094','irregular-most-missing-the',['most'],'most',[],[r'Add the before'],r'the'),
]


def stable_motion(page, tag, mobile):
    data = current_diagnostic(page)
    exact = data['assembled']['text']
    for mode in ['no-preference', 'reduce']:
        page.emulate_media(reduced_motion=mode)
        page.wait_for_timeout(900)
        check(page.locator('#assembled-answer').text_content() == exact, f'{tag}/{mode}: submitted answer still exact after 900ms')
        styles = page.locator('#assembled-answer, #assembled-answer *').evaluate_all("nodes=>nodes.map(n=>({transform:getComputedStyle(n).transform,animation:getComputedStyle(n).animationName,opacity:getComputedStyle(n).opacity}))")
        check(all(s['transform'] == 'none' and float(s['opacity']) > 0 and not re.search('shatter|fragment|explod',s['animation'],re.I) for s in styles),
              f'{tag}/{mode}: no scattered letters, transform or disappearance')
        layout(page, f'{tag}/{mode}')
        screenshot(page, tag, mode)
    page.emulate_media(reduced_motion='no-preference')


def correct_case(page, tag, module, question_id, labels, expected_text, mobile):
    seed(page, module, question_id)
    ids = select(page, labels, mobile)
    activate(page.locator('[data-action="submit"]'), mobile)
    expect(page.locator('.reaction.success')).to_be_visible()
    check(page.locator('#assembled-answer').text_content() == expected_text, f'{tag}: exact correct preview')
    state = saved(page)
    check(state['score'] == 1 and state['results'][0]['mark'] == 1 and state['firstAnswer'] == expected_text, f'{tag}: accepted alternative earns its normal first-attempt mark')
    expect(page.locator('.answer-error-part, .answer-issue-tag, .has-answer-error')).to_have_count(0)
    if question_id == 'adj-073':
        expect(page.locator('.feedback-message')).to_have_text(GOOD)
        expect(page.locator('#announcer')).to_contain_text(GOOD)
        check(True, f'{tag}: concise good rule and purpose of than are exact')
    layout(page, tag)
    screenshot(page, tag, 'correct')
    screenshot(page, tag, 'correct', viewport=True)
    return ids


def score_and_reveal(page, tag, mobile):
    seed(page, 'adjectives', 'adj-024')
    select(page, ['the','big','g'], mobile)
    activate(page.locator('[data-action="submit"]'), mobile)
    first = saved(page)['firstAnswer']
    activate(page.locator('[data-action="retry"]'), mobile)
    expect(page.locator('.reaction, .answer-issue-tag, .answer-error-part, .has-answer-error')).to_have_count(0)
    activate(page.locator('[data-action="clear"]'), mobile)
    q = saved(page)['questions'][0]
    for block_id in q['correctSequences'][0]:
        activate(page.locator(f'[data-action="add-block"][data-block="{block_id}"]'), mobile)
    activate(page.locator('[data-action="submit"]'), mobile)
    state = saved(page)
    check(state['score'] == 0 and state['attempts'] == 2 and state['firstAnswer'] == first and state['results'][0]['mark'] == 0 and state['results'][0]['firstAnswer'] == first,
          f'{tag}: correct retry earns zero and preserves original first answer verbatim')
    snapshot = saved(page)
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('.reaction.success')).to_be_visible()
    check(saved(page) == snapshot, f'{tag}: correct retry reload preserves entire state, including stored feedback')
    seed(page, 'adjectives', 'adj-024')
    select(page, ['the','big','g'], mobile)
    activate(page.locator('[data-action="submit"]'), mobile)
    activate(page.locator('[data-action="give-up"]'), mobile)
    expect(page.locator('.reaction.success')).to_be_visible()
    expect(page.locator('.correct-recipe')).to_be_visible()
    check(page.locator('#assembled-answer').text_content() == 'the biggest', f'{tag}: Give Up alone reveals full corrected answer')
    state = saved(page)
    check(state['score'] == 0 and state['firstAnswer'] == 'the bigg' and state['results'][0]['gaveUp'] and state['results'][0]['mark'] == 0,
          f'{tag}: Give Up preserves the actual first answer and zero mark')
    screenshot(page, tag, 'give-up')


def legacy_snapshots(page, tag, mobile):
    for correct in [False, True]:
        labels = ['better','than'] if correct else ['better']
        fixture = seed(page, 'adjectives', 'adj-073', labels=labels, submit=True, legacy=True)
        before = saved(page)
        if correct:
            expect(page.locator('.reaction.success .feedback-message')).to_have_text(GOOD)
            check(page.locator('#assembled-answer').text_content() == 'better than', f'{tag}: old correct snapshot has unchanged exact answer')
        else:
            wrong_assertions(page, f'{tag}/old-wrong', 'better', [], [r'\bthan\b'], r'than', announce=False)
        check(OLD not in page.locator('.reaction').inner_text(), f'{tag}: old generic {"correct" if correct else "wrong"} feedback is refreshed for display')
        check(saved(page) == before == fixture['state'], f'{tag}: display refresh preserves ALL saved fields, first answers, results, score and schema')
        page.reload(wait_until='domcontentloaded')
        expect(page.locator('.reaction')).to_be_visible()
        check(saved(page) == before, f'{tag}: old feedback reload preserves full stored snapshot exactly')
        check(page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:best'))") == fixture['best'], f'{tag}: independent best records remain identical')
        screenshot(page, tag, 'legacy-correct' if correct else 'legacy-wrong')
    # Existing reports must likewise use current formation explanation without
    # rewriting result arrays, first answers, questions or independent records.
    page.goto(BASE + '?report-fixture=' + str(time.monotonic_ns()), wait_until='domcontentloaded')
    report = page.evaluate("""async () => {
      const {createExperiment,submitTrial,retryTrial,makeReport}=await import('./js/core.js');
      const bank=(await(await fetch('./data/adjectives-questions.json')).json()).questions;
      const q=bank.find(q=>q.id==='adj-073'),s=createExperiment('adjectives',[q]);
      s.assembly=[s.questions[0].blocks.find(b=>b.label==='better').id];submitTrial(s);retryTrial(s);
      s.assembly=s.questions[0].correctSequences[0];submitTrial(s);const r=makeReport(s);
      r.questions[0].explanation='Use better than to compare two things. Use better than in this gap.';
      localStorage.removeItem('kslo-grammar-lab:session');localStorage.setItem('kslo-grammar-lab:last-report',JSON.stringify(r));return r;
    }""")
    best = page.evaluate("localStorage.getItem('kslo-grammar-lab:best')")
    page.evaluate("history.replaceState(null,'','#report')")
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('.report-explanation')).to_contain_text(GOOD)
    check('Use better than to compare two things' not in page.locator('.report-explanation').inner_text(), f'{tag}: report displays current concise rule, not old generic explanation')
    check(page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:last-report'))") == report, f'{tag}: report render preserves entire stored report and result arrays')
    check(page.evaluate("localStorage.getItem('kslo-grammar-lab:best')") == best, f'{tag}: report refresh does not alter best records')
    screenshot(page, tag, 'legacy-report')


def run(engine, width, height, mobile):
    tag = f'{engine.name}-{width}x{height}'
    print(f'RUN {tag}: stable feedback, touch={mobile}', flush=True)
    browser = engine.launch(headless=True)
    context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=mobile, has_touch=mobile, reduced_motion='no-preference')
    page = context.new_page()
    page.on('pageerror', lambda error: EVIDENCE['errors'].append(str(error)))
    try:
        for module, qid, slug, labels, text, marks, patterns, title in CASES:
            seed(page, module, qid)
            if slug == 'extra-more':
                layout(page, f'{tag}/ordinary-building', building=True)
                screenshot(page, tag, 'ordinary-building', viewport=True)
            select(page, labels, mobile)
            activate(page.locator('[data-action="submit"]'), mobile)
            wrong_assertions(page, f'{tag}/{slug}', text, marks, patterns, title)
            if slug in ['unfinished-bigg', 'invalid-operation']:
                stable_motion(page, f'{tag}-{slug}', mobile)
            screenshot(page, tag, slug)
            if slug == 'unfinished-bigg':
                page.evaluate('window.scrollTo(0,0)')
                screenshot(page, tag, slug, viewport=True)
            baseline = saved(page)
            page.reload(wait_until='domcontentloaded')
            expect(page.locator('.reaction.error')).to_be_visible()
            check(saved(page) == baseline, f'{tag}/{slug}: wrong-state reload preserves full snapshot exactly')
        correct_case(page, tag + '-good', 'adjectives', 'adj-073', ['better','than'], 'better than', mobile)
        for labels in [['fast','-est'], ['the','fast','-est']]:
            text = 'fastest' if len(labels) == 2 else 'the fastest'
            correct_case(page, tag + '-optional-' + str(len(labels)), 'adverbs', 'adv-002', labels, text, mobile)
        # Opposite-degree suffixes are absent from new adaptive trays, but may
        # legitimately remain selected in compatible older snapshots.
        seed(page, 'adverbs', 'adv-001', labels=['fast','-est','than'])
        activate(page.locator('[data-action="submit"]'), mobile)
        wrong_assertions(page, tag + '/wrong-degree', 'fastest than', ['fastest'], [r'comparative|compare|-er'], r'degree|comparative|superlative')
        screenshot(page, tag, 'wrong-degree')
        score_and_reveal(page, tag, mobile)
        legacy_snapshots(page, tag, mobile)
        print(f'COMPLETE {tag}: {len(EVIDENCE["checks"])} cumulative passed assertions; {len(EVIDENCE["errors"])} observed issues', flush=True)
    except Exception:
        screenshot(page, tag, 'failure')
        raise
    finally:
        context.close()
        browser.close()


def main():
    try:
        with sync_playwright() as p:
            run(p.chromium, 1440, 1000, False)
            run(p.webkit, 360, 640, True)
            run(p.webkit, 360, 800, True)
        if EVIDENCE['errors']:
            raise AssertionError(f'{len(EVIDENCE["errors"])} runtime/layout observations failed; inspect {OUT / "results.json"}')
        check(True, 'no JavaScript runtime or layout errors')
    finally:
        (OUT / 'results.json').write_text(json.dumps(EVIDENCE, indent=2) + '\n')
    print(f'PASS {len(EVIDENCE["checks"])} focused answer-feedback assertions; {len(EVIDENCE["screenshots"])} screenshots. {OUT}', flush=True)


if __name__ == '__main__':
    main()
