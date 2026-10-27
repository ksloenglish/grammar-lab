from playwright.sync_api import sync_playwright, expect
import json
with sync_playwright() as p:
    for engine in [p.chromium,p.webkit]:
        browser=engine.launch()
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.goto('http://127.0.0.1:3000/?module=adjectives&n=10',wait_until='networkidle')
        page.locator('[data-action="start"]').click()
        state=page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session'))")
        ids=state['questions'][0]['correctSequences'][0]
        page.evaluate("""() => {window.dragTrace=[];for(const type of ['dragstart','drop','click'])document.addEventListener(type,event=>window.dragTrace.push({type,id:event.target.closest('[data-block]')?.dataset.block,text:event.target.innerText,x:event.clientX,y:event.clientY}),true)}""")
        source=page.locator(f'[data-action="add-block"][data-block="{ids[0]}"]')
        source.scroll_into_view_if_needed()
        page.wait_for_timeout(700)
        print(engine.name,'wanted',ids[0],source.inner_text(),'source',source.bounding_box(),'target',page.locator('#assembly-zone').bounding_box())
        source.drag_to(page.locator('#assembly-zone'),target_position={'x':25,'y':25})
        page.wait_for_timeout(700)
        result=page.evaluate("({events:window.dragTrace,assembly:JSON.parse(localStorage.getItem('kslo-grammar-lab:session')).assembly})")
        print(json.dumps(result,indent=2))
        expect(page.locator(f'[data-action="return-block"][data-block="{ids[0]}"]')).to_be_visible()
        browser.close()
