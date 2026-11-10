"""Explicit final-y regression: real taps, all 22 affected questions and schema-2 history.

Run against the ordinary static server on port 3000. No app hooks or source edits.
The legacy metadata is constructed from fresh questions, NOT mutable git HEAD.
Evidence is saved beneath ignored test-results/explicit-y/.
"""
from __future__ import annotations
import importlib.util
import json
import os
import time
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('GRAMMAR_TEST_URL', 'http://127.0.0.1:3000/').rstrip('/') + '/'
OUT = ROOT / 'test-results/explicit-y'
OUT.mkdir(parents=True, exist_ok=True)
EVIDENCE = {'url': BASE, 'checks': [], 'cases': [], 'screenshots': [], 'errors': []}
AFFECTED = [('adjectives', f'adj-{n:03}') for n in range(31, 41)] + [('adverbs', f'adv-{n:03}') for n in range(37, 49)]
# Verified against efeba2ba296c16452964695027b973396dde82be before the fix.
# Exact old -ier/-iest base-key maps and interleaved explicit/direct recipes are
# recreated below, so publishing a new HEAD cannot invalidate the fixture.
LEGACY_REVISION = 'efeba2ba296c16452964695027b973396dde82be'
_spec = importlib.util.spec_from_file_location('explicit_y_metrics', ROOT / 'tests/home-ui-check.py')
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


def shot(page, tag, name):
    path = OUT / f'{tag}-{name}.png'
    page.evaluate("async()=>{await document.fonts.ready;document.activeElement?.blur();window.scrollTo({top:0,behavior:'instant'});await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame)}")
    page.screenshot(path=str(path), full_page=True, animations='disabled')
    EVIDENCE['screenshots'].append(str(path))


SEED = """async ({module,id,legacy=null,labels=null,report=false}) => {
 const {createExperiment,makeReport}=await import('./js/core.js');
 const bank=(await(await fetch('./data/'+module+'-questions.json')).json()).questions;
 const raw=bank.find(q=>q.id===id);if(!raw)throw Error('Missing question '+id);
 const s=createExperiment(module,[raw]),q=s.questions[0];
 const find=label=>{const b=q.blocks.find(b=>b.label===label);if(!b)throw Error('Missing '+label);return b.id;};
 const canonical=q.correctSequences.map(seq=>[...seq]);
 if(legacy){
   for(const b of q.blocks)if(b.kind==='suffix'&&['-ier','-iest'].includes(b.label))
     b.transforms={...b.transforms,[q.base]:q.base.slice(0,-1)+b.label.slice(1)};
   const operation=q.blocks.find(b=>b.operation==='remove-final-y').id;
   q.correctSequences=canonical.flatMap(seq=>[seq,seq.filter(id=>id!==operation)]);
 }
 if(labels)s.assembly=labels.map(find);
 if(legacy==='wrong'){s.status='wrong';s.attempts=1;s.firstAnswer='noisiest';s.feedback='Add the before noisiest.';}
 if(legacy==='correct'){
   s.status='correct';s.attempts=1;s.firstAnswer='the noisiest';s.score=1;s.feedback=q.explanation;
   s.results=[{questionId:q.id,firstAnswer:'the noisiest',finalAnswer:'the noisiest',mark:1,gaveUp:false}];
 }
 if(legacy==='corrupt')q.blocks.find(b=>b.label==='-iest').transforms[q.base]='arbitrary room';
 const best={'adjectives:10':{score:8,count:10,percentage:80,date:'2026-11-10'}};
 localStorage.clear();localStorage.setItem('kslo-grammar-lab:best',JSON.stringify(best));
 const r=report?makeReport(s):null;
 localStorage.setItem('kslo-grammar-lab:'+(report?'last-report':'session'),JSON.stringify(r||s));
 return {state:s,report:r,best,canonical};
}"""


def seed(page, module, qid, legacy=None, labels=None, report=False):
    # Navigate to Home first so the old document's pagehide cannot overwrite
    # the next fixture; imports use real public engine APIs only.
    page.goto(BASE + '?explicit-y=' + str(time.monotonic_ns()), wait_until='domcontentloaded')
    expect(page.locator('.module-card')).to_have_count(2)
    fixture = page.evaluate(SEED, {'module': module, 'id': qid, 'legacy': legacy, 'labels': labels, 'report': report})
    page.evaluate("route=>history.replaceState(null,'','#'+route)", 'report' if report else 'experiment')
    page.reload(wait_until='domcontentloaded')
    if legacy != 'corrupt':
        expect(page.locator('.report-item' if report else '.sentence')).to_be_visible()
    return fixture


