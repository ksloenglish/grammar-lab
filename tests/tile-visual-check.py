"""Audit prepared adaptive trays; retain Home flask and module safeguards."""
import os
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('GRAMMAR_TEST_URL', 'http://127.0.0.1:3000/').rstrip('/') + '/'
OUT = Path('test-results/tile-final')
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    for engine, width in [(p.chromium, 1440), (p.webkit, 360)]:
        browser = engine.launch()
        page = browser.new_page(viewport={'width': width, 'height': 1000 if width == 1440 else 800})
        page.goto(BASE, wait_until='networkidle')
        expect(page.locator('.module-card')).to_have_count(2)
        assert page.locator('.module-symbol').count() == 0
        assert page.locator('.flask-svg').count() == 3
        page.locator('.lab-scene').screenshot(path=str(OUT / f'flasks-{width}.png'))
        page.locator('.modules-grid').screenshot(path=str(OUT / f'modules-{width}.png'))
        page.goto(BASE + '?module=adjectives&n=10', wait_until='networkidle')
        page.locator('[data-action="start"]').click()
        result = page.evaluate("""async () => {
          const {renderIngredients}=await import('./js/ingredients.js');
          const {prepareAdaptiveQuestion,adaptiveBlocks}=await import('./js/comparison-blocks.js');
          const banks=await Promise.all(['adjectives','adverbs'].map(async m=>(await(await fetch('./data/'+m+'-questions.json')).json()).questions));
          const host=document.querySelector('#reagent-tray');let checked=0, questions=0;const errors=[];
          const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
          for(const raw of banks.flat()){
            const question=prepareAdaptiveQuestion(raw);
            host.innerHTML=renderIngredients(question,question.blocks.map(b=>b.id),[],true,escape);
            const labels=[...host.querySelectorAll('.block-label')];
            if(labels[0]?.textContent!==question.base)errors.push({id:question.id,baseFirst:false});
            if(host.querySelector('h3,.ingredient-group-heading,.ingredient-category'))errors.push({id:question.id,categories:true});
            if(labels.length!==adaptiveBlocks(question,[]).length)errors.push({id:question.id,flatCount:false});
            for(const label of labels){
              const style=getComputedStyle(label),rect=label.getBoundingClientRect(),button=label.closest('button'),box=button.getBoundingClientRect();
              const minimum=innerWidth<=736?18:20;
              if(parseFloat(style.fontSize)<minimum||style.whiteSpace!=='nowrap'||rect.height>parseFloat(style.lineHeight)+1||rect.right>box.right+1||box.right>host.getBoundingClientRect().right+1||box.height<44||box.width<44)errors.push({id:question.id,label:label.textContent,height:rect.height,width:rect.width,target:box.height,font:style.fontSize});
              checked++;
            }
            const operation=host.querySelector('[data-block="'+question.blocks.find(b=>b.operation==='remove-final-y')?.id+'"]');
            if(/y$/i.test(question.base)){
              if(!operation||operation.querySelector('.block-label').textContent!=='y'||!getComputedStyle(operation,'::before').content.includes('✕')||operation.getBoundingClientRect().width>86)errors.push({id:question.id,operation:'missing compact cross-y'});
            }else if(operation)errors.push({id:question.id,operation:'unnecessary remove-y'});
            const doubling=question.blocks.find(b=>b.operation==='double-final-consonant');
            if(doubling){
              const tile=host.querySelector('[data-block="'+doubling.id+'"]');
              if(!tile||tile.querySelector('.block-label').textContent!==doubling.consonant||getComputedStyle(tile,'::before').content.includes('✕'))errors.push({id:question.id,operation:'doubling label/cross'});
            }
            questions++;
          }
          const reliable=prepareAdaptiveQuestion(banks[0].find(q=>q.base==='reliable'));
          host.innerHTML=renderIngredients(reliable,reliable.blocks.map(b=>b.id),[],true,escape);
          return{checked,questions,errors};
        }""")
        assert result['questions'] == 192, result
        assert not result['errors'], result['errors'][:5]
        page.locator('.tray-panel').screenshot(path=str(OUT / f'reliable-tray-{width}.png'))
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        (OUT / f'adaptive-labels-{width}.json').write_text(json.dumps(result, indent=2) + '\n')
        print(f'{engine.name}/{width}px: {result["checked"]} adaptive labels, 192 base-first flat trays, readable 44px targets and conditional operations. PASS')
        browser.close()
