import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE=os.environ.get('GRAMMAR_TEST_URL','http://127.0.0.1:3000/')
OUT=Path('test-results/y-change');OUT.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
    for engine,tag,width in [(p.chromium,'desktop',1440),(p.webkit,'phone',360)]:
        browser=engine.launch()
        page=browser.new_page(viewport={'width':width,'height':1000 if width==1440 else 800})
        page.goto(BASE,wait_until='networkidle')
        expect(page.locator('.module-card')).to_have_count(2)
        ids=page.evaluate("""async () => {
          const {createExperiment}=await import('./js/core.js');
          const bank=(await (await fetch('./data/adjectives-questions.json')).json()).questions;
          const question=bank.find(q=>q.base==='happy'&&q.degree==='comparative');
          const session=createExperiment('adjectives',[question,...bank.filter(q=>q.id!==question.id).slice(0,9)]);
          localStorage.setItem('kslo-grammar-lab:session',JSON.stringify(session));
          return {base:question.blocks.find(b=>b.label==='happy').id,operation:question.blocks.find(b=>b.kind==='operation').id,suffix:question.blocks.find(b=>b.label==='-ier').id,than:question.blocks.find(b=>b.label==='than').id};
        }""")
        page.goto(BASE+'#experiment',wait_until='networkidle')
        page.reload(wait_until='networkidle')
        expect(page.locator('.sentence')).to_be_visible()
        operation=page.locator(f'[data-action="add-block"][data-block="{ids["operation"]}"]')
        cross=operation.evaluate("node=>({content:getComputedStyle(node,'::after').content,colour:getComputedStyle(node,'::after').color})")
        assert '✕' in cross['content'] and cross['colour']=='rgb(181, 45, 66)',cross
        page.locator(f'[data-action="add-block"][data-block="{ids["base"]}"]').click()
        operation.click()
        expect(page.locator('#assembled-answer')).to_have_text('happ')
        expect(page.locator('.deleted-letter')).to_have_text('y')
        page.locator('.chamber-panel').screenshot(path=str(OUT/f'{tag}-removed-y.png'))
        page.locator(f'[data-action="add-block"][data-block="{ids["suffix"]}"]').click()
        expect(page.locator('.spelling-word.completed')).to_have_text('happier')
        page.locator(f'[data-action="add-block"][data-block="{ids["than"]}"]').click()
        expect(page.locator('#assembled-answer')).to_have_text('happier than')
        page.locator('.chamber-panel').screenshot(path=str(OUT/f'{tag}-happier.png'))
        page.locator('[data-action="submit"]').click()
        expect(page.locator('.reaction.success')).to_be_visible()
        assert page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session')).score")==1
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.emulate_media(reduced_motion='reduce')
        assert float(page.locator('.deleted-letter').evaluate("node=>getComputedStyle(node).animationDuration").replace('s',''))<=0.001
        results.append(f'{engine.name}/{width}px: red cross, visible removed y and stem, happier than, +1 first mark, reduced motion and no overflow PASS')
        browser.close()
Path('test-results/y-change-results.json').write_text(json.dumps(results,indent=2)+'\n')
for result in results:print(result)
