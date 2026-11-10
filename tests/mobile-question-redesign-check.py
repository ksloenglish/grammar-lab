"""Adaptive question UI audit, with genuine CSS-height viewport screenshots.

Run GRAMMAR_TEST_URL=http://127.0.0.1:3000/ python3 tests/mobile-question-redesign-check.py.
Uses current engine-created sessions in batches of 24 (not one reload per question).
Old-snapshot fixtures deliberately retain unprepared questions. No source/data edits.
Evidence is written beneath ignored test-results/mobile-redesign/.
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('GRAMMAR_TEST_URL', 'http://127.0.0.1:3000/').rstrip('/') + '/'
OUT = ROOT / 'test-results/mobile-redesign'
OUT.mkdir(parents=True, exist_ok=True)
EVIDENCE = {'url': BASE, 'checks': [], 'sweeps': [], 'screenshots': [], 'errors': []}


def check(condition, message):
    if not condition:
        EVIDENCE['errors'].append(message)
        raise AssertionError(message)
    EVIDENCE['checks'].append(message)


def save_evidence():
    (OUT / 'results.json').write_text(json.dumps(EVIDENCE, indent=2) + '\n')


def saved(page):
    return page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session'))")


def settle(page):
    page.evaluate('async () => {await document.fonts.ready; await new Promise(requestAnimationFrame); await new Promise(requestAnimationFrame); window.scrollTo(0,0);}')


def screenshot(page, name):
    settle(page)
    page.screenshot(path=str(OUT / name), full_page=False, animations='disabled')
    EVIDENCE['screenshots'].append(name)


SEED = """async ({module, ids}) => {
  const {createExperiment}=await import('./js/core.js');
  const bank=(await(await fetch('./data/'+module+'-questions.json')).json()).questions;
  const questions=ids.map(id=>bank.find(q=>q.id===id));
  if(questions.some(q=>!q))throw new Error('Missing fixture ID');
  localStorage.clear();
  const state=createExperiment(module,questions);
  localStorage.setItem('kslo-grammar-lab:session',JSON.stringify(state));
  return state;
}"""


def seed(page, module, ids):
    # A prior active session persists on pagehide. Leave it BEFORE injecting
    # the next fixture, using a fresh document rather than same-hash navigation.
    page.goto(BASE + '?fixture=' + str(time.monotonic_ns()), wait_until='domcontentloaded')
    expect(page.locator('.module-card')).to_have_count(2)
    state = page.evaluate(SEED, {'module': module, 'ids': ids})
    page.evaluate("history.replaceState(null,'','#experiment')")
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('.sentence')).to_be_visible()
    settle(page)
    return state


METRICS = """() => {
  const rect=selector=>{const n=document.querySelector(selector),r=n.getBoundingClientRect();return {x:r.x,y:r.y,bottom:r.bottom,width:r.width,height:r.height};};
  const state=JSON.parse(localStorage.getItem('kslo-grammar-lab:session'));
  const q=state.questions[state.index];
  const tray=document.querySelector('#reagent-tray');
  const buttons=[...tray.querySelectorAll('button')];
  const labels=buttons.map(n=>n.querySelector('.block-label')?.textContent);
  const targetErrors=buttons.flatMap(n=>{
    const r=n.getBoundingClientRect(),l=n.querySelector('.block-label'),lr=l.getBoundingClientRect(),s=getComputedStyle(l);
    return r.height<43.9||r.width<43.9||parseFloat(s.fontSize)<(innerWidth<=736?18:20)||s.whiteSpace!=='nowrap'||lr.right>r.right+1||lr.height>parseFloat(s.lineHeight)+1?[{label:l.textContent,width:r.width,height:r.height,font:s.fontSize}]:[];
  });
  const actionBottom=Math.max(...[...document.querySelectorAll('.trial-actions button')].map(n=>n.getBoundingClientRect().bottom));
  const tileBottom=Math.max(...buttons.map(n=>n.getBoundingClientRect().bottom));
  const h1=document.querySelector('h1.sentence'),chamber=document.querySelector('.chamber-panel'),panel=document.querySelector('.tray-panel');
  return {id:q.id,base:q.base,degree:q.degree,width:innerWidth,height:innerHeight,
    question:rect('h1.sentence'),chamber:rect('.chamber-panel'),tray:rect('.tray-panel'),actions:rect('.trial-actions'),
    interactionBottom:Math.max(actionBottom,tileBottom),panelBottom:Math.max(rect('.chamber-panel').bottom,rect('.tray-panel').bottom),
    pageHeight:document.documentElement.scrollHeight,overflow:Math.max(document.body.scrollWidth,document.documentElement.scrollWidth)-innerWidth,
    labels,targetErrors,bodyScope:document.body.classList.contains('question-page'),
    domOrder:Boolean(h1.compareDocumentPosition(chamber)&Node.DOCUMENT_POSITION_FOLLOWING)&&Boolean(chamber.compareDocumentPosition(panel)&Node.DOCUMENT_POSITION_FOLLOWING),
    obsolete:document.querySelectorAll('.beaker-meter,.move-buttons,[data-action="move-block"],#reagent-tray h3').length,
    score:rect('.score-display'),scoreText:document.querySelector('.score-display').textContent.trim(),
    instruction:document.querySelector('.tray-help')?.textContent.trim(),
    padding:parseFloat(getComputedStyle(panel).paddingLeft)};
}"""


REACHABILITY = """async () => {
  const {prepareAdaptiveQuestion,adaptiveBlocks}=await import('./js/comparison-blocks.js');
  const {assemble,normalise}=await import('./js/core.js');
  const output=[];
  for(const module of ['adjectives','adverbs']){
    const bank=(await(await fetch('./data/'+module+'-questions.json')).json()).questions;
    for(const raw of bank){
      const q=prepareAdaptiveQuestion(raw),reachable=[];
      for(const sequence of q.correctSequences){
        const selected=[];let visible=true;
        for(const id of sequence){if(!adaptiveBlocks(q,selected).some(b=>b.id===id)){visible=false;break;}selected.push(id);}
        if(visible)reachable.push({sequence,text:normalise(assemble(q,sequence).text)});
      }
      output.push({module,id:q.id,base:q.base,degree:q.degree,answers:q.answers,
        missing:q.answers.filter(a=>!reachable.some(r=>r.text===normalise(a))),
        canonicalVisible:reachable.some(r=>JSON.stringify(r.sequence)===JSON.stringify(q.correctSequences[0]))});
    }
  }
  return output;
}"""


def audit_metrics(metrics, tag):
    check(metrics['bodyScope'], f'{tag}: question-page scope active')
    check(metrics['domOrder'], f'{tag}: DOM order Question → Build your answer → Word blocks')
    check(metrics['labels'][0] == metrics['base'], f'{tag}: base tile first')
    check(not metrics['obsolete'], f'{tag}: no score/beaker graphic, categories or reorder controls')
    check(metrics['score']['height'] <= 32.1 and metrics['scoreText'].startswith('Score'), f'{tag}: compact text-only score, at most 32px high')
    check(metrics['instruction'] == 'Tap to add. Tap your answer blocks to remove.', f'{tag}: concise instruction')
    check(not metrics['targetErrors'], f'{tag}: readable single-line 44px tiles {metrics["targetErrors"]}')
    check(metrics['overflow'] <= 0, f'{tag}: no horizontal overflow ({metrics["overflow"]}px)')
    if metrics['width'] <= 736:
        check(12 <= metrics['padding'] <= 16, f'{tag}: compact question-only panel padding')
        check(metrics['question']['y'] < metrics['chamber']['y'] < metrics['tray']['y'], f'{tag}: phone vertical reading order')
        check(metrics['interactionBottom'] <= 800, f'{tag}: entire ordinary building interaction within 800px ({metrics["interactionBottom"]:.1f}px)')


ADVANCE = """async () => {
  const pause=()=>new Promise(requestAnimationFrame);
  const state=JSON.parse(localStorage.getItem('kslo-grammar-lab:session'));
  const q=state.questions[state.index];
  for(const id of q.correctSequences[0]){
    const button=document.querySelector('[data-action="add-block"][data-block="'+id+'"]');
    if(!button)throw new Error(q.id+': canonical ingredient invisible: '+id);
    button.click();await pause();
  }
  document.querySelector('[data-action="submit"]').click();await pause();
  const result=JSON.parse(localStorage.getItem('kslo-grammar-lab:session'));
  if(result.status!=='correct'||result.results.at(-1).mark!==1)throw new Error(q.id+': first-answer scoring failed');
  document.querySelector('[data-action="next"]').click();await pause();
}"""


def sweep(page, tag, reachability):
    rows = []
    for module in ['adjectives', 'adverbs']:
        ids = [r['id'] for r in reachability if r['module'] == module]
        for start in range(0, len(ids), 24):
            seed(page, module, ids[start:start + 24])
            for question_id in ids[start:start + 24]:
                settle(page)
                metrics = page.evaluate(METRICS)
                check(metrics['id'] == question_id, f'{tag}/{question_id}: actual current question')
                rows.append(metrics)
                try:
                    audit_metrics(metrics, f'{tag}/{question_id}')
                except AssertionError:
                    EVIDENCE['failureGeometry'] = metrics
                    screenshot(page, f'{tag}-failure-{question_id}.png')
                    raise
                page.evaluate(ADVANCE)
            print(f'{tag}: measured/scored {len(rows)}/192', flush=True)
    largest = max(rows, key=lambda row: row['interactionBottom'])
    EVIDENCE['sweeps'].append({'viewport': tag, 'questions': len(rows), 'largest': largest,
                              'over640': [r['id'] for r in rows if r['interactionBottom'] > 640], 'measurements': rows})
    print(f'{tag}: largest interaction bottom {largest["interactionBottom"]:.1f}px {largest["id"]}/{largest["base"]}; over640={sum(r["interactionBottom"]>640 for r in rows)}', flush=True)
    module = 'adjectives' if largest['id'].startswith('adj-') else 'adverbs'
    seed(page, module, [largest['id']])
    screenshot(page, f'{tag}-largest-{largest["id"]}.png')


def representatives(page, tag, bank_rows, mobile):
    cases = [('fast','comparative','adverbs'),('noisy','comparative','adjectives'),
             ('big','comparative','adjectives'),('interesting','comparative','adjectives'),
             ('far','comparative','adjectives'),('fast','superlative','adverbs')]
    for base, degree, module in cases:
        row = next(r for r in bank_rows if r['module'] == module and r['base'] == base and r['degree'] == degree)
        state = seed(page, module, [row['id']])
        metrics = page.evaluate(METRICS)
        audit_metrics(metrics, f'{tag}/{base}/{degree}')
        screenshot(page, f'{tag}-{base}-{degree}-building.png')
        if base == 'fast' and degree == 'comparative' and mobile and page.viewport_size['height'] == 640:
            check(metrics['interactionBottom'] <= 640, f'{tag}: regular fast fits ordinary 640px building budget')
        if base == 'noisy':
            q = state['questions'][0]
            sequence = next(s for s in q['correctSequences'] if any(b['id'] in s and b.get('operation') == 'remove-final-y' for b in q['blocks']))
            for block_id in sequence:
                locator = page.locator(f'[data-action="add-block"][data-block="{block_id}"]')
                locator.tap() if mobile else locator.click()
                if next(b for b in q['blocks'] if b['id'] == block_id).get('operation') == 'remove-final-y':
                    expect(page.locator('#assembled-answer')).to_have_text('nois')
                    screenshot(page, f'{tag}-noisy-remove-y-selected.png')
            expect(page.locator('#assembled-answer')).to_have_text('noisier than')
            screenshot(page, f'{tag}-noisier-than-selected.png')
        if base == 'fast' and degree == 'superlative':
            q = state['questions'][0]
            the = next(b['id'] for b in q['blocks'] if b['label'] == 'the')
            for with_the in [False, True]:
                sequence = next(s for s in q['correctSequences'] if (the in s) == with_the)
                for block_id in sequence:
                    locator = page.locator(f'[data-action="add-block"][data-block="{block_id}"]')
                    locator.tap() if mobile else locator.click()
                expect(page.locator('#assembled-answer')).to_have_text('the fastest' if with_the else 'fastest')
                screenshot(page, f'{tag}-superlative-{with_the}-selected.png')
                page.locator('[data-action="clear"]').tap() if mobile else page.locator('[data-action="clear"]').click()
        if base == 'big':
            q = state['questions'][0]
            ids = [next(b['id'] for b in q['blocks'] if b['label'] == 'big'),
                   next(b['id'] for b in q['blocks'] if b.get('operation') == 'double-final-consonant'),
                   next(b['id'] for b in q['blocks'] if b['label'] == '-er')]
            for index, block_id in enumerate(ids):
                locator = page.locator(f'[data-action="add-block"][data-block="{block_id}"]')
                locator.tap() if mobile else locator.click()
                expect(page.locator('#assembled-answer')).to_have_text(['big','bigg','bigger'][index])
                if index == 1:
                    screenshot(page, f'{tag}-big-g-selected.png')
            screenshot(page, f'{tag}-big-g-er-selected.png')
            locator = page.locator(f'[data-action="return-block"][data-block="{ids[1]}"]')
            locator.tap() if mobile else locator.click()
            expect(page.locator('#assembled-answer')).to_have_text('biger')
            check(saved(page)['assembly'] == [ids[0],ids[2]], f'{tag}: genuine touch/click removes literal doubling operation')
            page.locator('[data-action="submit"]').tap() if mobile else page.locator('[data-action="submit"]').click()
            expect(page.locator('.reaction.error')).to_be_visible()
            screenshot(page, f'{tag}-wrong.png')
            page.locator('[data-action="retry"]').tap() if mobile else page.locator('[data-action="retry"]').click()
            check(saved(page)['attempts'] == 1 and saved(page)['score'] == 0, f'{tag}: retry preserves zero mark and first attempt')
            screenshot(page, f'{tag}-retry.png')
            page.locator('[data-action="submit"]').tap() if mobile else page.locator('[data-action="submit"]').click()
            page.locator('[data-action="give-up"]').tap() if mobile else page.locator('[data-action="give-up"]').click()
            expect(page.locator('.reaction.success')).to_be_visible()
            check(saved(page)['score'] == 0 and saved(page)['results'][0]['gaveUp'], f'{tag}: revealed answer does not award marks')
            screenshot(page, f'{tag}-revealed.png')
            check(page.evaluate('document.documentElement.scrollWidth<=innerWidth'), f'{tag}: feedback may scroll vertically but does not clip horizontally')


def migration(page):
    page.goto(BASE + '?fixture=' + str(time.monotonic_ns()), wait_until='domcontentloaded')
    expect(page.locator('.module-card')).to_have_count(2)
    original = page.evaluate("""async () => {
      const {createExperiment}=await import('./js/core.js');
      const bank=(await(await fetch('./data/adjectives-questions.json')).json()).questions;
      const q=bank.find(q=>q.base==='big'&&q.degree==='comparative');
      const old=createExperiment('adjectives',[q]);
      old.questions=[structuredClone(q)];old.trayOrder=q.blocks.map(b=>b.id);old.assembly=[...q.correctSequences[0]];
      const best={'adjectives:10':{score:8,count:10,percentage:80,date:'2026-11-10'}};
      localStorage.clear();localStorage.setItem('kslo-grammar-lab:session',JSON.stringify(old));localStorage.setItem('kslo-grammar-lab:best',JSON.stringify(best));
      return{old,best};
    }""")
    page.goto(BASE + '#experiment', wait_until='domcontentloaded')
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('.sentence')).to_be_visible()
    expect(page.locator('#assembled-answer')).to_have_text('bigger than')
    # Resume upgrades runtime state; persistence may intentionally wait until
    # the next ordinary action. Add/return the new operation without scoring.
    page.locator('[data-action="add-block"][data-block="double-final-consonant"]').tap()
    page.locator('[data-action="return-block"][data-block="double-final-consonant"]').tap()
    state = saved(page)
    for key in ['schema','assembly','score','attempts','firstAnswer','results','startedAt']:
        check(state[key] == original['old'][key], f'actual pre-upgrade big snapshot: preserves {key}')
    check('double-final-consonant' in state['trayOrder'], 'actual old big snapshot: missing doubling ID added to trayOrder')
    check(page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:best'))") == original['best'], 'actual old big snapshot: best record unchanged')
    expect(page.locator('#assembled-answer')).to_have_text('bigger than')
    check('-ger' not in page.locator('#reagent-tray .block-label').all_inner_texts(), 'legacy compound suffix remains valid selected but not newly visible')
    screenshot(page, 'webkit-360x640-old-compound-resumed.png')
    page.locator('[data-action="submit"]').tap()
    check(saved(page)['score'] == 1, 'actual old selected compound answer still scores normally')
    page.goto(BASE + '?fixture=' + str(time.monotonic_ns()), wait_until='domcontentloaded')
    expect(page.locator('.module-card')).to_have_count(2)
    invalid = page.evaluate("""async () => {
      const {createExperiment}=await import('./js/core.js');
      const q=(await(await fetch('./data/adjectives-questions.json')).json()).questions[0];
      const old=createExperiment('adjectives',[q]);
      old.questions[0].blocks.push({id:'unsupported',label:'magic',kind:'operation',operation:'unsupported-operation'});
      localStorage.setItem('kslo-grammar-lab:session',JSON.stringify(old));return old;
    }""")
    page.goto(BASE, wait_until='domcontentloaded')
    expect(page.locator('.notice').first).to_contain_text('updated the questions')
    expect(page.locator('.resume-banner')).to_have_count(0)
    check(saved(page) is None, 'unsupported saved operation cannot resume or receive marks')
    check(page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:archive:session'))") == invalid, 'unsupported operation snapshot archived unchanged')
    check(page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:best'))") == original['best'], 'unsupported operation archival preserves independent best')
    check(not page.evaluate("document.body.classList.contains('question-page')"), 'Home after archival is outside question-page styling scope')


def main():
    try:
        with sync_playwright() as p:
            reachability = None
            for engine, width, height, mobile in [(p.chromium,1440,1000,False),(p.webkit,360,640,True),(p.webkit,360,800,True)]:
                tag = f'{engine.name}-{width}x{height}'
                browser = engine.launch(headless=True)
                context = browser.new_context(viewport={'width':width,'height':height},is_mobile=mobile,has_touch=mobile,reduced_motion='reduce')
                page = context.new_page()
                page.on('pageerror', lambda error: EVIDENCE['errors'].append(str(error)))
                page.goto(BASE, wait_until='networkidle')
                if reachability is None:
                    reachability = page.evaluate(REACHABILITY)
                    check(len(reachability) == 192, 'all 192 unchanged authored questions audited')
                    for row in reachability:
                        check(not row['missing'] and row['canonicalVisible'], f'{row["id"]}: every accepted answer reachable through currently visible tiles; canonical first sequence visible')
                    EVIDENCE['reachability'] = reachability
                if height != 800:
                    sweep(page, tag, reachability)
                representatives(page, tag, reachability, mobile)
                if mobile and height == 640:
                    migration(page)
                    page.set_viewport_size({'width':320,'height':640})
                    for base in ['interesting','big','far']:
                        row=next(r for r in reachability if r['module']=='adjectives' and r['base']==base and r['degree']=='comparative')
                        seed(page,'adjectives',[row['id']])
                        check(page.evaluate('document.documentElement.scrollWidth<=innerWidth'), f'webkit320/{base}: no horizontal overflow')
                        if base == 'interesting':
                            screenshot(page,'webkit-320x640-long-word.png')
                context.close()
                browser.close()
            check(not EVIDENCE['errors'], f'no runtime errors ({EVIDENCE["errors"]})')
    finally:
        save_evidence()
    print(f'PASS {len(EVIDENCE["checks"])} mobile redesign assertions; {len(EVIDENCE["screenshots"])} real-viewport screenshots. Evidence: {OUT}', flush=True)


if __name__ == '__main__':
    main()
