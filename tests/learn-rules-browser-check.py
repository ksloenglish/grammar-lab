"""Learn-only audit: two modules x desktop Chromium/touch WebKit, fresh profiles.

Uses current JSON, native keyboard and public engine APIs; never edits app/banks.
GRAMMAR_TEST_URL may select a checked local server or public GitHub Pages URL.
Artifacts: ignored test-results/learn-rules/{results.json,run.log,screenshots/}.
"""
from __future__ import annotations
import copy
import json
import os
import traceback
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('GRAMMAR_TEST_URL', 'http://127.0.0.1:3000/').rstrip('/') + '/'
OUT = ROOT / 'test-results/learn-rules'
(OUT / 'screenshots').mkdir(parents=True, exist_ok=True)
RESULT = {'url': BASE, 'checks': [], 'cases': [], 'screenshots': [], 'errors': []}


def check(value, message):
    if not value:
        raise AssertionError(message)
    RESULT['checks'].append(message)


def layout(page, tag):
    check(page.evaluate('Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)<=innerWidth'), tag + ': no horizontal overflow')
    metrics = page.locator('.learn-intro,.learn-section p,.learn-form-row dt,.learn-form-value strong,.learn-recipes code,.learn-wrong,.learn-right').evaluate_all("""nodes=>nodes.filter(n=>n.getClientRects().length).map(n=>({text:n.textContent,font:parseFloat(getComputedStyle(n).fontSize),wordBreak:getComputedStyle(n).wordBreak,overflowWrap:getComputedStyle(n).overflowWrap,overflow:n.scrollWidth>n.clientWidth+1}))""")
    check(bool(metrics) and all(m['font'] >= 16 for m in metrics), tag + ': visible Learn body/form/recipe text at least 16px')
    check(all(m['wordBreak'] not in ['break-all'] and m['overflowWrap'] not in ['anywhere'] for m in metrics), tag + ': phrases wrap without breaking letters')
    check(all(not m['overflow'] for m in metrics), tag + ': Learn text fits its own containers')


def shot(page, tag, name, locator=None):
    path = OUT / 'screenshots' / f'{tag}-{name}.png'
    if locator is not None:
        locator.scroll_into_view_if_needed()
    else:
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
    page.screenshot(path=str(path), animations='disabled')
    RESULT['screenshots'].append(str(path))


SEED = """async module=>{
 const {createExperiment,submitTrial,advanceTrial,makeReport}=await import('./js/core.js');
 const bank=(await(await fetch('./data/'+module+'-questions.json')).json()).questions.slice(0,10);
 const state=createExperiment(module,bank);state.assembly=[...state.questions[0].correctSequences[0]];submitTrial(state);advanceTrial(state);
 const complete=createExperiment(module,bank);
 for(let i=0;i<10;i++){complete.assembly=[...complete.questions[complete.index].correctSequences[0]];submitTrial(complete);if(i<9)advanceTrial(complete);}
 const report=makeReport(complete),best={[module+':10']:{score:9,count:10,percentage:90,date:'2026-11-10'}};
 localStorage.setItem('kslo-grammar-lab:session',JSON.stringify(state));
 localStorage.setItem('kslo-grammar-lab:last-report',JSON.stringify(report));
 localStorage.setItem('kslo-grammar-lab:best',JSON.stringify(best));
 return {state,report,best};
}"""


def records(page):
    return page.evaluate("Object.fromEntries(['session','last-report','best'].map(k=>[k,JSON.parse(localStorage.getItem('kslo-grammar-lab:'+k))]))")


