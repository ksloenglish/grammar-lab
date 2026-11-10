# Release verification

Latest published release: **v261110-185540**, deployed successfully on 10 November 2026 HKT by GitHub Actions run **42803207612**, for source commit **33b4f29**. The previous release evidence is retained below.

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
