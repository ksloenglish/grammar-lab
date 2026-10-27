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
    return {
        "id": f"{'adj' if module == 'adjectives' else 'adv'}-{number:03d}",
        "sentence": sentence,
        "base": base,
        "degree": degree,
        "rule": rule,
        "blocks": blocks,
        "answers": answers,
        "correctSequences": sequences,
        "feedback": feedback,
        "explanation": explanation,
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
        ("tall", "taller", "tallest", "The drama-room doorway is _____ than the music-room doorway.", "This is the _____ display stand in the corridor."),
        ("clean", "cleaner", "cleanest", "After the tidy-up, this table is _____ than it was before.", "Of the four worktables, this is the _____ one after the tidy-up."),
        ("bright", "brighter", "brightest", "The new notice is _____ than the old notice.", "Mina chose the _____ card for the science display."),
        ("short", "shorter", "shortest", "This route is _____ than the route through the playground.", "This is the _____ queue at the lunchtime rehearsal."),
        ("warm", "warmer", "warmest", "The library corner feels _____ than the corridor today.", "The sunny bench is the _____ place in this sketch of the playground."),
        ("old", "older", "oldest", "The printed timetable is _____ than the online copy.", "This is the _____ photo in the class history display."),
        ("strong", "stronger", "strongest", "The second paper bridge is _____ than the first one.", "This is the _____ glue in our fictional materials test."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in regular_pairs:
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, "-er", "Regular forms")); n += 1
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, "-est", "Regular forms", article_in_gap=False)); n += 1

    e_pairs = [
        ("large", "larger", "largest", "This classroom is _____ than the art room.", "The hall poster is the _____ item in the display."),
        ("nice", "nicer", "nicest", "The revised title is _____ than the first title.", "Of the three welcome cards, this is the _____ one."),
        ("safe", "safer", "safest", "The marked route is _____ than the shortcut beside the store room.", "The teacher chose _____ route for the equipment trolley."),
        ("late", "later", "latest", "The second rehearsal begins _____ than the first rehearsal.", "The notice on the board gives _____ starting time."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in e_pairs:
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, "-r", "Spelling changes")); n += 1
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, "-st", "Spelling changes", article_in_gap=base in {"safe", "late"})); n += 1

    doubled_pairs = [
        ("big", "bigger", "biggest", "The cardboard box is _____ than the sample tray.", "The stage model is the _____ object in the design sketch."),
        ("hot", "hotter", "hottest", "The tea in this flask is _____ than the tea in that flask.", "This is the _____ day in our imaginary weather chart."),
        ("thin", "thinner", "thinnest", "This marker is _____ than the blue marker.", "This is the _____ line in the poster design."),
        ("wet", "wetter", "wettest", "The path beside the tap is _____ than the path near the gate.", "This is the _____ part of the pretend playground map after rain."),
        ("sad", "sadder", "saddest", "The ending of the second story is _____ than the ending of the first story.", "This is the _____ scene in the class-made comic."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in doubled_pairs:
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, "-ger" if base == "big" else "-er", "Spelling changes")); n += 1
        ending = {"big": "-gest", "hot": "-test", "thin": "-nest", "wet": "-test", "sad": "-dest"}[base]
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, ending, "Spelling changes", article_in_gap=False)); n += 1

    y_pairs = [
        ("easy", "easier", "easiest", "This clue is _____ than the final clue.", "This is the _____ question on the practice sheet."),
        ("busy", "busier", "busiest", "The library is _____ than the study room at lunchtime.", "The entrance is the _____ area on this school-event map."),
        ("noisy", "noisier", "noisiest", "The canteen is _____ than the reading corner during the break.", "This is the _____ part of the sound-recording task."),
        ("happy", "happier", "happiest", "The class looked _____ after the successful rehearsal.", "This is the _____ face in the illustrated feedback chart."),
        ("heavy", "heavier", "heaviest", "This bag of textbooks is _____ than the bag of worksheets.", "This is the _____ box in the fictional delivery list."),
        ("tidy", "tidier", "tidiest", "Ravi's desk is _____ than it was yesterday.", "This is the _____ table after the group sorting task."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in y_pairs:
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, "-ier", "Spelling changes")); n += 1
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, "-iest", "Spelling changes", article_in_gap=False)); n += 1

    long_pairs = [
        ("careful", "The second pair was _____ than the first pair while carrying the glass beakers.", "This is the _____ set of instructions in the practical booklet."),
        ("interesting", "The visitor's second example was _____ than the first example.", "This is _____ article in the class magazine."),
        ("useful", "The labelled diagram is _____ than the unlabelled diagram.", "The checklist is the _____ page in the revision pack."),
        ("popular", "The chess club was _____ than the board-game club at the fictional activity fair.", "This is _____ choice on the mock survey board."),
        ("practical", "The foldable stand is _____ than the large display frame.", "This is the _____ solution in our design discussion."),
        ("colourful", "The new mural is _____ than the old noticeboard.", "This is _____ poster in the art-club gallery."),
        ("important", "The safety sign is _____ than the decoration for this drill.", "This is the _____ reminder on the laboratory door."),
    ]
    for base, comp_sentence, sup_sentence in long_pairs:
        questions.append(long_comparative("adjectives", n, comp_sentence, base)); n += 1
        questions.append(long_superlative("adjectives", n, sup_sentence, base, article_in_gap=not sup_sentence.startswith("This is the") and not sup_sentence.startswith("This is _____"))) ; n += 1

    alternatives = [
        ("quiet", "quieter", "quietest", "-er", "The reading room is _____ than the corridor at break time.", "This is the _____ corner in the library plan."),
        ("clever", "cleverer", "cleverest", "-er", "The revised solution is _____ than the first solution.", "This is _____ idea in the group brainstorm."),
        ("narrow", "narrower", "narrowest", "-er", "This shelf is _____ than the display shelf.", "This is the _____ aisle in the classroom-layout sketch."),
        ("simple", "simpler", "simplest", "-r", "The second instruction is _____ than the first instruction.", "This is _____ explanation in the revision guide."),
    ]
    for base, comparative, superlative, ending, comp_sentence, sup_sentence in alternatives:
        questions.append(alternative_comparative("adjectives", n, comp_sentence, base, comparative, ending)); n += 1
        questions.append(alternative_superlative("adjectives", n, sup_sentence, base, superlative, "-st" if base != "simple" else "-st", article_in_gap=sup_sentence.startswith("This is _____"))); n += 1

    questions.append(irregular_adjective_comparative(n, "The revised poster is _____ than the first draft.", "good", "better")); n += 1
    questions.append(irregular_adjective_superlative(n, "This is _____ example in the teacher's model set.", "good", "best")); n += 1
    questions.append(irregular_adjective_comparative(n, "The second draft has a _____ layout than the first draft.", "bad", "worse")); n += 1
    questions.append(irregular_adjective_superlative(n, "This is _____ layout in the fictional before-and-after set.", "bad", "worst")); n += 1
    questions.append(far_adjective_comparative(n, "The sports hall is _____ from the classroom than the library is.")); n += 1
    questions.append(far_adjective_superlative(n, "This is _____ classroom from the hall on the school-map activity.")); n += 1

    assert n == 73 and len(questions) == 72
    return {"module": "adjectives", "questions": questions}


