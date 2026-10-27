# K S Lo Grammar Lab

A browser-only grammar workbench for K S Lo English. Students combine word parts, test comparative and superlative structures, and learn from specific feedback. British English is used throughout.

## Live app

The GitHub Pages address is `https://ksloenglish.github.io/grammar-lab/`. Teacher assignment links use `?module=adjectives&n=20` or `?module=adverbs&n=30`; these open setup with the module and trial count preselected, not the first trial. To create a fresh assignment link, do not append an experiment/report hash.

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

A word block is `{ "id": "base", "label": "easy", "kind": "word" }`. A suffix block is `{ "id": "suffix", "label": "-ier", "kind": "suffix", "transforms": { "easy": "easier" } }`. A connector such as `than` or `the` is a normal word block. IDs must be unique within a question. Each block can be used once.

When a suffix follows a word, its transform for that exact word is used; otherwise its label, without the hyphen, is appended. This lets incorrect reactions such as `easyer` be shown and explained. A suffix placed first remains separate. For doubling, `big` + `-ger` gives `bigger`, and `big` + `-gest` gives `biggest`. Correct `-r`/`-st` blocks are used for e-ending bases, `-ier`/`-iest` for consonant-y bases, and `-er`/`-est` where appropriate. Do not conceal an invalid accepted suffix label with a transform.

`answers` contains gap contents only. NEVER supply `than` anywhere in a question stem: students must choose it themselves. Every comparative gap answer must include exactly one `than`, at its end. Give each accepted answer a `correctSequences` entry; `["base", "suffix", "than"]` can form `easier than`. Rewrite intervening phrases so the entire answer fits one contiguous gap. For quantity adjectives, include the simple noun in the gap where necessary: `Room B has _____ Room A.` → `more chairs than`. Never supply `the` anywhere in a superlative stem. All adjective-superlative accepted answers start with `the`; every superlative tray offers it. Use natural our/my/this/all wording for other nouns rather than giving away the article. Accept standard alternatives in context, including optional `the` for natural adverbial superlatives and farther/further.

Include a literal `-er` suffix in EVERY tray. It is correct where appropriate and a distractor otherwise; never duplicate an existing `-er` block or make a wrong `-er` combination correct with a transform. Offer the complete core set in every tray: more, most, than, the, -er, -est, -r, -st, -ier, -iest, and the base word. Add relevant paired doubling endings and comparative/superlative irregular forms, plus a quantity noun when needed. The earlier 2–3-distractor cap is superseded: unused ingredients are intentional. Keep labels unique and do not add unrelated irregular families or prebuilt nonwords. Group Words / Other words / Endings using optional block category values word/structure/ending; js/ingredients.js renders these groups without changing grading.

Feedback matches exact incorrect strings in `answers` or a JavaScript `pattern`; matching is case-insensitive and the first entry wins. Keep patterns narrow and never target a correct answer as wrong. Explanations must describe the actual rule and answer, not merely say “wrong”. Use natural, readily understood school/home/sport/shop situations, familiar words and clear comparison groups. Avoid contrived floor-location comparisons, unclear reference points or adjectives/adverbs that do not naturally describe their subject/action.

Keep each bank at 60 or more questions with balanced comparative/superlative, regular, spelling, longer-form and irregular patterns as appropriate. The initial banks have 96 questions each: 48 comparative, 48 superlative and 24 per rule group. Short adverbs and early do not follow the usual long -ly pattern; do not invent adverb doubling examples just to match adjectives. Run validation and tests after every edit.

Keep all question sentences, explanations and feedback at CEFR B1 or below. Check target headwords against the bundled CEFR source data; never guess a level for an unlisted derivative. Grammar forms and names are treated separately from prose difficulty. `tests/content-b1-audit.json` records the target checks. Natural classroom meaning needs an independent review as well as structural validation.

## Edit Learn content

A Learn document has `module`, `intro`, `sections`, `miniCheck` and `sources`. Sections use `title`, plain-text `text`, optional `examples` and `note`. Include exactly three mini-checks, each with a sentence, unique options, an answer among those options and an explanation. Mini-check stems also omit `than` and, for superlatives, `the`; comparative correct options supply than, and adjective-superlative correct options supply the. Never make a grammatically valid optional-article adverb form a wrong option. Complete teaching examples and explanations may show `than`. Content is escaped and displayed as text, never executed as HTML.

## Add a module

Create a bank and Learn document using these schemas. Add a manifest entry with a unique `id`, `title`, `shortTitle`, `description`, `symbol`, `accent` (`teal` or `violet`), `available: true`, and relative `bank`/`learn` filenames. Home, Learn, setup, trials, storage, assignment links and reports discover it automatically. A placeholder uses `available: false` and needs no bank/Learn file. Extend structure-specific context and degree validation when adding a non-comparison structure; the assembly/scoring engine itself remains reusable. Update `site/manus-routes.json` for new Learn/setup views.

