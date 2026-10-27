import os,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
BASE=os.environ.get('GRAMMAR_TEST_URL','http://127.0.0.1:3000/')
OUT=Path('test-results/tile-final');OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 for engine,width in [(p.chromium,1440),(p.webkit,360)]:
  browser=engine.launch();page=browser.new_page(viewport={'width':width,'height':1000 if width==1440 else 800})
  page.goto(BASE,wait_until='networkidle');expect(page.locator('.module-card')).to_have_count(2)
  assert page.locator('.module-symbol').count()==0
  assert page.locator('.flask-svg').count()==3
  page.locator('.lab-scene').screenshot(path=str(OUT/f'flasks-{width}.png'))
  page.locator('.modules-grid').screenshot(path=str(OUT/f'modules-{width}.png'))
  page.goto(BASE+'?module=adjectives&n=10',wait_until='networkidle');page.locator('[data-action="start"]').click()
  result=page.evaluate("""async () => {
   const {renderIngredients}=await import('./js/ingredients.js');
   const banks=await Promise.all(['adjectives','adverbs'].map(async m=>(await(await fetch('./data/'+m+'-questions.json')).json()).questions));
   const host=document.querySelector('#reagent-tray'),original=host.innerHTML;let checked=0;const errors=[];
   for(const question of banks.flat()){
    host.innerHTML=renderIngredients(question,question.blocks.map(b=>b.id),[],true,s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'));
    for(const label of host.querySelectorAll('.block-label')){
     const style=getComputedStyle(label),rect=label.getBoundingClientRect(),button=label.closest('button'),box=button.getBoundingClientRect();
     if(style.whiteSpace!=='nowrap'||rect.height>parseFloat(style.lineHeight)+1||rect.right>box.right+1||box.right>host.getBoundingClientRect().right+1)errors.push({id:question.id,label:label.textContent,height:rect.height,width:rect.width});
     checked++;
    }
    const operation=host.querySelector('.operation');if(operation.querySelector('.block-label').textContent!=='y'||!getComputedStyle(operation,'::before').content.includes('✕')||operation.getBoundingClientRect().width>86)errors.push({id:question.id,operation:'not compact cross-y'});
   }
   const reliable=banks[0].find(q=>q.base==='reliable');host.innerHTML=renderIngredients(reliable,reliable.blocks.map(b=>b.id),[],true,String);
   return{checked,errors};
  }""")
  assert not result['errors'],result['errors'][:5]
  page.locator('.tray-panel').screenshot(path=str(OUT/f'reliable-tray-{width}.png'))
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  print(f'{engine.name}/{width}px: {result["checked"]} tile labels single-line; compact cross-y; no Aa/Av; conical SVG flasks. PASS')
  browser.close()