def adverb_bank() -> dict[str, Any]:
    questions: list[dict[str, Any]] = []
    n = 1

    flat_pairs = [
        ("fast", "faster", "fastest", "-er", "-est", "During the relay practice, Eva ran _____ than she did in the first round.", "Of the four runners in the practice race, Eva ran _____."),
        ("hard", "harder", "hardest", "-er", "-est", "Ming worked _____ than usual on the model bridge.", "Of the team members, Ming worked _____ on the display."),
        ("high", "higher", "highest", "-er", "-est", "During the game, Jin threw the ball _____ than before.", "Of the three jumps, Jin jumped _____ on the final attempt."),
        ("low", "lower", "lowest", "-er", "-est", "During the sound check, the group spoke _____ than the previous group.", "Of the groups in the sound check, they spoke _____."),
        ("long", "longer", "longest", "-er", "-est", "For the final note, the bell rang _____ than it did at lunchtime.", "Of the alarms tested, the bell rang _____."),
        ("late", "later", "latest", "-r", "-st", "On Tuesday, the shuttle arrived _____ than expected.", "Of the three buses, route 2 arrived _____."),
        ("early", "earlier", "earliest", "-ier", "-iest", "On Wednesday, the library opened _____ than on Tuesday.", "Of the four days, the library opened _____ on Thursday."),
    ]
    for base, comparative, superlative, comp_ending, sup_ending, comp_sentence, sup_sentence in flat_pairs:
        rule = "Spelling changes" if base in {"late", "early"} else "Regular forms"
        questions.append(flat_adverb_comparative(n, comp_sentence, base, comparative, comp_ending, rule)); n += 1
        questions.append(flat_adverb_superlative(n, sup_sentence, base, superlative, sup_ending, rule)); n += 1

    ly_pairs = [
        ("carefully", "The second pair checked the measurements _____ than the first pair.", "Of the pairs, the second pair checked the measurements _____."),
        ("quietly", "The group entered the reading room _____ than the earlier group.", "Of the groups, they entered the reading room _____."),
        ("clearly", "Asha explained the instructions _____ than in her first attempt.", "Of the presenters, Asha explained the instructions _____."),
        ("politely", "The student asked for help _____ than before.", "Of the role-play groups, this group asked for help _____."),
        ("quickly", "The team completed the sorting task _____ than the other team.", "Of the trial teams, this team completed the sorting task _____."),
        ("slowly", "The class walked across the wet-floor practice mat _____ than before.", "Of the groups, this group walked across the practice mat _____."),
        ("confidently", "Nora presented her idea _____ than in the rehearsal.", "Of the presenters, Nora presented her idea _____."),
        ("patiently", "Kai waited for the equipment _____ than his partner.", "Of the pairs, Kai waited for the equipment _____."),
        ("seriously", "The group discussed the safety rule _____ than in the first meeting.", "Of the groups, this group discussed the safety rule _____."),
        ("neatly", "Mina arranged the labels _____ than before.", "Of the teams, Mina arranged the labels _____."),
        ("loudly", "The announcer read the notice _____ than during the first sound check.", "Of the speakers, the announcer read the notice _____."),
        ("accurately", "The helper copied the timetable _____ than in the first trial.", "Of the helpers, the student copied the timetable _____."),
        ("regularly", "The group updated the class noticeboard _____ than last term.", "Of the groups, this group updated the class noticeboard _____."),
        ("eagerly", "The pupils volunteered to demonstrate _____ than in the previous activity.", "Of the volunteers, this pupil volunteered _____."),
        ("creatively", "The team designed the campaign poster _____ than the other team.", "Of the teams, this team designed the campaign poster _____."),
        ("safely", "The students carried the science tray _____ than before.", "Of the groups, this group carried the science tray _____."),
        ("effectively", "The leader organised the materials _____ than in the first round.", "Of the leaders, this pupil organised the materials _____."),
        ("independently", "Ravi completed the research task _____ than during the first week.", "Of the students, Ravi completed the research task _____."),
        ("responsibly", "The group used the shared tablets _____ than last lesson.", "Of the groups, this group used the shared tablets _____."),
        ("successfully", "The pair solved the coding task _____ than the other pair.", "Of the pairs, this pair solved the coding task _____."),
        ("generously", "The class shared the art supplies _____ than in the earlier activity.", "Of the groups, this class shared the art supplies _____."),
        ("attentively", "The audience listened to the guest speaker _____ than in the rehearsal.", "Of the groups, this audience listened to the guest speaker _____."),
        ("calmly", "The class responded to the practice drill _____ than in the first run-through.", "Of the groups, this class responded to the practice drill _____."),
        ("enthusiastically", "The students joined the warm-up _____ than last week.", "Of the groups, these students joined the warm-up _____."),
        ("thoughtfully", "Sana responded to the visitor's question _____ than in the first discussion.", "Of the students, Sana responded to the visitor's question _____."),
        ("precisely", "The group measured the liquid _____ than in the first trial.", "Of the groups, this group measured the liquid _____."),
    ]
    for base, comp_sentence, sup_sentence in ly_pairs:
        questions.append(ly_adverb_comparative(n, comp_sentence, base)); n += 1
        questions.append(ly_adverb_superlative(n, sup_sentence, base)); n += 1

    questions.append(well_adverb_comparative(n, "The blue team explained its plan _____ than the red team.")); n += 1
    questions.append(well_adverb_superlative(n, "Of the groups, the first team explained its plan _____.")); n += 1
    questions.append(badly_adverb_comparative(n, "The rain damaged the paper display _____ than it damaged the plastic sign.")); n += 1
    questions.append(badly_adverb_superlative(n, "Of the notices left outside, the paper one was damaged _____.")); n += 1
    questions.append(far_adverb_comparative(n, "In the route challenge, the orange token rolled _____ than the blue token.")); n += 1
    questions.append(far_adverb_superlative(n, "Of the tokens in the route challenge, the orange token rolled _____.")); n += 1

    assert n == 73 and len(questions) == 72
    return {"module": "adverbs", "questions": questions}


