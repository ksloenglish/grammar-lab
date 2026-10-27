# K S Lo Grammar Lab

The user approved the complete scope and clarified choices in the conversation, then authorised building, repository setup, pushing and publishing on 27 October 2026. Target: new `ksloenglish/grammar-lab`, GitHub Pages. No backend, login, telemetry, external runtime services or personal-data collection.

## Implementation

Dependency-free HTML/CSS/ES-module JavaScript served from `site/`. Relative paths and hash navigation support GitHub Pages subpaths. A reusable engine handles ordered word/suffix blocks, explicit bank-provided fusion transforms, answer alternatives, targeted feedback, first-attempt-only scoring, random sampling without replacement and independently scored retry rounds. Teacher-editable JSON defines module cards, banks and Learn sections/mini-checks. Native buttons support tapping and keyboards; native drag/drop plus accessible movement controls support ordering. Local storage saves serialisable experiment state and separate 10/20/30 best records; name/class never enters saved state. Graceful storage and loading failures preserve usable practice. Browser back uses an experiment guard; refresh uses a native leave warning and can resume.

`site/index.html`: semantic page shell; `site/css/styles.css`: responsive laboratory styling, motion and print; `site/js/core.js`: pure reusable assembly/scoring; `site/js/storage.js`: defensive persistence; `site/js/app.js`: navigation and views; `site/version.js`: only version definition; `site/data/modules.json`: module manifest; `site/data/{id}-questions.json`: banks; `site/data/{id}-learn.json`: learning content; `site/assets/`: original supplied logo; `scripts/`: validators and version/build helpers; `tests/`: automated tests; `.github/workflows/deploy.yml`: HKT version update and Pages deployment; `README.md`: teacher/deployment guide.

Both initial modules have at least 60 balanced questions and three mini-checks. Standard alternatives are accepted where permitted, including farther/further and appropriate optional adverbial `the`. Trial count links open preselected setup. Unfinished sessions resume locally. Best scores are separate by trial count and exclude retry practice. Report includes all questions, first answers, answers, first-attempt marks, percentages and rule breakdown. Optional print identity fields stay in ephemeral DOM only.

## Design

Modern laboratory theme as requested: an editorial scientific-workbench aesthetic, warm off-white surfaces, ink navy type, deep teal reaction colour and restrained violet for the second module. Clear typography, generous negative space, tactile reagent tiles and thin technical dividers. Desktop uses an asymmetric introduction and a compact live assembly demonstration; modules form stacked workbench panels. Phone layouts flow vertically at 360px; large screens use comfortably enlarged readable components. System sans-serif display/body pairing with monospace only for small specimen markers. Preserve original logo pixels in a padded navy rounded square.

Signature elements: small outlined glassware motifs, numbered specimen badges, and a dashed Assembly Chamber with fused answer preview. Brief 250–500ms glow/splitting effects and CSS particles; no continuous distracting movement. Reduced motion disables these effects. Sound is opt-in through local Web Audio tones. Contrast, focus, live regions and native controls take priority over decorative effects.

Voice: curious, precise and encouraging. Examples: “Small parts. Stronger grammar.” and “A reaction worth revising.”

## Delivery

Set up GitHub Actions with least necessary Pages permissions. Update `version.js` with the deployment timestamp in Asia/Hong_Kong. Publish only site files, not scripts or test artefacts. Verify content, scores, persistence, interaction, accessibility and subpath behaviour before delivery. Document observed test coverage honestly.
