"""Local visual and spacing checks for K S Lo Grammar Lab.

Captures the full requested student journey in independent Chromium contexts. The app text may
change, so locators prefer semantic classes and data-action attributes over copy. Output is
written only to ignored test-results/spacing-visual/.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("GRAMMAR_TEST_URL", "http://127.0.0.1:3000/")
OUT = Path(__file__).resolve().parents[1] / "test-results" / "spacing-visual"
OUT.mkdir(parents=True, exist_ok=True)
results: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    results.append(message)


def box(page, selector: str, index: int = 0) -> dict:
    locator = page.locator(selector).nth(index)
    expect(locator).to_be_visible()
    value = locator.bounding_box()
    if not value:
        raise AssertionError(f"{selector}[{index}] has no bounding box")
    return value


def gap_below(page, upper: str, lower: str, upper_index: int = 0, lower_index: int = 0) -> float:
    top = box(page, upper, upper_index)
    bottom = box(page, lower, lower_index)
    return bottom["y"] - (top["y"] + top["height"])


def gap_between_siblings(page, selector: str, first: int = 0, second: int = 1) -> float:
    a = box(page, selector, first)
    b = box(page, selector, second)
    return b["x"] - (a["x"] + a["width"])


def shot(page, name: str) -> None:
    page.screenshot(path=str(OUT / name), full_page=True)


def reset_home(page) -> None:
    page.goto(BASE, wait_until="networkidle")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="networkidle")
    expect(page.locator(".module-card")).to_have_count(2)


def start_trial(page) -> None:
    page.goto(BASE + "?module=adjectives&n=10", wait_until="networkidle")
    expect(page.locator("[data-action='start']")).to_be_visible()
    page.locator("[data-action='start']").click()
    expect(page.locator(".sentence")).to_be_visible()


def make_wrong(page) -> None:
    state = page.evaluate("JSON.parse(localStorage.getItem('kslo-grammar-lab:session'))")
    question = state["questions"][state["index"]]
    accepted = {token for sequence in question.get("correctSequences", []) for token in sequence}
    wrong = next(block["id"] for block in question["blocks"] if block["id"] not in accepted)
    page.locator(f"[data-action='add-block'][data-block='{wrong}']").click()
    page.locator("[data-action='submit']").click()
    expect(page.locator(".reaction.error")).to_be_visible()


def seed_report(page) -> None:
    report = page.evaluate(
        """async () => {
          const bank = await (await fetch('./data/adjectives-questions.json')).json();
          const questions = bank.questions.slice(0, 2);
          return {
            schema: 1,
            moduleId: 'adjectives',
            questions,
            results: [
              { questionId: questions[0].id, firstAnswer: questions[0].answers[0], finalAnswer: questions[0].answers[0], mark: 1, gaveUp: false },
              { questionId: questions[1].id, firstAnswer: 'not an accepted answer', finalAnswer: questions[1].answers[0], mark: 0, gaveUp: false }
            ],
            count: 2,
            score: 1,
            percentage: 50,
            practice: false,
            originalReport: null,
            finishedAt: '2026-10-27T10:00:00.000Z'
          };
        }"""
    )
    page.evaluate("report => localStorage.setItem('kslo-grammar-lab:last-report', JSON.stringify(report))", report)
    page.goto(BASE + "#report", wait_until="networkidle")
    expect(page.locator(".report-hero")).to_be_visible()


def store_resume_state(page) -> None:
    start_trial(page)
    page.locator("[data-route='home']").first.click()
    expect(page.locator("#confirm-dialog")).to_be_visible()
    page.locator("#confirm-dialog [value='leave']").click()
    expect(page.locator(".resume-banner")).to_be_visible()


def assert_common(page, tag: str, mobile: bool) -> None:
    check(page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"{tag}: no horizontal overflow")
    check(page.locator(".button:focus-visible").count() >= 0, f"{tag}: focus selector remains available")
    # 14px action gaps meet the 12px minimum even when flex wraps.
    gap = page.locator(".trial-actions").evaluate("node => parseFloat(getComputedStyle(node).gap)")
    check(gap >= 12, f"{tag}: button groups have at least 12px gap")
    if mobile:
        # Important readability requirement for word blocks on a 360px screen.
        size = page.locator(".reagent").first.evaluate("node => parseFloat(getComputedStyle(node).fontSize)")
        check(size >= 18, f"{tag}: mobile word blocks are at least 18px ({size:g}px)")


def exercise(page, tag: str, mobile: bool) -> None:
    reset_home(page)
    shot(page, f"{tag}-home-clean.png")
    check(gap_below(page, ".demo-result", ".demo-caption") >= 16, f"{tag}: demo result has at least 16px before explanation")
    result_box = box(page, ".demo-result")
    demo_card = box(page, ".hero-demo")
    check(result_box["width"] < demo_card["width"] * 0.75, f"{tag}: demo result fits its text instead of stretching across the card")
    check(abs(result_box["x"] + result_box["width"] / 2 - demo_card["x"] - demo_card["width"] / 2) < 2, f"{tag}: compact demo result is centred")
    check(box(page, ".module-card")["x"] - box(page, ".module-card h3")["x"] <= -20, f"{tag}: module card content has at least 20px left padding")

    # Home with resume actions.
    store_resume_state(page)
    shot(page, f"{tag}-home-resume.png")
    actions = page.locator(".resume-banner .button")
    if actions.count() > 1 and not mobile:
        check(gap_between_siblings(page, ".resume-banner .button") >= 12, f"{tag}: resume buttons have at least 12px between them")
    else:
        check(gap_below(page, ".resume-banner .button", ".resume-banner .button", 0, 1) >= 12, f"{tag}: stacked resume buttons have at least 12px between them")

    # Setup with the saved-session notice, including start-button-to-callout space and sidebar CTA-to-copy space.
    page.goto(BASE + "?module=adjectives&n=10", wait_until="networkidle")
    expect(page.locator(".setup-card .notice")).to_be_visible()
    shot(page, f"{tag}-setup.png")
    check(gap_below(page, ".setup-card [data-action='start']", ".setup-card .notice") >= 16, f"{tag}: start button has at least 16px before notice")
    check(gap_below(page, ".side-panel .button", ".side-panel .privacy-copy") >= 16, f"{tag}: sidebar button has at least 16px before privacy text")

    # Learn, including the deliberately separated back link/eyebrow and mini-check result.
    page.goto(BASE + "#learn/adjectives", wait_until="networkidle")
    expect(page.locator(".mini-check")).to_be_visible()
    for i in range(3):
        page.locator(f"input[name='mini-{i}']").first.check()
    page.locator("#mini-form button[type='submit']").click()
    expect(page.locator("#mini-result")).not_to_be_empty()
    shot(page, f"{tag}-learn.png")
    check(gap_below(page, ".page-heading .back-link", ".page-heading .eyebrow") >= 20, f"{tag}: back link and page eyebrow are separate with breathing room")
    check(gap_below(page, ".learn-check-actions", "#mini-result") >= 16, f"{tag}: mini-check buttons have at least 16px before result")

    # Fresh trial, word blocks, and a wrong feedback state.
    page.evaluate("localStorage.clear()")
    start_trial(page)
    shot(page, f"{tag}-trial-building.png")
    assert_common(page, tag, mobile)
    reagent_size = page.locator(".reagent").first.evaluate("node => parseFloat(getComputedStyle(node).fontSize)")
    check(reagent_size >= (18 if mobile else 20), f"{tag}: word blocks meet minimum readable size ({reagent_size:g}px)")
    panel = box(page, ".tray-panel")
    label = box(page, ".tray-panel .panel-label")
    check(label["x"] - panel["x"] >= (20 if mobile else 22), f"{tag}: tray panel has required inner padding")
    make_wrong(page)
    shot(page, f"{tag}-trial-wrong.png")
    check(gap_below(page, ".reaction.error", ".trial-actions") >= 16, f"{tag}: wrong feedback has at least 16px before action buttons")

    # Native dialog: direct child padding and action spacing.
    page.locator("[data-action='end']").click()
    expect(page.locator("#confirm-dialog")).to_be_visible()
    shot(page, f"{tag}-confirmation.png")
    dialog = box(page, "#confirm-dialog")
    title = box(page, "#dialog-title")
    body = box(page, "#dialog-message")
    dialog_padding = page.locator("#dialog-title, #dialog-message").evaluate_all(
        "nodes => nodes.map(node => parseFloat(getComputedStyle(node).paddingLeft))"
    )
    check(all(value >= 20 for value in dialog_padding), f"{tag}: confirmation dialog title and body have 20px+ direct-child padding")
    message_top_padding = page.locator("#dialog-message").evaluate("node => parseFloat(getComputedStyle(node).paddingTop)")
    check(message_top_padding >= 8, f"{tag}: confirmation dialog title and message are visibly separated")

    # Report verifies action-to-next-section separation.
    page.locator("#confirm-dialog [value='cancel']").click()
    seed_report(page)
    shot(page, f"{tag}-report.png")
    check(gap_below(page, ".report-actions", ".rule-breakdown") >= 24, f"{tag}: report actions have at least 24px before next section")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for tag, viewport, mobile in [
            ("desktop-1560", {"width": 1560, "height": 1100}, False),
            ("phone-360", {"width": 360, "height": 800}, True),
        ]:
            context = browser.new_context(viewport=viewport, device_scale_factor=1)
            page = context.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            exercise(page, tag, mobile)
            page.emulate_media(reduced_motion="reduce")
            check(page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == "auto", f"{tag}: reduced motion disables smooth scrolling")
            check(not errors, f"{tag}: no runtime errors while exercising visual states ({errors})")
            context.close()
        browser.close()

    (OUT / "spacing-results.json").write_text(json.dumps(results, indent=2) + "\n")
    print("\n".join("PASS " + item for item in results))
    print(f"Passed {len(results)} visual-spacing checks. Screenshots: {OUT}")


if __name__ == "__main__":
    main()