def learn_files() -> tuple[dict[str, Any], dict[str, Any]]:
    adjective_learn = {
        "module": "adjectives",
        "intro": "Use comparative adjectives to compare two things and superlative adjectives to identify the highest or lowest degree in a group of three or more. Build the form that matches the adjective and the sentence.",
        "sections": [
            {
                "title": "Short adjectives: -er and -est",
                "text": "Most short adjectives take -er for a comparison and -est for a superlative: tall → taller → tallest. If the adjective ends in -e, add -r or -st: large → larger → largest. For a short consonant-vowel-consonant word, double the final consonant: big → bigger → biggest.",
                "examples": ["This box is bigger than that tray.", "This is the largest poster in the hall."],
                "note": "Do not double after two consonants or after w, x or y.",
            },
            {
                "title": "Adjectives ending in -y",
                "text": "Change final -y to -i before -er and -est: easy → easier → easiest; busy → busier → busiest.",
                "examples": ["This clue is easier than the final clue.", "It is the noisiest part of the task."],
            },
            {
                "title": "Longer adjectives and valid alternatives",
                "text": "Longer adjectives usually use more and most: more careful, the most interesting. Some two-syllable adjectives have more than one standard form: quieter or more quiet; cleverer or more clever; narrower or more narrow; simpler or more simple.",
                "examples": ["The diagram is more useful than the list.", "This is the simplest explanation.", "This is the most simple explanation."],
                "note": "Choose a conventional form for the adjective; both listed alternatives are accepted in this course.",
            },
            {
                "title": "Irregular forms and far",
                "text": "Good → better → best and bad → worse → worst. Far has two standard families: farther/farthest and further/furthest. Farther often focuses on physical distance; further also works with distance and broader meanings.",
                "examples": ["The revised poster is better than the first draft.", "This is the farthest classroom from the hall."],
            },
            {
                "title": "Than, the, good and well",
                "text": "A comparative often uses than: cleaner than the old table. A superlative adjective before a noun normally needs the: the cleanest table, unless another determiner already does the job. Use good for a noun or thing; use well for how an action is done.",
                "examples": ["The design is good.", "She explained the design well."],
            },
        ],
        "miniCheck": [
            {
                "sentence": "The poster is _____ than the first draft.",
                "options": ["larger", "largeer", "more large"],
                "answer": "larger",
                "explanation": "Large ends in -e, so add -r: larger than.",
            },
            {
                "sentence": "Of the three displays, Nia's is the _____.",
                "options": ["best", "goodest", "most good"],
                "answer": "best",
                "explanation": "Good is irregular: good → better → best.",
            },
            {
                "sentence": "This is the _____ corner in the library plan.",
                "options": ["quietest", "quieter", "quietiest"],
                "answer": "quietest",
                "explanation": "Use the superlative quietest. The most quiet is also a valid standard alternative, but it is not an option here.",
            },
        ],
        "sources": [
            {"title": "Cambridge Dictionary Grammar: Comparison: adjectives", "url": CAMBRIDGE_COMPARISON},
            {"title": "Cambridge Dictionary Grammar: Farther, farthest or further, furthest?", "url": CAMBRIDGE_FAR},
        ],
    }
    adverb_learn = {
        "module": "adverbs",
        "intro": "Use comparative adverbs to compare how two actions happen and superlative adverbs for the highest or lowest degree of an action in a group. Keep the adverb rule separate from the adjective rule.",
        "sections": [
            {
                "title": "Short adverbs: -er and -est",
                "text": "Fast, hard, high, low and long normally take -er and -est: faster/fastest and harder/hardest. Late becomes later/latest. Early is an important exception to the usual -ly pattern: earlier/earliest.",
                "examples": ["Eva ran faster than before.", "The library opened earliest on Thursday."],
            },
            {
                "title": "Most -ly adverbs: more and most",
                "text": "Most adverbs ending in -ly use more and most: more carefully, most carefully; more clearly, most clearly. Do not add -er/-est, do not double letters, and do not change the y to i.",
                "examples": ["Asha explained the instructions more clearly than before.", "The group worked most carefully."],
                "note": "Early is the exception: earlier/earliest, not more early in this course.",
            },
            {
                "title": "Irregular forms and far",
                "text": "Well → better → best. Badly usually becomes worse/worst; more badly and most badly can also be natural when the manner or extent of harm is the focus. Farther/farthest and further/furthest are both standard; farther often stresses physical distance.",
                "examples": ["The team explained the plan better than before.", "The rain damaged the paper sign most badly."],
            },
            {
                "title": "Than, optional the, and hardly",
                "text": "Use than after a comparative: more quickly than the other team. With superlative adverbs, the is often used but can be omitted when both sound natural: She ran the fastest / She ran fastest. Hard means with effort; hardly means almost not, so it is not the comparative of hard.",
                "examples": ["Kai worked harder than usual.", "Of the runners, Eva ran the fastest.", "I could hardly hear the announcement."],
            },
        ],
        "miniCheck": [
            {
                "sentence": "Our group spoke _____ than last time.",
                "options": ["more clearly", "clearer", "clearliest"],
                "answer": "more clearly",
                "explanation": "Clearly is an -ly adverb, so use more clearly than.",
            },
            {
                "sentence": "Of the three teams, Aisha performed _____.",
                "options": ["best", "goodest", "more well"],
                "answer": "best",
                "explanation": "Well is irregular as an adverb: well → better → best. The is also natural: performed the best.",
            },
            {
                "sentence": "Of the three buses, route 2 arrived _____.",
                "options": ["earliest", "earlier", "earlyest"],
                "answer": "earliest",
                "explanation": "Early is the -ly exception: early → earlier → earliest. The earliest is also natural in this adverbial position.",
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
    assert len(questions) >= 60, f"{module}: fewer than 60 questions"
    assert len({q["id"] for q in questions}) == len(questions), f"{module}: duplicate question ids"
    assert all(q["id"].startswith(expected_prefix) for q in questions), f"{module}: wrong id prefix"
    assert Counter(q["degree"] for q in questions) == Counter({"comparative": 36, "superlative": 36}), f"{module}: unbalanced degrees"
    rule_counts = Counter(q["rule"] for q in questions)
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
    modules = modules_file()

    adjective_report = validate_bank(adjectives)
    adverb_report = validate_bank(adverbs)
    validate_learn(adjective_learn)
    validate_learn(adverb_learn)

    dump("adjectives-questions.json", adjectives)
    dump("adverbs-questions.json", adverbs)
    dump("adjectives-learn.json", adjective_learn)
    dump("adverbs-learn.json", adverb_learn)
    dump("modules.json", modules)

    print(json.dumps({"adjectives": adjective_report, "adverbs": adverb_report}, indent=2))


if __name__ == "__main__":
    main()
