# K S Lo Grammar Lab

A browser-only grammar workbench for K S Lo English. Students combine word parts, test comparative and superlative structures, and learn from specific feedback. British English is used throughout.

## Live app

The GitHub Pages address is `https://ksloenglish.github.io/grammar-lab/`. Teacher assignment links use `?module=adjectives&n=20` or `?module=adverbs&n=30`; these open setup with the module and question count preselected, not the first question. To create a fresh assignment link, do not append an experiment/report hash.

## Files

`site/` is the complete static app. `index.html` supplies the semantic shell and original supplied logo; `css/styles.css` supplies the responsive laboratory design; `js/app.js` supplies views and navigation. `js/core.js` contains reusable assembly, answer checking, scoring and report functions; `js/storage.js` handles local persistence defensively; `js/question-context.js` shares connector, suffix and feedback checks with bank and saved-state validation. `version.js` is the single version definition. `assets/kslo-english-logo.png` is the unchanged original logo.

`site/data/modules.json` lists modules and card metadata. Each ready module references a `*-questions.json` bank and a separate `*-learn.json` document. Runtime content is loaded from these JSON files. The optional generator in `scripts/author-content.py` is a development convenience; teachers can edit JSON directly and need not run it. Do not rerun the generator after manual edits unless you intend to regenerate its content.

`scripts/validate.mjs` checks structure, unique questions, completed-sentence connector/article context, required `-er` options, accepted suffix labels, feedback consistency, answer reachability, balance, distractors and mini-checks. `scripts/build.mjs` validates and copies only `site/` into `dist/`. `tests/` contains regression and optional browser tests. `.github/workflows/deploy.yml` handles automatic versioning and GitHub Pages publication.

## Run and verify locally

No package installation or runtime libraries are needed. Use Node.js 22 or later and Python 3:

```sh
npm run dev
# Open http://localhost:3000/
npm run validate
npm test
npm run build
```

Opening `index.html` with `file://` does not work because browsers restrict fetching JSON there; use a static HTTP server. Optional browser interaction/spacing tests require Python Playwright and its Chromium/WebKit browsers. These are development-only dependencies, not downloaded by students. Set `GRAMMAR_TEST_URL` to test another HTTP origin or GitHub Pages subpath.

## Edit or add questions

Every JSON question has a stable unique `id`, a `sentence` with exactly one `_____` gap, a base-word hint, `degree`, `rule`, `blocks`, accepted `answers`, `correctSequences`, targeted `feedback` and a default `explanation`.

A word block is `{ "id": "base", "label": "easy", "kind": "word" }`. A suffix block is `{ "id": "suffix", "label": "-ier", "kind": "suffix", "transforms": { "eas": "easier" } }`. A connector such as `than` or `the` is a normal word block. IDs must be unique within a question. Each block can be used once.

When a suffix follows a word, its transform for that exact word is used; otherwise its label, without the hyphen, is appended. This lets incorrect reactions such as `easyer` be shown and explained. A suffix placed first remains separate. For new visible doubling recipes, `big` + `g` + `-er` gives `bigger`, and `big` + `g` + `-est` gives `biggest`. Older combined `-ger`/`-gest` recipes remain valid for saved answers. Correct `-r`/`-st` blocks are used for e-ending bases, `-ier`/`-iest` for consonant-y bases, and `-er`/`-est` where appropriate. Do not conceal an invalid accepted suffix label with a transform.

`answers` contains gap contents only. NEVER supply `than` anywhere in a question stem: students must choose it themselves. Every comparative gap answer must include exactly one `than`, at its end. Give each accepted answer a `correctSequences` entry; `["base", "remove-y", "suffix", "than"]` forms `easier than`; the Remove y block is required before -ier/-iest. Rewrite intervening phrases so the entire answer fits one contiguous gap. Accepted gap answers contain only the target adjective/adverb form and necessary grammar words (than/the/more/most), never a noun. Replace a quantity comparison if its natural answer would require a noun; nouns may remain in the sentence outside the gap. Never supply `the` anywhere in a superlative stem. All adjective-superlative accepted answers start with `the`; every superlative tray offers it. Use natural our/my/this/all wording for other nouns rather than giving away the article. Accept standard alternatives in context, including optional `the` for natural adverbial superlatives and farther/further.

