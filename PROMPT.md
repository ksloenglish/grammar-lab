# K S Lo Grammar Lab — updated build and maintenance prompt

Create or maintain **K S Lo Grammar Lab**, a static grammar-learning app for Hong Kong secondary students. Use British English. The authorised repository is `ksloenglish/grammar-lab`; the user approved making it public for GitHub Pages. Handle repository setup, pushing and publishing, rather than asking the teacher to do routine setup.

Students conduct grammar experiments by choosing ingredients, assembling structures and seeing whether their reaction works. Build comparative/superlative adjectives and comparative/superlative adverbs first. Show passive voice, present/past simple, present/past continuous and perfect tenses as Coming soon. Add later modules through editable question banks, Learn documents and the module manifest, without changing the reusable assembly/scoring logic.

## Technical and privacy requirements

Use static HTML/CSS/JavaScript, relative paths and minimal libraries. No backend, login or application collection of personal data. Keep question banks and Learn content in separate teacher-editable JSON files. Document structure, question editing, module addition and deployment in README.

Save unfinished experiments and best scores in localStorage. Keep best records separate for each module and 10/20/30 count. Explain prominently that scores/progress exist only in this browser on this device and will be lost if browser data is cleared or the browser is reset. Handle blocked/full storage honestly. Optional report name/class fields remain on screen and in requested printouts only; never store or transmit them.

After a correction makes earlier saved question snapshots incompatible, do not resume those faulty questions. Preserve best scores, back up old snapshots locally where possible, explain the update and ask students to start a new experiment.

## Branding

Use the supplied original transparent K S Lo English logo unchanged apart from proportional display sizing. Place it in a generously padded rounded square with sufficient background contrast; the white logo must not disappear on white.

The footer displays the sole `version.js` version in `v[yymmdd]-[hhmmss]` format, Hong Kong Time (UTC+8). A GitHub Action updates it for every deployment. Include `© 2026 K S Lo English. All Rights Reserved.` with the brand linked to `https://english.kslo.hk/` in a new tab.

## Approved visual direction

Use a **colourful LIGHT science lab** that feels fun and exciting, not a serious editorial form with a few added particles. Use bold rounded system sans-serif, lively teal/violet/coral/amber accents, tactile coloured word tiles, playful lab panels and functional beaker progress. Keep the question area calm, readable and high-contrast. No clip art, novelty fonts, external font dependency or endless distracting animation.

Include brief animated Home flasks/mixing, block snapping and fusion, clearly visible correct-answer sparks, genuinely separating wrong-word fragments, a beaker filled to the actual score percentage and a short report celebration. Animations are smooth and short, generally 200–600ms; reduced-motion preferences disable decorative movement. The app is completely silent: no sound toggle, audio playback or Web Audio generation. Effects never change marking or block controls.

Support 360px phones, desktops and classroom projectors. Use deliberate card/dialog padding and consistent component spacing. Button rows have comfortable gaps and at least 16–24px before following text/callouts. Word-block text is normal-case sans-serif, at least 20px desktop and 18px phone. Left-align **Build your answer** and **Word blocks** with panel content; keep **01 / BUILD** and **02 / SELECT** on the right. Decorative marks must not push headings into the middle. Keep the green easier/tick Home result content-sized and centred, with breathing space before its caption.

Provide WCAG AA contrast, visible focus, full keyboard operation and screen-reader announcements. Visually inspect Home, Learn, Setup, building, correct/wrong feedback, Report and confirmation dialogues on phone and desktop. No-overflow checks alone are not visual verification.

## Home and Learn

Home has the title/logo, a concise two- or three-sentence explanation and module cards. Available cards offer Learn and Experiment and show saved best records. Placeholder modules say Coming soon.

Hide top-right navigation on Home. On non-Home pages it displays the full **Lab home** label, including on phones, with an obvious button treatment and a minimum 44px touch target. Never replace its text with an icon-only control. Preserve the unfinished-experiment leave confirmation.

