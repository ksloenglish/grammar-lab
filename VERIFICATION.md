# Release verification

Latest published release: **v261110-191134**, deployed successfully on 10 November 2026 HKT by GitHub Actions run **42805410191**, for source commit **2d72266**. The previous release evidence is retained below.

The corrected application was successfully deployed and checked at https://ksloenglish.github.io/grammar-lab/ on 27 October 2026 (Hong Kong Time). The app release is **v261027-194643**. GitHub Actions run **40498668338** completed successfully for the final visual-change commit **b08d7f8**.

## Content and assessment

Both module banks contain 96 questions, with 48 comparative and 48 superlative questions and 24 questions in each rule group. All 192 situations were independently reviewed; 32 flagged contexts were clarified, with permanent generator overrides and an audit record. Published question JSON was compared with the verified source.

Deployment validation and 30 Node regression tests pass. Comparative stems do not provide than; superlative stems do not provide the. Formation words more/most are not prefilled. All adjective-superlative answers include the; natural optional-the adverb alternatives remain supported. Every tray contains the complete formation ingredients and the controlled final-y deletion operation. Accepted sequences are reachable and cannot conceal invalid suffix labels. First-attempt-only marking, retry/give-up and separate wrong-answer practice scores are preserved.

## Interactions, storage and visual checks

The cross-browser interaction suite passed 76 assertions in Chromium and WebKit, including keyboard operation, tap/return/reordering, native drag, browser-back and End confirmation, first-attempt scores, assignment setup, resume, best records, mini-checks, reports and printing. Blocked-storage and network-error paths were checked. Old incompatible question snapshots are backed up locally and not resumed; independent best scores are preserved.

The visual-spacing suite passed 41 checks. Playful Home, Setup, Learn, trials, feedback, Report and confirmation layouts were inspected. The live public app was checked on a 1440px desktop and a 360px phone.

The final all-bank tile audit passed for **2,430 labels per viewport**: all words are on one line without smaller font or clipped labels. The deletion control is compact and shows a red cross before y, with a precise accessible operation name. The happy → happ → happier sequence, visible crossed-out y, +1 first-attempt mark, reduced motion and no overflow were verified on the actual published site. Aa/Av badges are absent. Conical Home flasks have short flared necks, sloping shoulders, broad bases and clipped liquid; their rendered appearance was visually reviewed.

## Deployment and maintenance

The public repository is https://github.com/ksloenglish/grammar-lab. GitHub Pages publishing is configured through Actions. The action updates the sole version.js in Hong Kong Time. Built CSS and every JavaScript module edge carry that version to prevent mixed cached releases. No backend, account, external font or application analytics is used. Report identity fields are not stored or sent.

The reusable PROMPT.md, README, generator, deployment validator and regression tests preserve the final teaching and UI rules. Documentation-only verification commits can use the existing `[skip ci]` convention because they do not change deployed app files.

## Home usability update — 10 November 2026

Removed the sound control, its listeners, playback calls and Web Audio code. Top-right Lab home remains a visible, outlined text button on 360px phones, with a 44px minimum touch target and the existing unfinished-experiment confirmation. The Home heading is How to build a word; the example shows easy + ×y + -ier → easier and shares the engine-generated easy → eas → easier spelling strip. The compact red-cross-before-y operation has an accessible remove-final-y label. No question-bank, scoring or storage schema changed.

Local release checks passed: bank validation for both unchanged 96-question banks; all 34 Node regressions (including four permanent Home/silence checks); static build; affected JavaScript and Python syntax; git diff --check; 112 focused Home/mobile/silence browser assertions and 76 existing interaction assertions on Chromium and WebKit. The existing spelling, all-bank tile (2,430 labels per viewport), 41-check visual-spacing, colourful visual-journey and bank-update/storage suites also passed. Desktop and phone Home demos and mobile navigation were visually inspected; reduced motion and leave confirmation remained functional. Browser-test prerequisites were restored in the sandbox before completing browser checks.

GitHub Actions run **42803207612** completed successfully for source commit **33b4f29**. The workflow version commit **7b9dd2d** was pulled without rewriting history. The live release is **v261110-185540**. Public-site tests passed all 112 focused Home/UI/silence assertions and 76 interaction assertions on desktop Chromium and 360px WebKit, plus the spelling-operation suite. The public index, version, CSS, application/effects modules and both question banks returned HTTP 200 and matched the versioned local build byte for byte.

## Home-only spelling-strip removal — 10 November 2026

At the teacher’s request, removed the highlighted yellow easy → eas → easier intermediate spelling strip from the Home demonstration only. Kept the easy + ×y + -ier ingredients, downward arrow, easier result and caption. The shared spelling-step renderer and all experiment feedback remain unchanged. Updated the permanent source and browser regressions to reject a Home spelling strip while requiring experiment spelling rendering. Updated current README, prompt, plan and outcomes so the strip is not regenerated.

Local validation passed both question banks, all 34 Node regressions, the static build, JavaScript/Python syntax and git diff --check. The focused Home suite passed 114 desktop/mobile assertions; experiment spelling checks passed on Chromium 1440px and WebKit 360px, and all 41 visual-spacing checks passed.

The Home-only removal was published successfully as **v261110-191134**, GitHub Actions run **42805410191**, source commit **2d72266**. The automatic version commit **c0144c8** was pulled. Live checks passed all 114 focused Home assertions and the experiment spelling suite on desktop Chromium and 360px WebKit. The public version returned HTTP 200 and matched the source; public Home markup omits the strip while experiment markup retains spelling feedback. Simplified desktop and mobile Home screenshots were visually inspected.

## Noun-free accepted answers — 10 November 2026

Replaced exactly six noun-bearing adjective comparatives: adj-085/087/089/091/093/095. New answers are better than, worse than and farther than/further than. The other 90 adjective questions and all 96 adverb questions are unchanged. Both banks retain 96 unique IDs, 48/48 comparative/superlative questions and 24 questions per rule group; all alternatives remain constructible. Existing noun-free quantity superlatives stay unchanged. The full deterministic generators match the JSON banks exactly, and the existing headword audit mappings were refreshed using already-audited good/bad/far targets.

Removed the generator’s quantity-comparative path. Generator, deployment and shared saved-question validation reject noun/unrelated word ingredients, extra lexical headwords and arbitrary transform-smuggled nouns. The exact old adj-089 JSON is preserved in regression fixtures. Schema remains 2: incompatible noun-bearing snapshots are archived while unaffected current experiments and independent best scores are retained. Core, storage and first-attempt scoring code are unchanged. README, prompt, plan and outcomes now preserve the permanent no-noun-in-answer rule.

Local release baseline passed: both bank validations, all 48 Node regressions (14 new noun-free tests), static build, changed JS/Python syntax, git diff --check, full-generator equality and a negative generator transform test. Existing cross-browser interaction suite passed 76 assertions; old-schema bank archival and spelling suites passed; the all-bank tile audit passed 2,436 labels per viewport; all 41 spacing checks passed. The new schema-2 noun-bank archival/resume/report browser test passed 40 checks on desktop Chromium and 360px WebKit with best 8/10 retained. All six replacements were rendered on both browsers (12 cases): correct new sentence/base/answers, no noun tiles, compatible resume and no document overflow. Representative phone cup and desktop long-plan screenshots were visually inspected.