Include a literal `-er` suffix in every AUTHORED bank tray (the rendered superlative subset uses -est/-st). It is correct where appropriate and a distractor otherwise; never duplicate an existing `-er` block or make a wrong `-er` combination correct with a transform. Keep the complete compatibility core set in every authored bank: more, most, than, the, -er, -est, -r, -st, -ier, -iest, and the base word. Add relevant paired doubling endings and comparative/superlative irregular forms, with no noun ingredients. The earlier 2–3-distractor cap is superseded: unused ingredients are intentional. Keep labels unique and do not add unrelated irregular families or prebuilt nonwords. Optional authored block categories remain compatibility metadata; js/ingredients.js renders one flat, degree-adaptive collection with the base first.

Comparison feedback is diagnosed from the actual selected blocks and assembled phrase by `js/feedback.js`: one actionable priority mistake, never a generic repetition of the correct explanation. Bank feedback retains exact strings/patterns as editable legacy metadata; keep them narrow and never target a correct alternative. Explanations must describe the actual rule and answer, not merely say “wrong”. Use natural, readily understood school/home/sport/shop situations, familiar words and clear comparison groups. Avoid contrived floor-location comparisons, unclear reference points or adjectives/adverbs that do not naturally describe their subject/action.

Keep each bank at 60 or more questions with balanced comparative/superlative, regular, spelling, longer-form and irregular patterns as appropriate. The initial banks have 96 questions each: 48 comparative, 48 superlative and 24 per rule group. Short adverbs and early do not follow the usual long -ly pattern; do not invent adverb doubling examples just to match adjectives. Run validation and tests after every edit.

Keep all question sentences, explanations and feedback at CEFR B1 or below. Check target headwords against the bundled CEFR source data; never guess a level for an unlisted derivative. Grammar forms and names are treated separately from prose difficulty. `tests/content-b1-audit.json` records the target checks. Natural classroom meaning needs an independent review as well as structural validation.

## Edit Learn content

A Learn document has `module`, `intro`, `sections`, `miniCheck` and `sources`. Sections use `title`, plain-text `text`, optional `examples` and `note`. Include exactly three mini-checks, each with a sentence, unique options, an answer among those options and an explanation. Mini-check stems also omit `than` and, for superlatives, `the`; comparative correct options supply than, and adjective-superlative correct options supply the. Never make a grammatically valid optional-article adverb form a wrong option. Complete teaching examples and explanations may show `than`. Content is escaped and displayed as text, never executed as HTML.

## Add a module

Create a bank and Learn document using these schemas. Add a manifest entry with a unique `id`, `title`, `shortTitle`, `description`, `symbol`, `accent` (`teal` or `violet`), `available: true`, and relative `bank`/`learn` filenames. Home, Learn, setup, questions, storage, assignment links and reports discover it automatically. A placeholder uses `available: false` and needs no bank/Learn file. Extend structure-specific context and degree validation when adding a non-comparison structure; the assembly/scoring engine itself remains reusable. Update `site/manus-routes.json` for new Learn/setup views.

## Scoring, persistence and privacy

A question earns one mark only if its first non-empty submission is correct. A wrong first submission, later successful retry or Give Up earns zero. Empty submissions do not count. Reports retain first answers. Wrong-answer practice has a separate score and never changes the original report or best records.

Best scores are separate for each module and 10/20/30 count. Unfinished experiments, mini-check choices and the latest report are stored under the `kslo-grammar-lab:` localStorage prefix in the same browser profile/device. Clearing browser data, resetting the browser, private browsing or using a different browser/device can remove or hide them. Storage failure is explained and practice remains usable without false persistence claims.

The assessment correction uses saved-question schema 2. Older incompatible experiments/reports are backed up locally under `archive:session`/`archive:last-report` where storage permits, then excluded from current practice. Students see a notice asking them to start a new experiment. The independent best-score key is not cleared. New unfinished experiments resume normally.

Optional name/class fields exist only on screen and in the requested printout. They are never stored, sent, or put in URLs. The app is completely silent, with no sound control or audio-generation code. There is no backend, login, cookies, app analytics, tracking or external font library. GitHub can maintain its own host access logs; these are separate from the app.

