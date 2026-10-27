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

CORE_ENDINGS = ("-er", "-est", "-r", "-st", "-ier", "-iest")
CORE_STRUCTURES = ("more", "most", "than", "the")
CORE_OPERATIONS = ("Remove y",)
COMPLETE_CORE = CORE_ENDINGS + CORE_STRUCTURES + CORE_OPERATIONS
IRREGULAR_FORMS = {
    "good": ("better", "best"),
    "bad": ("worse", "worst"),
    "well": ("better", "best"),
    "badly": ("worse", "worst"),
    "far": ("farther", "further", "farthest", "furthest"),
    "little": ("less", "least"),
    "much": ("more", "most"),
    "many": ("more", "most"),
}

# Context-only revisions from tests/context-review-issues.json.  Keep them
# keyed to stable question IDs so regenerating the banks cannot restore an
# older, less clear template sentence.  Each stem deliberately leaves degree
# words, comparative than, and superlative the for the learner to build.
CLARITY_OVERRIDES = {
    "adj-010": "Monday was _____ day last week.",
    "adj-012": "This is _____ photo in our family album.",
    "adj-021": "Walking across at traffic lights is _____ walking across elsewhere on this road.",
    "adj-035": "Our school bus is _____ our car.",
    "adj-037": "Before the game, Tom was _____ his brother.",
    "adj-041": "Ming was _____ Tom when they carried glass cups.",
    "adj-042": "Among students carrying glasses of water, Ming is _____.",
    "adj-050": "This is _____ idea for our school.",
    "adj-077": "Today's weather is _____ yesterday's weather.",
    "adj-078": "This is _____ weather we have had this week.",
    "adj-080": "This was _____ bus ride I took this week.",
    "adj-081": "From my home, the shop is _____ the school.",
    "adj-083": "From our home, the park is _____ the school.",
    "adj-088": "Of four bowls, this one has _____ rice.",
    "adv-004": "Of everyone in my class, I worked _____.",
    "adv-005": "Ming threw the ball _____ Tom did.",
    "adv-009": "The bell rang _____ it did yesterday.",
    "adv-012": "Among teams, our team ran _____.",
    "adv-013": "Tom studied _____ his brother did for the test.",
    "adv-014": "Tom studied _____ in his class.",
    "adv-037": "The library opened _____ it did yesterday.",
    "adv-038": "During our school week, our library opened _____ on Monday.",
    "adv-043": "Our lesson started _____ the other class's lesson.",
    "adv-047": "In summer, the sun comes up _____ in winter.",
    "adv-048": "In my family, Dad gets up _____.",
    "adv-054": "Among our teachers, Mr Lee spoke _____.",
    "adv-064": "Of these bus services, this one runs _____.",
    "adv-066": "Among students, Ming took our competition _____.",
    "adv-067": "Our team played _____ it did last time.",
    "adv-068": "Among all teams, our team completed this challenge _____.",
    "adv-072": "Of these clocks, this one is set _____.",
    "adv-084": "Of our cards, rain damaged this blue card _____.",
}


def block(
    block_id: str,
    label: str,
    kind: str = "word",
    transforms: dict[str, str] | None = None,
    operation: str | None = None,
) -> dict[str, Any]:
    category = "ending" if kind in {"suffix", "operation"} else "structure" if label in CORE_STRUCTURES else "word"
    value: dict[str, Any] = {"id": block_id, "label": label, "kind": kind, "category": category}
    if transforms:
        value["transforms"] = transforms
    if operation:
        value["operation"] = operation
    return value


def complete_ingredients(blocks: list[dict[str, Any]], base: str) -> None:
    """Add the permanent full-choice tray without altering existing block IDs."""
    labels = {item["label"] for item in blocks}
    next_index = 0

    def add(label: str, kind: str = "word") -> None:
        nonlocal next_index
        if label in labels:
            return
        while f"b{next_index}" in {item["id"] for item in blocks}:
            next_index += 1
        blocks.append(block(f"b{next_index}", label, kind))
        labels.add(label)
        next_index += 1

    add(base)
    for ending in CORE_ENDINGS:
        add(ending, "suffix")
    for structure in CORE_STRUCTURES:
        add(structure)
    for form in IRREGULAR_FORMS.get(base, ()):
        add(form)
    if not any(item["id"] == "remove-y" for item in blocks):
        blocks.append(block("remove-y", "Remove y", "operation", operation="remove-final-y"))


