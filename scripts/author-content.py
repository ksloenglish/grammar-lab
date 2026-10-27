#!/usr/bin/env python3
"""Author the K S Lo Grammar Lab editable JSON content banks.

Run from anywhere: python3 /home/ubuntu/grammarlab/scripts/author-content.py
The generated deliverables are JSON only under site/data/.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site" / "data"

CAMBRIDGE_COMPARISON = "https://dictionary.cambridge.org/us/grammar/british-grammar/comparison-adjectives-bigger-biggest-more-interesting"
CAMBRIDGE_FAR = "https://dictionary.cambridge.org/us/grammar/british-grammar/farther-farthest-or-further-furthest"
EF_ADVERBS = "https://www.ef.com/wwen/english-resources/english-grammar/comparative-and-superlative-adverbs/"


def block(block_id: str, label: str, kind: str = "word", transforms: dict[str, str] | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"id": block_id, "label": label, "kind": kind}
    if transforms:
        value["transforms"] = transforms
    return value


def assemble(blocks: list[dict[str, Any]], sequence: list[str]) -> str:
    """Mirror the planned bank-engine rule: suffixes fuse with the previous token."""
    by_id = {item["id"]: item for item in blocks}
    pieces: list[str] = []
    for block_id in sequence:
        item = by_id[block_id]
        if item["kind"] == "suffix":
            if not pieces:
                raise ValueError(f"Suffix {block_id} has no preceding word")
            base = pieces[-1]
            suffix = item["label"].removeprefix("-")
            pieces[-1] = item.get("transforms", {}).get(base, base + suffix)
        else:
            pieces.append(item["label"])
    return " ".join(pieces)


def make_question(
    module: str,
    number: int,
    sentence: str,
    base: str,
    degree: str,
    rule: str,
    blocks: list[dict[str, Any]],
    sequences: list[list[str]],
    feedback: list[dict[str, str | list[str]]],
    explanation: str,
) -> dict[str, Any]:
    answers: list[str] = []
    for sequence in sequences:
        answer = assemble(blocks, sequence)
        if answer not in answers:
            answers.append(answer)
    answer_text = " or ".join(answers)
    purpose = "to compare two things" if degree == "comparative" else "for the top one in a group"
    short_feedback: list[dict[str, str | list[str]]] = []
    for item in feedback[:-1]:
        wrong_answers = item.get("answers")
        if isinstance(wrong_answers, list):
            short_feedback.append({"answers": wrong_answers, "message": f"{wrong_answers[0].capitalize()} is not right. Use {answer_text} {purpose}."})
    if degree == "comparative":
        short_explanation = f"Use {answer_text} to compare two things."
    else:
        short_explanation = f"Use {answer_text} for the top one in a group."
    short_feedback.append({"message": f"Use {answer_text} {purpose}."})
    return {
        "id": f"{'adj' if module == 'adjectives' else 'adv'}-{number:03d}",
        "sentence": sentence,
        "base": base,
        "degree": degree,
        "rule": rule,
        "blocks": blocks,
        "answers": answers,
        "correctSequences": sequences,
        "feedback": short_feedback,
        "explanation": short_explanation,
    }


def fb(*items: tuple[str, str], fallback: str) -> list[dict[str, str | list[str]]]:
    """Make three specific likely-error messages plus the mandatory item-specific fallback."""
    result: list[dict[str, str | list[str]]] = []
    for wrong_answer, message in items:
        result.append({"answers": [wrong_answer], "message": message})
    result.append({"message": fallback})
    return result


def suffix(label: str, base: str, result: str) -> dict[str, Any]:
    """Use a transform only for the named explicit base when raw joining is insufficient."""
    raw = base + label.removeprefix("-")
    return block("b1", label, "suffix", {base: result} if raw != result else None)


COMPARATIVE_TO_SUPERLATIVE = {
    "-er": "-est", "-r": "-st", "-ier": "-iest", "-ger": "-gest",
    "-ter": "-test", "-ner": "-nest", "-der": "-dest",
}
SUPERLATIVE_TO_COMPARATIVE = {value: key for key, value in COMPARATIVE_TO_SUPERLATIVE.items()}


def short_comparative(module: str, n: int, sentence: str, base: str, result: str, ending: str, rule: str) -> dict[str, Any]:
    superlative_ending = COMPARATIVE_TO_SUPERLATIVE[ending]
    superlative_result = result[:-2] + "est"
    blocks = [
        block("b0", base), suffix(ending, base, result), block("b2", "than"),
        block("b3", "more"),
        block("b4", superlative_ending, "suffix", {base: superlative_result} if base + superlative_ending.removeprefix("-") != superlative_result else None),
        block("b5", "most"),
    ]
    return make_question(
        module, n, sentence, base, "comparative", rule, blocks, [["b0", "b1", "b2"]],
        fb(
            (base + " than", f"The base form {base} does not show a comparison. Use {result} than."),
            ("more " + base + " than", f"{base.capitalize()} is being practised as a short form here, so use {result}, not more {base}."),
            (superlative_result + " than", "A superlative does not compare two things with than."),
            fallback=f"For this comparison, build {result} and then add than.",
        ),
        f"Use {result} than for this comparative form.",
    )


def short_superlative(module: str, n: int, sentence: str, base: str, result: str, ending: str, rule: str, article_in_gap: bool) -> dict[str, Any]:
    comparative_ending = SUPERLATIVE_TO_COMPARATIVE[ending]
    comparative_result = base + comparative_ending.removeprefix("-")
    if comparative_ending == "-ier":
        comparative_result = result[:-3] + "er"
    blocks = [block("b0", base), suffix(ending, base, result)]
    sequence = ["b0", "b1"]
    if article_in_gap:
        blocks.append(block("b2", "the"))
        sequence = ["b2", "b0", "b1"]
        distractor_start = 3
    else:
        distractor_start = 2
    blocks.extend([
        block(f"b{distractor_start}", "more"),
        block(f"b{distractor_start + 1}", comparative_ending, "suffix", {base: comparative_result} if base + comparative_ending.removeprefix("-") != comparative_result else None),
        block(f"b{distractor_start + 2}", "than"),
    ])
    shown = ("the " if article_in_gap else "") + result
    return make_question(
        module, n, sentence, base, "superlative", rule, blocks, [sequence],
        fb(
            (comparative_result, f"{comparative_result.capitalize()} is comparative. This sentence needs the highest degree."),
            ("more " + base, f"Use the short-form superlative {result}, not more {base}."),
            (result + " than", "Do not use than with a superlative."),
            fallback=f"For this superlative, use {shown}; the sentence already supplies any other needed word.",
        ),
        f"Use {shown}. A superlative identifies the highest degree in a group.",
    )


def long_comparative(module: str, n: int, sentence: str, base: str) -> dict[str, Any]:
    blocks = [
        block("b0", base), block("b1", "more"), block("b2", "than"),
        block("b3", "-er", "suffix"), block("b4", "most"), block("b5", "-est", "suffix"),
    ]
    return make_question(
        module, n, sentence, base, "comparative", "Longer forms", blocks, [["b1", "b0", "b2"]],
        fb(
            (base + "er than", f"Do not add -er to this longer adjective. Use more {base}."),
            ("most " + base + " than", "Most makes a superlative; a comparison with than needs more."),
            (base + "est than", "-est and than do not make this comparative form."),
            fallback=f"Use more {base} than to compare the two observed options.",
        ),
        f"{base.capitalize()} is a longer adjective here, so use more {base} than.",
    )


def long_superlative(module: str, n: int, sentence: str, base: str, article_in_gap: bool) -> dict[str, Any]:
    blocks = [block("b0", base), block("b1", "most")]
    sequence = ["b1", "b0"]
    if article_in_gap:
        blocks.append(block("b2", "the"))
        sequence = ["b2", "b1", "b0"]
        start = 3
    else:
        start = 2
    blocks.extend([
        block(f"b{start}", "-er", "suffix"),
        block(f"b{start + 1}", "-est", "suffix"),
        block(f"b{start + 2}", "than"),
    ])
    shown = ("the " if article_in_gap else "") + "most " + base
    return make_question(
        module, n, sentence, base, "superlative", "Longer forms", blocks, [sequence],
        fb(
            (base + "est", f"Do not add -est to this longer adjective. Use most {base}."),
            (base + "er", f"Do not add -er to this longer adjective. Use most {base}."),
            ("most " + base + " than", "A superlative does not use than."),
            fallback=f"Use {shown}; a superlative adjective before a noun needs the definite article unless the sentence already has it.",
        ),
        f"Use {shown}. The sentence identifies one item as the highest degree in its group.",
    )


def alternative_comparative(module: str, n: int, sentence: str, base: str, result: str, ending: str) -> dict[str, Any]:
    blocks = [
        block("b0", base), suffix(ending, base, result), block("b2", "more"), block("b3", "than"),
        block("b4", "-est", "suffix"), block("b5", "most"), block("b6", "-ier", "suffix"),
    ]
    return make_question(
        module, n, sentence, base, "comparative", "Regular forms", blocks,
        [["b0", "b1", "b3"], ["b2", "b0", "b3"]],
        fb(
            ("most " + base + " than", "Most makes a superlative, not a comparison with than."),
            (base + "est than", "A superlative ending does not go with than here."),
            (base + "ier than", f"Do not force an -ier ending onto {base}. Use {result} or more {base}."),
            fallback=f"Both {result} than and more {base} than are accepted standard alternatives here.",
        ),
        f"Both {result} than and more {base} than are accepted standard comparative forms.",
    )


def alternative_superlative(module: str, n: int, sentence: str, base: str, result: str, ending: str, article_in_gap: bool) -> dict[str, Any]:
    blocks = [block("b0", base), suffix(ending, base, result), block("b2", "most")]
    sequences = [["b0", "b1"], ["b2", "b0"]]
    start = 3
    if article_in_gap:
        blocks.append(block("b3", "the"))
        sequences = [["b3", "b0", "b1"], ["b3", "b2", "b0"]]
        start = 4
    blocks.extend([
        block(f"b{start}", "-er", "suffix"),
        block(f"b{start + 1}", "-ier", "suffix"),
        block(f"b{start + 2}", "than"),
    ])
    shown = ("the " if article_in_gap else "") + result
    return make_question(
        module, n, sentence, base, "superlative", "Regular forms", blocks, sequences,
        fb(
            (base + "er", "-er makes a comparative. This sentence needs a superlative."),
            (base + "ier", f"Do not make {base} end in -ier. Use {result} or most {base}."),
            (result + " than", "Do not use than with a superlative."),
            fallback=f"Both {shown} and {("the " if article_in_gap else "")}most {base} are accepted standard alternatives here.",
        ),
        f"Both {shown} and {("the " if article_in_gap else "")}most {base} are accepted standard superlative forms.",
    )


def irregular_adjective_comparative(n: int, sentence: str, base: str, result: str, superlative: str) -> dict[str, Any]:
    blocks = [block("b0", result), block("b1", "than"), block("b2", base), block("b3", "-er", "suffix"), block("b4", superlative)]
    return make_question(
        "adjectives", n, sentence, base, "comparative", "Irregular forms", blocks, [["b0", "b1"]],
        fb(
            (base + "er than", f"{base.capitalize()} is irregular: use {result}, not {base}er."),
            (superlative + " than", "That is a superlative; this sentence compares two items."),
            (base + " than", "The base adjective alone does not show a comparison."),
            fallback=f"Use the irregular comparative {result} than.",
        ),
        f"{base.capitalize()} changes irregularly to {result} in the comparative.",
    )


def irregular_adjective_superlative(n: int, sentence: str, base: str, result: str) -> dict[str, Any]:
    blocks = [block("b0", result), block("b1", "the"), block("b2", base), block("b3", "-est", "suffix"), block("b4", "more")]
    return make_question(
        "adjectives", n, sentence, base, "superlative", "Irregular forms", blocks, [["b1", "b0"]],
        fb(
            (base + "est", f"{base.capitalize()} is irregular: use {result}, not {base}est."),
            ("more " + base, "More makes a comparative; this sentence needs the highest degree."),
            (base, "The base adjective alone does not make a superlative."),
            fallback=f"Use the irregular superlative the {result}.",
        ),
        f"{base.capitalize()} changes irregularly to the {result} in the superlative.",
    )


def quantity_adjective_comparative(n: int, sentence: str, base: str, result: str, superlative: str) -> dict[str, Any]:
    """Practise irregular quantity adjectives where than is already in the sentence."""
    blocks = [block("b0", result), block("b1", base), block("b2", "-er", "suffix"), block("b3", superlative)]
    return make_question(
        "adjectives", n, sentence, base, "comparative", "Irregular forms", blocks, [["b0"]],
        fb(
            (base, f"The base form {base} does not make the comparison. Use {result}."),
            (base + "er", f"{base.capitalize()} does not take a plain -er ending here."),
            (superlative, f"{superlative.capitalize()} is superlative; the sentence compares two quantities."),
            fallback=f"Use the irregular comparative {result}; than is already in the sentence.",
        ),
        f"Use {result}. The sentence already supplies than after the quantity noun.",
    )


def quantity_adjective_superlative(n: int, sentence: str, base: str, result: str, comparative: str) -> dict[str, Any]:
    """Practise irregular quantity adjectives where the is already in the sentence."""
    blocks = [block("b0", result), block("b1", base), block("b2", "-est", "suffix"), block("b3", comparative)]
    return make_question(
        "adjectives", n, sentence, base, "superlative", "Irregular forms", blocks, [["b0"]],
        fb(
            (base, f"The base form {base} does not show the highest or lowest quantity."),
            (base + "est", f"{base.capitalize()} does not take a plain -est ending here."),
            (comparative, f"{comparative.capitalize()} is comparative; this sentence needs a superlative."),
            fallback=f"Use the irregular superlative {result}; the is already in the sentence.",
        ),
        f"Use {result}. The sentence already supplies the before the quantity noun.",
    )


def far_adjective_comparative(n: int, sentence: str) -> dict[str, Any]:
    blocks = [
        block("b0", "farther"), block("b1", "further"), block("b2", "than"),
        block("b3", "far"), block("b4", "-er", "suffix"), block("b5", "farthest"),
    ]
    return make_question(
        "adjectives", n, sentence, "far", "comparative", "Irregular forms", blocks,
        [["b0", "b2"], ["b1", "b2"]],
        fb(
            ("farer than", "Far does not normally take a plain -er ending in standard English."),
            ("farthest than", "Farthest is a superlative, so it does not compare two places with than."),
            ("far than", "The base form far does not make the comparison."),
            fallback="Both farther than and further than are accepted here; farther often stresses physical distance.",
        ),
        "Both farther than and further than are accepted. Farther often stresses physical distance; further also occurs with distance and broader meanings.",
    )


def far_adjective_superlative(n: int, sentence: str) -> dict[str, Any]:
    blocks = [
        block("b0", "farthest"), block("b1", "furthest"), block("b2", "the"),
        block("b3", "far"), block("b4", "-est", "suffix"), block("b5", "more"),
    ]
    return make_question(
        "adjectives", n, sentence, "far", "superlative", "Irregular forms", blocks,
        [["b2", "b0"], ["b2", "b1"]],
        fb(
            ("farest", "Far does not normally take a plain -est ending in standard English."),
            ("more far", "Use an irregular superlative, not more far."),
            ("far", "The base form far does not identify the greatest distance."),
            fallback="Both the farthest and the furthest are accepted here.",
        ),
        "Both the farthest and the furthest are accepted superlative adjective forms.",
    )


def flat_adverb_comparative(n: int, sentence: str, base: str, result: str, ending: str, rule: str) -> dict[str, Any]:
    return short_comparative("adverbs", n, sentence, base, result, ending, rule)


def flat_adverb_superlative(n: int, sentence: str, base: str, result: str, ending: str, rule: str) -> dict[str, Any]:
    # Adverbial superlatives are accepted with and without the, assembled from the same tray.
    comparative_ending = SUPERLATIVE_TO_COMPARATIVE[ending]
    comparative_result = base + comparative_ending.removeprefix("-")
    if comparative_ending == "-ier":
        comparative_result = result[:-3] + "er"
    blocks = [
        block("b0", base), suffix(ending, base, result), block("b2", "the"),
        block("b3", "more"), block("b4", comparative_ending, "suffix", {base: comparative_result} if base + comparative_ending.removeprefix("-") != comparative_result else None), block("b5", "than"),
    ]
    return make_question(
        "adverbs", n, sentence, base, "superlative", rule, blocks,
        [["b2", "b0", "b1"], ["b0", "b1"]],
        fb(
            (comparative_result, f"{comparative_result.capitalize()} is comparative. This sentence asks for the highest degree."),
            ("more " + base, f"Use the short adverb superlative {result}, not more {base}."),
            (result + " than", "Do not use than with a superlative."),
            fallback=f"Both the {result} and {result} are natural after this verb.",
        ),
        f"Both the {result} and {result} are accepted adverbial superlatives in this sentence.",
    )


def ly_adverb_comparative(n: int, sentence: str, base: str) -> dict[str, Any]:
    blocks = [
        block("b0", base), block("b1", "more"), block("b2", "than"),
        block("b3", "-er", "suffix"), block("b4", "most"), block("b5", "-est", "suffix"),
    ]
    return make_question(
        "adverbs", n, sentence, base, "comparative", "Longer forms", blocks, [["b1", "b0", "b2"]],
        fb(
            (base + "er than", f"Do not add -er to an -ly adverb such as {base}. Use more {base}."),
            ("most " + base + " than", "Most makes a superlative; a comparison with than needs more."),
            (base + " than", "The base adverb needs more to make this comparison."),
            fallback=f"Use more {base} than. Do not change the y to i or double an ending on an -ly adverb.",
        ),
        f"Use more {base} than. Most -ly adverbs use more and most, without changing y to i.",
    )


def ly_adverb_superlative(n: int, sentence: str, base: str) -> dict[str, Any]:
    blocks = [
        block("b0", base), block("b1", "most"), block("b2", "the"),
        block("b3", "-est", "suffix"), block("b4", "more"), block("b5", "than"),
    ]
    return make_question(
        "adverbs", n, sentence, base, "superlative", "Longer forms", blocks,
        [["b2", "b1", "b0"], ["b1", "b0"]],
        fb(
            (base + "est", f"Do not add -est to an -ly adverb such as {base}. Use most {base}."),
            ("more " + base, "More makes a comparative. This sentence needs the highest degree."),
            ("most " + base + " than", "Do not use than with a superlative."),
            fallback=f"Both the most {base} and most {base} are natural in this adverbial position.",
        ),
        f"Both the most {base} and most {base} are accepted adverbial superlatives.",
    )


def well_adverb_comparative(n: int, sentence: str) -> dict[str, Any]:
    blocks = [block("b0", "better"), block("b1", "than"), block("b2", "well"), block("b3", "-er", "suffix"), block("b4", "more")]
    return make_question(
        "adverbs", n, sentence, "well", "comparative", "Irregular forms", blocks, [["b0", "b1"]],
        fb(
            ("weller than", "Well is irregular as an adverb: use better, not weller."),
            ("more well than", "For how an action is done here, the standard comparative is better."),
            ("well than", "The base adverb alone does not make a comparison."),
            fallback="Use better than. Well describes how an action is done; good is the related adjective.",
        ),
        "Use better than. Well is an adverb here, describing how the plan was explained.",
    )


def well_adverb_superlative(n: int, sentence: str) -> dict[str, Any]:
    blocks = [block("b0", "best"), block("b1", "the"), block("b2", "well"), block("b3", "-est", "suffix"), block("b4", "more")]
    return make_question(
        "adverbs", n, sentence, "well", "superlative", "Irregular forms", blocks, [["b1", "b0"], ["b0"]],
        fb(
            ("wellest", "Well is irregular as an adverb: use best, not wellest."),
            ("more well", "This sentence needs a superlative, and the standard form is best."),
            ("well", "The base adverb alone does not show the highest degree."),
            fallback="Both the best and best are natural adverbial superlatives here.",
        ),
        "Use the best or best. Well is an adverb here, not the adjective good.",
    )


def badly_adverb_comparative(n: int, sentence: str) -> dict[str, Any]:
    blocks = [
        block("b0", "worse"), block("b1", "more"), block("b2", "badly"), block("b3", "than"),
        block("b4", "badlier"), block("b5", "worser"), block("b6", "worst"),
    ]
    return make_question(
        "adverbs", n, sentence, "badly", "comparative", "Irregular forms", blocks,
        [["b0", "b3"], ["b1", "b2", "b3"]],
        fb(
            ("badlier than", "Do not change badly to badlier. Use worse, or more badly in this manner context."),
            ("worser than", "Worse is already the irregular comparative; worser is not standard here."),
            ("worst than", "Worst is a superlative, not a comparison with than."),
            fallback="Both worse than and more badly than are accepted in this context.",
        ),
        "Worse than is the usual irregular form. More badly than is also natural when focusing on the manner or extent of damage.",
    )


def badly_adverb_superlative(n: int, sentence: str) -> dict[str, Any]:
    blocks = [
        block("b0", "worst"), block("b1", "most"), block("b2", "badly"), block("b3", "the"),
        block("b4", "badlier"), block("b5", "worse"), block("b6", "than"),
    ]
    return make_question(
        "adverbs", n, sentence, "badly", "superlative", "Irregular forms", blocks,
        [["b3", "b0"], ["b0"], ["b3", "b1", "b2"], ["b1", "b2"]],
        fb(
            ("badlier", "Do not make badly into badlier. Use worst, or most badly in this manner context."),
            ("worse", "Worse is comparative; this sentence needs the highest degree."),
            ("worst than", "Do not use than with a superlative."),
            fallback="Worst and most badly are both accepted here; the is optional with these adverbial superlatives.",
        ),
        "Use worst or most badly. With an adverbial superlative, the may be included or omitted when natural.",
    )


def far_adverb_comparative(n: int, sentence: str) -> dict[str, Any]:
    blocks = [
        block("b0", "farther"), block("b1", "further"), block("b2", "than"),
        block("b3", "far"), block("b4", "-er", "suffix"), block("b5", "farthest"),
    ]
    return make_question(
        "adverbs", n, sentence, "far", "comparative", "Irregular forms", blocks,
        [["b0", "b2"], ["b1", "b2"]],
        fb(
            ("farer than", "Far does not normally take a plain -er ending in standard English."),
            ("farthest than", "Farthest is a superlative, so it does not compare two actions with than."),
            ("far than", "The base adverb far does not make the comparison."),
            fallback="Both farther than and further than are accepted in this distance context.",
        ),
        "Both farther than and further than are accepted. Farther often stresses physical distance.",
    )


def far_adverb_superlative(n: int, sentence: str) -> dict[str, Any]:
    blocks = [
        block("b0", "farthest"), block("b1", "furthest"), block("b2", "the"),
        block("b3", "farther"), block("b4", "further"), block("b5", "than"),
    ]
    return make_question(
        "adverbs", n, sentence, "far", "superlative", "Irregular forms", blocks,
        [["b2", "b0"], ["b0"], ["b2", "b1"], ["b1"]],
        fb(
            ("farther", "Farther is comparative; this sentence needs the greatest distance."),
            ("further", "Further is comparative; this sentence needs the greatest distance."),
            ("farthest than", "Do not use than with a superlative."),
            fallback="Both (the) farthest and (the) furthest are accepted adverbial superlatives here.",
        ),
        "Both the farthest/farthest and the furthest/furthest are accepted adverbial superlatives.",
    )


def adjective_bank() -> dict[str, Any]:
    questions: list[dict[str, Any]] = []
    n = 1

    regular_pairs = [
        ("tall", "taller", "tallest", "The school gate is _____ than the side gate.", "This is the _____ boy in the class."),
        ("clean", "cleaner", "cleanest", "My desk is _____ than your desk.", "This is the _____ classroom in the school."),
        ("bright", "brighter", "brightest", "This shirt is _____ than that shirt.", "This is the _____ light in the room."),
        ("short", "shorter", "shortest", "The walk to school is _____ than the walk to the shop.", "This is the _____ road home."),
        ("warm", "warmer", "warmest", "Today is _____ than yesterday.", "This is the _____ day this week."),
        ("old", "older", "oldest", "My phone is _____ than my sister's phone.", "This is the _____ photo at home."),
        ("strong", "stronger", "strongest", "This bag is _____ than that bag.", "Ming is the _____ player on the team."),
        ("kind", "kinder", "kindest", "May was _____ than Tom today.", "May is the _____ student in the group."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in regular_pairs:
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, "-er", "Regular forms")); n += 1
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, "-est", "Regular forms", article_in_gap=False)); n += 1

    e_pairs = [
        ("large", "larger", "largest", "The school hall is _____ than our classroom.", "The red bag is the _____ bag here."),
        ("nice", "nicer", "nicest", "This shop is _____ than the old shop.", "This is the _____ cake in the shop."),
        ("safe", "safer", "safest", "The zebra crossing is _____ than the small road.", "The teacher chose _____ way home."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in e_pairs:
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, "-r", "Spelling changes")); n += 1
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, "-st", "Spelling changes", article_in_gap=base in {"safe", "late"})); n += 1

    doubled_pairs = [
        ("big", "bigger", "biggest", "My lunch box is _____ than yours.", "This is the _____ box in the room."),
        ("hot", "hotter", "hottest", "This soup is _____ than my tea.", "This is the _____ day in July."),
        ("thin", "thinner", "thinnest", "This paper is _____ than that paper.", "This is the _____ book on the shelf."),
        ("wet", "wetter", "wettest", "The floor by the door is _____ than the floor by the window.", "This is the _____ part of the playground."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in doubled_pairs:
        comp_ending = {"big": "-ger", "hot": "-ter", "thin": "-ner", "wet": "-ter"}[base]
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, comp_ending, "Spelling changes")); n += 1
        ending = {"big": "-gest", "hot": "-test", "thin": "-nest", "wet": "-test"}[base]
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, ending, "Spelling changes", article_in_gap=False)); n += 1

    y_pairs = [
        ("easy", "easier", "easiest", "This question is _____ than the last one.", "This is the _____ question in the test."),
        ("busy", "busier", "busiest", "The canteen is _____ than the library at lunch time.", "Monday is the _____ day at school."),
        ("noisy", "noisier", "noisiest", "The bus is _____ than the library.", "This is the _____ room in the school."),
        ("happy", "happier", "happiest", "Tom was _____ after the game than before it.", "This is the _____ day of my week."),
        ("heavy", "heavier", "heaviest", "My school bag is _____ than my sister's bag.", "This is the _____ bag in the class."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in y_pairs:
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, "-ier", "Spelling changes")); n += 1
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, "-iest", "Spelling changes", article_in_gap=False)); n += 1

    long_pairs = [
        ("careful", "Ming was _____ than Tom with the glass cups.", "This is the _____ set of rules for the game.", False),
        ("interesting", "This book is _____ than that book.", "This is _____ story in the book.", True),
        ("useful", "This map is _____ than the old map.", "The bus card is the _____ card in my bag.", False),
        ("popular", "Football is _____ than tennis at our school.", "This is _____ game in the class.", True),
        ("practical", "A small bag is _____ than a large bag for this trip.", "This is the _____ idea for school.", False),
        ("beautiful", "This new shop sign is _____ than the old one.", "This is _____ picture in the room.", True),
        ("important", "A school ID card is _____ than a new pen.", "This is the _____ rule in the room.", False),
        ("comfortable", "This chair is _____ than that chair.", "This is _____ seat on the bus.", True),
        ("reliable", "This bus is _____ than the old bus.", "This is the _____ bus route home.", False),
        ("creative", "Ming's poster is _____ than Tom's poster.", "This is _____ idea in the class.", True),
        ("expensive", "This phone is _____ than that phone.", "This is the _____ thing in the shop.", False),
        ("dangerous", "Running on a wet floor is _____ than walking.", "This is _____ road near the school.", True),
    ]
    for base, comp_sentence, sup_sentence, article_in_gap in long_pairs:
        questions.append(long_comparative("adjectives", n, comp_sentence, base)); n += 1
        questions.append(long_superlative("adjectives", n, sup_sentence, base, article_in_gap=article_in_gap)); n += 1

    alternatives = [
        ("quiet", "quieter", "quietest", "-er", "The library is _____ than the canteen.", "This is _____ place in the library."),
        ("clever", "cleverer", "cleverest", "-er", "Ming's answer is _____ than Tom's answer.", "This is _____ idea in the group."),
        ("narrow", "narrower", "narrowest", "-er", "This path is _____ than the road.", "This is _____ path in the park."),
        ("simple", "simpler", "simplest", "-r", "The second rule is _____ than the first rule.", "This is _____ way to go home."),
    ]
    for base, comparative, superlative, ending, comp_sentence, sup_sentence in alternatives:
        questions.append(alternative_comparative("adjectives", n, comp_sentence, base, comparative, ending)); n += 1
        questions.append(alternative_superlative("adjectives", n, sup_sentence, base, superlative, "-st" if base != "simple" else "-st", article_in_gap=sup_sentence.startswith("This is _____"))); n += 1

    irregular_pairs = [
        ("good", "better", "best", "This new pen is _____ than my old pen.", "This is _____ pen in the shop."),
        ("good", "better", "best", "The new bus route is _____ than the old route.", "This is _____ way to school."),
        ("bad", "worse", "worst", "The rain today is _____ than yesterday's rain.", "This is _____ weather this week."),
        ("bad", "worse", "worst", "This bus ride is _____ than the last one.", "This is _____ bus ride this week."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in irregular_pairs:
        questions.append(irregular_adjective_comparative(n, comp_sentence, base, comparative, superlative)); n += 1
        questions.append(irregular_adjective_superlative(n, sup_sentence, base, superlative)); n += 1

    questions.append(far_adjective_comparative(n, "The shop is _____ the school is from my home.")); n += 1
    questions.append(far_adjective_superlative(n, "This is _____ bus stop from my home.")); n += 1
    questions.append(far_adjective_comparative(n, "The park is _____ the school is from my home.")); n += 1
    questions.append(far_adjective_superlative(n, "This is _____ shop from our school.")); n += 1

    quantity_sets = [
        ("little", "less", "least", "There is _____ water in this bottle than in that bottle.", "This bottle has the _____ water."),
        ("little", "less", "least", "There is _____ rice in this bowl than in that bowl.", "This bowl has the _____ rice."),
        ("much", "more", "most", "There is _____ tea in this cup than in that cup.", "This cup has the _____ tea."),
        ("much", "more", "most", "There is _____ time before lunch than before class.", "This plan gives us the _____ time."),
        ("many", "more", "most", "There are _____ books in this bag than in that bag.", "This bag has the _____ books."),
        ("many", "more", "most", "There are _____ chairs in Room B than in Room A.", "Room B has the _____ chairs."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in quantity_sets:
        questions.append(quantity_adjective_comparative(n, comp_sentence, base, comparative, superlative)); n += 1
        questions.append(quantity_adjective_superlative(n, sup_sentence, base, superlative, comparative)); n += 1

    assert n == 97 and len(questions) == 96
    return {"module": "adjectives", "questions": questions}


def adverb_bank() -> dict[str, Any]:
    questions: list[dict[str, Any]] = []
    n = 1

    flat_pairs = [
        ("fast", "faster", "fastest", "Ming ran _____ than Tom in PE.", "Of the runners, Ming ran _____."),
        ("hard", "harder", "hardest", "I worked _____ than my friend today.", "Of the students, I worked _____."),
        ("high", "higher", "highest", "Ming threw the ball _____ than Tom.", "Of the players, Ming threw the ball _____."),
        ("low", "lower", "lowest", "The class spoke _____ than the teacher.", "Of the groups, this group spoke _____."),
        ("long", "longer", "longest", "The bell rang _____ than yesterday.", "Of the bells, this one rang _____."),
        ("fast", "faster", "fastest", "Our team packed _____ than the other team.", "Of the teams, our team packed _____."),
        ("hard", "harder", "hardest", "Tom studied _____ than before the test.", "Of the class, Tom studied _____."),
        ("high", "higher", "highest", "The ball bounced _____ than before.", "Of the balls, the red ball bounced _____."),
        ("low", "lower", "lowest", "The music played _____ than before.", "Of the songs, this song played _____."),
        ("long", "longer", "longest", "The bus waited _____ than usual.", "Of the buses, this bus waited _____."),
        ("near", "nearer", "nearest", "Ming stood _____ to the door than Tom.", "Of the students, Ming stood _____ to the door."),
        ("soon", "sooner", "soonest", "Bus 2 came _____ than Bus 1.", "Of the buses, Bus 2 came _____."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in flat_pairs:
        comp_ending, sup_ending = "-er", "-est"
        questions.append(flat_adverb_comparative(n, comp_sentence, base, comparative, comp_ending, "Regular forms")); n += 1
        questions.append(flat_adverb_superlative(n, sup_sentence, base, superlative, sup_ending, "Regular forms")); n += 1

    spelling_pairs = [
        ("late", "later", "latest", "Bus 1 arrived _____ than Bus 2.", "Of the buses, Bus 1 arrived _____."),
        ("late", "later", "latest", "My group finished _____ than your group.", "Of the groups, my group finished _____."),
        ("late", "later", "latest", "Tom came home _____ than May.", "Of my friends, Tom came home _____."),
        ("late", "later", "latest", "The shop opened _____ than we thought.", "Of the shops, the small shop opened _____."),
        ("late", "later", "latest", "The bell rang _____ than usual.", "Of the bells, this bell rang _____."),
        ("late", "later", "latest", "I got home _____ than my sister.", "Of my family, I got home _____."),
        ("early", "earlier", "earliest", "The library opened _____ than yesterday.", "Of the days, the library opened _____ on Monday."),
        ("early", "earlier", "earliest", "The bus left _____ than usual.", "Of the buses, Bus 1 left _____."),
        ("early", "earlier", "earliest", "Ming came to school _____ than Tom.", "Of the students, Ming came _____."),
        ("early", "earlier", "earliest", "Our class started _____ than the other class.", "Of the classes, our class started _____."),
        ("early", "earlier", "earliest", "The shop opened _____ than the bank.", "Of the shops, this one opened _____."),
        ("early", "earlier", "earliest", "The sun came up _____ in summer than in winter.", "Of the days, the sun came up _____."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in spelling_pairs:
        comp_ending, sup_ending = ("-r", "-st") if base == "late" else ("-ier", "-iest")
        questions.append(flat_adverb_comparative(n, comp_sentence, base, comparative, comp_ending, "Spelling changes")); n += 1
        questions.append(flat_adverb_superlative(n, sup_sentence, base, superlative, sup_ending, "Spelling changes")); n += 1

    ly_pairs = [
        ("carefully", "Ming wrote _____ than Tom.", "Of the students, Ming wrote _____."),
        ("quietly", "The class walked _____ than before.", "Of the groups, this group walked _____."),
        ("clearly", "The teacher spoke _____ than before.", "Of the teachers, this teacher spoke _____."),
        ("easily", "Jia found the new bus stop _____ than the old one.", "Of the bus stops, this one was found _____."),
        ("quickly", "My team finished _____ than the other team.", "Of the teams, my team finished _____."),
        ("slowly", "The bus moved _____ than before.", "Of the buses, this bus moved _____."),
        ("happily", "Tom smiled _____ after the game than before it.", "Of the students, Tom smiled _____."),
        ("regularly", "The school bus came _____ this month than last month.", "Of the buses, this bus came _____."),
        ("seriously", "Ming listened _____ than before.", "Of the students, Ming listened _____."),
        ("successfully", "Our team finished the game _____ than last time.", "Of the teams, our team finished the game _____."),
        ("loudly", "The boy spoke _____ than before.", "Of the children, this boy spoke _____."),
        ("correctly", "The new clock showed the time _____ than the old clock.", "Of the clocks, this clock showed the time _____."),
    ]
    for base, comp_sentence, sup_sentence in ly_pairs:
        questions.append(ly_adverb_comparative(n, comp_sentence, base)); n += 1
        questions.append(ly_adverb_superlative(n, sup_sentence, base)); n += 1

    well_pairs = [
        ("The blue team explained its plan _____ than the red team.", "Of the teams, the blue team explained its plan _____."),
        ("Jia answered the question _____ than before.", "Of the students, Jia answered the question _____."),
        ("The class used the new microphone _____ than before.", "Of the groups, this group used the microphone _____."),
        ("Tom showed us the game _____ than May.", "Of the students, Tom showed us the game _____."),
    ]
    for comp_sentence, sup_sentence in well_pairs:
        questions.append(well_adverb_comparative(n, comp_sentence)); n += 1
        questions.append(well_adverb_superlative(n, sup_sentence)); n += 1

    badly_pairs = [
        ("The rain damaged the paper sign _____ than the plastic sign.", "Of the signs, the paper one was damaged _____."),
        ("Water marked the blue card _____ than the red card.", "Of the cards, the blue card was marked _____."),
        ("The old bus worked _____ than the new bus.", "Of the buses, the old bus worked _____."),
        ("The old microphone worked _____ than before.", "Of the microphones, the old one worked _____."),
    ]
    for comp_sentence, sup_sentence in badly_pairs:
        questions.append(badly_adverb_comparative(n, comp_sentence)); n += 1
        questions.append(badly_adverb_superlative(n, sup_sentence)); n += 1

    far_pairs = [
        ("The red ball rolled _____ than the blue ball.", "Of the balls, the red ball rolled _____."),
        ("The green marble rolled _____ than the red marble.", "Of the marbles, the green marble rolled _____."),
        ("Jia's beanbag travelled _____ than Kai's beanbag.", "Of the beanbags, Jia's travelled _____."),
        ("The blue counter moved _____ than the yellow counter.", "Of the counters, the blue counter moved _____."),
    ]
    for comp_sentence, sup_sentence in far_pairs:
        questions.append(far_adverb_comparative(n, comp_sentence)); n += 1
        questions.append(far_adverb_superlative(n, sup_sentence)); n += 1

    assert n == 97 and len(questions) == 96
    return {"module": "adverbs", "questions": questions}


def learn_files() -> tuple[dict[str, Any], dict[str, Any]]:
    adjective_learn = {
        "module": "adjectives",
        "intro": "Use a comparative to compare two things: tall → taller. Use a superlative to show the top one in a group: tall → tallest.",
        "sections": [
            {
                "title": "Short adjectives: -er and -est",
                "text": "For many short adjectives, add -er or -est: tall → taller → tallest. If the word ends in -e, add -r or -st: large → larger → largest. Double the last letter in short words such as big → bigger → biggest.",
                "examples": ["My bag is bigger than your bag.", "This is the largest room in the school."],
                "note": "Do not double w, x or y.",
            },
            {
                "title": "Adjectives ending in -y",
                "text": "For easy, busy, noisy, happy and heavy, change y to i: easy → easier → easiest. But shy keeps y: shy → shyer → shyest.",
                "examples": ["This question is easier than the last one.", "The canteen is the noisiest place at school."],
            },
            {
                "title": "Longer adjectives and two correct forms",
                "text": "Use more and most with longer adjectives: more careful; the most interesting. With quiet, clever, narrow and simple, two forms can be right.",
                "examples": ["This map is more useful than the old map.", "This is the simplest way home.", "This is the most simple way home."],
                "note": "Both listed forms are accepted in this course.",
            },
            {
                "title": "Irregular forms and far",
                "text": "Good → better → best. Bad → worse → worst. For distance, use farther/farthest or further/furthest. Both are correct.",
                "examples": ["This bus route is better than the old route.", "This is the farthest shop from our school."],
            },
            {
                "title": "Common mistakes",
                "text": "Use one pattern only: easier, not more easier; the fastest, not the most fastest.",
                "examples": ["The second question is easier than the first.", "She chose the most interesting book."],
            },
            {
                "title": "Than, the, good and well",
                "text": "Use than after a comparative: cleaner than the old desk. Use the before a superlative adjective and a noun: the cleanest desk. Use good before a noun. Use well to say how someone does something.",
                "examples": ["The plan is good.", "She explained the plan well."],
            },
        ],
        "miniCheck": [
            {
                "sentence": "The school hall is _____ than our classroom.",
                "options": ["larger", "largeer", "more large"],
                "answer": "larger",
                "explanation": "Large ends in -e, so add -r: larger.",
            },
            {
                "sentence": "Of the three bags, the red bag is the _____.",
                "options": ["best", "goodest", "most good"],
                "answer": "best",
                "explanation": "Good is irregular: good → better → best.",
            },
            {
                "sentence": "This is the _____ place in the library.",
                "options": ["quietest", "quieter", "quietiest"],
                "answer": "quietest",
                "explanation": "Use quietest. The most quiet is also correct, but it is not an option here.",
            },
        ],
        "sources": [
            {"title": "Cambridge Dictionary Grammar: Comparison: adjectives", "url": CAMBRIDGE_COMPARISON},
            {"title": "Cambridge Dictionary Grammar: Farther, farthest or further, furthest?", "url": CAMBRIDGE_FAR},
        ],
    }
    adverb_learn = {
        "module": "adverbs",
        "intro": "An adverb tells us how an action happens. Use a comparative adverb to compare two actions. Use a superlative adverb for the top one in a group.",
        "sections": [
            {
                "title": "Short adverbs: -er and -est",
                "text": "Fast, hard, high, low and long take -er and -est: faster/fastest and harder/hardest. For late, add -r and -st: later/latest. For early, change y to i: earlier/earliest.",
                "examples": ["Ming ran faster than Tom.", "The library opened earliest on Monday."],
            },
            {
                "title": "Most -ly adverbs: more and most",
                "text": "Most adverbs ending in -ly use more and most: more carefully; most carefully. Do not add -er or -est to these adverbs. Early is different: earlier/earliest.",
                "examples": ["The teacher spoke more clearly than before.", "Ming wrote most carefully."],
                "note": "Do not change -ly to -lier or -liest.",
            },
            {
                "title": "Irregular forms and far",
                "text": "Well → better → best. Badly → worse → worst. For damage, more badly and most badly can also be right. For distance, use farther/farthest or further/furthest.",
                "examples": ["Jia answered the question better than before.", "The rain damaged the paper sign most badly."],
            },
            {
                "title": "Common mistakes",
                "text": "Use faster, not more fast. Use more easily, not easilier. Use one pattern only.",
                "examples": ["Our team finished faster than the other team.", "Jia found the new bus stop more easily."],
            },
            {
                "title": "Than, optional the, and hardly",
                "text": "Use than after a comparative: more quickly than the other team. With a superlative adverb, the is often optional: She ran the fastest / She ran fastest. Hard means with effort. Hardly means almost not.",
                "examples": ["Tom worked harder than usual.", "Of the runners, Ming ran the fastest.", "I could hardly hear the teacher."],
            },
        ],
        "miniCheck": [
            {
                "sentence": "The teacher spoke _____ than before.",
                "options": ["more clearly", "clearer", "clearliest"],
                "answer": "more clearly",
                "explanation": "Clearly ends in -ly, so use more clearly.",
            },
            {
                "sentence": "Of the three teams, the blue team played _____.",
                "options": ["best", "goodest", "more well"],
                "answer": "best",
                "explanation": "Well is irregular: well → better → best. The best is also correct here.",
            },
            {
                "sentence": "Of the three buses, Bus 2 arrived _____.",
                "options": ["earliest", "earlier", "earlyest"],
                "answer": "earliest",
                "explanation": "Early changes y to i: early → earlier → earliest. The earliest is also correct here.",
            },
        ],
        "sources": [
            {"title": "EF English Grammar: Comparative and superlative adverbs", "url": EF_ADVERBS},
            {"title": "Cambridge Dictionary Grammar: Farther, farthest or further, furthest?", "url": CAMBRIDGE_FAR},
        ],
    }
    return adjective_learn, adverb_learn


def modules_file() -> dict[str, Any]:
    return {
        "modules": [
            {
                "id": "adjectives",
                "title": "Comparative & superlative adjectives",
                "shortTitle": "Adjectives",
                "description": "Build accurate adjective comparisons, superlatives, spelling changes and accepted alternatives.",
                "symbol": "Aa",
                "accent": "teal",
                "available": True,
                "bank": "adjectives-questions.json",
                "learn": "adjectives-learn.json",
            },
            {
                "id": "adverbs",
                "title": "Comparative & superlative adverbs",
                "shortTitle": "Adverbs",
                "description": "Practise how actions happen with regular, -ly and irregular adverb forms.",
                "symbol": "Av",
                "accent": "violet",
                "available": True,
                "bank": "adverbs-questions.json",
                "learn": "adverbs-learn.json",
            },
            {
                "id": "passive",
                "title": "Passive voice",
                "shortTitle": "Passive",
                "description": "Coming soon: build accurate passive voice sentences.",
                "symbol": "Pv",
                "accent": "slate",
                "available": False,
            },
            {
                "id": "present-simple",
                "title": "Present simple",
                "shortTitle": "Present simple",
                "description": "Coming soon: practise routines, facts and present simple forms.",
                "symbol": "Ps",
                "accent": "slate",
                "available": False,
            },
            {
                "id": "past-simple",
                "title": "Past simple",
                "shortTitle": "Past simple",
                "description": "Coming soon: practise completed actions in the past.",
                "symbol": "Pa",
                "accent": "slate",
                "available": False,
            },
            {
                "id": "present-continuous",
                "title": "Present continuous",
                "shortTitle": "Present continuous",
                "description": "Coming soon: practise actions happening now.",
                "symbol": "Pc",
                "accent": "slate",
                "available": False,
            },
            {
                "id": "past-continuous",
                "title": "Past continuous",
                "shortTitle": "Past continuous",
                "description": "Coming soon: practise actions in progress in the past.",
                "symbol": "Pt",
                "accent": "slate",
                "available": False,
            },
            {
                "id": "perfect-tenses",
                "title": "Perfect tenses",
                "shortTitle": "Perfect tenses",
                "description": "Coming soon: connect actions and times with perfect tenses.",
                "symbol": "Pf",
                "accent": "slate",
                "available": False,
            },
        ]
    }


def validate_bank(bank: dict[str, Any]) -> dict[str, Any]:
    module = bank["module"]
    questions = bank["questions"]
    expected_prefix = "adj-" if module == "adjectives" else "adv-"
    assert len(questions) == 96, f"{module}: expected 96 questions"
    assert len({q["id"] for q in questions}) == len(questions), f"{module}: duplicate question ids"
    assert all(q["id"].startswith(expected_prefix) for q in questions), f"{module}: wrong id prefix"
    assert Counter(q["degree"] for q in questions) == Counter({"comparative": 48, "superlative": 48}), f"{module}: unbalanced degrees"
    rule_counts = Counter(q["rule"] for q in questions)
    assert rule_counts == Counter({"Regular forms": 24, "Spelling changes": 24, "Longer forms": 24, "Irregular forms": 24}), f"{module}: unbalanced rule groups"
    for q in questions:
        assert q["sentence"].count("_____") == 1, f"{q['id']}: gap must appear exactly once"
        assert len(q["feedback"]) >= 4, f"{q['id']}: needs 3 specifics plus fallback"
        assert q["feedback"][-1].keys() == {"message"}, f"{q['id']}: final feedback must be fallback"
        ids = [b["id"] for b in q["blocks"]]
        labels = [b["label"] for b in q["blocks"]]
        assert len(ids) == len(set(ids)), f"{q['id']}: duplicate block id"
        assert len(labels) == len(set(labels)), f"{q['id']}: duplicate block label"
        used = set()
        built = []
        for sequence in q["correctSequences"]:
            assert sequence, f"{q['id']}: empty correct sequence"
            assert set(sequence) <= set(ids), f"{q['id']}: sequence references unavailable block"
            answer = assemble(q["blocks"], sequence)
            built.append(answer)
            used.update(sequence)
        assert set(q["answers"]) == set(built), f"{q['id']}: answer not constructible"
        distractor_count = len(q["blocks"]) - len(used)
        assert distractor_count == 3, f"{q['id']}: expected 3 distractor blocks, got {distractor_count}"
        for entry in q["feedback"][:-1]:
            assert "message" in entry and ("answers" in entry or "pattern" in entry), f"{q['id']}: malformed targeted feedback"
            if "answers" in entry:
                assert not (set(entry["answers"]) & set(q["answers"])), f"{q['id']}: feedback targets a correct answer"
            if "pattern" in entry:
                re.compile(str(entry["pattern"]))
    return {"count": len(questions), "degrees": dict(Counter(q["degree"] for q in questions)), "rules": dict(rule_counts)}


def validate_learn(learn: dict[str, Any]) -> None:
    assert len(learn["miniCheck"]) == 3, f"{learn['module']}: must have exactly 3 mini checks"
    for check in learn["miniCheck"]:
        assert check["sentence"].count("_____") == 1
        assert check["answer"] in check["options"]


def dump(name: str, content: dict[str, Any]) -> None:
    (DATA / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    adjectives = adjective_bank()
    adverbs = adverb_bank()
    adjective_learn, adverb_learn = learn_files()
    adjective_report = validate_bank(adjectives)
    adverb_report = validate_bank(adverbs)
    validate_learn(adjective_learn)
    validate_learn(adverb_learn)

    dump("adjectives-questions.json", adjectives)
    dump("adverbs-questions.json", adverbs)
    dump("adjectives-learn.json", adjective_learn)
    dump("adverbs-learn.json", adverb_learn)

    print(json.dumps({"adjectives": adjective_report, "adverbs": adverb_report}, indent=2))


if __name__ == "__main__":
    main()
