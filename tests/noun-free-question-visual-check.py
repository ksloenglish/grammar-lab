import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('GRAMMAR_TEST_URL', 'http://127.0.0.1:3000/')
OUT = Path('test-results/noun-free/question-visuals')
OUT.mkdir(parents=True, exist_ok=True)
IDS = ['adj-085', 'adj-087', 'adj-089', 'adj-091', 'adj-093', 'adj-095']
results = []
with sync_playwright() as p:
    for engine, width, height in [(p.chromium, 1440, 1000), (p.webkit, 360, 1100)]:
        browser = engine.launch()
        page = browser.new_page(viewport={'width': width, 'height': height}, reduced_motion='reduce')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        for question_id in IDS:
            page.goto(BASE, wait_until='networkidle')
            page.evaluate('''async id => {
                const {createExperiment} = await import('./js/core.js');
                const bank = (await (await fetch('./data/adjectives-questions.json')).json()).questions;
                const question = bank.find(q => q.id === id);
                const selected = [question, ...bank.filter(q => q.id !== id).slice(0, 9)];
                localStorage.clear();
                localStorage.setItem('kslo-grammar-lab:session', JSON.stringify(createExperiment('adjectives', selected)));
            }''', question_id)
            page.reload(wait_until='networkidle')
            page.locator('[data-action="resume"]').click()
            expect(page.locator('.sentence')).to_be_visible()
            state = page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session'))")
            question = state['questions'][state['index']]
            assert question['id'] == question_id
            assert question['base'] in {'good', 'bad', 'far'}
            assert set(question['answers']) <= {'better than', 'worse than', 'farther than', 'further than'}
            labels = page.locator('.reagent .block-label').all_inner_texts()
            assert not set(labels) & {'tea', 'rice', 'water', 'time', 'books', 'chairs'}, (question_id, labels)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), question_id
            page.screenshot(path=str(OUT / f'{engine.name}-{width}-{question_id}.png'))
            page.locator('.sentence').screenshot(path=str(OUT / f'{engine.name}-{width}-{question_id}-sentence.png'))
            results.append(f'{engine.name}/{width}px/{question_id}: replacement visible; no noun tiles; compatible resume and no overflow')
        assert not errors, errors
        browser.close()
(OUT / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
for result in results:
    print('PASS', result)