def with_remove_y_sequences(blocks: list[dict[str, Any]], base: str, sequences: list[list[str]]) -> list[list[str]]:
    """Put explicit final-y deletion before each retained direct spelling sequence."""
    if not base.endswith("y"):
        return sequences
    by_id = {item["id"]: item for item in blocks}
    completed: list[list[str]] = []
    for sequence in sequences:
        deletion_sequences: list[list[str]] = []
        for index, block_id in enumerate(sequence[:-1]):
            next_id = sequence[index + 1]
            if (
                by_id[block_id]["label"] == base
                and by_id[next_id]["kind"] == "suffix"
                and by_id[next_id]["label"] in {"-ier", "-iest"}
            ):
                deletion_sequences.append(sequence[: index + 1] + ["remove-y"] + sequence[index + 1 :])
        completed.extend(deletion_sequences)
        completed.append(sequence)
    return completed


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
        elif item["kind"] == "operation":
            if not pieces:
                raise ValueError(f"Operation {block_id} has no preceding word")
            if item.get("operation") != "remove-final-y":
                raise ValueError(f"Unknown operation {item.get('operation')}")
            if not pieces[-1].endswith("y"):
                raise ValueError(f"Operation {block_id} requires a final y")
            pieces[-1] = pieces[-1][:-1]
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
    question_id = f"{'adj' if module == 'adjectives' else 'adv'}-{number:03d}"
    sentence = CLARITY_OVERRIDES.get(question_id, sentence)
    # Comparatives always put than inside the student-built gap.  This removes
    # only legacy ``_____ than`` templates; templates where than occurred later
    # in a clause are deliberately rewritten at their source below.
    if degree == "comparative":
        sentence = re.sub(r"_____\s+than\b", "_____", sentence, flags=re.I)
    assert not re.search(r"\bthan\b", sentence, re.I), f"{module}-{number}: than must not appear in a question stem"
    assert not re.search(r"\b(?:more|most)\b", sentence, re.I), f"{module}-{number}: degree words must not be prefilled in a question stem"
    requires_article = module == "adjectives" and degree == "superlative"
    if degree == "superlative":
        assert not re.search(r"\bthe\b", sentence, re.I), f"{module}-{number}: the must not appear in a superlative stem"
    complete_ingredients(blocks, base)
    sequences = with_remove_y_sequences(blocks, base, sequences)
    answers: list[str] = []
    for sequence in sequences:
        answer = assemble(blocks, sequence)
        if answer not in answers:
            answers.append(answer)
    if degree == "comparative":
        assert all(answer.lower().count("than") == 1 for answer in answers), f"{module}-{number}: each comparative answer must build one than"
    else:
        assert all("than" not in answer.lower() for answer in answers), f"{module}-{number}: a superlative answer must not contain than"
        the_blocks = [item["id"] for item in blocks if item["label"] == "the"]
        assert len(the_blocks) == 1, f"{module}-{number}: every superlative tray needs one literal the block"
        if requires_article:
            assert all(answer.lower().startswith("the ") for answer in answers), f"{module}-{number}: adjective superlative answers must start with the"
            assert all(the_blocks[0] in sequence for sequence in sequences), f"{module}-{number}: adjective superlative must build the"
        else:
            assert any(answer.lower().startswith("the ") for answer in answers), f"{module}-{number}: adverb superlative needs a the form"
            assert any(not answer.lower().startswith("the ") for answer in answers), f"{module}-{number}: adverb superlative needs a bare form"
    answer_text = " or ".join(answers)
    purpose = "to compare two things" if degree == "comparative" else "for the top one in a group"
    ending = "-er" if degree == "comparative" else "-est"
    if rule == "Longer forms":
        hint = f"Put {'more' if degree == 'comparative' else 'most'} before {base}. Do not add {ending}."
    elif rule == "Spelling changes" and base.endswith("y"):
        hint = f"Change y to i, then add {ending}."
    elif rule == "Spelling changes" and base.endswith("e"):
        hint = f"The word ends in e. Add {'-r' if degree == 'comparative' else '-st'}."
    elif rule == "Spelling changes":
        hint = f"Double the last letter, then add {ending}."
    elif rule == "Irregular forms":
        hint = f"{base.capitalize()} changes its form. Use {answer_text} in this gap."
    elif len(answers) > 1:
        hint = f"Both forms fit this sentence: {answer_text}."
    else:
        hint = f"Add {ending} to this short word."
    short_feedback: list[dict[str, str | list[str]]] = []
    for item in feedback[:-1]:
        wrong_answers = item.get("answers")
        if isinstance(wrong_answers, list):
            short_feedback.append({"answers": wrong_answers, "message": f"{wrong_answers[0].capitalize()} is not right here. {hint} Use {answer_text} {purpose}."})
    if degree == "comparative":
        short_explanation = f"Use {answer_text} to compare two things. {hint}"
    else:
        short_explanation = f"Use {answer_text} for the top one in a group. {hint}"
    short_feedback.append({"message": f"Use {answer_text} {purpose}."})
    return {
        "id": question_id,
        "sentence": sentence,
        "base": base,
        "degree": degree,
        "rule": rule,
        "requiresArticle": requires_article,
        "ingredientMode": "complete",
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
        block("b5", "most") if ending == "-er" else block("b5", "-er", "suffix"),
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


def short_superlative(module: str, n: int, sentence: str, base: str, result: str, ending: str, rule: str, had_article_block: bool = False) -> dict[str, Any]:
    comparative_ending = SUPERLATIVE_TO_COMPARATIVE[ending]
    comparative_result = base + comparative_ending.removeprefix("-")
    if comparative_ending == "-ier":
        comparative_result = result[:-3] + "er"
    blocks = [block("b0", base), suffix(ending, base, result)]
    if had_article_block:
        blocks.append(block("b2", "the"))
        sequence = ["b2", "b0", "b1"]
        distractor_start = 3
    else:
        sequence = ["b5", "b0", "b1"]
        distractor_start = 2
    blocks.extend([
        block(f"b{distractor_start}", "more"),
        block(f"b{distractor_start + 1}", comparative_ending, "suffix", {base: comparative_result} if base + comparative_ending.removeprefix("-") != comparative_result else None),
        block(f"b{distractor_start + 2}", "than") if comparative_ending == "-er" else block(f"b{distractor_start + 2}", "-er", "suffix"),
    ])
    if not had_article_block:
        blocks.append(block("b5", "the"))
    shown = "the " + result
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


def long_superlative(module: str, n: int, sentence: str, base: str, had_article_block: bool) -> dict[str, Any]:
    blocks = [block("b0", base), block("b1", "most")]
    if had_article_block:
        blocks.append(block("b2", "the"))
        sequence = ["b2", "b1", "b0"]
        start = 3
    else:
        sequence = ["b5", "b1", "b0"]
        start = 2
    blocks.extend([
        block(f"b{start}", "-er", "suffix"),
        block(f"b{start + 1}", "-est", "suffix"),
        block(f"b{start + 2}", "than"),
    ])
    if not had_article_block:
        blocks.append(block("b5", "the"))
    shown = "the most " + base
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
        block("b4", "-est", "suffix"), block("b5", "most") if ending == "-er" else block("b5", "-er", "suffix"), block("b6", "-ier", "suffix"),
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


def alternative_superlative(module: str, n: int, sentence: str, base: str, result: str, ending: str) -> dict[str, Any]:
    blocks = [block("b0", base), suffix(ending, base, result), block("b2", "most"), block("b3", "the")]
    sequences = [["b3", "b0", "b1"], ["b3", "b2", "b0"]]
    start = 4
    blocks.extend([
        block(f"b{start}", "-er", "suffix"),
        block(f"b{start + 1}", "-ier", "suffix"),
        block(f"b{start + 2}", "than"),
    ])
    shown = "the " + result
    return make_question(
        module, n, sentence, base, "superlative", "Regular forms", blocks, sequences,
        fb(
            (base + "er", "-er makes a comparative. This sentence needs a superlative."),
            (base + "ier", f"Do not make {base} end in -ier. Use {result} or most {base}."),
            (result + " than", "Do not use than with a superlative."),
            fallback=f"Both {shown} and the most {base} are accepted standard alternatives here.",
        ),
        f"Both {shown} and the most {base} are accepted standard superlative forms.",
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
    blocks = [block("b0", result), block("b1", "the"), block("b2", base), block("b3", "-est", "suffix"), block("b4", "-er", "suffix")]
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


def quantity_adjective_comparative(n: int, sentence: str, base: str, result: str, superlative: str, noun: str) -> dict[str, Any]:
    """Build an irregular quantity comparative, its noun and than inside the gap."""
    blocks = [
        block("b0", result), block("b1", noun), block("b2", "than"),
        block("b3", base), block("b4", "-er", "suffix"), block("b5", superlative),
    ]
    return make_question(
        "adjectives", n, sentence, base, "comparative", "Irregular forms", blocks, [["b0", "b1", "b2"]],
        fb(
            (f"{base} {noun} than", f"The base form {base} does not make the comparison. Use {result} {noun} than."),
            (f"{base}er {noun} than", f"{base.capitalize()} does not take a plain -er ending here."),
            (f"{superlative} {noun} than", f"{superlative.capitalize()} is superlative; the sentence compares two quantities."),
            fallback=f"Use the irregular comparative {result} {noun} than.",
        ),
        f"Use {result} {noun} than.",
    )


def quantity_adjective_superlative(n: int, sentence: str, base: str, result: str, comparative: str) -> dict[str, Any]:
    """Practise irregular quantity adjectives with the and the quantity noun built separately."""
    blocks = [block("b0", result), block("b1", base), block("b2", "-est", "suffix"), block("b3", "-er", "suffix"), block("b4", "the")]
    return make_question(
        "adjectives", n, sentence, base, "superlative", "Irregular forms", blocks, [["b4", "b0"]],
        fb(
            (base, f"The base form {base} does not show the highest or lowest quantity."),
            (base + "est", f"{base.capitalize()} does not take a plain -est ending here."),
            (comparative, f"{comparative.capitalize()} is comparative; this sentence needs a superlative."),
            fallback=f"Use the irregular superlative the {result}.",
        ),
        f"Use the {result}. The article is part of the adjective superlative built in the gap.",
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
        block("b3", "far"), block("b4", "-est", "suffix"), block("b5", "-er", "suffix"),
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
        block("b3", "more"), block("b4", comparative_ending, "suffix", {base: comparative_result} if base + comparative_ending.removeprefix("-") != comparative_result else None), block("b5", "than") if comparative_ending == "-er" else block("b5", "-er", "suffix"),
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
        block("b3", "-est", "suffix"), block("b4", "more"), block("b5", "-er", "suffix"),
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
    blocks = [block("b0", "best"), block("b1", "the"), block("b2", "well"), block("b3", "-est", "suffix"), block("b4", "-er", "suffix")]
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
        block("b4", "-er", "suffix"), block("b6", "worst"),
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
        block("b5", "worse"), block("b6", "-er", "suffix"),
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
        block("b3", "farther"), block("b4", "further"), block("b5", "-er", "suffix"),
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
        ("tall", "taller", "tallest", "The school gate is _____ than the side gate.", "In our class, this is _____ boy."),
        ("clean", "cleaner", "cleanest", "My desk is _____ than your desk.", "At our school, this is _____ classroom."),
        ("bright", "brighter", "brightest", "This shirt is _____ than that shirt.", "In this room, this is _____ light."),
        ("short", "shorter", "shortest", "The walk to school is _____ than the walk to the shop.", "For our trip home, this is _____ road."),
        ("warm", "warmer", "warmest", "Today is _____ than yesterday.", "This is _____ day of our week."),
        ("old", "older", "oldest", "My phone is _____ than my sister's phone.", "At my home, this is _____ photo."),
        ("strong", "stronger", "strongest", "This bag is _____ than that bag.", "On our team, Ming is _____ player."),
        ("kind", "kinder", "kindest", "May was _____ than Tom today.", "In our group, May is _____ student."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in regular_pairs:
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, "-er", "Regular forms")); n += 1
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, "-est", "Regular forms")); n += 1

    e_pairs = [
        ("large", "larger", "largest", "The school hall is _____ than our classroom.", "Our red bag is _____ bag here."),
        ("nice", "nicer", "nicest", "This shop is _____ than the old shop.", "In this shop, this is _____ cake."),
        ("safe", "safer", "safest", "The zebra crossing is _____ than the small road.", "Our teacher chose _____ way home."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in e_pairs:
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, "-r", "Spelling changes")); n += 1
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, "-st", "Spelling changes", had_article_block=base == "safe")); n += 1

    doubled_pairs = [
        ("big", "bigger", "biggest", "My lunch box is _____ than yours.", "In this room, this is _____ box."),
        ("hot", "hotter", "hottest", "This soup is _____ than my tea.", "In July, this is _____ day."),
        ("thin", "thinner", "thinnest", "This paper is _____ than that paper.", "On this shelf, this is _____ book."),
        ("wet", "wetter", "wettest", "My shoes are _____ than your shoes.", "Of all our shoes, these are _____."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in doubled_pairs:
        comp_ending = {"big": "-ger", "hot": "-ter", "thin": "-ner", "wet": "-ter"}[base]
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, comp_ending, "Spelling changes")); n += 1
        ending = {"big": "-gest", "hot": "-test", "thin": "-nest", "wet": "-test"}[base]
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, ending, "Spelling changes")); n += 1

    y_pairs = [
        ("easy", "easier", "easiest", "This question is _____ than the last one.", "In this test, this is _____ question."),
        ("busy", "busier", "busiest", "The canteen is _____ than the library at lunch time.", "For our school week, Monday is _____ day."),
        ("noisy", "noisier", "noisiest", "The bus is _____ than the library.", "At our school, this is _____ room."),
        ("happy", "happier", "happiest", "Tom was _____ before the game.", "For my week, this is _____ day."),
        ("heavy", "heavier", "heaviest", "My school bag is _____ than my sister's bag.", "In our class, this is _____ bag."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in y_pairs:
        questions.append(short_comparative("adjectives", n, comp_sentence, base, comparative, "-ier", "Spelling changes")); n += 1
        questions.append(short_superlative("adjectives", n, sup_sentence, base, superlative, "-iest", "Spelling changes")); n += 1

    long_pairs = [
        ("careful", "Ming was _____ than Tom with the glass cups.", "Among students holding glasses, Ming is _____.", False),
        ("interesting", "This book is _____ than that book.", "This is _____ story in our book.", True),
        ("useful", "This map is _____ than the old map.", "My bus card is _____ card in my bag.", False),
        ("popular", "Football is _____ than tennis at our school.", "This is _____ game in our class.", True),
        ("practical", "A small bag is _____ than a large bag for this trip.", "For our school, this is _____ idea.", False),
        ("beautiful", "This new shop sign is _____ than the old one.", "This is _____ picture in our room.", True),
        ("important", "A school ID card is _____ than a new pen.", "In our room, this is _____ rule.", False),
        ("comfortable", "This chair is _____ than that chair.", "This is _____ seat on our bus.", True),
        ("reliable", "This bus is _____ than the old bus.", "This is _____ bus route home.", False),
        ("creative", "Ming's poster is _____ than Tom's poster.", "This is _____ idea in our class.", True),
        ("expensive", "This phone is _____ than that phone.", "This is _____ thing in our shop.", False),
        ("dangerous", "Running on a wet floor is _____ than walking.", "This is _____ road near our school.", True),
    ]
    for base, comp_sentence, sup_sentence, had_article_block in long_pairs:
        questions.append(long_comparative("adjectives", n, comp_sentence, base)); n += 1
        questions.append(long_superlative("adjectives", n, sup_sentence, base, had_article_block)); n += 1

    alternatives = [
        ("quiet", "quieter", "quietest", "-er", "The library is _____ than the canteen.", "This is _____ place in our library."),
        ("clever", "cleverer", "cleverest", "-er", "Ming's plan is _____ than Tom's plan.", "This is _____ idea in our group."),
        ("narrow", "narrower", "narrowest", "-er", "This path is _____ than the road.", "This is _____ path in our park."),
        ("simple", "simpler", "simplest", "-r", "The second rule is _____ than the first rule.", "This is _____ way to go home."),
    ]
    for base, comparative, superlative, ending, comp_sentence, sup_sentence in alternatives:
        questions.append(alternative_comparative("adjectives", n, comp_sentence, base, comparative, ending)); n += 1
        questions.append(alternative_superlative("adjectives", n, sup_sentence, base, superlative, "-est" if base != "simple" else "-st")); n += 1

    irregular_pairs = [
        ("good", "better", "best", "This new pen is _____ than my old pen.", "This is _____ pen in our shop."),
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
        ("little", "less", "least", "This bottle holds _____ that bottle.", "water", "This bottle has _____ water."),
        ("little", "less", "least", "This bowl has _____ that bowl.", "rice", "This bowl has _____ rice."),
        ("much", "more", "most", "This cup holds _____ that cup.", "tea", "This cup has _____ tea."),
        ("much", "more", "most", "This plan gives us _____ the old plan.", "time", "This plan gives us _____ time."),
        ("many", "more", "most", "This bag has _____ that bag.", "books", "This bag has _____ books."),
        ("many", "more", "most", "Room B has _____ Room A.", "chairs", "Room B has _____ chairs."),
    ]
    for base, comparative, superlative, comp_sentence, noun, sup_sentence in quantity_sets:
        questions.append(quantity_adjective_comparative(n, comp_sentence, base, comparative, superlative, noun)); n += 1
        questions.append(quantity_adjective_superlative(n, sup_sentence, base, superlative, comparative)); n += 1

    assert n == 97 and len(questions) == 96
    return {"module": "adjectives", "questions": questions}


def adverb_bank() -> dict[str, Any]:
    questions: list[dict[str, Any]] = []
    n = 1

    flat_pairs = [
        ("fast", "faster", "fastest", "Ming ran _____ than Tom in PE.", "Among our runners, Ming ran _____."),
        ("hard", "harder", "hardest", "I worked _____ than my friend today.", "Among students, I worked _____."),
        ("high", "higher", "highest", "Ming threw the ball _____ than Tom.", "Among players, Ming threw _____."),
        ("low", "lower", "lowest", "The red bell rang _____ the blue bell.", "Among bells, our red bell rang _____."),
        ("long", "longer", "longest", "The bell rang _____ than yesterday.", "Among bells, this one rang _____."),
        ("fast", "faster", "fastest", "Our team packed _____ than the other team.", "Among teams, our team packed _____."),
        ("hard", "harder", "hardest", "Tom studied _____ than before the test.", "In our class, Tom studied _____."),
        ("high", "higher", "highest", "The ball bounced _____ than before.", "Among balls, our red ball bounced _____."),
        ("low", "lower", "lowest", "This whistle sounded _____ the bell.", "Among instruments, this whistle sounded _____."),
        ("long", "longer", "longest", "The bus waited _____ than usual.", "Among buses, this bus waited _____."),
        ("near", "nearer", "nearest", "Ming stood _____ Tom did to the door.", "Among students, Ming stood _____ to our door."),
        ("soon", "sooner", "soonest", "Bus 2 came _____ than Bus 1.", "Among buses, Bus 2 came _____."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in flat_pairs:
        comp_ending, sup_ending = "-er", "-est"
        questions.append(flat_adverb_comparative(n, comp_sentence, base, comparative, comp_ending, "Regular forms")); n += 1
        questions.append(flat_adverb_superlative(n, sup_sentence, base, superlative, sup_ending, "Regular forms")); n += 1

    spelling_pairs = [
        ("late", "later", "latest", "Bus 1 arrived _____ than Bus 2.", "Among buses, Bus 1 arrived _____."),
        ("late", "later", "latest", "My group finished _____ than your group.", "Among groups, my group finished _____."),
        ("late", "later", "latest", "Tom came home _____ than May.", "Among my friends, Tom came home _____."),
        ("late", "later", "latest", "The shop opened _____ than we thought.", "Among shops, our small shop opened _____."),
        ("late", "later", "latest", "The bell rang _____ than usual.", "Among bells, this bell rang _____."),
        ("late", "later", "latest", "I got home _____ than my sister.", "Among my family, I got home _____."),
        ("early", "earlier", "earliest", "The library opened _____ than yesterday.", "Across school days, our library opened _____ on Monday."),
        ("early", "earlier", "earliest", "The bus left _____ than usual.", "Among buses, Bus 1 left _____."),
        ("early", "earlier", "earliest", "Ming came to school _____ than Tom.", "Among students, Ming came _____."),
        ("early", "earlier", "earliest", "Our class started _____ than the other class.", "Among classes, our class started _____."),
        ("early", "earlier", "earliest", "The shop opened _____ than the bank.", "Among shops, this one opened _____."),
        ("early", "earlier", "earliest", "In summer, the sun came up _____ in winter.", "Across all days, sunrise came _____."),
    ]
    for base, comparative, superlative, comp_sentence, sup_sentence in spelling_pairs:
        comp_ending, sup_ending = ("-r", "-st") if base == "late" else ("-ier", "-iest")
        questions.append(flat_adverb_comparative(n, comp_sentence, base, comparative, comp_ending, "Spelling changes")); n += 1
        questions.append(flat_adverb_superlative(n, sup_sentence, base, superlative, sup_ending, "Spelling changes")); n += 1

    ly_pairs = [
        ("carefully", "Ming wrote _____ than Tom.", "Among students, Ming wrote _____."),
        ("quietly", "The class walked _____ than before.", "Among groups, this group walked _____."),
        ("clearly", "The teacher spoke _____ than before.", "Among teachers, our teacher spoke _____."),
        ("easily", "Jia found the new bus stop _____ than the old one.", "Among bus stops, this one was found _____."),
        ("quickly", "My team finished _____ than the other team.", "Among teams, my team finished _____."),
        ("slowly", "The bus moved _____ than before.", "Among buses, this bus moved _____."),
        ("happily", "Tom smiled _____ before the game.", "Among students, Tom smiled _____."),
        ("regularly", "This month, the school bus came _____ last month.", "Among buses, this bus came _____."),
        ("seriously", "Ming listened _____ than before.", "Among students, Ming listened _____."),
        ("successfully", "Our team finished the game _____ than last time.", "Among teams, our team finished a game _____."),
        ("loudly", "The boy spoke _____ than before.", "Among children, this boy spoke _____."),
        ("correctly", "The new clock showed the time _____ than the old clock.", "Among clocks, this clock showed time _____."),
    ]
    for base, comp_sentence, sup_sentence in ly_pairs:
        questions.append(ly_adverb_comparative(n, comp_sentence, base)); n += 1
        questions.append(ly_adverb_superlative(n, sup_sentence, base)); n += 1

    well_pairs = [
        ("The blue team explained its plan _____ than the red team.", "Among teams, our blue team explained its plan _____."),
        ("Jia answered the question _____ than before.", "Among students, Jia answered a question _____."),
        ("Jia sang into the new microphone _____ than before.", "Among singers, Jia sang into our microphone _____."),
        ("Tom explained the game _____ than May.", "Among students, Tom explained a game _____."),
    ]
    for comp_sentence, sup_sentence in well_pairs:
        questions.append(well_adverb_comparative(n, comp_sentence)); n += 1
        questions.append(well_adverb_superlative(n, sup_sentence)); n += 1

    badly_pairs = [
        ("The rain damaged the paper sign _____ it damaged the plastic sign.", "Our paper sign was damaged _____ of all."),
        ("Water marked the blue card _____ it marked the red card.", "Our blue card was marked _____ of all."),
        ("The spill damaged the old poster _____ it damaged the new poster.", "Our old poster was damaged _____ of all."),
        ("A leaking bottle damaged the paper label _____ it damaged the plastic label.", "Our paper label was damaged _____ of all."),
    ]
    for comp_sentence, sup_sentence in badly_pairs:
        questions.append(badly_adverb_comparative(n, comp_sentence)); n += 1
        questions.append(badly_adverb_superlative(n, sup_sentence)); n += 1

    far_pairs = [
        ("The red ball rolled _____ than the blue ball.", "Among balls, our red ball rolled _____."),
        ("The green marble rolled _____ than the red marble.", "Among marbles, our green marble rolled _____."),
        ("Jia's beanbag travelled _____ than Kai's beanbag.", "Among beanbags, Jia's travelled _____."),
        ("The blue counter moved _____ than the yellow counter.", "Among counters, our blue counter moved _____."),
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
                "text": "For easy, busy, noisy, happy and heavy, change y to i: easy → easier → easiest. In Grammar Lab, use Remove y only for a final y: happy + Remove y + -ier → happier. But shy keeps y: shy → shyer → shyest.",
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
                "sentence": "Our school hall is _____ our classroom.",
                "options": ["larger than", "largeer than", "larger"],
                "answer": "larger than",
                "explanation": "Large ends in -e, so add -r and then than: larger than.",
            },
            {
                "sentence": "Of three bags, our red bag is _____.",
                "options": ["the best", "the goodest", "the better"],
                "answer": "the best",
                "explanation": "Good is irregular: good → better → best. A superlative adjective before a noun phrase needs the: the best.",
            },
            {
                "sentence": "This is _____ place in our library.",
                "options": ["the quietest", "the quieter", "the quietiest"],
                "answer": "the quietest",
                "explanation": "Use the quietest. The most quiet is also correct, but it is not an option here.",
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
                "text": "Fast, hard, high, low and long take -er and -est: faster/fastest and harder/hardest. For late, add -r and -st: later/latest. For early, change y to i: earlier/earliest. In Grammar Lab, use Remove y only for a final y: early + Remove y + -ier → earlier.",
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
                "sentence": "Our teacher spoke _____ before.",
                "options": ["more clearly than", "clearer than", "more clearly"],
                "answer": "more clearly than",
                "explanation": "Clearly ends in -ly, so use more clearly than.",
            },
            {
                "sentence": "Of three teams, our blue team played _____.",
                "options": ["the best", "goodest", "more well"],
                "answer": "the best",
                "explanation": "Well is irregular: well → better → best. Best is also natural here; it is not offered as a wrong option.",
            },
            {
                "sentence": "Among three buses, Bus 2 arrived _____.",
                "options": ["the earliest", "the earlier", "earlyest"],
                "answer": "the earliest",
                "explanation": "Early changes y to i: early → earlier → earliest. Earliest is also natural here; it is not offered as a wrong option.",
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
        assert not re.search(r"\bthan\b", q["sentence"], re.I), f"{q['id']}: than must not appear in a question stem"
        assert not re.search(r"\b(?:more|most)\b", q["sentence"], re.I), f"{q['id']}: degree words must not be prefilled in a question stem"
        assert len(q["feedback"]) >= 4, f"{q['id']}: needs 3 specifics plus fallback"
        assert q["feedback"][-1].keys() == {"message"}, f"{q['id']}: final feedback must be fallback"
        assert q["ingredientMode"] == "complete", f"{q['id']}: ingredient mode must be complete"
        expected_article = module == "adjectives" and q["degree"] == "superlative"
        assert q["requiresArticle"] is expected_article, f"{q['id']}: incorrect requiresArticle value"
        ids = [b["id"] for b in q["blocks"]]
        labels = [b["label"] for b in q["blocks"]]
        by_id = {item["id"]: item for item in q["blocks"]}
        assert len(ids) == len(set(ids)), f"{q['id']}: duplicate block id"
        assert len(labels) == len(set(labels)), f"{q['id']}: duplicate block label"
        assert set(COMPLETE_CORE) <= set(labels), f"{q['id']}: missing complete core ingredients"
        assert q["base"] in labels, f"{q['id']}: base word is missing from its tray"
        assert set(IRREGULAR_FORMS.get(q["base"], ())) <= set(labels), f"{q['id']}: missing relevant irregular forms"
        remove_y_blocks = [item for item in q["blocks"] if item["id"] == "remove-y"]
        assert remove_y_blocks == [{"id": "remove-y", "label": "Remove y", "kind": "operation", "category": "ending", "operation": "remove-final-y"}], f"{q['id']}: missing or malformed Remove y operation"
        for item in q["blocks"]:
            expected_category = "ending" if item["kind"] in {"suffix", "operation"} else "structure" if item["label"] in CORE_STRUCTURES else "word"
            assert item["category"] == expected_category, f"{q['id']}: incorrect category for {item['label']}"
        built = []
        for sequence in q["correctSequences"]:
            assert sequence, f"{q['id']}: empty correct sequence"
            assert set(sequence) <= set(ids), f"{q['id']}: sequence references unavailable block"
            if "remove-y" in sequence:
                operation_index = sequence.index("remove-y")
                assert q["base"].endswith("y") and 0 < operation_index < len(sequence) - 1, f"{q['id']}: Remove y must sit between a y-ending base and suffix"
                assert by_id[sequence[operation_index - 1]]["label"] == q["base"], f"{q['id']}: Remove y must follow the base"
                assert by_id[sequence[operation_index + 1]]["label"] in {"-ier", "-iest"}, f"{q['id']}: Remove y must precede -ier or -iest"
            answer = assemble(q["blocks"], sequence)
            built.append(answer)
        for sequence in q["correctSequences"]:
            for index, block_id in enumerate(sequence[:-1]):
                if (
                    q["base"].endswith("y")
                    and by_id[block_id]["label"] == q["base"]
                    and by_id[sequence[index + 1]]["label"] in {"-ier", "-iest"}
                ):
                    explicit_sequence = sequence[: index + 1] + ["remove-y"] + sequence[index + 1 :]
                    assert explicit_sequence in q["correctSequences"], f"{q['id']}: missing explicit final-y deletion sequence"
                    assert q["correctSequences"].index(explicit_sequence) < q["correctSequences"].index(sequence), f"{q['id']}: explicit final-y deletion must be canonical"
        assert set(q["answers"]) == set(built), f"{q['id']}: answer not constructible"
        if q["degree"] == "comparative":
            assert all(answer.lower().count("than") == 1 for answer in q["answers"]), f"{q['id']}: each comparative answer must build one than"
            assert all(q["sentence"].replace("_____", answer).lower().count("than") == 1 for answer in q["answers"]), f"{q['id']}: completed comparative needs one connector"
        else:
            assert all("than" not in answer.lower() for answer in q["answers"]), f"{q['id']}: superlative answer must not contain than"
            assert not re.search(r"\bthe\b", q["sentence"], re.I), f"{q['id']}: superlative stem must be article-free"
            assert labels.count("the") == 1, f"{q['id']}: superlative tray needs one literal the block"
            if q["requiresArticle"]:
                assert all(answer.lower().startswith("the ") for answer in q["answers"]), f"{q['id']}: adjective superlative answers must begin with the"
            else:
                assert any(answer.lower().startswith("the ") for answer in q["answers"]), f"{q['id']}: adverb superlative needs the option"
                assert any(not answer.lower().startswith("the ") for answer in q["answers"]), f"{q['id']}: adverb superlative needs the bare option"
        for entry in q["feedback"][:-1]:
            assert "message" in entry and ("answers" in entry or "pattern" in entry), f"{q['id']}: malformed targeted feedback"
            if "answers" in entry:
                assert not (set(entry["answers"]) & set(q["answers"])), f"{q['id']}: feedback targets a correct answer"
            if "pattern" in entry:
                re.compile(str(entry["pattern"]))
    return {"count": len(questions), "superlatives": sum(q["degree"] == "superlative" for q in questions), "degrees": dict(Counter(q["degree"] for q in questions)), "rules": dict(rule_counts)}


def validate_learn(learn: dict[str, Any]) -> None:
    assert len(learn["miniCheck"]) == 3, f"{learn['module']}: must have exactly 3 mini checks"
    for check in learn["miniCheck"]:
        assert check["sentence"].count("_____") == 1
        assert not re.search(r"\bthan\b", check["sentence"], re.I), f"{learn['module']}: than must not appear in a mini-check stem"
        assert not re.search(r"\bthe\b", check["sentence"], re.I), f"{learn['module']}: mini-check stems must be article-free"
        assert check["options"].count(check["answer"]) == 1, f"{learn['module']}: each mini-check needs one listed correct option"
        if learn["module"] == "adverbs" and check["answer"].lower().startswith("the "):
            bare_form = check["answer"][4:]
            assert bare_form not in check["options"], f"{learn['module']}: a valid bare adverb superlative cannot be a wrong option"


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
