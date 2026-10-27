"""Read-only Chromium visual audit for the colourful Grammar Lab redesign.

This script only creates browser-local test state and writes screenshots/results beneath
``test-results/fun-visual/``. It intentionally does not alter application files or data.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("GRAMMAR_TEST_URL", "http://127.0.0.1:3000/")
OUT = Path(__file__).resolve().parents[1] / "test-results" / "fun-visual"
OUT.mkdir(parents=True, exist_ok=True)
results: list[dict] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def screenshot(page, name: str) -> None:
    page.screenshot(path=str(OUT / name), full_page=True)


def box(page, selector: str) -> dict:
    loc = page.locator(selector).first
    expect(loc).to_be_visible()
    value = loc.bounding_box()
    if not value:
        raise AssertionError(f"No bounding box for {selector}")
    return value


def no_overflow(page, tag: str) -> None:
    scroll, width = page.evaluate("[document.documentElement.scrollWidth, innerWidth]")
    check(scroll <= width, f"{tag}: horizontal overflow ({scroll}px > {width}px)")


def start_trial(page) -> None:
    # The previous visual state may still have an active experiment in app memory.
    # End it through the same confirmation control a student sees before navigating.
    if page.locator("#confirm-dialog").evaluate("node => node.open"):
        page.locator("#confirm-dialog [value='leave']").click()
    page.goto(BASE + "?module=adjectives&n=10", wait_until="networkidle")
    if page.locator("#confirm-dialog").evaluate("node => node.open"):
        page.locator("#confirm-dialog [value='leave']").click()
    page.locator("[data-action='start']").click()
    if page.locator("#confirm-dialog").evaluate("node => node.open"):
        page.locator("#confirm-dialog [value='leave']").click()
    expect(page.locator(".sentence")).to_be_visible()


def answer_ids(page) -> list[str]:
    state = page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session'))")
    question = state["questions"][state["index"]]
    return question["correctSequences"][0]


def make_correct(page) -> None:
    for block_id in answer_ids(page):
        page.locator(f"[data-action='add-block'][data-block='{block_id}']").click()
    page.locator("[data-action='submit']").click()
    expect(page.locator(".reaction.success")).to_be_visible()


def make_wrong(page) -> None:
    state = page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session'))")
    question = state["questions"][state["index"]]
    accepted = {item for sequence in question["correctSequences"] for item in sequence}
    wrong_id = next(block["id"] for block in question["blocks"] if block["id"] not in accepted)
    page.locator(f"[data-action='add-block'][data-block='{wrong_id}']").click()
    page.locator("[data-action='submit']").click()
    expect(page.locator(".reaction.error")).to_be_visible()


def seed_report(page) -> None:
    report = page.evaluate("""async () => {
      const bank = await (await fetch('./data/adjectives-questions.json')).json();
      // The production validator deliberately rejects any not-yet-refreshed
      // superlative tray without its separate “the” ingredient. Use valid
      // comparative records for a visual-only report fixture.
      const questions = bank.questions.filter(question => question.degree === 'comparative').slice(0, 2);
      return {schema: 2, moduleId: 'adjectives', questions,
        results: [
          {questionId: questions[0].id, firstAnswer: questions[0].answers[0], finalAnswer: questions[0].answers[0], mark: 1, gaveUp: false},
          {questionId: questions[1].id, firstAnswer: 'wrong', finalAnswer: questions[1].answers[0], mark: 0, gaveUp: false}
        ], count: 2, score: 1, percentage: 50, practice: false,
        originalReport: null, finishedAt: '2026-10-27T10:00:00.000Z'};
    }""")
    page.evaluate("report => localStorage.setItem('kslo-grammar-lab:last-report', JSON.stringify(report))", report)
    page.goto(BASE + "#report", wait_until="networkidle")
    expect(page.locator(".report-hero")).to_be_visible()


def inspect_viewport(page, tag: str) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    page.goto(BASE, wait_until="networkidle")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="networkidle")
    expect(page.locator(".lab-scene")).to_be_visible()
    expect(page.locator(".lab-flask")).to_have_count(3)
    expect(page.locator(".scene-spark")).to_have_count(2)
    screenshot(page, f"{tag}-home.png")
    no_overflow(page, f"{tag} home")
    demo = box(page, ".hero-demo")
    result = box(page, ".demo-result")
    check(abs((result["x"] + result["width"] / 2) - (demo["x"] + demo["width"] / 2)) < 2, f"{tag}: compact demo result is centred")
    check(result["width"] <= 168.1, f"{tag}: demo result is at most 168px ({result['width']:.1f}px)")

    start_trial(page)
    screenshot(page, f"{tag}-trial-building.png")
    no_overflow(page, f"{tag} trial building")
    expect(page.locator(".beaker-meter")).to_have_count(1)
    heading = box(page, ".chamber-panel .panel-label h2")
    zone = box(page, ".assembly-zone")
    tray_heading = box(page, ".tray-panel .panel-label h2")
    tray_help = box(page, ".tray-help")
    check(abs(heading["x"] - zone["x"]) < 1, f"{tag}: Build heading aligns with assembly zone")
    check(abs(tray_heading["x"] - tray_help["x"]) < 1, f"{tag}: Word blocks heading aligns with tray help")
    word_size = page.locator(".reagent").first.evaluate("node => parseFloat(getComputedStyle(node).fontSize)")
    check(word_size >= (18 if page.viewport_size["width"] == 360 else 20), f"{tag}: word blocks are readable ({word_size:.0f}px)")

    make_correct(page)
    screenshot(page, f"{tag}-trial-correct.png")
    no_overflow(page, f"{tag} trial correct")
    expect(page.locator(".particle")).to_have_count(16)
    expect(page.locator(".reaction-success .chamber-panel")).to_be_visible()

    page.evaluate("localStorage.clear()")
    start_trial(page)
    make_wrong(page)
    screenshot(page, f"{tag}-trial-wrong.png")
    no_overflow(page, f"{tag} trial wrong")
    fragments = page.locator(".shatter-word span")
    expect(fragments.first).to_be_visible()
    fragment_opacity = fragments.first.evaluate("node => getComputedStyle(node).opacity")
    check(float(fragment_opacity) > 0, f"{tag}: final wrong-word scatter remains visible")

    seed_report(page)
    screenshot(page, f"{tag}-report.png")
    no_overflow(page, f"{tag} report")
    expect(page.locator(".report-score .beaker-meter.large")).to_have_count(1)
    expect(page.locator(".confetti-piece")).to_have_count(24)
    page.emulate_media(reduced_motion="reduce")
    check(page.locator(".report-confetti").evaluate("node => getComputedStyle(node).display") == "none", f"{tag}: reduced motion hides confetti")
    check(not errors, f"{tag}: no page errors: {errors}")

    results.append({"viewport": tag, "status": "pass", "word_font_px": word_size})


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for tag, viewport in (("desktop-1440", {"width": 1440, "height": 1000}), ("phone-360", {"width": 360, "height": 800})):
            context = browser.new_context(viewport=viewport, device_scale_factor=1)
            page = context.new_page()
            inspect_viewport(page, tag)
            context.close()
        browser.close()
    (OUT / "fun-visual-results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