End Experiment asks before discarding unfinished work. In-app navigation/browser back asks before leaving and preserves unfinished work where storage is available. Refresh/closing uses the browser's native leave warning; its exact text is controlled by the browser.

## GitHub Pages deployment

Use `main`. Settings → Pages is configured to **GitHub Actions**. Pushes to main and manual dispatch validate the bank, run regression tests, generate an Asia/Hong_Kong deployment timestamp, commit only `site/version.js`, package `site/`, upload the Pages artefact and deploy. The workflow token's version commit does not recursively trigger another workflow.

Versions follow `v[yymmdd]-[hhmmss]`, e.g. `v261027-181817`, in Hong Kong Time (UTC+8). `site/version.js` is the only version source, used by footer and reports. Generation occurs immediately before packaging. No scheduled job is needed.

Permissions are `contents: write`, `pages: write`, `id-token: write`. If branch protection blocks the bot's single-file version commit, allow this workflow to write it or retain generation while omitting the commit. Do not add secrets or student data to the repository. Before local edits after a deployment, pull the bot's version commit with `git pull --ff-only`.

All runtime assets use relative URLs and views use hashes, so `/grammar-lab/` works without backend rewrites. JSON edits pushed to main deploy automatically.

## Accessibility and layout

Tap/click adds a block to the end of the answer, and tap/click on a selected block returns it to the tray. Drag/drop, movement arrows and Left/Right reordering are disabled. Keyboard users activate the same add/return buttons with Tab and Enter/Space; change order by returning and re-adding blocks or clearing the answer. Results have live announcements; focus is visible, colours are high-contrast and reduced motion disables effects. Printing removes navigation/actions, includes optional identity and preserves all questions and rule results.

Use **Build your answer**, **Word blocks**, **Check answer**, **Clear answer**. Block text is normal-case sans-serif, at least 20px desktop/18px phone. Cards/dialogues have deliberate padding and button groups have gaps. The compact question workspace uses its own smaller mobile spacing; unrelated views and confirmation dialogues keep their generous padding. The green `easier ✓` demo is centred and content-sized, not full-width. Run visual-spacing and browser interaction checks after styling changes; no overflow alone does not prove a good layout.

© 2026 K S Lo English. All Rights Reserved.

## Playful light-lab effects

The approved UI is a colourful light science lab, not a formal editorial page. Bold rounded system typography, lively lab panels and chunky coloured word tiles preserve clear high-contrast reading. `js/effects.js` builds decorative Home flasks, score beakers, sparks and report confetti. The beaker level uses the actual score percentage; effects never alter marking. Placement/fusion, correct reactions and report celebrations are brief, with no endlessly distracting motion. Wrong answers stay intact with stable underlined problem parts and a text issue label; no letters scatter. Reduced-motion preferences suppress animations, printing omits decorative effects, and all effects are silent. Everything runs as ordinary static CSS/JavaScript on GitHub Pages.

## Final-y deletion ingredient

Every comparison tray also offers **Remove y**, an operation block with `kind: "operation"`, `operation: "remove-final-y"`, and category `ending`. A red cross marks deletion. It removes only the final y from the immediately preceding word, e.g. happy → happ; adding -ier then makes happier. The live strip shows the crossed-out y, intermediate stem and joined form. Inappropriate placement or use on a non-y word remains visibly invalid and cannot earn a mark. Explicit deletion is required: direct easy + -ier yields easyier, not easier, and is incorrect. Only easy + ×y + -ier removes y and forms easier. Give Up displays a correct ingredient recipe. The engine recomputes these visual traces from the selected blocks; no extra personal data is stored.

The build appends the deployment version to CSS, the JavaScript entry and every relative module import in `dist/`. Source files remain unchanged. This prevents a browser's cached earlier engine from being mixed with newer question-bank or spelling-operation code on GitHub Pages.

## Final tile and Home visual rules

Word labels stay on one line. Content-sized wrapping rows give longer words their own width without smaller text or ellipses. The deletion control displays only a red cross before y, in both tray and answer; its internal Remove y name and accessible remove-final-y description remain intact. Available cards use Lab labels only, not Aa/Av abbreviation badges. Home flask vectors have short flared necks, sloping shoulders, clipped liquid, glass highlights and broad bases. `tests/tile-visual-check.py` checks all current bank labels per viewport across both banks.