def audit(page, module, mobile, tag):
    page.goto(BASE, wait_until='domcontentloaded')
    expect(page.locator('.module-card')).to_have_count(2)
    fixture = page.evaluate(SEED, module)
    expected_records = {'session': fixture['state'], 'last-report': fixture['report'], 'best': fixture['best']}
    page.goto(BASE + '#learn/' + module, wait_until='domcontentloaded')
    expect(page.locator('.learn-intro')).to_be_visible()
    data = page.evaluate("async m=>(await(await fetch('./data/'+m+'-learn.json')).json())", module)
    check(data == json.loads((ROOT / f'site/data/{module}-learn.json').read_text()), tag + ': loaded fresh exact Learn JSON')
    expect(page.locator('h1')).to_have_text('Learn the rules.')
    expect(page.locator('section.learn-section')).to_have_count(6)
    extras = [(i, s) for i, s in enumerate(data['sections']) if s.get('extra')]
    expect(page.locator('details.learn-extra')).to_have_count(len(extras))
    check(all(not n.evaluate('(n)=>n.open') for n in page.locator('details.learn-extra').all()), tag + ': all extras initially closed')
    expect(page.locator('.learn-intro')).to_have_text(data['intro'])
    expect(page.locator('.learn-scope-note')).to_have_text(data['scopeNote'])
    expect(page.locator('.learn-source-note')).to_have_text(data['sourceNote'])
    expect(page.locator('.mini-question')).to_have_count(3)
    expect(page.locator('.learn-sidebar nav a[href^="#rule-"]')).to_have_count(len(data['sections']))
    layout(page, tag + '/initial')
    if mobile:
        shot(page, tag, 'first-page')
    for i, section in enumerate(data['sections']):
        target = page.locator(f'#rule-{i}')
        expect(target.locator('h2')).to_have_text(section['title'])
        if section.get('extra'):
            summary = target.locator('summary')
            expect(summary).to_contain_text('Extra reading')
            summary.scroll_into_view_if_needed()
            summary.focus()
            page.keyboard.press('Enter')
            check(target.evaluate('(n)=>n.open'), tag + f'/rule-{i}: native Enter opens details')
            page.keyboard.press('Space')
            check(not target.evaluate('(n)=>n.open'), tag + f'/rule-{i}: native Space closes details')
            page.keyboard.press('Space')
            check(target.evaluate('(n)=>n.open'), tag + f'/rule-{i}: native Space opens details')
        expect(target.locator(':scope > p' if not section.get('extra') else '.learn-extra-content > p').first).to_have_text(section['text'])
        for j, form in enumerate(section.get('forms', [])):
            row = target.locator('dl.learn-form-list > div.learn-form-row').nth(j)
            expect(row.locator('dt')).to_have_text(form['label'])
            expect(row.locator('dd .learn-form-value small')).to_have_text(['Comparative', 'Superlative'])
            expect(row.locator('dd strong')).to_have_text([form['comparative'], form['superlative']])
        expect(target.locator('.learn-recipes li')).to_have_text(section.get('recipes', []))
        for j, pair in enumerate(section.get('mistakes', [])):
            card = target.locator('.learn-mistakes li').nth(j)
            expect(card.locator('.learn-wrong b')).to_have_text('Not')
            expect(card.locator('.learn-right b')).to_have_text('Use')
            expect(card.locator('.learn-wrong')).to_have_text('Not ' + pair['wrong'])
            expect(card.locator('.learn-right')).to_have_text('Use ' + pair['right'])
        expect(target.locator('.example-list li')).to_have_text(section.get('examples', []))
        if section.get('note'):
            expect(target.locator('.rule-note')).to_have_text(section['note'])
        check(True, tag + f'/rule-{i}: complete authored text/forms/recipes/mistakes/examples shown')
        if mobile and i == next(k for k, s in enumerate(data['sections']) if s.get('forms')):
            shot(page, tag, 'forms', target.locator('.learn-form-list'))
        if mobile and module == 'adjectives' and '×y' in ''.join(section.get('recipes', [])):
            if not any('adjectives-xy-recipe' in p for p in RESULT['screenshots']):
                shot(page, tag, 'xy-recipe', target.locator('.learn-recipes'))
        if section.get('extra'):
            layout(page, tag + f'/extra-{i}')
            if mobile and i == extras[0][0]:
                shot(page, tag, 'extra-first', target)
            target.locator('summary').focus()
            page.keyboard.press('Enter')
            check(not target.evaluate('(n)=>n.open'), tag + f'/rule-{i}: closes before sidebar activation')
            page.locator(f'.learn-sidebar a[href="#rule-{i}"]').click()
            check(target.evaluate('(n)=>n.open'), tag + f'/rule-{i}: sidebar opens closed matching detail')
            check(page.evaluate('location.hash') == '#learn/' + module, tag + f'/rule-{i}: sidebar preserves Learn route')
            expect(target.locator('.example-list li').first).to_be_visible() if section.get('examples') else expect(target.locator('.learn-extra-content')).to_be_visible()
            target.locator('summary').focus()
            page.keyboard.press('Enter')
    for i, source in enumerate(data['sources']):
        link = page.locator('.learn-sources a').nth(i)
        expect(link).to_have_text(source['title'])
        expect(link).to_have_attribute('href', source['url'])
        expect(link).to_have_attribute('target', '_blank')
    experiment_links = page.locator('a[href="#setup/' + module + '"]')
    expect(experiment_links).to_have_count(2)
    for i, question in enumerate(data['miniCheck']):
        page.locator('.mini-question').nth(i).get_by_label(question['answer'], exact=True).check()
    page.get_by_role('button', name='Check my answers').click()
    expect(page.locator('#mini-result')).to_contain_text('3/3 correct')
    for i, question in enumerate(data['miniCheck']):
        expect(page.locator(f'#mini-feedback-{i}')).to_have_text('Correct. ' + question['explanation'])
    check(True, tag + ': all three mini answers score 3/3 with exact concise feedback')
    if mobile and module == 'adverbs':
        shot(page, tag, 'mini-result', page.locator('#mini-result'))
    check(records(page) == expected_records, tag + ': Learn checks preserve scored session, best 9/10 and last report')
    page.goto(BASE + '#learn/' + module, wait_until='domcontentloaded')
    expect(page.locator('.learn-intro')).to_be_visible()
    for i, question in enumerate(data['miniCheck']):
        expect(page.locator(f'input[name="mini-{i}"]:checked')).to_have_value(question['answer'])
    check(True, tag + ': savedChoices reload under existing Learn route and storage key')
    first = data['miniCheck'][0]
    wrong = next(x for x in first['options'] if x != first['answer'])
    page.locator('.mini-question').first.get_by_label(wrong, exact=True).check()
    page.get_by_role('button', name='Check my answers').click()
    expect(page.locator('#mini-result')).to_contain_text('2/3 correct')
    expect(page.locator('#mini-feedback-0.error')).to_have_text('Correct answer: ' + first['answer'] + '. ' + first['explanation'])
    check(True, tag + ': wrong choice gets actionable rule feedback without assessment score changes')
    page.locator('.learn-check-actions a').click()
    expect(page.locator('.trial-options')).to_be_visible()
    check(page.evaluate('location.hash') == '#setup/' + module, tag + ': Experiment opens module-scoped setup')
    check(records(page) == expected_records, tag + ': navigation preserves session, best and report')
    page.goto(BASE, wait_until='domcontentloaded')
    expect(page.locator('.module-card')).to_have_count(2)
    expect(page.locator('.learn-form-list,.learn-extra,.learn-recipes')).to_have_count(0)
    check(page.evaluate('Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)<=innerWidth'), tag + ': Home smoke has no overflow or Learn DOM')
    RESULT['cases'].append({'browser': 'webkit' if mobile else 'chromium', 'module': module, 'core': 6, 'extra': len(extras), 'miniChecks': 3, 'savedScore': fixture['state']['score'], 'best': 9})


