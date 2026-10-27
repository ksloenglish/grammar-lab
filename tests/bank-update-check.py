import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('GRAMMAR_TEST_URL', 'http://127.0.0.1:3000/')
results = []
with sync_playwright() as p:
    for engine in [p.chromium, p.webkit]:
        browser = engine.launch()
        page = browser.new_page()
        page.goto(BASE, wait_until='networkidle')
        expect(page.locator('.module-card')).to_have_count(2)
        page.evaluate("""async () => {
          localStorage.clear();
          const questions = (await (await fetch('./data/adjectives-questions.json')).json()).questions.slice(0,10);
          const old = {schema:1,moduleId:'adjectives',questions,count:10,index:0,score:0,results:[],assembly:[],trayOrder:questions[0].blocks.map(b=>b.id),attempts:0,firstAnswer:null,status:'building',practice:false};
          localStorage.setItem('kslo-grammar-lab:session',JSON.stringify(old));
          localStorage.setItem('kslo-grammar-lab:last-report',JSON.stringify({...old,results:[]}));
          localStorage.setItem('kslo-grammar-lab:best',JSON.stringify({'adjectives:10':{score:8,count:10,percentage:80,date:'2026-10-27'}}));
        }""")
        page.reload(wait_until='networkidle')
        expect(page.locator('.notice').first).to_contain_text('updated the questions')
        expect(page.locator('.resume-banner')).to_have_count(0)
        expect(page.locator('.best-chip').first).to_contain_text('best 8/10')
        state = page.evaluate("({old:JSON.parse(localStorage.getItem('kslo-grammar-lab:archive:session')),session:localStorage.getItem('kslo-grammar-lab:session'),report:localStorage.getItem('kslo-grammar-lab:last-report')})")
        assert state['old']['schema'] == 1 and state['session'] is None and state['report'] is None
        results.append(f'{engine.name}: old questions backed up; no unsafe resume; best 8/10 preserved')
        page.goto(BASE+'?module=adjectives&n=10',wait_until='networkidle')
        page.locator('[data-action="start"]').click()
        expect(page.locator('.sentence')).to_be_visible()
        assert 'than' not in page.locator('.sentence').inner_text().lower().split()
        assert page.locator('.reagent .block-label',has_text='-er').count() >= 1
        assert page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session')).schema") == 2
        results.append(f'{engine.name}: new bank starts with no supplied than and includes -er')
        browser.close()
Path('test-results').mkdir(exist_ok=True)
Path('test-results/bank-update-results.json').write_text(json.dumps(results,indent=2)+'\n')
for result in results: print('PASS',result)