def tap_ids(page, ids, mobile, action='add'):
    for block_id in ids:
        activate(page.locator(f'[data-action="{action}-block"][data-block="{block_id}"]'), mobile)


def ids_for(q, labels):
    return [next(b['id'] for b in q['blocks'] if b['label'] == label) for label in labels]


def diagnostic(page):
    return page.evaluate("""async()=>{const {assemble}=await import('./js/core.js');const {diagnoseAnswer}=await import('./js/feedback.js');
    const s=JSON.parse(localStorage.getItem('kslo-grammar-lab:session')),q=s.questions[s.index],a=assemble(q,s.assembly);
    return {assembled:a,diagnostic:diagnoseAnswer(q,a.text,s.assembly)};}""")


def layout(page, tag, empty=False):
    check(page.evaluate('Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)<=innerWidth'), tag+': no horizontal overflow')
    mobile = page.viewport_size['width'] == 360
    for node in page.locator('.reagent .block-label, .token-button').all():
        m = node.evaluate(TEXT_METRICS)
        check(m['fonts'] and min(m['fonts']) >= (18 if mobile else 20) and m['rects'] and not m['clipped'] and not m['hidden'], tag+': readable one-line tile '+m['text'])
    sizes = page.locator('.trial-actions button,.reagent,.token-button').evaluate_all('nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return [r.width,r.height]})')
    check(all(w >= 43.9 and h >= 43.9 for w,h in sizes), tag+': 44px controls')
    if empty and mobile:
        bottom = page.evaluate('Math.max(...[...document.querySelectorAll(".trial-actions button,.reagent")].map(n=>n.getBoundingClientRect().bottom))')
        check(bottom <= page.viewport_size['height'], f'{tag}: empty ordinary question fits {bottom:.1f}px')


def missing_y(page, tag, text, first=None):
    d = diagnostic(page)
    check(d['assembled']['text'] == text, tag+': literal y retained in engine')
    expect(page.locator('#assembled-answer')).to_have_text(text)
    expect(page.locator('.deleted-letter,.spelling-change')).to_have_count(0)
    check(all(not p.get('spellingChanges') for p in d['assembled']['parts']), tag+': no invented spelling trace')
    expect(page.locator('.reaction.error')).to_be_visible()
    expect(page.locator('.reaction.error h3')).to_have_text('Missing ×y')
    expect(page.locator('.answer-issue-tag')).to_have_text('Missing ×y')
    q = saved(page)['questions'][0]
    suffix = '-ier' if q['degree'] == 'comparative' else '-iest'
    hint = f'Add ×y after {q["base"]} and before {suffix} to remove the final y.'
    expect(page.locator('.reaction.error .feedback-message')).to_have_text(hint)
    stem_wrong = q['base'] + suffix[1:]
    expect(page.locator('#assembled-answer mark.answer-error-part')).to_have_text(stem_wrong)
    state = saved(page)
    check(state['score'] == 0 and state['attempts'] == 1 and state['results'] == [] and state['firstAnswer'] == (first or text), tag+': exact first wrong answer and zero score preserved')
    check(d['diagnostic']['title'] == 'Missing ×y' and d['diagnostic']['message'] == hint, tag+': current actual diagnostic')
    EVIDENCE['cases'].append({'tag': tag, 'text': text, 'diagnostic': d['diagnostic']})


def all_questions(page, tag, mobile):
    for module, qid in AFFECTED:
        fixture = seed(page, module, qid)
        q = saved(page)['questions'][0]
        layout(page, tag+'/'+qid, empty=True)
        operation = next(b['id'] for b in q['blocks'] if b.get('operation') == 'remove-final-y')
        # Every accepted form, including optional-the early superlatives.
        for seq_index, sequence in enumerate(fixture['canonical']):
            if seq_index:
                seed(page, module, qid)
            check(operation in sequence, tag+'/'+qid+': canonical includes explicit ×y')
            tap_ids(page, sequence, mobile)
            activate(page.locator('[data-action="submit"]'), mobile)
            expect(page.locator('.reaction.success')).to_be_visible()
            state = saved(page)
            check(state['score'] == 1 and state['results'][0]['mark'] == 1 and state['firstAnswer'] in q['answers'], tag+'/'+qid+': accepted canonical first answer earns one')
            EVIDENCE['cases'].append({'tag':tag+'/'+qid,'kind':'canonical','text':state['firstAnswer']})
            if qid == 'adj-036':
                expect(page.locator('.deleted-letter')).to_have_text('y')
                shot(page, tag, 'noisy-explicit-correct')
        seed(page, module, qid)
        direct = [block_id for block_id in fixture['canonical'][0] if block_id != operation]
        tap_ids(page, direct, mobile)
        literal = ('the ' if q['degree'] == 'superlative' and q['answers'][0].startswith('the ') else '') + q['base'] + ('ier than' if q['degree'] == 'comparative' else 'iest')
        expect(page.locator('#assembled-answer')).to_have_text(literal)
        expect(page.locator('.deleted-letter,.spelling-change')).to_have_count(0)
        activate(page.locator('[data-action="submit"]'), mobile)
        missing_y(page, tag+'/'+qid+'/direct', literal)
        if qid == 'adj-036':
            shot(page, tag, 'noisy-with-the-missing-y')
    print(f'COMPLETE {tag}: all 22 explicit canonical/direct variants', flush=True)


