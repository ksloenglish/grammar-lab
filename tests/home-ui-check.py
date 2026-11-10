"""Focused silent-app and Home UI regression checks (no full scoring-suite repeat).

Run against a ready server with:
    GRAMMAR_TEST_URL=http://127.0.0.1:3000/ python3 tests/home-ui-check.py

Uses Chromium desktop (1440x1000) and WebKit phone (360x800). Screenshots and
assertion evidence are written to ignored test-results/home-ui/ only. Each browser has a
fresh, isolated context, and audio instrumentation is installed before app JS.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("GRAMMAR_TEST_URL", "http://127.0.0.1:3000/")
OUT = Path(__file__).resolve().parents[1] / "test-results" / "home-ui"
REMOVE_Y_NAME = re.compile(r"remove(?:\s+the)?[\s-]+final[\s-]+y", re.I)
CROSSES = "✕×✖"
RESULTS: list[str] = []

# Record reads as well as calls: even merely accessing an audio API is a failure.
# Forward to native implementations so instrumentation cannot hide app failures.
# Track audio creation/insertion too, including elements removed before assertions.
AUDIO_INIT = r"""
(() => {
  const calls = [], installed = [];
  Object.defineProperty(window, '__homeUIAudioAudit', {
    value: {calls, installed}, writable: false, configurable: false
  });
  const record = api => calls.push({api, route: location.href});
  for (const name of ['Audio', 'AudioContext', 'webkitAudioContext',
                      'OfflineAudioContext', 'webkitOfflineAudioContext',
                      'SpeechSynthesisUtterance', 'speechSynthesis']) {
    if (!(name in window)) continue;
    const native = window[name];
    const wrapped = typeof native === 'function' ? new Proxy(native, {
      construct(target, args, newTarget) {
        record(name + '.construct');
        return Reflect.construct(target, args, newTarget);
      },
      apply(target, receiver, args) {
        record(name + '.call');
        return Reflect.apply(target, receiver, args);
      }
    }) : native;
    Object.defineProperty(window, name, {
      configurable: true,
      get() { record(name + '.access'); return wrapped; }
    });
    installed.push(name);
  }
  const nativePlay = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function(...args) {
    record('HTMLMediaElement.play');
    return Reflect.apply(nativePlay, this, args);
  };
  installed.push('HTMLMediaElement.play');
  for (const method of ['createElement', 'createElementNS']) {
    const native = Document.prototype[method];
    Document.prototype[method] = function(...args) {
      const tag = String(args[method === 'createElementNS' ? 1 : 0]).toLowerCase();
      if (tag === 'audio') record('document.' + method + '(audio)');
      return Reflect.apply(native, this, args);
    };
    installed.push('document.' + method);
  }
  const observer = new MutationObserver(records => {
    for (const mutation of records) for (const node of mutation.addedNodes) {
      if (node.nodeType === 1 &&
          (node.localName === 'audio' || node.querySelector('audio'))) {
        record('audio element inserted');
      }
    }
  });
  observer.observe(document, {childList: true, subtree: true});
  installed.push('MutationObserver');
})();
"""

# Inspect actual text ranges rather than trusting scrollWidth/no-overflow alone.
# This catches font-size:0, ellipsis, wrapping, and text clipped by any ancestor.
TEXT_METRICS = r"""(node) => {
  const style = getComputedStyle(node), box = node.getBoundingClientRect();
  const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
  const rects = [], fonts = [], hidden = [];
  let text;
  while ((text = walker.nextNode())) {
    if (!text.textContent.trim()) continue;
    const owner = text.parentElement, textStyle = getComputedStyle(owner);
    fonts.push(parseFloat(textStyle.fontSize));
    if (textStyle.visibility !== 'visible' || textStyle.display === 'none' ||
        Number(textStyle.opacity) === 0) hidden.push(text.textContent);
    const range = document.createRange(); range.selectNodeContents(text);
    for (const rect of range.getClientRects()) {
      if (rect.width && rect.height) rects.push({
        left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom
      });
    }
  }
  const clipped = [];
  for (const rect of rects) {
    for (let ancestor = node; ancestor; ancestor = ancestor.parentElement) {
      const a = ancestor.getBoundingClientRect(), s = getComputedStyle(ancestor);
      if (['hidden', 'clip', 'auto', 'scroll'].includes(s.overflowX) &&
          (rect.left < a.left - 1 || rect.right > a.right + 1)) clipped.push('horizontal');
      if (['hidden', 'clip', 'auto', 'scroll'].includes(s.overflowY) &&
          (rect.top < a.top - 1 || rect.bottom > a.bottom + 1)) clipped.push('vertical');
    }
  }
  return {
    text: node.textContent.trim(), font: parseFloat(style.fontSize), fonts,
    width: box.width, height: box.height, x: box.x, y: box.y,
    right: box.right, bottom: box.bottom, rects, hidden, clipped,
    whiteSpace: style.whiteSpace, textOverflow: style.textOverflow
  };
}"""


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    RESULTS.append(message)


def shot(page, tag: str, state: str, locator=None) -> None:
    path = str(OUT / f"home-ui-{tag}-{state}.png")
    if locator is None:
        page.screenshot(path=path, full_page=True, animations="disabled")
    else:
        locator.screenshot(path=path, animations="disabled")


def no_overflow(page, tag: str, state: str) -> None:
    dimensions = page.evaluate("""() => ({
      viewport: innerWidth, html: document.documentElement.scrollWidth,
      body: document.body.scrollWidth
    })""")
    check(max(dimensions["html"], dimensions["body"]) <= dimensions["viewport"],
          f"{tag}/{state}: no document overflow ({dimensions})")


def silent(page, tag: str, state: str) -> None:
    expect(page.locator("#sound-toggle, .sound-toggle, audio")).to_have_count(0)
    # Also reject renamed/hidden sound controls, not just the old ID.
    controls = page.locator('button, input, [role="button"], [role="switch"], [role="checkbox"]')
    named_audio_controls = controls.evaluate_all(r"""nodes => nodes.filter(node =>
      /\b(sound|audio|mute|unmute)\b/i.test([
        node.textContent, node.getAttribute('aria-label'), node.getAttribute('title'),
        node.id, node.className, node.getAttribute('name')
      ].join(' '))
    ).map(node => node.outerHTML)""")
    check(not named_audio_controls, f"{tag}/{state}: no sound/audio control ({named_audio_controls})")
    audit = page.evaluate("window.__homeUIAudioAudit")
    check(audit is not None and all(name in audit["installed"] for name in
          ["Audio", "HTMLMediaElement.play", "document.createElement", "MutationObserver"]),
          f"{tag}/{state}: pre-app audio instrumentation active")
    check(not audit["calls"], f"{tag}/{state}: no audio API accesses or calls ({audit['calls']})")


def home_navigation_hidden(page, tag: str, state: str) -> None:
    nav = page.locator(".header-nav")
    expect(nav).to_have_count(1)
    expect(nav).to_be_hidden()
    expect(nav.locator(".home-link")).to_have_text("Lab home")
    check(True, f"{tag}/{state}: top-right navigation is hidden only on Home")


def home_link(page, tag: str, state: str):
    link = page.locator(".header-nav").get_by_role("link", name="Lab home", exact=True)
    expect(link).to_have_count(1)
    expect(link).to_be_visible()
    expect(link).to_have_text("Lab home")
    metrics = link.evaluate(TEXT_METRICS)
    viewport = page.viewport_size
    check(metrics["height"] >= 44, f"{tag}/{state}: Lab home tap target at least 44px high")
    check(metrics["font"] > 0 and metrics["fonts"] and min(metrics["fonts"]) >= 12
          and metrics["rects"] and not metrics["hidden"] and not metrics["clipped"],
          f"{tag}/{state}: literal Lab home text readable, not font-size:0/icon-only ({metrics})")
    check(metrics["x"] >= viewport["width"] / 2 and metrics["right"] <= viewport["width"]
          and metrics["y"] >= 0 and metrics["bottom"] <= viewport["height"],
          f"{tag}/{state}: Lab home is visible in top-right navigation")
    return link


def readable_labels(locator, minimum: int, tag: str, state: str) -> None:
    failures = []
    check(locator.count() > 0, f"{tag}/{state}: tile labels exist")
    for node in locator.all():
        expect(node).to_be_visible()
        metrics = node.evaluate(TEXT_METRICS)
        rects = metrics["rects"]
        one_line = bool(rects) and max(r["top"] for r in rects) < min(r["bottom"] for r in rects)
        if (metrics["font"] < minimum or not metrics["fonts"] or min(metrics["fonts"]) < minimum
                or metrics["whiteSpace"] != "nowrap" or metrics["textOverflow"] == "ellipsis"
                or not one_line or metrics["hidden"] or metrics["clipped"]):
            failures.append(metrics)
    check(not failures, f"{tag}/{state}: all labels at least {minimum}px, one line and unclipped ({failures})")


def demo(page, tag: str, minimum: int) -> None:
    panel = page.locator(".hero-demo")
    expect(panel.get_by_text("How to build a word", exact=True)).to_be_visible()
    check(panel.locator(".spelling-change, .deleted-letter").count() == 0,
          f"{tag}/Home: intermediate yellow spelling strip is absent")
    check(panel.get_by_text(re.compile(r"^(WORD EXAMPLE|BUILD A WORD)$", re.I)).count() == 0,
          f"{tag}/Home: awkward old demo heading removed")
    tokens = panel.locator(".demo-equation .demo-token")
    expect(tokens).to_have_count(3)
    labels = [re.sub(f"[{CROSSES}\\s]", "", node.inner_text()) for node in tokens.all()]
    check(labels == ["easy", "y", "-ier"], f"{tag}/Home: ingredients ordered easy / remove-y / -ier ({labels})")
    expect(panel.locator(".demo-plus")).to_have_count(2)
    for plus in panel.locator(".demo-plus").all():
        expect(plus).to_have_text("+")
    pieces = panel.locator(".demo-equation > .demo-token, .demo-equation > .demo-plus")
    recipe = [re.sub(f"[{CROSSES}\\s]", "", node.inner_text()) for node in pieces.all()]
    check(recipe == ["easy", "+", "y", "+", "-ier"],
          f"{tag}/Home: plus signs separate all three ingredients ({recipe})")
    operation = tokens.nth(1)
    expect(panel.get_by_label(REMOVE_Y_NAME)).to_have_count(1)
    check(operation.evaluate("(node, target) => node === target || node.contains(target)",
                             panel.get_by_label(REMOVE_Y_NAME).element_handle()),
          f"{tag}/Home: remove-final-y accessible name belongs to operation tile")
    cross = operation.evaluate(r"""node => {
      const before = getComputedStyle(node, '::before');
      const candidates = [...node.querySelectorAll('*')].filter(child =>
        /^[✕×✖]$/.test(child.textContent.trim()));
      if (/[✕×✖]/.test(before.content)) {
        const s = getComputedStyle(node);
        return {visible: before.display !== 'none' && before.visibility === 'visible' &&
                Number(before.opacity) > 0 && parseFloat(before.fontSize) > 0,
                colour: before.color, beforeY: s.flexDirection !== 'row-reverse' &&
                Number(before.order) <= 0};
      }
      const child = candidates[0];
      if (!child) return {visible: false, beforeY: false, colour: ''};
      const style = getComputedStyle(child), box = child.getBoundingClientRect();
      const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
      let text, yBox;
      while ((text = walker.nextNode())) if (text.textContent.trim() === 'y') {
        const range = document.createRange(); range.selectNodeContents(text);
        yBox = range.getBoundingClientRect(); break;
      }
      return {visible: box.width > 0 && box.height > 0 && style.visibility === 'visible'
              && Number(style.opacity) > 0, colour: style.color,
              beforeY: !!yBox && box.right <= yBox.left + 1};
    }""")
    rgb = [float(part) for part in re.findall(r"[\d.]+", cross["colour"])[:3]]
    red = len(rgb) == 3 and rgb[0] >= 140 and rgb[0] > 1.25 * max(rgb[1:])
    check(cross["visible"] and cross["beforeY"] and red,
          f"{tag}/Home: visible red cross before y ({cross})")
    positions = [node.bounding_box() for node in tokens.all()]
    check(all(a["x"] + a["width"] <= b["x"] + 1 for a, b in zip(positions, positions[1:])),
          f"{tag}/Home: ingredient tiles have visible left-to-right order without overlap")
    readable_labels(tokens, minimum, tag, "Home demo")
    expect(panel.locator(".demo-result")).to_contain_text("easier")
    result_text = re.sub(r"[✓✔\s]", "", panel.locator(".demo-result").inner_text())
    check(result_text == "easier", f"{tag}/Home: demo result is easier")
    readable_labels(panel.locator(".demo-result"), minimum, tag, "Home result")


def saved(page) -> dict:
    return page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session'))")


def submit(page, sequence: list[str]) -> None:
    for block_id in sequence:
        page.locator(f'[data-action="add-block"][data-block="{block_id}"]').click()
    page.locator('[data-action="submit"]').click()


def run(engine, tag: str, width: int, height: int) -> None:
    browser = engine.launch(headless=True)
    context = browser.new_context(viewport={"width": width, "height": height},
                                  is_mobile=width == 360, has_touch=width == 360,
                                  reduced_motion="reduce")
    context.add_init_script(AUDIO_INIT)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    minimum = 18 if width == 360 else 20
    try:
        page.goto(BASE, wait_until="networkidle")
        expect(page.locator(".module-card")).to_have_count(2)
        # Save Home evidence before assertions so regressions remain inspectable.
        shot(page, tag, "home")
        home_navigation_hidden(page, tag, "Home")
        demo(page, tag, minimum)
        no_overflow(page, tag, "Home")
        silent(page, tag, "Home")
        shot(page, tag, "home-demo", page.locator(".hero-demo"))

        page.locator('[data-route="learn/adjectives"]').first.click()
        expect(page.locator(".mini-question")).to_have_count(3)
        silent(page, tag, "Learn")
        no_overflow(page, tag, "Learn")
        home_link(page, tag, "Learn").click()
        expect(page.locator(".module-card")).to_have_count(2)
        home_navigation_hidden(page, tag, "Home after Learn")

        page.locator('[data-route="setup/adjectives"]').first.click()
        expect(page.locator('[data-action="start"]')).to_be_visible()
        shot(page, tag, "setup")
        if width == 360:
            shot(page, tag, "setup-navigation", page.locator(".site-header"))
        silent(page, tag, "setup")
        no_overflow(page, tag, "setup")
        home_link(page, tag, "setup").click()
        expect(page.locator(".module-card")).to_have_count(2)
        home_navigation_hidden(page, tag, "Home after setup")
        expect(page.locator("#confirm-dialog")).not_to_be_visible()
        check(page.evaluate("location.hash") == "#home", f"{tag}: setup Lab home link navigates Home without a guard")
        if width == 360:
            shot(page, tag, "setup-to-home")

        page.locator('[data-route="setup/adjectives"]').first.click()
        page.locator('[data-action="start"]').click()
        expect(page.locator(".sentence")).to_be_visible()
        readable_labels(page.locator("#reagent-tray .block-label"), minimum, tag, "experiment tray")
        no_overflow(page, tag, "building")
        silent(page, tag, "building")
        state = saved(page)
        submit(page, state["questions"][state["index"]]["correctSequences"][0])
        expect(page.locator(".reaction.success")).to_be_visible()
        silent(page, tag, "correct submission")
        page.locator('[data-action="next"]').click()
        expect(page.locator('[data-action="submit"]')).to_be_visible()
        state = saved(page)
        question = state["questions"][state["index"]]
        # A degree-relevant connector alone is never a complete answer.
        connector = "than" if question["degree"] == "comparative" else "the"
        wrong = next(block["id"] for block in question["blocks"] if block["label"] == connector)
        submit(page, [wrong])
        expect(page.locator(".reaction.error")).to_be_visible()
        silent(page, tag, "wrong submission")
        no_overflow(page, tag, "wrong feedback")

        previous = saved(page)
        # Use the corrected top-right link, not the brand or secondary back link.
        home_link(page, tag, "active experiment").click()
        expect(page.locator("#confirm-dialog")).to_be_visible()
        expect(page.locator("#dialog-title")).to_have_text("Leave this experiment?")
        shot(page, tag, "experiment-confirmation")
        shot(page, tag, "experiment-confirmation-dialog", page.locator("#confirm-dialog"))
        page.locator('#confirm-dialog [value="cancel"]').click()
        expect(page.locator("#confirm-dialog")).not_to_be_visible()
        expect(page.locator(".reaction.error")).to_be_visible()
        check(saved(page) == previous, f"{tag}: cancelling Lab home guard preserves experiment and wrong feedback")
        page.locator(".header-nav").get_by_role("link", name="Lab home", exact=True).click()
        expect(page.locator("#confirm-dialog")).to_be_visible()
        page.locator('#confirm-dialog [value="leave"]').click()
        expect(page.locator('[data-action="resume"]')).to_be_visible()
        check(saved(page) == previous, f"{tag}: confirmed Home navigation retains unfinished experiment")
        page.wait_for_timeout(800)  # Include delayed reactions before the final audio audit.
        silent(page, tag, "returned Home after confirmation")
        no_overflow(page, tag, "returned Home")
        check(not errors, f"{tag}: no JavaScript runtime errors ({errors})")
    finally:
        context.close()
        browser.close()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        run(playwright.chromium, "desktop", 1440, 1000)
        run(playwright.webkit, "phone", 360, 800)
    (OUT / "home-ui-results.json").write_text(json.dumps(RESULTS, indent=2) + "\n")
    print("\n".join("PASS " + result for result in RESULTS))
    print(f"Passed {len(RESULTS)} focused Home UI assertions across desktop Chromium and phone WebKit.")


if __name__ == "__main__":
    main()