The Home demonstration heading is **How to build a word**. Show **easy + ×y + -ier → easier**, using the compact red-cross-before-y operation and an accessible remove-final-y name. Use the assembly engine for the correct result, but do not show the intermediate yellow spelling-step strip on Home. Keep the spelling-step renderer and crossed-out-y feedback during experiments. The caption says “Remove the final y. Add -ier.” Keep all three ingredient labels readable and unclipped at phone and desktop sizes.

Learn explains formation, spelling and common mistakes: short words, consonant-y endings, longer words and -ly adverbs; -r, doubling and y changes; good/well → better/best, bad/badly → worse/worst, far alternatives; than/the; errors such as more easier, the most fastest and more fast. Distinguish adjective and adverb rules accurately and accept standard alternatives in context. End each Learn with exactly three mini-checks and an Experiment button.

Teaching examples can show complete structures, but **mini-check question stems must not give away comparative than or superlative the**. Do not make a valid optional-the adverb form a wrong multiple-choice option.

## Core teaching principle: assemble the whole structure

Students must select the ingredients themselves. **Never prefill comparative than, superlative the, or the formation words more/most in a question stem.** Keep all superlative stems free of literal the, using natural possessive/demonstrative/group wording where needed. A base-word hint is allowed.

Every comparative answer includes exactly one than at the end of the contiguous gap phrase. Rewrite non-adjacent comparisons so the entire phrase fits that gap. Never include a noun in an accepted gap answer or ingredient tray. Replace quantity comparisons that need noun-containing answers with natural adjective/adverb comparisons; nouns may remain in the sentence outside the gap.

Every adjective-superlative accepted answer begins with the. Every superlative tray offers the, but natural optional-the **adverb** superlatives remain accepted. Validate completed sentences, not only stored answer reachability. Reject duplicated than/the and invalid accepted suffix labels.

## Complete ingredient trays

The final instruction **supersedes the former two- or three-distractor limit**. Every comparison question offers:

- the base word;
- more, most, than and the;
- -er/-est, -r/-st and -ier/-iest;
- relevant paired doubling endings, such as -ger/-gest for big;
- the relevant base's irregular comparative and superlative forms, including all standard far alternatives;
- a distinct **Remove y** operation.

Reuse labels/IDs rather than duplicating blocks. Do not add unrelated irregular word families or prebuilt nonwords such as worser/badlier. Students can produce incorrect forms by combining the genuine ingredients. Group choices into Words, Other words and Endings & changes. Many unused ingredients are intentional.

## Remove y and visible spelling changes

Show the deletion tile as a **red cross before y**, with no visible word “remove”. Keep it compact and retain an accessible remove-final-y label. It is a controlled operation, not an ordinary word or suffix: it removes only the final y from the immediately preceding word. For example, `happy + Remove y + -ier + than` builds `happier than`; `early + Remove y + -ier` builds earlier.

Show the spelling change clearly: happy with its final y crossed out → happ → happier. Use a brief removal/joining effect and a static reduced-motion equivalent. An operation on a non-y word or in the wrong position must remain visibly invalid, not silently do nothing or earn a mark. Prefer explicit deletion recipes in examples/correct sequences, but retain direct -ier/-iest assembly as an accepted equivalent. Explain the operation in B1 language.

## Question content and interactions

Each initial bank contains **96 questions**, with 48 comparative/48 superlative and 24 per rule group. Keep every question, explanation and feedback B1-friendly: short natural sentences, familiar school/home/sport/shop situations and clear comparisons. Check target headwords against the bundled Oxford/Cambridge CEFR data; never invent a level for an absent entry. Independently inspect the meaning of all situations, not just grammar. Avoid awkward floor-location comparisons, mismatched actions/qualities and unclear reference points.

Each question defines sentence, hint, degree/rule, blocks, all accepted gap answers, constructible sequences, specific feedback for likely wrong combinations and a default explanation. Correct suffix labels must reflect the real spelling rule; do not hide an invalid label with a transform.

Setup offers 10/20/30. Randomly sample without repeats. The question shows the gap sentence and randomly ordered ingredients within groups. Students tap/click to append blocks and tap/click selected blocks to return them. Drag/drop and movement arrows are disabled; change order by return/re-add or Clear. Tab/Enter/Space activates these same native buttons; Left/Right does not reorder. Word plus suffix visibly fuses. Correct submission shows a tick and reaction; wrong submission shows a cross and separated incorrect structure plus rule-specific explanation. Offer Retry and Give Up. Give Up shows correct answers, a canonical ingredient recipe and a short explanation.

