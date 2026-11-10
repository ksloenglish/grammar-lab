"""Noun-free bank migration on the real app; only isolated browser-local test data."""
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('GRAMMAR_TEST_URL', 'http://127.0.0.1:3000/').rstrip('/') + '/'
OUT = ROOT / 'test-results' / 'noun-bank-update'
OUT.mkdir(parents=True, exist_ok=True)
# Share the exact historical question with the Node regression; never substitute
# the new adj-089 for this same-schema fixture when the bank is regenerated.
fixture_source = (ROOT / 'tests' / 'noun-free-answers.test.js').read_text()
OLD_ADJ089 = json.loads(fixture_source.split('const OLD_ADJ089_JSON = String.raw`', 1)[1].split('`;', 1)[0])
checks = []
evidence = {'url': BASE, 'browsers': []}


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    checks.append(message)
    print('PASS', message, flush=True)


def saved(page):
    return page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session'))")


def store_state(page):
    return page.evaluate("""() => Object.fromEntries(
      ['session', 'last-report', 'archive:session', 'archive:last-report', 'best']
      .map(key => [key, JSON.parse(localStorage.getItem('kslo-grammar-lab:' + key))]))""")


def submit_sequence(page, sequence):
    for block_id in sequence:
        page.locator(f'[data-action="add-block"][data-block="{block_id}"]').click()
    page.locator('[data-action="submit"]').click()