Hide top-right navigation on Home. On non-Home pages it shows the full **Lab home** label in an outlined teal button, including at 360px. It retains the unfinished-experiment confirmation and a minimum 44px touch target. The Home example is headed **How to build a word** and shows **easy + ×y + -ier → easier**, with accessible final-y deletion. Do not show the intermediate yellow spelling strip on Home; keep spelling-step feedback during experiments. The caption matches the ingredients: “Remove the final y. Add -ier.” `tests/home-ui-check.py` checks these changes and silence on desktop Chromium and 360px WebKit.

## Compact question controls

The setup field is Number of questions, with content-sized 10/20/30 question choices instead of stacked full-width rows. Answer blocks are content-sized on desktop and mobile and wrap as needed. The base hint appears in parentheses immediately after the blank, e.g. In this test, this is _____ (easy) question; it is no longer a separate Base word line. Stored question wording and all answers remain unchanged. The No login needed Home footnote is removed.

## Adaptive mobile question workspace

On phones, the question page uses a compact text score without the container graphic, followed by Question → Build your answer → Word blocks. Question-only padding and empty heights are reduced, and Check/Clear share a row. The normal building state targets a single 360×640–800 CSS-pixel screen; long sentences, feedback and enlarged text can still scroll naturally. Other views retain their existing layout.

Instructions are “Tap to add. Tap your answer blocks to remove.” The visible tray is one flat wrapping collection, with the available base first. Comparative defaults are more, than, -er and -r; superlative defaults are most, the, -est and -st. Y-ending bases additionally offer ×y and -ier/-iest. Actual doubling forms offer the literal last consonant, e.g. big + g + -er + than → bigger than; the + big + g + -est → the biggest. Current-degree irregulars and standard alternatives remain available. Selected blocks still tap-return; no drag or movement arrows are enabled.

The complete authored bank ingredients remain for compatibility, but the rendered adaptive subset supersedes earlier category grouping/all-visible requirements. `js/comparison-blocks.js` derives the subset, controlled doubling block and preferred visible recipes without changing question wording or accepted answers. Every accepted answer must be reachable with visible options. Compatible schema-2 unfinished work is upgraded in memory, preserving score, attempts, first answers, selected IDs and independent best records; older combined -ger/-gest recipes remain valid for saved answers. Deployment validates both authored and adaptive reachability. A doubling operation applied to an incompatible word, letter or position remains visibly invalid and cannot earn a mark.

## Mistake-specific answer feedback

Correct feedback gives a concise formation rule and explains the connector/article without a generic Use [answer] to compare two things introduction. For example: Good changes its form to better. Use than to introduce the other person, thing or action in the comparison. Both banks and the generator use concise explanation templates.

Wrong answers remain exactly as submitted. A stable underlined highlight marks only the problematic assembled part, with a text label such as Missing ending or Missing than. The remark diagnoses the actual selected structure. For example, the bigg is unfinished: the g has already been doubled, so -est is missing. Other diagnostics address formation, degree, y spelling, doubling, irregular words, extra blocks and order. Hints do not automatically reveal a whole corrected answer; Give Up remains the reveal action. Colour is not the only signal, and reduced motion keeps the same readable information.

`js/feedback.js` contains pure deterministic correct-explanation and error-diagnostic functions. Compatible saved attempts and reports render fresh feedback without changing their original answers, attempts, scores, best records or schema. All question wording/answers/blocks/recipes remain unchanged. Existing first-attempt marking, retries, practice reports, keyboard/touch operation and browser-only privacy are retained.

## Mandatory explicit final-y removal

The automatic y-dropping suffix shortcut is removed. noisy + -iest now yields noisyiest and gets no mark; noisy + ×y + -iest yields noisiest. For a complete adjective superlative, also choose the; a comparative also needs than. The same rule applies to all 22 y-change questions, including early with the accepted optional-the superlatives. Missing-×y feedback names the omitted block and its position.

Only explicit stem transforms and explicit accepted recipes remain in the affected bank/generator metadata. Saved older metadata is upgraded without adding a block to unfinished work or resetting marks/first answers/best records. Previously checked results retain their historical grade; any canonical read-only block display is identified as such. Arbitrary corrupt metadata remains invalid. This supersedes the former direct -ier/-iest compatibility rule, not the grammatical accepted words themselves.
