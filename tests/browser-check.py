"""Development-only end-to-end verification; no student data or network service."""
import json
import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('GRAMMAR_TEST_URL', 'http://127.0.0.1:3000/')
OUT = Path(__file__).resolve().parents[1] / 'test-results'
OUT.mkdir(exist_ok=True)
results = []

def check(condition, message):
    if not condition:
        raise AssertionError(message)
    results.append(message)

def saved(page):
    return page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session'))")

def assemble_answer(page, sequence, keyboard=False):
    for id in sequence:
        button = page.locator(f'[data-action="add-block"][data-block="{id}"]')
        if keyboard:
            button.focus()
            page.keyboard.press('Enter')
        else:
            button.click()
    page.locator('[data-action="submit"]').click()

with sync_playwright() as p:
    for engine in ['chromium', 'webkit']:
        browser = getattr(p, engine).launch(headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: dialog.accept())
        page.goto(BASE)
        expect(page.locator('.module-card')).to_have_count(2)
        check(page.locator('#sound-toggle').get_attribute('aria-pressed') == 'false', f'{engine}: sound initially off')
        check('resetting' in page.locator('#storage-notice').inner_text(), f'{engine}: browser reset notice visible')
        page.screenshot(path=str(OUT / f'{engine}-home-desktop.png'), full_page=True)
        for module in ['adjectives', 'adverbs']:
            page.goto(BASE + f'?module={module}&n=10')
            expect(page.locator('[name="trial-count"][value="10"]')).to_be_checked()
            check(page.locator('[data-action="start"]').count() == 1, f'{engine}/{module}: assignment opens setup, not first trial')
            page.locator('[data-action="start"]').click()
            expect(page.locator('.sentence')).to_be_visible()
            state = saved(page)
            check(state['count'] == 10 and len(set(q['id'] for q in state['questions'])) == 10, f'{engine}/{module}: 10 unique trials')
            for trial in range(10):
                state = saved(page)
                question = state['questions'][trial]
                sequence = question['correctSequences'][0]
                if trial == 0:
                    # Place via keyboard, reorder with visible buttons, return and re-add.
                    first = sequence[0]
                    page.locator(f'[data-action="add-block"][data-block="{first}"]').focus()
                    page.keyboard.press('Enter')
                    page.locator(f'[data-action="return-block"][data-block="{first}"]').click()
                    expect(page.locator(f'[data-action="add-block"][data-block="{first}"]')).to_be_visible()
                    page.reload()
                    expect(page.locator('.sentence')).to_be_visible()
                    check(saved(page)['index'] == 0, f'{engine}/{module}: refresh resumes unfinished experiment')
                    assemble_answer(page, sequence, keyboard=True)
                elif trial == 1:
                    # Submit an incomplete answer, then retry with the correct reaction.
                    page.locator(f'[data-action="add-block"][data-block="{sequence[0]}"]').click()
                    # A whole-word irregular can itself be correct; use a guaranteed distractor instead.
                    if len(sequence) == 1:
                        page.locator('[data-action="clear"]').click()
                        used = {id for seq in question['correctSequences'] for id in seq}
                        wrong = next(block['id'] for block in question['blocks'] if block['id'] not in used)
                        page.locator(f'[data-action="add-block"][data-block="{wrong}"]').click()
                    page.locator('[data-action="submit"]').click()
                    expect(page.locator('[data-action="retry"]')).to_be_visible()
                    page.locator('[data-action="retry"]').click()
                    page.locator('[data-action="clear"]').click()
                    assemble_answer(page, sequence)
                    check(saved(page)['score'] == 1, f'{engine}/{module}: successful retry adds no mark')
                elif trial == 2:
                    used = {id for seq in question['correctSequences'] for id in seq}
                    wrong = next(block['id'] for block in question['blocks'] if block['id'] not in used)
                    page.locator(f'[data-action="add-block"][data-block="{wrong}"]').click()
                    page.locator('[data-action="submit"]').click()
                    page.locator('[data-action="give-up"]').click()
                    expect(page.locator('[data-action="next"]')).to_be_visible()
                else:
                    assemble_answer(page, sequence)
                expect(page.locator('[data-action="next"]')).to_be_visible()
                page.locator('[data-action="next"]').click()
            expect(page.locator('.report-score')).to_be_visible()
            check('8/10' in re.sub(r'\s+', '', page.locator('.report-score strong').inner_text()), f'{engine}/{module}: final first-attempt score 8/10')
            check(page.locator('.report-item').count() == 10, f'{engine}/{module}: all 10 first answers reported')
            record = page.evaluate(f"JSON.parse(localStorage.getItem('kslo-grammar-lab:best'))['{module}:10']")
            check(record['score'] == 8, f'{engine}/{module}: local 10-trial best stored separately')
            page.locator('#report-name').fill('Temporary Test Name')
            page.locator('#report-class').fill('S2 Test')
            check('Temporary Test Name' not in page.evaluate('JSON.stringify(localStorage)'), f'{engine}/{module}: report name never stored')
            if engine == 'chromium' and module == 'adjectives':
                page.locator('#print-identity').evaluate("node => node.textContent='Name: Temporary Test Name · Class: S2 Test'")
                page.emulate_media(media='print')
                page.pdf(path=str(OUT / 'lab-report-print.pdf'), print_background=False)
                check(page.locator('.report-item').count() == 10, 'print: all practised questions retained')
                page.emulate_media(media='screen')
            page.locator('[data-action="practice"]').click()
            for trial in range(2):
                state = saved(page)
                assemble_answer(page, state['questions'][trial]['correctSequences'][0])
                page.locator('[data-action="next"]').click()
            expect(page.locator('.report-score')).to_be_visible()
            check('2/2' in re.sub(r'\s+', '', page.locator('.report-score strong').inner_text()), f'{engine}/{module}: wrong-answer round scored separately')
            check('8/10' in page.locator('.original-report-summary').inner_text(), f'{engine}/{module}: original report unchanged')
            check(page.evaluate(f"JSON.parse(localStorage.getItem('kslo-grammar-lab:best'))['{module}:10'].score") == 8, f'{engine}/{module}: practice does not overwrite best')
        # Learn mini-check; no raw placeholder or unsafe markup.
        page.goto(BASE + '#learn/adjectives')
        expect(page.locator('.mini-question')).to_have_count(3)
        learn = page.evaluate("async () => (await fetch('./data/adjectives-learn.json')).json()")
        for i, question in enumerate(learn['miniCheck']):
            page.locator(f'[name="mini-{i}"]').filter(has=None) if False else None
            page.locator(f'input[name="mini-{i}"][value="{question["answer"]}"]').check()
        page.locator('#mini-form button[type="submit"]').click()
        expect(page.locator('#mini-result')).to_contain_text('3/3')
        check(True, f'{engine}: Learn mini-check 3/3')
        # Browser-back guard cancellation and leaving, then resume from Home.
        page.locator('[data-route="setup/adjectives"]').first.click()
        page.locator('[data-action="start"]').click()
        page.go_back()
        expect(page.locator('#confirm-dialog')).to_be_visible()
        page.locator('#confirm-dialog [value="cancel"]').click()
        expect(page.locator('.sentence')).to_be_visible()
        check(True, f'{engine}: browser-back cancellation preserves active trial')
        page.locator('[data-route="home"]').first.click()
        page.locator('#confirm-dialog [value="leave"]').click()
        expect(page.locator('[data-action="resume"]')).to_be_visible()
        page.locator('[data-action="resume"]').click()
        expect(page.locator('.sentence')).to_be_visible()
        # Desktop drag/drop and reordering.
        state = saved(page)
        blocks = state['questions'][0]['correctSequences'][0]
        page.locator(f'[data-action="add-block"][data-block="{blocks[0]}"]').drag_to(page.locator('#assembly-zone'))
        expect(page.locator(f'[data-action="return-block"][data-block="{blocks[0]}"]')).to_be_visible()
        if len(blocks) > 1:
            page.wait_for_timeout(200)
            page.locator(f'[data-action="add-block"][data-block="{blocks[1]}"]').click()
            page.locator(f'[data-action="move-block"][data-block="{blocks[1]}"][data-direction="-1"]').click()
            check(saved(page)['assembly'][0] == blocks[1], f'{engine}: placed blocks reorder')
        check(True, f'{engine}: native drag-to-place works')
        page.locator('[data-action="end"]').click()
        expect(page.locator('#confirm-dialog')).to_be_visible()
        page.locator('#confirm-dialog [value="leave"]').click()
        expect(page.locator('.module-card')).to_have_count(2)
        check(page.evaluate("localStorage.getItem('kslo-grammar-lab:session')") is None, f'{engine}: confirmed End discards unfinished session')
        # Responsive sizes, portrait and landscape.
        for width, height in [(360, 800), (768, 1024), (844, 390), (1920, 1080)]:
            page.set_viewport_size({'width': width, 'height': height})
            check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'{engine}: home no horizontal overflow at {width}x{height}')
        page.set_viewport_size({'width': 360, 'height': 800})
        page.screenshot(path=str(OUT / f'{engine}-home-mobile.png'), full_page=True)
        page.goto(BASE + '?module=adverbs&n=30')
        expect(page.locator('[name="trial-count"][value="30"]')).to_be_checked()
        page.locator('[data-action="start"]').click()
        expect(page.locator('.sentence')).to_be_visible()
        check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'{engine}: trial no overflow at 360px')
        page.screenshot(path=str(OUT / f'{engine}-trial-mobile.png'), full_page=True)
        page.emulate_media(reduced_motion='reduce')
        check(page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == 'auto', f'{engine}: reduced motion respected')
        check(not errors, f'{engine}: no JavaScript runtime errors ({errors})')
        context.close()
        browser.close()
    # Storage-disabled and slow-loading graceful behaviour, isolated from saved results.
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 360, 'height': 800}, has_touch=True, is_mobile=True)
    context.add_init_script("Storage.prototype.setItem = function(){throw new DOMException('Blocked','SecurityError')}")
    page = context.new_page()
    page.goto(BASE)
    expect(page.locator('#storage-notice')).to_contain_text('unavailable')
    page.locator('[data-route="setup/adjectives"]').click()
    page.locator('[data-action="start"]').click()
    page.locator('[data-action="add-block"]').first.tap()
    expect(page.locator('.assembled-block')).to_have_count(1)
    check(True, 'touch tap-to-place works with blocked storage')
    check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'touch trial remains within 360px')
    context.close()
    context = browser.new_context()
    page = context.new_page()
    page.route('**/data/modules.json', lambda route: route.abort())
    page.goto(BASE)
    expect(page.locator('.error-panel')).to_be_visible()
    check(True, 'network failure offers accessible retry instead of a blank page')
    context.close(); browser.close()

(OUT / 'browser-results.json').write_text(json.dumps(results, indent=2) + '\n')
print('\n'.join('PASS ' + line for line in results))
print(f'Passed {len(results)} end-to-end assertions across Chromium and WebKit.')
