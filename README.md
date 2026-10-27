# K S Lo Grammar Lab

A browser-only grammar workbench for K S Lo English. Students combine word parts, test comparative and superlative structures, and learn from specific feedback. British English is used throughout.

## Live app

The intended GitHub Pages address is `https://ksloenglish.github.io/grammar-lab/`. Teacher assignment links use `?module=adjectives&n=20` or `?module=adverbs&n=30`; these open setup with the module and trial count preselected, not the first trial. To create a fresh assignment link, do not append an experiment/report hash.

## Files

`site/` is the complete static app. `index.html` supplies the semantic shell and original supplied logo, `css/styles.css` supplies the responsive laboratory design, and `js/app.js` supplies views and navigation. `js/core.js` contains reusable assembly, answer checking, scoring and report functions; `js/storage.js` handles local persistence defensively. `version.js` is the single version definition. `assets/kslo-english-logo.png` is the unchanged original logo.

`site/data/modules.json` lists modules and card metadata. Each ready module references a `*-questions.json` bank and a separate `*-learn.json` document. Runtime content is loaded from these JSON files. The generator in `scripts/author-content.py`, if present, is an optional development convenience; teachers can edit the JSON directly and need not run it. Do not rerun the generator after manual edits unless you intend to regenerate its content.

`scripts/validate.mjs` checks content structure, unique questions, answer reachability, degree balance, distractors and mini-checks. `scripts/build.mjs` validates and copies only `site/` into `dist/`. `tests/` contains regression tests. The deployment workflow is `.github/workflows/deploy.yml`.

## Run and verify locally

No package installation or runtime libraries are needed. Use Node.js 22 or later and Python 3:

```sh
npm run dev
# Open http://localhost:3000/
npm run validate
npm test
npm run build
```

Opening `index.html` directly with `file://` does not work because browsers restrict fetching JSON there; use a static HTTP server. Browser interaction tests, when present, require the optional Python Playwright package and its Chromium/WebKit browsers. These are development-only dependencies, not downloaded by students.

## Edit or add questions

Edit the appropriate JSON bank in `site/data/`. Every question has a stable unique `id`, a `sentence` containing exactly one `_____` gap, a base-word hint, a `degree`, a `rule` label for report breakdowns, `blocks`, accepted `answers`, `correctSequences`, targeted `feedback` and a default `explanation`.

A word block is `{ "id": "base", "label": "easy", "kind": "word" }`. A suffix block is `{ "id": "suffix", "label": "-ier", "kind": "suffix", "transforms": { "easy": "easier" } }`. A connector such as `than` or `the` is a normal word block. Block IDs only need to be unique within their question. Every block can be used once.

When a suffix follows a word, its transform for that exact word is used. Otherwise its label, without the leading hyphen, is appended to the previous word. This deliberately lets incorrect reactions such as `easyer` be shown and explained. A suffix placed first remains visibly separate. For doubling, `big` plus `-ger` gives `bigger`, and `big` plus `-gest` gives `biggest`. Explicit transforms make the engine independent of a particular grammatical structure.

`answers` contains gap contents only, not the whole sentence. Include standard alternatives wherever the context permits. For every accepted answer, provide an ordered `correctSequences` entry containing block IDs that constructs it. For example `["base", "suffix", "than"]` can form `easier than`. Do not require another `the` or `than` if it is already supplied outside the gap. Adverbial superlatives often permit both with and without `the`; adjective superlatives before a noun generally require it unless another determiner is already present.

Include 2–3 distinct, plausible distractor blocks beyond the parts needed for the accepted alternatives. `feedback` entries match either exact incorrect strings in `answers`, or a JavaScript regular-expression string in `pattern`; matching is case-insensitive. The first matching entry wins. Keep patterns narrow enough not to misdiagnose another error. The fallback `explanation` must describe the correct formation for that question, not simply “wrong answer”. Use familiar fictional Hong Kong school contexts, rather than unverified factual claims.

Keep each bank at 60 or more questions, approximately half comparative and half superlative, with balanced regular, spelling-change, longer-form and irregular patterns as appropriate to the part of speech. Short adverbs and early are not governed by the regular long -ly pattern. Do not invent doubling examples for adverbs simply to match the adjective bank. Run `npm run validate` and `npm test` after editing.

