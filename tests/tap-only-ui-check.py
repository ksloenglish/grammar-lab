"""Tap-only UI regression on fresh Chromium desktop and touch-enabled WebKit phones.

GRAMMAR_TEST_URL=http://127.0.0.1:3000/ python3 tests/tap-only-ui-check.py
Screenshots and JSON evidence stay in gitignored test-results/tap-only-ui/.
Uses unchanged real bank questions; no app-source modifications or test hooks.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("GRAMMAR_TEST_URL", "http://127.0.0.1:3000/").rstrip("/") + "/"
OUT = ROOT / "test-results" / "tap-only-ui"
RESULTS: list[str] = []
BANK_HASHES = {
    "adjectives": "7ff392eda0bd54dcce344cfa0c1a087314a94932e4b24840dd5677682e9c9006",
    "adverbs": "70796e68030a3ac052fe2ed4c872da64ec8f20f09b674bd1571b265ed93f0da3",
}
# Reuse the existing strict text-range/clipping audit, without executing its main.
_spec = importlib.util.spec_from_file_location("home_ui_metrics", ROOT / "tests/home-ui-check.py")
_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_metrics)
TEXT_METRICS = _metrics.TEXT_METRICS


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    RESULTS.append(message)


def saved(page):
    return page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session'))")


def shot(page, tag, state, locator=None):
    OUT.mkdir(parents=True, exist_ok=True)
    path = str(OUT / f"{tag}-{state}.png")
    if locator is None:
        page.screenshot(path=path, full_page=True, animations="disabled")
    else:
        locator.screenshot(path=path, animations="disabled")


def activate(locator, mobile):
    locator.tap() if mobile else locator.click()


def block(page, action, block_id):
    return page.locator(f'[data-action="{action}-block"][data-block="{block_id}"]')


def assert_assembly(page, ids, tag, message):
    expect(page.locator(".assembled-block")).to_have_count(len(ids))
    check(saved(page)["assembly"] == ids, f"{tag}: {message}")
    check(page.locator(".assembled-block").evaluate_all("nodes => nodes.map(node => node.dataset.block)") == ids,
          f"{tag}: DOM order matches saved assembly")


def no_overflow(page, tag):
    sizes = page.evaluate("({viewport: innerWidth, html: document.documentElement.scrollWidth, body: document.body.scrollWidth})")
    check(max(sizes["html"], sizes["body"]) <= sizes["viewport"], f"{tag}: no horizontal overflow ({sizes})")


def terminology(page, tag):
    text = page.locator("body").inner_text()
    accessible = page.locator("[aria-label]").evaluate_all("nodes => nodes.map(node => node.getAttribute('aria-label')).join(' ')")
    check(not re.search(r"\btrials?\b", text + " " + accessible, re.I), f"{tag}: visible and accessible copy uses questions, not trials")
    check(not re.search(r"\bdrag(?:ging)?\b|drop or tap|arrow buttons|press Left or Right", text, re.I),
          f"{tag}: no obsolete drag/reorder instructions")


def header(page, tag, home=False):
    nav = page.locator(".header-nav")
    expect(nav).to_have_count(1)
    link = nav.locator(".home-link")
    expect(link).to_have_text("Lab home")
    if home:
        expect(nav).to_be_hidden()
        expect(link).to_be_hidden()
        check(True, f"{tag}: Home top-right navigation is hidden")
    else:
        expect(nav).to_be_visible()
        expect(link).to_be_visible()
        m = link.evaluate(TEXT_METRICS)
        check(m["height"] >= 44 and m["width"] >= 44, f"{tag}: labelled Lab home target is at least 44 by 44px")
        check(m["fonts"] and min(m["fonts"]) >= 12 and m["rects"] and not m["hidden"] and not m["clipped"],
              f"{tag}: Lab home text is readable, not icon-only")
        check(m["x"] >= page.viewport_size["width"] / 2 and m["right"] <= page.viewport_size["width"],
              f"{tag}: labelled navigation remains in the top right")
    return link


def selector(page, tag, width, mobile):
    options = page.locator(".trial-options .choice")
    expect(page.locator(".trial-options legend")).to_have_text("Number of questions")
    expect(options).to_have_count(3)
    labels = [re.sub(r"\s+", " ", node.inner_text()).strip() for node in options.all()]
    check(labels == ["10 questions", "20 questions", "30 questions"], f"{tag}: exact 10/20/30 questions labels ({labels})")
    metrics = [node.evaluate(TEXT_METRICS) for node in options.all()]
    parent_width = page.locator(".trial-options").bounding_box()["width"]
    check(all(m["width"] < parent_width - 2 and m["height"] >= 44 for m in metrics),
          f"{tag}: question options are content-sized touch targets, not full-width rows")
    check(all(m["rects"] and not m["hidden"] and not m["clipped"] and m["fonts"] and min(m["fonts"]) >= 12 for m in metrics),
          f"{tag}: selector labels are fully readable and unclipped")
    if width >= 360:
        check(max(m["y"] for m in metrics) - min(m["y"] for m in metrics) <= 1,
              f"{tag}: all three question options fit on one row")
    for count in [10, 30, 20]:
        activate(options.filter(has=page.locator(f'[name="trial-count"][value="{count}"]')), mobile)
        expect(page.locator(f'[name="trial-count"][value="{count}"]')).to_be_checked()
    check(True, f"{tag}: click/tap selector changes 10/30/20 values without auto-start")
    expect(page.locator('[data-action="start"]')).to_be_visible()
    no_overflow(page, f"{tag}/setup")


def seed_fixture(page, module="adjectives"):
    # Use the real engine to make a prepared current schema-2 session.
    page.goto(BASE, wait_until="networkidle")
    state = page.evaluate("""async module => {
      const {createExperiment} = await import('./js/core.js');
      const bank = await (await fetch(`./data/${module}-questions.json`)).json();
      const ids = module === 'adjectives' ? ['adj-043', 'adj-055', 'adj-041'] : ['adv-067', 'adv-049', 'adv-063'];
      const first = ids.map(id => bank.questions.find(question => question.id === id));
      const questions = [...first, ...bank.questions.filter(question => !ids.includes(question.id))].slice(0, 10);
      const state = createExperiment(module, questions);
      localStorage.setItem('kslo-grammar-lab:session', JSON.stringify(state));
      return state;
    }""", module)
    page.goto(BASE + "#experiment", wait_until="networkidle")
    page.reload(wait_until="networkidle")
    expect(page.locator(".sentence")).to_be_visible()
    check(saved(page) == state and state["schema"] == 2, f"{module}: compatible saved schema-2 fixture resumes unchanged")
    return state


def no_drag(page, tag):
    nodes = page.locator(".reagent, .assembled-block")
    attrs = nodes.evaluate_all("nodes => nodes.map(node => ({html:node.getAttribute('draggable'), native:node.draggable}))")
    check(attrs and all(item["html"] == "false" and item["native"] is False for item in attrs),
          f"{tag}: every reagent and selected block explicitly has draggable=false")
    expect(page.locator('[draggable="true"], .move-buttons, [data-action="move-block"]')).to_have_count(0)
    check(True, f"{tag}: no draggable=true nodes or arrow move actions")
    baseline = saved(page)
    source = page.locator('[data-action="add-block"]:not(:disabled)').first
    if source.count():
        source.scroll_into_view_if_needed()
        source.drag_to(page.locator("#assembly-zone"), target_position={"x": 20, "y": 20})
        page.wait_for_timeout(180)
        check(saved(page) == baseline, f"{tag}: actual pointer drag from tray cannot add or alter saved state")
    if page.locator(".assembled-block").count():
        selected = page.locator(".assembled-block").first
        selected.drag_to(page.locator("#reagent-tray"), target_position={"x": 20, "y": 20})
        check(saved(page) == baseline, f"{tag}: actual selected-block drag cannot return an answer")
        if page.locator(".assembled-block").count() > 1:
            selected.drag_to(page.locator(".assembled-block").last)
            check(saved(page) == baseline, f"{tag}: dragging over another selected block cannot reorder")
    # Exercise former delegated handlers even if native draggable=false blocks them.
    page.evaluate("""() => {
      const sources = [document.querySelector('[data-action="add-block"]'), document.querySelector('.assembled-block')].filter(Boolean);
      for (const source of sources) {
        const transfer = new DataTransfer(); transfer.setData('text/plain', source.dataset.block);
        source.dispatchEvent(new DragEvent('dragstart', {bubbles:true, dataTransfer:transfer}));
        for (const target of [document.querySelector('#assembly-zone'), document.querySelector('.assembled-block'), document.querySelector('#reagent-tray')].filter(Boolean)) {
          target.dispatchEvent(new DragEvent('dragover', {bubbles:true, dataTransfer:transfer}));
          target.dispatchEvent(new DragEvent('drop', {bubbles:true, dataTransfer:transfer}));
        }
        source.dispatchEvent(new DragEvent('dragend', {bubbles:true, dataTransfer:transfer}));
      }
    }""")
    page.wait_for_timeout(180)
    check(saved(page) == baseline, f"{tag}: synthetic drag/drop events also leave assembly and full saved state unchanged")
    expect(page.locator(".drag-over")).to_have_count(0)


def inline_hint(page, tag, base):
    expect(page.locator(".base-hint")).to_have_count(0)
    group = page.locator(".sentence .gap-with-hint")
    expect(group).to_have_count(1)
    expect(group.locator(":scope > .gap")).to_have_count(1)
    hint = group.locator(":scope > .inline-base-hint")
    expect(hint).to_have_text(f"({base})")
    expect(hint).to_be_visible()
    check(group.evaluate("node => node.children.length === 2 && node.children[0].classList.contains('gap') && node.children[0].nextElementSibling.classList.contains('inline-base-hint')"),
          f"{tag}: (base) is immediately AFTER the existing blank within one wrapper")
    before = group.locator(".gap").bounding_box()
    after = hint.bounding_box()
    check(after["x"] >= before["x"] + before["width"] - 1 and abs(after["y"] - before["y"]) < max(after["height"], before["height"]),
          f"{tag}: long ({base}) hint sits to the right of blank on the same line")
    m = hint.evaluate(TEXT_METRICS)
    check(m["rects"] and not m["hidden"] and not m["clipped"] and m["x"] >= 0 and m["right"] <= page.viewport_size["width"],
          f"{tag}: long inline base hint is readable and unclipped")
    no_overflow(page, f"{tag}/inline-hint")


def labels(page, tag, minimum):
    failures = []
    nodes = page.locator("#reagent-tray .block-label, #assembly-zone .token-button")
    for node in nodes.all():
        m = node.evaluate(TEXT_METRICS)
        rects = m["rects"]
        one_line = bool(rects) and max(r["top"] for r in rects) < min(r["bottom"] for r in rects)
        if m["font"] < minimum or not m["fonts"] or min(m["fonts"]) < minimum or not one_line or m["textOverflow"] == "ellipsis" or m["hidden"] or m["clipped"]:
            failures.append(m)
    check(nodes.count() > 0 and not failures, f"{tag}: all tray/selected labels at least {minimum}px, one-line and unclipped ({failures})")
    selected = page.locator(".assembled-block")
    if selected.count():
        content_width = page.locator("#assembly-zone").evaluate("node => node.clientWidth - parseFloat(getComputedStyle(node).paddingLeft) - parseFloat(getComputedStyle(node).paddingRight)")
        widths = [node.bounding_box()["width"] for node in selected.all()]
        check(all(width < content_width - 2 for width in widths), f"{tag}: selected blocks are content-sized, never full answer rows ({widths})")
        if page.viewport_size["width"] >= 360 and selected.count() == 3:
            positions = [node.bounding_box() for node in selected.all()]
            check(any(abs(a["y"] - b["y"]) <= 1 for i, a in enumerate(positions) for b in positions[i + 1:]),
                  f"{tag}: selected three-block answer does not put every block on its own row")


def add_sequence(page, ids, mobile):
    for block_id in ids:
        activate(block(page, "add", block_id), mobile)


def scoring(page, tag, mobile):
    activate(page.locator('[data-action="submit"]'), mobile)
    expect(page.locator(".reaction.success")).to_be_visible()
    state = saved(page)
    check(state["score"] == 1 and state["attempts"] == 1 and state["results"][0]["mark"] == 1,
          f"{tag}: correct first submission still earns exactly one mark")
    no_drag(page, f"{tag}/locked-correct")
    activate(page.locator('[data-action="next"]'), mobile)
    question = saved(page)["questions"][1]
    inline_hint(page, f"{tag}/comfortable", question["base"])
    wrong_id = next(item["id"] for item in question["blocks"] if item["label"] == question["base"])
    activate(block(page, "add", wrong_id), mobile)
    activate(page.locator('[data-action="submit"]'), mobile)
    expect(page.locator(".reaction.error")).to_be_visible()
    wrong = saved(page)
    activate(page.locator('[data-action="retry"]'), mobile)
    activate(page.locator('[data-action="clear"]'), mobile)
    add_sequence(page, question["correctSequences"][0], mobile)
    activate(page.locator('[data-action="submit"]'), mobile)
    expect(page.locator(".reaction.success")).to_be_visible()
    state = saved(page)
    check(state["score"] == 1 and state["attempts"] == 2 and state["firstAnswer"] == wrong["firstAnswer"] and state["results"][1]["mark"] == 0,
          f"{tag}: successful retry preserves first answer and adds no mark")
    activate(page.locator('[data-action="next"]'), mobile)
    question = saved(page)["questions"][2]
    wrong_id = next(item["id"] for item in question["blocks"] if item["label"] == question["base"])
    activate(block(page, "add", wrong_id), mobile)
    activate(page.locator('[data-action="submit"]'), mobile)
    activate(page.locator('[data-action="give-up"]'), mobile)
    state = saved(page)
    check(state["score"] == 1 and state["results"][2]["gaveUp"] and state["results"][2]["mark"] == 0,
          f"{tag}: Give Up still reveals correct answer without a mark")
    activate(page.locator('[data-action="next"]'), mobile)
    for index in range(3, 10):
        question = saved(page)["questions"][index]
        add_sequence(page, question["correctSequences"][0], mobile)
        activate(page.locator('[data-action="submit"]'), mobile)
        activate(page.locator('[data-action="next"]'), mobile)
    expect(page.locator(".report-score")).to_be_visible()
    header(page, f"{tag}/report")
    terminology(page, f"{tag}/report")
    expect(page.locator(".report-item")).to_have_count(10)
    check("8/10" in re.sub(r"\s+", "", page.locator(".report-score strong").inner_text()), f"{tag}: completed first-attempt report remains 8/10")
    check(page.evaluate("localStorage.getItem('kslo-grammar-lab:session')") is None, f"{tag}: completed saved session is removed")
    no_overflow(page, f"{tag}/report")
    shot(page, tag, "report-header", page.locator(".site-header"))
    page.locator("#report-name").fill("Tap-only ephemeral name")
    page.locator("#report-class").fill("S2 temporary class")
    store = page.evaluate("JSON.stringify(localStorage)")
    check("Tap-only ephemeral name" not in store and "S2 temporary class" not in store, f"{tag}: report identity remains ephemeral")
    best = page.evaluate("localStorage.getItem('kslo-grammar-lab:best')")
    original = page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:last-report'))")
    activate(page.locator('[data-action="practice"]'), mobile)
    for index in range(2):
        add_sequence(page, saved(page)["questions"][index]["correctSequences"][0], mobile)
        activate(page.locator('[data-action="submit"]'), mobile)
        activate(page.locator('[data-action="next"]'), mobile)
    expect(page.locator(".original-report-summary")).to_contain_text("8/10")
    check("2/2" in re.sub(r"\s+", "", page.locator(".report-score strong").inner_text()), f"{tag}: separate wrong-answer practice remains 2/2")
    check(page.evaluate("localStorage.getItem('kslo-grammar-lab:best')") == best, f"{tag}: retry practice does not overwrite best saved state")
    current = page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:last-report'))")
    check(current["originalReport"] == original, f"{tag}: original report snapshot is unchanged in practice")


def run(engine, tag, width):
    mobile = width <= 360
    print(f"RUN {tag}: fresh {engine.name} context, touch={mobile}", flush=True)
    browser = engine.launch(headless=True)
    context = browser.new_context(viewport={"width": width, "height": 800 if mobile else 1000},
                                  is_mobile=mobile, has_touch=mobile, reduced_motion="reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(BASE, wait_until="networkidle")
        expect(page.locator(".module-card")).to_have_count(2)
        header(page, f"{tag}/Home", home=True)
        expect(page.locator(".hero-footnote")).to_have_count(0)
        check("No login needed" not in page.locator(".hero").inner_text(), f"{tag}: obsolete hero login footnote is absent")
        terminology(page, f"{tag}/Home")
        no_overflow(page, f"{tag}/Home")
        shot(page, tag, "home")
        shot(page, tag, "home-header", page.locator(".site-header"))
        for module, expected in BANK_HASHES.items():
            text = page.evaluate("async module => (await fetch(`./data/${module}-questions.json`)).text()", module)
            check(hashlib.sha256(text.encode()).hexdigest() == expected, f"{tag}: served {module} bank JSON remains byte-identical")
        activate(page.locator('[data-route="learn/adjectives"]').first, mobile)
        expect(page.locator(".mini-question")).to_have_count(3)
        header(page, f"{tag}/Learn")
        terminology(page, f"{tag}/Learn")
        activate(header(page, f"{tag}/Learn return"), mobile)
        header(page, f"{tag}/Home return", home=True)
        page.goto(BASE + "?module=adjectives&n=20", wait_until="networkidle")
        expect(page.locator('[name="trial-count"][value="20"]')).to_be_checked()
        header(page, f"{tag}/setup")
        selector(page, tag, width, mobile)
        terminology(page, f"{tag}/setup")
        shot(page, tag, "setup")
        shot(page, tag, "setup-selector", page.locator(".trial-options"))
        shot(page, tag, "setup-header", page.locator(".site-header"))
        activate(page.locator('[data-action="start"]'), mobile)
        expect(page.locator(".sentence")).to_be_visible()
        check(saved(page)["count"] == 20, f"{tag}: selector still starts exactly 20 questions")
        state = seed_fixture(page)
        header(page, f"{tag}/experiment")
        inline_hint(page, tag, state["questions"][0]["base"])
        no_drag(page, f"{tag}/empty")
        ids = state["questions"][0]["correctSequences"][0]
        # Genuine Tab traversal and native Enter/Space activation, not dispatchEvent.
        first = page.locator('[data-action="add-block"]').first
        first_id = first.get_attribute("data-block")
        first.focus()
        page.keyboard.press("Tab")
        expect(first).not_to_be_focused()
        page.keyboard.press("Shift+Tab")
        expect(first).to_be_focused()
        page.keyboard.press("Enter")
        expect(block(page, "return", first_id)).to_be_focused()
        page.keyboard.press("Space")
        expect(block(page, "add", first_id)).to_be_focused()
        assert_assembly(page, [], tag, "Tab/Enter add and Space return preserve focus")
        add_sequence(page, ids, mobile)
        assert_assembly(page, ids, tag, "genuine tap/click appends three blocks in selection order")
        labels(page, tag, 18 if mobile else 20)
        no_drag(page, f"{tag}/three-selected")
        shot(page, tag, "three-block-answer-inline-hint")
        shot(page, tag, "three-block-answer", page.locator(".chamber-panel"))
        shot(page, tag, "inline-base-hint", page.locator(".trial-card"))
        baseline = saved(page)
        selected = block(page, "return", ids[0])
        selected.focus()
        for key in ["ArrowRight", "ArrowLeft"]:
            page.keyboard.press(key)
            expect(selected).to_be_focused()
            check(saved(page) == baseline, f"{tag}: {key} changes neither order nor saved state/focus")
        activate(selected, mobile)
        assert_assembly(page, ids[1:], tag, "tap/click selected block returns it")
        activate(block(page, "add", ids[0]), mobile)
        assert_assembly(page, ids[1:] + ids[:1], tag, "return/re-add changes order only by appending to the end")
        block(page, "return", ids[0]).focus()
        page.keyboard.press("Enter")
        expect(block(page, "add", ids[0])).to_be_focused()
        page.keyboard.press("Space")
        expect(block(page, "return", ids[0])).to_be_focused()
        assert_assembly(page, ids[1:] + ids[:1], tag, "Enter return and Space add use native button actions with restored focus")
        activate(page.locator('[data-action="clear"]'), mobile)
        assert_assembly(page, [], tag, "Clear remains operational")
        expect(page.locator('[data-action="add-block"]').first).to_be_focused()
        check(saved(page) == state, f"{tag}: add/return/re-add/Clear change no schema, scoring, tray order or question snapshots")
        add_sequence(page, ids, mobile)
        baseline = saved(page)
        page.reload(wait_until="networkidle")
        check(saved(page) == baseline, f"{tag}: refresh resumes current assembled state byte-for-byte")
        header(page, f"{tag}/resumed experiment")
        terminology(page, f"{tag}/experiment")
        scoring(page, tag, mobile)
        # A second current-bank long hint exercises the longest adverb label.
        adverb = seed_fixture(page, "adverbs")
        inline_hint(page, f"{tag}/successfully", adverb["questions"][0]["base"])
        add_sequence(page, adverb["questions"][0]["correctSequences"][0], mobile)
        labels(page, f"{tag}/long-adverb", 18 if mobile else 20)
        no_overflow(page, f"{tag}/long-adverb")
        shot(page, tag, "long-adverb-inline-hint")
        check(not errors, f"{tag}: no JavaScript runtime errors ({errors})")
        print(f"PASS {tag}: focused interaction, scoring and layout checks complete", flush=True)
    except Exception:
        shot(page, tag, "failure")
        raise
    finally:
        context.close()
        browser.close()


def run_drag_regression():
    """Small revised equivalent for the former drag-to-place smoke script."""
    with sync_playwright() as playwright:
        for engine in [playwright.chromium, playwright.webkit]:
            browser = engine.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            page = context.new_page()
            try:
                state = seed_fixture(page)
                no_drag(page, f"{engine.name}/empty-tray")
                ids = state["questions"][0]["correctSequences"][0]
                add_sequence(page, ids, False)
                no_drag(page, f"{engine.name}/selected")
                activate(block(page, "return", ids[0]), False)
                activate(block(page, "add", ids[0]), False)
                assert_assembly(page, ids[1:] + ids[:1], engine.name, "only return/re-add changes order")
            finally:
                context.close()
                browser.close()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "no-drag-results.json").write_text(json.dumps(RESULTS, indent=2) + "\n")
    print(f"Passed {len(RESULTS)} tap-only/no-drag smoke assertions across Chromium and WebKit.")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        run(playwright.chromium, "desktop-1440", 1440)
        run(playwright.webkit, "phone-360", 360)
        run(playwright.webkit, "phone-320", 320)
    (OUT / "tap-only-ui-results.json").write_text(json.dumps(RESULTS, indent=2) + "\n")
    print("\n".join("PASS " + result for result in RESULTS))
    print(f"Passed {len(RESULTS)} focused tap-only UI assertions on 1440px Chromium and 360/320px touch-enabled WebKit.")


if __name__ == "__main__":
    main()