with sync_playwright() as p:
    for engine_name, viewport in [('chromium', {'width': 1440, 'height': 1000}),
                                  ('webkit', {'width': 360, 'height': 800})]:
        browser = getattr(p, engine_name).launch(headless=True)
        context = browser.new_context(viewport=viewport)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: dialog.accept())
        label = f'{engine_name}/{viewport["width"]}px'
        try:
            page.goto(BASE, wait_until='networkidle')
            expect(page.locator('.module-card')).to_have_count(2)
            seeded = page.evaluate("""async fixture => {
              localStorage.clear();
              const { createExperiment } = await import('./js/core.js');
              const { QUESTION_SCHEMA } = await import('./js/question-context.js');
              const current = (await (await fetch('./data/adjectives-questions.json')).json()).questions;
              const questions = [fixture, ...current.filter(q => q.id !== fixture.id).slice(0, 9)];
              const old = createExperiment('adjectives', questions);
              old.assembly = [...fixture.correctSequences[0]];
              const results = questions.map((q, i) => ({ questionId:q.id,
                firstAnswer:i < 8 ? q.answers[0] : '(No answer)', finalAnswer:q.answers[0],
                mark:Number(i < 8), gaveUp:i >= 8 }));
              const oldReport = { schema:QUESTION_SCHEMA, moduleId:'adjectives', questions,
                results, count:10, score:8, percentage:80, practice:false,
                originalReport:null, finishedAt:'2026-11-10T12:00:00.000Z' };
              const best = {'adjectives:10':{score:8,count:10,percentage:80,date:'2026-11-10T12:00:00.000Z'}};
              localStorage.setItem('kslo-grammar-lab:session', JSON.stringify(old));
              localStorage.setItem('kslo-grammar-lab:last-report', JSON.stringify(oldReport));
              localStorage.setItem('kslo-grammar-lab:best', JSON.stringify(best));
              return { old, oldReport, best, schema:QUESTION_SCHEMA };
            }""", OLD_ADJ089)
            check(seeded['schema'] == seeded['old']['schema'] == seeded['oldReport']['schema'] == 2,
                  f'{label}: faulty experiment and coherent 8/10 report use unchanged schema 2')
            check(seeded['old']['questions'][0] == OLD_ADJ089 and seeded['old']['assembly'] == ['b0', 'b1', 'b2'],
                  f'{label}: seed preserves exact much / more tea than fixture and coherent tray')
            page.reload(wait_until='networkidle')
            expect(page.locator('.notice').first).to_contain_text('updated the questions')
            expect(page.locator('.notice').first).to_contain_text('start a new experiment')
            expect(page.locator('.resume-banner')).to_have_count(0)
            expect(page.locator('.best-chip').first).to_contain_text('best 8/10')
            state = store_state(page)
            check(state['session'] is None and state['last-report'] is None,
                  f'{label}: noun-bearing same-schema experiment and report excluded')
            check(state['archive:session'] == seeded['old'] and state['archive:last-report'] == seeded['oldReport'],
                  f'{label}: exact old experiment and full report archived locally')
            check(state['best'] == seeded['best'], f'{label}: independent best 8/10 retained byte-for-data')
            page.screenshot(path=str(OUT / f'{engine_name}-update-notice.png'), full_page=True)
            archived = state

            page.goto(BASE + '#report', wait_until='networkidle')
            expect(page.locator('.error-panel')).to_contain_text('No lab report yet')
            expect(page.locator('.report-item')).to_have_count(0)
            check('more tea than' not in page.locator('#app').inner_text(),
                  f'{label}: old noun-bearing report cannot be displayed as current')

            # Start using the actual current bank rather than an invented fixture.
            page.goto(BASE + '?module=adjectives&n=10', wait_until='networkidle')
            page.locator('[data-action="start"]').click()
            expect(page.locator('.sentence')).to_be_visible()
            initial = saved(page)
            check(initial['schema'] == 2 and initial['count'] == 10,
                  f'{label}: compatible experiment starts with unchanged schema and ten trials')
            current_issues = page.evaluate("""async () => {
              const { questionContextIssues } = await import('./js/question-context.js');
              const q = JSON.parse(localStorage.getItem('kslo-grammar-lab:session')).questions;
              return q.flatMap(question => questionContextIssues(question).map(issue => question.id+': '+issue));
            }""")
            check(not current_issues, f'{label}: every new trial has noun-free answers and ingredients')
            expect(page.locator('.notice')).to_have_count(0)

            # First submission earns one mark; correct retry earns zero.
            submit_sequence(page, initial['questions'][0]['correctSequences'][0])
            expect(page.locator('[data-action="next"]')).to_be_visible()
            check(saved(page)['score'] == 1, f'{label}: new first correct answer earns exactly one mark')
            page.locator('[data-action="next"]').click()
            second = saved(page)['questions'][1]
            wrong = next(block['id'] for block in second['blocks'] if block['label'] == 'than')
            submit_sequence(page, [wrong])
            expect(page.locator('[data-action="retry"]')).to_be_visible()
            page.locator('[data-action="retry"]').click()
            page.locator('[data-action="clear"]').click()
            submit_sequence(page, second['correctSequences'][0])
            expect(page.locator('[data-action="next"]')).to_be_visible()
            check(saved(page)['score'] == 1 and saved(page)['results'][1]['mark'] == 0,
                  f'{label}: later successful retry adds no first-attempt mark')
            page.locator('[data-action="next"]').click()
            third = saved(page)['questions'][2]
            partial = third['correctSequences'][0][0]
            page.locator(f'[data-action="add-block"][data-block="{partial}"]').click()
            before_reload = saved(page)
            check(before_reload['index'] == 2 and before_reload['assembly'] == [partial],
                  f'{label}: compatible unfinished assembly stored with two completed trials')
            page.reload(wait_until='networkidle')
            expect(page.locator('.sentence')).to_be_visible()
            after_reload = saved(page)
            check(after_reload == before_reload, f'{label}: compatible snapshot resumes without altering score, attempts, results or assembly')
            expect(page.locator('.trial-meta strong')).to_contain_text('Trial 3 of 10')
            expect(page.locator('.score-display strong')).to_contain_text('1')
            page.screenshot(path=str(OUT / f'{engine_name}-compatible-resumed.png'), full_page=True)

            # Home/Resume uses the same compatibility path and retains the record.
            page.locator('[data-route="home"]').first.click()
            expect(page.locator('#confirm-dialog')).to_be_visible()
            page.locator('#confirm-dialog [value="leave"]').click()
            expect(page.locator('.resume-banner')).to_contain_text('2 completed')
            expect(page.locator('.best-chip').first).to_contain_text('best 8/10')
            page.locator('[data-action="resume"]').click()
            expect(page.locator('.sentence')).to_be_visible()
            check(saved(page) == before_reload, f'{label}: explicit Resume also preserves compatible work and original best')
            page.locator('[data-action="clear"]').click()
            submit_sequence(page, [next(block['id'] for block in third['blocks'] if block['label'] == 'than')])
            page.locator('[data-action="give-up"]').click()
            expect(page.locator('[data-action="next"]')).to_be_visible()
            check(saved(page)['score'] == 1 and saved(page)['results'][2]['mark'] == 0,
                  f'{label}: Give Up adds zero after the resumed trial')
            page.locator('[data-action="next"]').click()
            for index in range(3, 10):
                question = saved(page)['questions'][index]
                submit_sequence(page, question['correctSequences'][0])
                expect(page.locator('[data-action="next"]')).to_be_visible()
                page.locator('[data-action="next"]').click()
            expect(page.locator('.report-score')).to_be_visible()
            expect(page.locator('.report-item')).to_have_count(10)
            final_state = store_state(page)
            report = final_state['last-report']
            check(report['score'] == 8 and report['percentage'] == 80 and [r['mark'] for r in report['results']] == [1, 0, 0, 1, 1, 1, 1, 1, 1, 1],
                  f'{label}: final 8/10 report preserves first-attempt-only marking')
            check(final_state['session'] is None and final_state['best'] == seeded['best'],
                  f'{label}: completed compatible work leaves independent old best 8/10 unchanged')
            check(final_state['archive:session'] == seeded['old'] and final_state['archive:last-report'] == seeded['oldReport'],
                  f'{label}: new work does not overwrite historical local backups')
            page.reload(wait_until='networkidle')
            expect(page.locator('.report-score')).to_be_visible()
            expect(page.locator('.report-score')).to_contain_text('80%')
            check(store_state(page)['last-report'] == report, f'{label}: compatible report survives reload with all scores preserved')
            check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'{label}: final report stays within viewport')
            check(not errors, f'{label}: no JavaScript runtime errors')
            page.screenshot(path=str(OUT / f'{engine_name}-compatible-report.png'), full_page=True)
            evidence['browsers'].append({'engine': engine_name, 'viewport': viewport, 'seeded': seeded,
                                         'archived': archived, 'before_reload': before_reload,
                                         'after_reload': after_reload, 'final': final_state, 'errors': errors})
        except Exception:
            page.screenshot(path=str(OUT / f'{engine_name}-failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()

evidence['checks'] = checks
(OUT / 'results.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(f'Passed {len(checks)} noun-bank-update checks across Chromium desktop and WebKit 360px.', flush=True)