## Scoring, persistence and privacy

A trial earns one mark only if its first non-empty submission is correct. A wrong first submission, later successful retry or Give Up earns zero. Empty submissions do not count. Reports retain first answers. Wrong-answer practice has a separate score and never changes the original report or best records.

Best scores are separate for each module and 10/20/30 count. Unfinished experiments, mini-check choices and the latest report are stored under the `kslo-grammar-lab:` localStorage prefix in the same browser profile/device. Clearing browser data, resetting the browser, private browsing or using a different browser/device can remove or hide them. Storage failure is explained and practice remains usable without false persistence claims.

The assessment correction uses saved-question schema 2. Older incompatible experiments/reports are backed up locally under `archive:session`/`archive:last-report` where storage permits, then excluded from current practice. Students see a notice asking them to start a new experiment. The independent best-score key is not cleared. New unfinished experiments resume normally.

Optional name/class fields exist only on screen and in the requested printout. They are never stored, sent, or put in URLs. Sound starts off and uses local Web Audio tones. There is no backend, login, cookies, app analytics, tracking or external font library. GitHub can maintain its own host access logs; these are separate from the app.

End Experiment asks before discarding unfinished work. In-app navigation/browser back asks before leaving and preserves unfinished work where storage is available. Refresh/closing uses the browser's native leave warning; its exact text is controlled by the browser.

## GitHub Pages deployment

Use `main`. Settings → Pages is configured to **GitHub Actions**. Pushes to main and manual dispatch validate the bank, run regression tests, generate an Asia/Hong_Kong deployment timestamp, commit only `site/version.js`, package `site/`, upload the Pages artefact and deploy. The workflow token's version commit does not recursively trigger another workflow.

Versions follow `v[yymmdd]-[hhmmss]`, e.g. `v261027-181817`, in Hong Kong Time (UTC+8). `site/version.js` is the only version source, used by footer and reports. Generation occurs immediately before packaging. No scheduled job is needed.

Permissions are `contents: write`, `pages: write`, `id-token: write`. If branch protection blocks the bot's single-file version commit, allow this workflow to write it or retain generation while omitting the commit. Do not add secrets or student data to the repository. Before local edits after a deployment, pull the bot's version commit with `git pull --ff-only`.

All runtime assets use relative URLs and views use hashes, so `/grammar-lab/` works without backend rewrites. JSON edits pushed to main deploy automatically.

## Accessibility and layout

Tap and native drag/drop work. Keyboard users place/return with Enter/Space and reorder with visible arrows or Left/Right on a placed block. Results have live announcements; focus is visible, colours are high-contrast and reduced motion disables effects. Printing removes navigation/actions, includes optional identity and preserves all questions and rule results.

Use **Build your answer**, **Word blocks**, **Check answer**, **Clear answer**. Block text is normal-case sans-serif, at least 20px desktop/18px phone. Cards/dialogues have deliberate padding, button groups have gaps, and at least 16px separates actions from following text/callouts. The green `easier ✓` demo is centred and content-sized, not full-width. Run visual-spacing and browser interaction checks after styling changes; no overflow alone does not prove a good layout.

© 2026 K S Lo English. All Rights Reserved.

## Playful light-lab effects

The approved UI is a colourful light science lab, not a formal editorial page. Bold rounded system typography, lively lab panels and chunky coloured word tiles preserve clear high-contrast reading. `js/effects.js` builds decorative Home flasks, score beakers, sparks and report confetti. The beaker level uses the actual score percentage; effects never alter marking. Placement/fusion, correct reactions, separated wrong-word fragments and report celebrations are brief, with no endlessly distracting motion. Reduced-motion preferences suppress animations, printing omits decorative effects, and sound remains off by default. Everything runs as ordinary static CSS/JavaScript on GitHub Pages.

## Final-y deletion ingredient

Every comparison tray also offers **Remove y**, an operation block with `kind: "operation"`, `operation: "remove-final-y"`, and category `ending`. A red cross marks deletion. It removes only the final y from the immediately preceding word, e.g. happy → happ; adding -ier then makes happier. The live strip shows the crossed-out y, intermediate stem and joined form. Inappropriate placement or use on a non-y word remains visibly invalid and cannot earn a mark. Explicit deletion sequences are preferred examples; direct -ier/-iest sequences remain accepted alternatives. Give Up displays a correct ingredient recipe. The engine recomputes these visual traces from the selected blocks; no extra personal data is stored.

The build appends the deployment version to CSS, the JavaScript entry and every relative module import in `dist/`. Source files remain unchanged. This prevents a browser's cached earlier engine from being mixed with newer question-bank or spelling-operation code on GitHub Pages.