def escaped_fields(browser):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    data = json.loads((ROOT / 'site/data/adjectives-learn.json').read_text())
    payload = '<b data-learn-probe="yes">Teacher text & symbols</b>'
    data['intro'] = data['scopeNote'] = data['sourceNote'] = payload
    section = data['sections'][0]
    section.update(title=payload, text=payload, note=payload, examples=[payload], recipes=[payload], forms=[{'label': payload, 'comparative': payload, 'superlative': payload}], mistakes=[{'wrong': payload, 'right': payload}])
    data['sources'][0]['title'] = payload
    page.route('**/adjectives-learn.json', lambda route: route.fulfill(json=data))
    page.goto(BASE + '#learn/adjectives', wait_until='domcontentloaded')
    expect(page.locator('.learn-intro')).to_have_text(payload)
    target = page.locator('#rule-0')
    for selector in ['h2', ':scope > p', '.rule-note', '.example-list li', '.learn-recipes li', '.learn-form-row dt']:
        expect(target.locator(selector).first).to_have_text(payload)
    expect(target.locator('.learn-form-row strong')).to_have_text([payload, payload])
    expect(page.locator('.learn-scope-note')).to_have_text(payload)
    expect(page.locator('.learn-source-note')).to_have_text(payload)
    expect(page.locator('.learn-sources a').first).to_have_text(payload)
    expect(page.locator('[data-learn-probe]')).to_have_count(0)
    check(not errors, 'author-controlled Learn fields remain plain text with no JavaScript errors')
    context.close()


def main():
    try:
        with sync_playwright() as p:
            for engine, mobile in [(p.chromium, False), (p.webkit, True)]:
                browser = engine.launch(headless=True)
                for module in ['adjectives', 'adverbs']:
                    context = browser.new_context(viewport={'width': 360 if mobile else 1440, 'height': 640 if mobile else 1000}, is_mobile=mobile, has_touch=mobile)
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    tag = ('phone' if mobile else 'desktop') + '-' + module
                    print('Checking ' + tag, flush=True)
                    audit(page, module, mobile, tag)
                    check(not errors, tag + ': no uncaught JavaScript errors')
                    context.close()
                if not mobile:
                    escaped_fields(browser)
                browser.close()
        RESULT['status'] = 'passed'
    except Exception as e:
        RESULT['status'] = 'failed'
        RESULT['errors'].append(str(e))
        traceback.print_exc()
    finally:
        RESULT['assertions'] = len(RESULT['checks'])
        (OUT / 'results.json').write_text(json.dumps(RESULT, indent=2) + '\n')
        print(json.dumps({'status': RESULT['status'], 'assertions': RESULT['assertions'], 'cases': len(RESULT['cases']), 'screenshots': len(RESULT['screenshots']), 'errors': RESULT['errors']}, indent=2), flush=True)
    if RESULT['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