## Scoring and reports

Only a correct first non-empty submission earns one mark. Wrong first answers, later retries and Give Up earn zero; never double-score. Show current score, Question X of Y and progress. End Experiment and browser-back leaving require confirmation.

At completion show score/percentage, an encouraging band comment, all questions with first answer/correct answer/tick-cross, and a rule-type breakdown. Retry Wrong Answers has its own score and never overwrites the original report or best records. Include New Experiment, Home and Print / Save as PDF, with a clean print layout and ephemeral optional name/class fields.

## Assignments, verification and publishing

A link such as `?module=adjectives&n=20` opens **setup with that module/count preselected**, not an immediate trial. Maintain browser resume and separate best records.

Permanently enforce the final assessment principles in the generator, deployment validator, regression tests and saved-question checks. Investigate reported mistakes at the root cause, correct the output and update this prompt/instructions so they do not recur. Keep corrected context overrides in the generator so regeneration cannot undo them.

Verify answer alternatives, article/connectors, all ingredients, y operations, first-attempt scoring, retry/give-up, persistence, keyboard/touch/tap-only interaction and disabled drag, responsive layouts, print, reduced motion and error states. Save the authorised code without rewriting remote history, push to GitHub automatically, confirm the Action deployment and verify the actual public site before delivery. Do not claim a preview/checkpoint is a published release.

## Home icon correction

Do not display the Aa or Av abbreviation badges on available module cards; the Lab 01 / Lab 02 labels are sufficient. In particular, Av is unwanted. Keep Home flasks recognisably conical laboratory glassware: short necks, flared rims, sloping shoulders and broad flat bases, with neatly clipped coloured liquid and subtle graduation marks. Never use a tall central neck on a rounded rectangular body that resembles a raised finger. Verify the rendered scene at phone and desktop sizes.

Tile words must stay on one line without smaller text or ellipses. Use content-sized wrapping rows so longer words such as reliable receive a wider tile. The deletion tile is a short red-cross-plus-y control, with the cross before y, both in the tray and after placement.

## Noun-free accepted answers — 10 November 2026

This rule supersedes the earlier quantity-noun-in-gap approach. Students build only the target adjective/adverb comparison and required grammar words. No accepted answer or word ingredient may include an additional noun. The six former noun-bearing adjective comparatives adj-085/087/089/091/093/095 are replaced with good/bad/far contexts and better than, worse than, farther than/further than answers. Keep the noun-free quantity superlatives the least/the most. Preserve 96 questions per module and all degree/rule counts. Enforce the rule in generator validation, deployment validation, regression tests and same-schema saved-question checks; archive incompatible old snapshots while preserving independent best scores.

## Tap-only UI and compact controls — 10 November 2026

This update supersedes all earlier drag/drop and movement-arrow requirements. Hide the top-right Lab home control on the Home page only; retain its full label on non-Home pages. Remove the No login needed footnote under Pick a grammar challenge. Use questions, not trials, in visible counts, including Number of questions; leave technical IDs and storage keys unchanged. Show the 10/20/30 choices as compact content-sized controls that wrap safely, not full-width stacked rows.

Use only tap/click to add and return ingredient blocks. Adding appends to the answer; tapping a selected block returns it. No native drag/drop, drag state, move arrow buttons or Left/Right reordering. Keep equivalent Tab/Enter/Space native-button access and focus/live announcements. Change order through return and re-add (or Clear), never through hidden reorder behaviour. Answer blocks are compact/content-sized on desktop and mobile and wrap naturally. Keep labels at least 20px desktop/18px mobile and touch targets at least 44px.

Display the base word directly after the blank in parentheses: In this test, this is _____ (easy) question. Remove the separate Base word paragraph. Keep the gap and hint visually adjacent, readable and escaped, and preserve the original stored sentence and noun-free answer recipes. All first-attempt scores, alternative forms, correct/wrong locks, retries, reports and browser-only persistence remain unchanged.