## Edit Learn content

A Learn JSON document has `module`, `intro`, `sections`, `miniCheck` and `sources`. Sections use `title`, plain-text `text`, an `examples` array and optional `note`. Include exactly three mini-checks, each with `sentence`, unique `options`, an `answer` found among those options, and `explanation`. Content is escaped and displayed as text, not executed as HTML.

## Add a module without changing the core engine

Create a question-bank JSON file and a Learn JSON file using these schemas. Add a manifest entry with a unique `id`, `title`, `shortTitle`, `description`, `symbol`, `accent` (`teal` or `violet`), `available: true`, and relative `bank`/`learn` filenames. The homepage, Learn, setup, trials, storage, assignment links and reports discover it automatically. For a placeholder use `available: false`; it requires no bank or Learn file. Extend content validators if introducing a structure whose degree fields are not comparative/superlative; the runtime engine does not depend on those values. Update the optional Manus route manifest for new Learn/setup views.

## Scoring, persistence and privacy

A trial earns one mark only if its first non-empty submission is correct. A wrong first submission, later successful retry or Give Up earns zero. Empty submissions do not count as attempts. Reports retain first answers. Wrong-answer practice is scored separately, leaves the original report unchanged and never updates best records.

Best scores are separate for each module and 10/20/30 trial count. Unfinished experiments, mini-check choices and the latest completed report are saved in localStorage with the `kslo-grammar-lab:` prefix. They stay only in the same browser profile on the same device. Clearing site/browser data, resetting the browser, using another browser/device, or temporary private browsing can remove or hide them. If storage is blocked or full, the app shows a notice and remains playable without promising persistence.

Optional report name and class fields exist only on screen and in the requested printout. They are never passed to localStorage, a URL or a network request. Sound starts off and uses local Web Audio tones. There is no application backend, login, cookies, analytics, tracking or external font library. GitHub, like other hosts, can maintain its own access logs; this is separate from the app.

End Experiment asks before discarding unfinished work. Navigating to another app page or using browser back asks before leaving and keeps unfinished work saved where storage is available. Refresh/closing uses the browser's standard leave warning and can resume the saved state. The exact native warning text is controlled by the browser.

## GitHub Pages deployment

The repository should use the `main` branch. In Settings → Pages choose **GitHub Actions** as the source. The provided workflow runs on pushes to main and manual dispatch. It validates content, runs regression tests, generates a Hong Kong Time deployment timestamp, commits only `site/version.js` if it changes, packages `site/`, uploads the Pages artefact and deploys it. GitHub's normal workflow token can write the single version commit; its own push does not recursively trigger another workflow.

Versions follow `v[yymmdd]-[hhmmss]`, for example `v261027-181817`, in `Asia/Hong_Kong` (UTC+8). `site/version.js` is the only version source and is imported into the footer and report. Version generation occurs immediately before packaging so the deployed timestamp identifies that build. No scheduled job or external service is needed.

The workflow needs `contents: write` for the version commit, `pages: write` and `id-token: write` for Pages deployment. If branch protection blocks a bot's version commit, allow this workflow to write that file or remove the commit step while retaining generation in the deployment artefact. GitHub Pages must be supported by the repository's visibility/account plan. Do not add secrets or student data to this repository.

All runtime assets use relative URLs, and views use hashes, so `/grammar-lab/` works without a backend or SPA rewrite. Normal JSON edits pushed to main deploy automatically. Before editing after an automatic version commit, run `git pull --ff-only` so the local branch includes it.

## Accessibility and printing

Tap and native HTML drag/drop both work; keyboard users can place/return with Enter or Space and reorder with the visible arrow buttons or Left/Right on a placed block. Results are announced in a live region. Focus is visible, colours are high-contrast, and reduced-motion preferences disable effects. The report print stylesheet removes navigation and action controls, displays name/class if supplied, and preserves every practised question and rule breakdown. Choose the browser's Save as PDF destination when printing.

© 2026 K S Lo English. All Rights Reserved.