def teacher_and_retry(page, tag, mobile):
    seed(page, 'adjectives', 'adj-036')
    q = saved(page)['questions'][0]
    base, op, suffix, article = ids_for(q, ['noisy','Remove y','-iest','the'])
    tap_ids(page, [base,suffix], mobile)
    expect(page.locator('#assembled-answer')).to_have_text('noisyiest')
    expect(page.locator('.deleted-letter,.spelling-change')).to_have_count(0)
    shot(page, tag, 'teacher-noisy-direct-preview')
    activate(page.locator('[data-action="submit"]'), mobile)
    missing_y(page, tag+'/teacher-without-the', 'noisyiest')
    layout(page, tag+'/teacher-wrong')
    shot(page, tag, 'teacher-noisy-missing-y-wrong')
    activate(page.locator('[data-action="retry"]'), mobile)
    tap_ids(page, [suffix], mobile, 'return')
    tap_ids(page, [op], mobile)
    expect(page.locator('#assembled-answer')).to_have_text('nois')
    expect(page.locator('.deleted-letter')).to_have_text('y')
    shot(page, tag, 'noisy-explicit-y-stem')
    tap_ids(page, [suffix], mobile)
    expect(page.locator('#assembled-answer')).to_have_text('noisiest')
    # Add the article at the beginning only via returning/re-adding ingredients.
    tap_ids(page, [base,op,suffix], mobile, 'return')
    tap_ids(page, [article,base,op,suffix], mobile)
    activate(page.locator('[data-action="submit"]'), mobile)
    expect(page.locator('.reaction.success')).to_be_visible()
    state = saved(page)
    check(state['score'] == 0 and state['attempts'] == 2 and state['firstAnswer'] == 'noisyiest' and state['results'][0]['firstAnswer'] == 'noisyiest' and state['results'][0]['mark'] == 0, tag+': teacher tap-only correct retry keeps literal first answer and zero mark')
    expect(page.locator('#assembled-answer')).to_have_text('the noisiest')
    shot(page, tag, 'teacher-noisy-retry-correct')
    activate(page.locator('[data-action="next"]'), mobile)
    expect(page.locator('.report-item')).to_be_visible()
    expect(page.locator('.answer-value').first).to_have_text('noisyiest')
    check(page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:last-report')).score") == 0, tag+': fresh report preserves retry zero')
    seed(page, 'adjectives', 'adj-035')
    q = saved(page)['questions'][0]
    base, op, suffix, than = ids_for(q, ['noisy','Remove y','-ier','than'])
    tap_ids(page, [base,suffix,than], mobile)
    activate(page.locator('[data-action="submit"]'), mobile)
    missing_y(page, tag+'/comparative', 'noisyier than')
    activate(page.locator('[data-action="retry"]'), mobile)
    tap_ids(page, [suffix,than], mobile, 'return')
    tap_ids(page, [op,suffix,than], mobile)
    activate(page.locator('[data-action="submit"]'), mobile)
    expect(page.locator('.reaction.success')).to_be_visible()
    state = saved(page)
    check(state['score'] == 0 and state['firstAnswer'] == 'noisyier than' and state['results'][0]['mark'] == 0, tag+': comparative retry preserves first answer/zero')


def legacy_cases(page, tag):
    for status in ['pending','wrong','correct']:
        labels = ['the','noisy','-iest'] if status == 'correct' else ['noisy','-iest']
        fixture = seed(page, 'adjectives', 'adj-036', legacy=status, labels=labels)
        state = saved(page)
        original = fixture['state']
        for key in ['schema','status','score','attempts','results','firstAnswer','startedAt']:
            check(state[key] == original[key], tag+'/legacy-'+status+': '+key+' retained')
        check(page.evaluate("localStorage.getItem('kslo-grammar-lab:archive:session')") is None, tag+'/legacy-'+status+': valid schema 2 not archived')
        check(page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:best'))") == fixture['best'], tag+'/legacy-'+status+': independent best retained')
        if status == 'correct':
            expect(page.locator('.reaction.success')).to_be_visible()
            if state['assembly'] != original['assembly'] or page.locator('#assembled-answer').text_content() != 'the noisyiest':
                expect(page.locator('.chamber-panel > .mark-note')).to_contain_text('Previously checked answer')
                check('canonical' in page.locator('#assembly-zone').get_attribute('aria-label').lower(), tag+': old correct canonical display explicitly labelled')
            check('first answer' in page.locator('body').inner_text().lower(), tag+': historical grade visibly retained')
        else:
            check(state['assembly'] == original['assembly'], tag+'/legacy-'+status+': selected IDs unchanged, no automatic operation')
            expect(page.locator('#assembled-answer')).to_have_text('noisyiest')
            expect(page.locator('.deleted-letter,.spelling-change')).to_have_count(0)
            if status == 'wrong':
                missing_y(page, tag+'/legacy-wrong', 'noisyiest', first='noisiest')
        before = saved(page)
        # Loading upgrades in memory; pagehide may persist only that sanctioned
        # metadata change. Compare with the real public pure upgrader, then
        # require the next reload to be completely stable.
        upgraded = page.evaluate("async state=>{const {upgradeAdaptiveSession}=await import('./js/comparison-blocks.js');return upgradeAdaptiveSession(state);}", before)
        page.reload(wait_until='domcontentloaded')
        expect(page.locator('.sentence')).to_be_visible()
        check(saved(page) == upgraded, tag+'/legacy-'+status+': pagehide persists only sanctioned metadata normalization')
        page.reload(wait_until='domcontentloaded')
        expect(page.locator('.sentence')).to_be_visible()
        check(saved(page) == upgraded, tag+'/legacy-'+status+': normalised reload is idempotent')
        shot(page, tag, 'legacy-'+status)
    fixture = seed(page, 'adjectives', 'adj-036', legacy='correct', labels=['the','noisy','-iest'], report=True)
    report = page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:last-report'))")
    for key in ['schema','score','count','percentage','results','finishedAt']:
        check(report[key] == fixture['report'][key], tag+'/legacy-report: '+key+' retained')
    expect(page.locator('.answer-value').first).to_have_text('the noisiest')
    check(page.evaluate("localStorage.getItem('kslo-grammar-lab:archive:last-report')") is None, tag+': valid historical report not archived')
    check(page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:best'))") == fixture['best'], tag+': old report independent best retained')
    shot(page, tag, 'legacy-report')
    fixture = seed(page, 'adjectives', 'adj-036', legacy='corrupt', labels=['noisy','-iest'])
    expect(page.locator('.module-card')).to_have_count(2)
    check(page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:archive:session'))") == fixture['state'], tag+': arbitrary transform remains rejectable and archived unchanged')
    check(page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:best'))") == fixture['best'], tag+': corrupt archive preserves best')


def main():
    try:
        with sync_playwright() as p:
            for engine, width, height, mobile in [(p.chromium,1440,1000,False),(p.webkit,360,640,True)]:
                tag = f'{engine.name}-{width}x{height}'
                print('RUN '+tag, flush=True)
                browser = engine.launch(headless=True)
                context = browser.new_context(viewport={'width':width,'height':height},is_mobile=mobile,has_touch=mobile)
                page = context.new_page()
                page.on('pageerror', lambda error: EVIDENCE['errors'].append(str(error)))
                try:
                    all_questions(page,tag,mobile)
                    teacher_and_retry(page,tag,mobile)
                    legacy_cases(page,tag)
                    print(f'PASS {tag}: {len(EVIDENCE["checks"])} cumulative checks', flush=True)
                except Exception:
                    shot(page,tag,'failure')
                    raise
                finally:
                    context.close()
                    browser.close()
        check(not EVIDENCE['errors'], 'no browser runtime errors')
    finally:
        (OUT/'results.json').write_text(json.dumps(EVIDENCE,indent=2)+'\n')
    print(f'PASS {len(EVIDENCE["checks"])} checks; {len(EVIDENCE["cases"])} cases; {len(EVIDENCE["screenshots"])} screenshots. {OUT}',flush=True)


if __name__ == '__main__':
    main()
