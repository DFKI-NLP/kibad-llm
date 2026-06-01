# Eval dashboard phase-by-phase refactor plan

## Checklist

- [x] Define safe, incremental refactor phases
- [x] Establish a future-proof `docs/eval-dashboard/index.html` entry point early
- [x] Specify concrete file extractions per phase
- [x] Add validation steps after each phase
- [x] Suggest sensible commit boundaries
- [x] Keep the initial testing strategy aligned with this Python-first repository
- [x] Start smoke tests and logic tests as early as practical
- [x] Make the `eval-dashboard.html` migration safe for links and bookmarks
- [x] Add a concrete baseline artifact and curated fixture strategy
- [x] Require post-phase planning-doc updates and compliance with `CONTRIBUTING.md`

## Goal

Refactor the eval dashboard in small, behavior-preserving steps.

The guiding idea is:

- keep the dashboard working at every step
- avoid introducing a new frontend **build** toolchain in the first pass
- still allow a lightweight JS logic-test setup once pure modules exist
- make the dashboard progressively easier to test from the start, not only at the end
- establish the dashboard's long-term folder structure early, then modularize CSS and JavaScript underneath it

This plan assumes:

- `docs/eval-dashboard/index.html` becomes the public dashboard page early in the refactor
- dashboard runtime assets live under `docs/eval-dashboard/assets/`
- tests and fixtures live under `tests/`
- runtime docs paths stay hyphenated (`eval-dashboard`), while test directories use Python-friendly underscores (`eval_dashboard`)
- the repo remains Python-first for docs/fixture/smoke coverage, while extracted dashboard logic should move to a minimal JS-native test runner once pure modules exist
- all work in this refactor complies with `CONTRIBUTING.md`

## Current implementation state

As of the current repository state:

- Phase 0 baseline artifacts exist under `tests/fixtures/eval_dashboard/baseline/`
- the dashboard runtime page now lives at `docs/eval-dashboard/index.html`
- `docs/eval-dashboard.html` is currently a temporary compatibility shim
- `properdocs.yml` navigation points to `eval-dashboard/index.html`
- `docs/index.md` links point to `eval-dashboard/index.html`
- populated Phase 5 runtime assets now exist under `docs/eval-dashboard/assets/`: CSS lives under `assets/css/`, `assets/js/main.js` remains the external entry module, and first pure helpers now live under `assets/js/utils/`
- structural smoke coverage now includes `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py` and `tests/unit/eval_dashboard/test_eval_dashboard_html_contracts.py`
- first browser-free JS utility logic coverage now exists under `tests/unit/eval_dashboard/js/` via the Node.js built-in test runner, which is now the long-term home for extracted dashboard logic tests in later phases
- curated Phase 2 fixtures now exist under `tests/fixtures/eval_dashboard/`, including valid version-0/1/2 examples, invalid edge-case fixtures, and explicit fixtures for all currently supported plot families (`bars`, `errors`, `confusion_matrix`, `tpfpfn`)
- fixture provenance is documented in `tests/fixtures/eval_dashboard/README.md`
- fixture integrity smoke coverage exists at `tests/unit/eval_dashboard/test_dashboard_fixtures.py`
- docs-build validation relies on the repo-level `check-mkdocs (uv)` hook against `properdocs.yml`, rather than a dashboard-specific subprocess test
- old-path coverage currently relies on the compatibility shim; the ProperDocs redirects plugin is **not** being used for this raw HTML page
- Phase 3 CSS extraction remains complete: `docs/eval-dashboard/index.html` still loads `assets/css/index.css` and contains no inline `<style>` block
- Phase 4 JS externalization is complete: `docs/eval-dashboard/index.html` now loads `assets/js/main.js` as a single external `type="module"` script and contains no inline `<script>` block
- the structural smoke tests now assert the external CSS and external module-script contract rather than a Phase 3 inline-script freeze
- the baseline contract now records the Phase 5 utility-module and JS-test harness contract instead of freezing the full `main.js` file contents

### Status checkpoint

The repository is currently **through Phase 5 and ready for Phase 6**:

- Phase 0 baseline artifacts landed
- Phase 1 folder migration and compatibility shim landed
- Phase 2 curated fixtures and structural smoke coverage landed
- Phase 3 CSS extraction and HTML contract guardrails landed
- Phase 4 JS externalization landed
- Phase 5 utility extraction, the permanent JS-native logic-test runner, and explicit CI wiring landed

That means the next implementation step is to **start Phase 6** by extracting state and selector logic while extending the same JS-native test harness.

______________________________________________________________________

## Conventions and design rules

### Directory naming convention

Use:

```text
docs/eval-dashboard/
tests/fixtures/eval_dashboard/
tests/unit/eval_dashboard/
tests/integration/eval_dashboard/
```

This keeps the public docs path stable while aligning test directories with existing repo conventions.

### Module dependency direction

Make the dependency rules explicit from the start:

- `utils/` imports nothing dashboard-specific
- `state/` depends only on plain data shapes and `utils/`
- `data/` depends on `utils/` and canonical data/state shapes, not on UI modules
- `ui/` consumes selector outputs and DOM refs, but not raw loader modules
- `plots/` consumes selector/data outputs, not broad global DOM state spread across the codebase
- `main.js` orchestrates imports, DOM refs, event wiring, and render/update flows
- no module should import back from `main.js`

### Shared DOM lookup ownership

The shared element lookup should live in `docs/eval-dashboard/assets/js/ui/dom.js`.

Recommended pattern:

- `ui/dom.js` exports a single `captureDomRefs(document)` helper plus low-level DOM helpers
- `main.js` calls `captureDomRefs(document)` once during bootstrap
- `main.js` owns the returned refs object and passes it into render/update flows

This keeps selectors/data modules DOM-free and prevents repeated global lookups scattered throughout the UI layer.

### Baseline artifact rule

“Behavior-preserving” should mean “preserves a checked-in baseline artifact and curated fixtures”, not only “still seems okay manually”.

### Contribution and planning-maintenance rule

- Every change made as part of this refactor must comply with `CONTRIBUTING.md`, including its requirements around documentation, testing, and review readiness.
- After each completed phase, update the planning docs under `docs/eval-dashboard/` so they accurately reflect:
    - the current implementation state
    - which phases are complete/in progress/next
    - any scope, sequencing, or validation changes discovered during the phase
- At minimum, keep `eval-dashboard-phase-by-phase-refactor-plan.md` and `eval-dashboard-modularization-plan.md` synchronized after each phase boundary.

### Phase completion checklist

Before considering any phase complete:

- finish the phase-specific validation listed below
- update the planning docs in `docs/eval-dashboard/` to record the new status and next step
- confirm the resulting changes still comply with `CONTRIBUTING.md`

______________________________________________________________________

## Phase 0. Record a concrete baseline and source-fixture audit

### Goal

Capture the current dashboard behavior in a checked-in artifact before any extraction work begins.

### Why

The current dashboard is large and tightly coupled. Before moving code around, define what “still works” means in a way that later phases can compare against.

### Tasks

- Keep the current dashboard behavior unchanged while recording a baseline before the folder move.
- Create a baseline area under:

```text
tests/
  fixtures/
    eval_dashboard/
      baseline/
        baseline-manifest.md
        baseline-summary.json
        optional-screenshots/
```

- Document representative features that must remain stable during refactoring.
- Identify a minimal set of representative source experiments for fixture curation.
- Prefer source experiments dated **later than `2026-01-16`** in `data/prediction_results/readme.md`, so the refactor is exercised against newer real-world dashboard inputs.

### Recommended source experiments to curate from

Start with a small representative subset drawn from newer experiments such as:

- `311_better_default_temperature`
- `327_faktencheck_core_with_persona`
- `333_organism_trends_with_persona`
- `380_faktencheck_core`
- `380_organism_trends`
- `397_faktencheck_core_v1_for_chunking`
- `422_organism_trends`
- `428_organism_trends_with_chunking`
- `454_faktencheck_core`
- `477_faktencheck_core`
- `477_organism_trends`
- `481_faktencheck_core`

If an older run is needed to preserve compatibility with an earlier input shape, include it deliberately as an edge fixture and document why.

### Baseline behavior checklist

At minimum, record whether the current dashboard correctly supports:

- loading local evaluation folders/files
- loading from GitHub URL input
- prediction grouping
- evaluation experiment tabs
- JSON side pane behavior
- error plots
- confusion matrix plots
- TP/FP/FN plots
- grouped bar plots
- figure export/download state
- light/dark styling

### What the baseline artifact should capture

At minimum:

- which curated sources or prototype fixtures cover which feature families
- expected visible tabs/panels/plot families
- whether figure export should be enabled
- any known caveats or intentionally unsupported cases

A good split is:

- `baseline-manifest.md` for prose and rationale
- `baseline-summary.json` for machine-checkable expectations

### Suggested validation

Build and serve the docs site and manually verify the dashboard once before starting the refactor.

Before closing Phase 0, update the planning docs under `docs/eval-dashboard/` with the recorded baseline status and confirm the baseline/documentation changes comply with `CONTRIBUTING.md`.

```bash
cd /home/arbi01/projects/kibad-llm
uv run --group cicd properdocs build
uv run --group cicd properdocs serve -w .
```

### Suggested commit boundary

`docs(eval-dashboard): record baseline artifact for modularization`

______________________________________________________________________

## Phase 1. Move to a future-proof dashboard folder structure without breaking links

### Goal

Settle the long-term dashboard namespace immediately so later diffs focus on behavior and module extraction rather than file relocation.

### Tasks

- Move `docs/eval-dashboard.html` to `docs/eval-dashboard/index.html`.
- Update `properdocs.yml` so the navigation points to the new dashboard entry page.
- Update in-repo links that currently point at `eval-dashboard.html`, including `docs/index.md`.
- If the docs host cleanly supports raw HTML redirects, add a redirect entry for `eval-dashboard.html`.
- Otherwise, keep a temporary shim at `docs/eval-dashboard.html`.
- Create the dashboard asset namespace at:

```text
docs/
  eval-dashboard/
    index.html
    assets/
      css/
      js/
```

- Keep the HTML body and behavior unchanged in this phase apart from path updates.
- Update relative references only as needed for the new page location.

### Why this phase comes first

If the dashboard is expected to grow soon, doing the folder move first avoids a second structural migration later and gives cleaner git history for subsequent CSS/JS extraction work.

### Suggested early smoke tests in this phase

Add a first structural test file under:

```text
tests/unit/eval_dashboard/
  test_eval_dashboard_entrypoint.py
```

Initial checks can include:

- `docs/eval-dashboard/index.html` exists
- `properdocs.yml` points nav to the new entry page
- `docs/index.md` links to the new entry page
- redirect/shim coverage exists for the old path

### Suggested validation

- verify ProperDocs navigation still resolves to the dashboard page
- verify old in-repo links were updated
- verify the compatibility strategy chosen for the old URL/path actually works in the built site
- verify the dashboard page loads after the path move
- verify no behavior changes apart from the file location
- update the planning docs in `docs/eval-dashboard/` to record the completed entrypoint migration and confirm the phase changes comply with `CONTRIBUTING.md`

### Suggested commit boundary

`docs(eval-dashboard): move dashboard entry to folder-based structure`

______________________________________________________________________

## Phase 2. Compile curated fixtures from newer experiment data and add first smoke tests

### Goal

Create stable, reviewable dashboard fixtures early and immediately use them for smoke coverage.

This phase should establish a **thin but durable pre-refactor safety net**.

It should **not** try to build a full-fledged dashboard interaction test suite against the current monolithic HTML page. At this point in the refactor, that would likely overfit unstable implementation details, add tooling overhead too early, and create test churn once CSS/JS extraction begins.

Instead, Phase 2 should focus on:

- stable fixture curation
- structural docs/runtime contracts
- lightweight validation of baseline assumptions
- test coverage that is expected to survive the first extraction phases largely unchanged

### Tasks

Add a dedicated fixture area:

```text
tests/
  fixtures/
    eval_dashboard/
      baseline/
      bars/
      errors/
      run_v0/
      run_v1/
      run_v2/
      confusion_matrix/
      tpfpfn/
      malformed/
      unsupported_version/
      conflicting_prediction_ids/
```

Possible sources to adapt from:

- representative experiment folders documented in `data/prediction_results/readme.md`
- especially runs dated later than `2026-01-16`
- simplified copies of real `job_return_value.json` + `.hydra/overrides.yaml` pairs

### Recommended fixture-sourcing policy

- Prefer newer representative runs such as `311_*`, `327_*`, `333_*`, `380_*`, `397_*`, `422_*`, `428_*`, `454_*`, `477_*`, and `481_*`.
- Curate **minimal snapshots**, not full copied experiment trees.
- Document the source run for every curated fixture.
- Do **not** make tests depend directly on `data/prediction_results/logs/` at runtime.

### What to include

At minimum:

- one valid version-0 style run
- one valid version-1 style run
- one valid version-2 style run
- one unsupported version example
- one malformed JSON/YAML example
- one conflicting prediction-id example
- one explicit grouped-bar-plot example
- one explicit error-plot example
- one example that produces confusion-matrix output
- one example that produces TP/FP/FN output
- one example that exercises a newer post-`2026-01-16` organism-trends-style run
- one example that exercises a newer post-`2026-01-16` faktencheck-style run

### Pre-refactor testing stance

Before CSS/JS extraction starts, prefer **contract-style smoke tests** over a broad browser-style test suite.

Good Phase 2 tests should mostly verify things that are expected to remain stable during Phases 3 to 5, such as:

- public entrypoint paths
- compatibility/redirect behavior
- presence of key dashboard DOM anchors and controls
- fixture integrity and provenance
- baseline feature expectations being backed by either curated fixtures or durable page structure

Avoid making Phase 2 depend on:

- a new frontend build pipeline
- broad browser automation against the current monolith
- brittle assertions over incidental markup/layout details that are likely to change during extraction

### Smoke tests to add now

Add:

```text
tests/unit/eval_dashboard/
  test_eval_dashboard_entrypoint.py
  test_dashboard_fixtures.py
  test_eval_dashboard_html_contracts.py
```

Potential initial checks:

- fixture directories exist and contain the expected required files
- intentionally invalid fixtures are documented as invalid
- the repo-level docs check still succeeds with the migrated dashboard entry page present

Add the following as open TODOs/goals of this phase before moving deeper into modularization. Several of these have now landed and should remain as guardrails for later phases:

- assert that valid fixture `job_return_value.json` files parse successfully
- assert that valid fixture `.hydra/overrides.yaml` files parse successfully
- assert that intentionally malformed fixtures fail in the intended way, and document whether the failure is malformed JSON, malformed YAML, or both
- assert that every currently supported plot family has an explicit curated fixture: `bars`, `errors`, `confusion_matrix`, and `tpfpfn`
- add a small HTML contract smoke layer for `docs/eval-dashboard/index.html` that checks durable anchors such as:
    - dashboard title/heading
    - local file/folder load controls
    - GitHub URL load control
    - prediction/evaluation containers
    - JSON pane container
    - export/download control
    - tooltip/plot container hooks
- after Phase 3, tighten that HTML contract layer to assert that the external stylesheet is present, the inline `<style>` block is gone, and the single inline `<script>` remains unchanged until Phase 4
- add a baseline-to-coverage smoke check so key entries in `baseline-summary.json` are backed by either:
    - an explicit fixture family, or
    - a durable structural assertion in `docs/eval-dashboard/index.html`
- add fixture-provenance assertions so the curated fixture README continues to document purpose, source basis, and notes for each fixture directory
- if practical, add a built-site compatibility smoke check that verifies the old dashboard path remains intentionally covered after docs build output is generated

### Tests that should intentionally wait until later phases

Do **not** force the following into Phase 2 unless stable JS modules already exist:

- detailed normalization logic tests
- selector/grouping/sorting logic tests
- rendering tests for isolated UI modules
- plot data-shaping tests
- browser-driven interaction tests for file loading, GitHub loading, tab switching, JSON pane sync, or export behavior

Those tests become much more valuable once the code has been extracted into importable JS modules with clearer seams.

### Why this phase comes early

Fixtures and smoke tests make later module extraction safer and prevent the refactor from becoming a long sequence of untested file moves.

Just as importantly, keeping Phase 2 intentionally lightweight avoids over-investing in brittle tests for the pre-modular monolith while still putting a meaningful safety net in place.

### Suggested validation

```bash
cd /home/arbi01/projects/kibad-llm
uv run --group cicd pytest tests/unit/eval_dashboard
uv run --group cicd check-mkdocs --config properdocs.yml
```

Before closing Phase 2, update the planning docs in `docs/eval-dashboard/` with the landed fixture/smoke-test status and confirm the added tests/docs comply with `CONTRIBUTING.md`.

### Suggested commit boundary

`test(eval-dashboard): add curated fixtures and initial smoke coverage`

______________________________________________________________________

## Phase 3. Extract CSS only and tighten structural tests

**Status in current repository:** completed.

### Goal

Move all styling out of `docs/eval-dashboard/index.html` without changing dashboard behavior.

### Tasks

Create:

```text
docs/eval-dashboard/assets/css/
  index.css
  tokens.css
  layout.css
  controls.css
  tables.css
  plots.css
```

Then:

- move the inline `<style>` block from `docs/eval-dashboard/index.html` into the CSS files
- keep the HTML structure unchanged
- have `docs/eval-dashboard/index.html` load only the external stylesheet

### Landed Phase 3 outcome

The current branch already matches this phase:

- `docs/eval-dashboard/assets/css/` contains `index.css`, `tokens.css`, `layout.css`, `controls.css`, `tables.css`, and `plots.css`
- `docs/eval-dashboard/index.html` references `assets/css/index.css`
- the inline `<style>` block is gone
- the lone inline `<script>` block is intentionally still present pending Phase 4
- `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py` asserts that the expected CSS files exist
- `tests/unit/eval_dashboard/test_eval_dashboard_html_contracts.py` asserts the external stylesheet reference, the removal of inline CSS, and the single-inline-script Phase 3 contract
- the Phase 3 inline-script fingerprint is checked against `tests/fixtures/eval_dashboard/baseline/baseline-summary.json`

### Suggested CSS split

- `tokens.css`: root variables, theme colors, typography
- `layout.css`: page spacing, panel layout, split views, grid layout
- `controls.css`: buttons, tabs, form controls, rows, chips
- `tables.css`: table layout, sticky headers, selected rows, JSON pane styles
- `plots.css`: plot cards, tooltips, legends, export-related styles
- `index.css`: imports or central stylesheet entry point

### Important constraint

Do **not** rename classes or change DOM structure in this phase unless absolutely necessary.

### Test additions in this phase

Extend `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py` or add `test_eval_dashboard_assets.py` to assert:

- expected CSS files exist
- `docs/eval-dashboard/index.html` references the external stylesheet
- the giant inline `<style>` block is gone or greatly reduced as intended

That coverage is now effectively present via the existing entrypoint and HTML-contract smoke tests.

### Validation checklist

After extraction, verify:

- page styling still loads
- dark/light theme still works
- sticky table headers still work
- JSON pane layout still works
- tooltip styling still works
- plot cards and legends still appear correctly

### Suggested validation

```bash
cd /home/arbi01/projects/kibad-llm
uv run --group cicd pytest tests/unit/eval_dashboard
uv run --group cicd properdocs build
uv run --group cicd properdocs serve -w .
```

Keep the planning docs in `docs/eval-dashboard/` updated with the completed CSS-extraction status, and ensure any follow-up changes for this phase comply with `CONTRIBUTING.md`.

### Suggested commit boundary

`docs(eval-dashboard): externalize dashboard CSS`

______________________________________________________________________

## Phase 4. Move the inline script into one external module

**Status in current repository:** completed.

### Goal

Reduce HTML complexity first, before splitting JavaScript into many files.

### Tasks

Create:

```text
docs/eval-dashboard/assets/js/
  main.js
```

Then:

- move the full inline `<script>` body from `docs/eval-dashboard/index.html` into `docs/eval-dashboard/assets/js/main.js`
- replace the inline block with a single external script reference
- use module loading from this point onward so later extraction does not require another script-loading transition

### Important constraint

This phase should still be **behavior-preserving**.
Do not split logic yet. Keep:

- the current `state`
- DOM element lookups
- current functions
- current event wiring

all together in `main.js`.

### Landed Phase 4 outcome

The current branch already matches this phase:

- `docs/eval-dashboard/assets/js/main.js` exists and contains the previously inline dashboard script body in one file
- `docs/eval-dashboard/index.html` references `assets/js/main.js` via a single `type="module"` script tag
- the inline `<script>` block is gone
- `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py` asserts that the expected JS entry file exists
- `tests/unit/eval_dashboard/test_eval_dashboard_html_contracts.py` asserts the external stylesheet reference, the external module-script reference, and the removal of inline CSS/JS from the runtime entry page

### Why this phase matters

Once the script is externalized, future refactors stop rewriting a huge HTML file and start operating on normal JS modules.

### Test additions in this phase

Extend structural tests to verify:

- `docs/eval-dashboard/assets/js/main.js` exists
- `docs/eval-dashboard/index.html` references the external script
- the giant inline `<script>` block is gone or reduced to the minimal loader tag

### Validation checklist

Verify that all existing interactions still work:

- local folder load
- GitHub load
- prediction table rendering
- evaluation table rendering
- plot rendering
- figure download button state
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the extracted-script changes comply with `CONTRIBUTING.md`

### Suggested commit boundary

`docs(eval-dashboard): move inline dashboard script to external module`

______________________________________________________________________

## Phase 5. Add lightweight JS logic tests and extract pure utilities

**Status in current repository:** complete.

### Goal

Start testing extracted pure JS logic as soon as it exists, while separating small reusable helpers from `main.js`.

### Tasks

Create:

```text
docs/eval-dashboard/assets/js/utils/
  flatten.js
  sort.js
  values.js
  text.js
```

Create a reserved place for JS logic tests under:

```text
tests/unit/eval_dashboard/js/
```

If a lightweight JS runner must be introduced, keep it minimal and browser-free. This is acceptable in the first pass because it is a test harness, not a frontend build pipeline.

Prefer a **JS-native** runner for extracted dashboard logic tests. In this repository, the default first choice should be the **Node.js built-in test runner** rather than a larger frontend stack. Do not treat a pytest-driven Node subprocess harness as the long-term testing architecture for `tests/unit/eval_dashboard/js/`.

### Candidate extractions

#### `flatten.js`

- object flattening helpers
- path traversal helpers if generic

#### `sort.js`

- sort collator setup
- sortable-number parsing
- sort config normalization
- generic item sorting helpers

#### `values.js`

- normalization of values
- default/effective value helpers
- display formatting helpers for values

#### `text.js`

- label/filename sanitization helpers
- reusable text formatting helpers

### Important constraint

Only move functions that are truly low-coupling and mostly independent of the DOM.

### Tests to add in this phase

Add first logic tests for extracted pure helpers, for example:

- sorting behavior
- filename/label sanitization
- flattening/path traversal helpers
- value formatting/defaulting behavior

Use the same JS-native runner that later selector/normalization/loader logic tests will use. Phase 5 should establish that permanent logic-test layer early so Phases 6 to 8 can extend it without another testing-strategy migration.

### Why this phase is early

It creates reusable building blocks and proves the dashboard can gain real logic coverage during the refactor rather than after it.

### Validation checklist

- imports still resolve
- sorting behavior remains unchanged
- filename generation remains unchanged
- flattening/grouping-dependent helpers still behave the same
- new JS logic tests pass under the chosen minimal JS-native runner
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the utility/test changes comply with `CONTRIBUTING.md`

### Phase 5 deliverables checklist

Phase 5 is complete only when all of the following are true:

- `docs/eval-dashboard/assets/js/utils/` contains the intended low-coupling utility modules extracted from `main.js`
- `docs/eval-dashboard/assets/js/main.js` imports those utility modules without changing runtime behavior
- `tests/unit/eval_dashboard/js/` is established as the long-term location for extracted dashboard JS logic tests
- extracted dashboard JS logic tests run through the permanent minimal JS-native runner rather than a pytest-driven Node subprocess bridge
- the JS-native dashboard logic-test command is wired into CI as an explicit check
- the extracted Phase 5 utility coverage has been re-validated under that permanent harness

### Current Phase 5 state

The current branch now covers the full scope of this phase:

- `docs/eval-dashboard/assets/js/utils/` contains `flatten.js`, `sort.js`, `values.js`, and `text.js`
- `docs/eval-dashboard/assets/js/main.js` imports those Phase 5 utility modules while preserving the existing runtime entrypoint contract
- `tests/unit/eval_dashboard/js/` is the long-term location for extracted dashboard JS logic tests
- `tests/unit/eval_dashboard/js/utils.flatten.test.mjs`, `utils.sort.test.mjs`, `utils.text.test.mjs`, and `utils.values.test.mjs` run the extracted pure-helper coverage through the Node.js built-in test runner
- `tests/unit/eval_dashboard/js/README.md` documents `node --test tests/unit/eval_dashboard/js/*.test.mjs` as the default local command for later phases
- the JS-native harness now uses a flat `*.test.mjs` namespace such as `utils.flatten.test.mjs` and `state.selectors.test.mjs`, so later phases can add files without changing the command or introducing recursive globbing
- `docs/eval-dashboard/assets/js/package.json` pins the dashboard runtime modules to ESM semantics for the permanent JS-native harness
- `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py` asserts that the expected utility modules exist
- `tests/unit/eval_dashboard/test_eval_dashboard_baseline_contract.py` and `tests/fixtures/eval_dashboard/baseline/baseline-summary.json` now record the permanent Node.js-native Phase 5 utility/test contract rather than freezing the full `main.js` file contents
- `.github/workflows/code_quality_and_tests.yml` runs the dashboard JS logic tests as their own explicit CI job

### Phase 5 completion notes

Phase 5 is now complete because:

- the temporary pytest-driven Node subprocess bridge has been removed
- the permanent minimal JS-native runner is `node --test tests/unit/eval_dashboard/js/*.test.mjs`
- the permanent harness keeps test files flat under `tests/unit/eval_dashboard/js/`, using module-scoped names such as `utils.sort.test.mjs` and `state.selectors.test.mjs`
- later phases should extend that same `tests/unit/eval_dashboard/js/` harness rather than reintroducing Python-driven bridging
- the extracted Phase 5 utility coverage has been re-validated under the permanent harness and under the updated Python-side contract checks

### Suggested commit boundary

`refactor(eval-dashboard): extract pure utility modules and add logic tests`

______________________________________________________________________

## Phase 6. Extract state and selectors, then add selector tests

### Goal

Separate canonical state from derived data access and test the derived logic early.

### Tasks

Create:

```text
docs/eval-dashboard/assets/js/state/
  store.js
  selectors.js
```

### `store.js`

Move:

- the main mutable `state` object
- load/reset state helpers
- eval-tab state initialization helpers
- small state mutation helpers that do not render directly

### `selectors.js`

Move derived-read logic such as:

- prediction lookup helpers
- evaluation lookup helpers
- prediction views
- prediction columns
- prediction groups
- selected groups/evaluations
- evaluations by experiment
- active evaluation context
- plot grouping/selectors

### Design rule

Selectors should:

- compute derived values from state
- avoid directly updating the DOM
- avoid directly attaching event listeners

### Tests to add in this phase

Add selector/state logic tests under:

```text
tests/unit/eval_dashboard/js/
```

Run those tests with the same minimal JS-native runner established at the Phase 5/6 boundary rather than by expanding a Python subprocess wrapper.

Keep those JS-native test files flat under `tests/unit/eval_dashboard/js/` so the established command remains:

```bash
node --test tests/unit/eval_dashboard/js/*.test.mjs
```

Recommended naming examples for this phase:

- `state.store.test.mjs`
- `state.selectors.test.mjs`

Focus on:

- grouping behavior
- selection behavior
- experiment grouping
- sorting-state interpretation
- plot-group selector derivation

### Why this phase matters

This is the major step that makes the dashboard testable at the logic layer.

### Validation checklist

Verify no regression in:

- grouping behavior
- selection behavior
- experiment tab behavior
- sorting state
- plot-group selection inputs
- selector tests pass
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the state/selector changes comply with `CONTRIBUTING.md`

### Suggested commit boundaries

- `refactor(eval-dashboard): extract state store`
- `refactor(eval-dashboard): extract selector logic and add tests`

______________________________________________________________________

## Phase 7. Extract parsing and normalization, then add normalization tests

### Goal

Make imported dashboard data handling testable and clearly separated from rendering.

### Tasks

Create:

```text
docs/eval-dashboard/assets/js/data/
  parse-overrides.js
  normalize.js
```

### `parse-overrides.js`

Move:

- overrides parsing logic
- any helper functions dedicated to `.hydra/overrides.yaml`

### `normalize.js`

Move:

- `job_return_value` version handlers
- `normalizeImportedJobReturnValue(...)`
- prediction-id extraction logic
- canonical normalization of prediction/evaluation payloads
- normalization helpers specific to imported run data

### Design rule

This layer should convert raw input into the dashboard’s canonical internal shape.

### Tests to add in this phase

Use curated fixtures to add logic tests for:

- `data.parse-overrides.test.mjs`

- `data.normalize.test.mjs`

- supported version handling

- unsupported version rejection

- malformed files failing cleanly

- missing prediction-id handling

- conflicting prediction-id handling

- normalization of newer post-`2026-01-16` experiment-derived fixtures

Keep these as JS-native logic tests under `tests/unit/eval_dashboard/js/`; Python should continue to own fixture/docs/smoke checks around them.

### Why this phase matters

Data normalization is one of the most valuable areas to test independently.

### Validation checklist

Verify that:

- supported versions still load
- unsupported versions are still rejected correctly
- malformed files still fail cleanly
- missing prediction ids are still handled correctly
- conflicting prediction ids are still handled correctly
- normalization tests pass
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the parsing/normalization changes comply with `CONTRIBUTING.md`

### Suggested commit boundaries

- `refactor(eval-dashboard): extract overrides parsing`
- `refactor(eval-dashboard): extract run normalization and add tests`

______________________________________________________________________

## Phase 8. Extract local file loading and GitHub loading

### Goal

Separate all ingestion flows from normalization and rendering.

### Tasks

Create:

```text
docs/eval-dashboard/assets/js/data/
  file-loader.js
  git-loader.js
```

### `file-loader.js`

Move logic related to:

- reading selected local files
- file text loading
- determining relevant dashboard files
- collecting entries from file/folder input
- loading evaluations from local entries/files

### `git-loader.js`

Move logic related to:

- GitHub URL parsing
- resolving repo/ref/folder information
- recursive GitHub folder listing
- fetching GitHub files
- progress updates during GitHub loading
- loading evaluations from a GitHub URL

### Design rule

- loader modules fetch raw content
- normalization modules interpret it
- UI modules present it

### Tests to add in this phase

Prefer tests for pure loader-adjacent logic first, such as:

- GitHub URL parsing
- local entry filtering/relevance checks
- duplicate-run detection helpers
- progress-state derivation helpers if they are extractable

Keep these loader-adjacent logic tests in the same JS-native test layer established earlier, and avoid growing a second ad hoc harness for them.

Keep end-to-end loader interaction checks in the smoke/manual validation loop unless they can be made deterministic.

### Validation checklist

Verify:

- local fixture folders still load
- GitHub URL loading still works
- progress/status text still updates
- duplicate-run handling still works
- unsupported-version/malformed-run handling still works
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the loader changes comply with `CONTRIBUTING.md`

### Suggested commit boundaries

- `refactor(eval-dashboard): extract local file loader`
- `refactor(eval-dashboard): extract GitHub loader`

______________________________________________________________________

## Phase 9. Extract UI modules and centralize DOM refs

### Goal

Separate rendering concerns from state/data logic and introduce the final DOM-ref boundary.

### Tasks

Create:

```text
docs/eval-dashboard/assets/js/ui/
  dom.js
  controls.js
  tabs.js
  status.js
  prediction-table.js
  evaluation-table.js
  eval-json-pane.js
```

### Suggested responsibilities

#### `dom.js`

- `captureDomRefs(document)`
- generic DOM helper functions
- repeated element creation helpers
- generic sticky-column offset helpers
- low-level class/visibility helpers

#### `controls.js`

- options panel rendering
- truncate/default-value controls
- group-by button rendering
- plot control rendering

#### `tabs.js`

- prediction/evaluation/plot tab button rendering
- active tab state synchronization helpers

#### `status.js`

- load status and summary rendering
- progress label and download button state rendering

#### `prediction-table.js`

- prediction table rendering
- prediction sorting headers
- prediction row/group rendering

#### `evaluation-table.js`

- evaluation table rendering
- evaluation sorting headers
- row selection behavior if table-specific

#### `eval-json-pane.js`

- JSON side pane rendering
- JSON tab behavior
- JSON syntax highlighting helpers if isolated there

### Design rule

UI modules should mostly:

- receive state-derived inputs and DOM refs
- render DOM
- expose event callbacks to `main.js`

Avoid hiding state mutations deep inside many rendering functions unless necessary.

### Validation checklist

Verify that:

- `main.js` now captures DOM refs once and passes them down
- table rendering remains correct
- group selection still works
- JSON pane still syncs with row selection
- options tabs still work
- default/truncate controls still work
- sort buttons still work
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the UI-module changes comply with `CONTRIBUTING.md`

### Suggested commit boundaries

- `refactor(eval-dashboard): extract dom refs and shared ui helpers`
- `refactor(eval-dashboard): extract prediction and evaluation renderers`
- `refactor(eval-dashboard): extract json pane and control renderers`

______________________________________________________________________

## Phase 10. Extract plotting and export modules

### Goal

Move plotting logic into dedicated modules and leave `main.js` as orchestration only.

### Tasks

Create:

```text
docs/eval-dashboard/assets/js/plots/
  shared.js
  bars.js
  confusion.js
  tpfpfn.js
  legend.js
  export.js
```

### Suggested responsibilities

#### `shared.js`

- shared plot math/helpers
- generic SVG helpers
- shared label/metric helpers for plotting

#### `bars.js`

- grouped bar plot logic
- standard metric bar rendering
- generic plot-entry-to-bars rendering

#### `confusion.js`

- confusion matrix normalization for plotting
- confusion tab map creation
- confusion plot rendering

#### `tpfpfn.js`

- TP/FP/FN normalization
- TP/FP/FN tab map creation
- TP/FP/FN visual rendering

#### `legend.js`

- grouped legend model building
- legend element rendering
- legend item filtering

#### `export.js`

- SVG serialization
- figure download preparation
- export orchestration

### Design rule

Plot modules should depend on selector/data outputs, not on raw DOM state spread throughout the codebase.

### Validation checklist

Verify:

- grouped bar plots still render
- confusion tabs still render and switch correctly
- TP/FP/FN tabs still render and switch correctly
- tooltips still work
- legend behavior still works
- figure download/export still works
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the plotting/export changes comply with `CONTRIBUTING.md`

### Suggested commit boundaries

- `refactor(eval-dashboard): extract shared plot helpers`
- `refactor(eval-dashboard): extract confusion and tpfpfn plot modules`
- `refactor(eval-dashboard): extract export and legend helpers`

______________________________________________________________________

## Phase 11. Reduce `main.js` to orchestration only

### Goal

Make `main.js` the bootstrap layer, not the implementation layer.

### What `main.js` should still do

- import modules
- initialize state
- capture DOM refs
- wire event listeners
- call render/update flows
- coordinate loading pipelines

### What `main.js` should ideally no longer contain

- complex normalization logic
- large rendering functions
- plotting implementations
- generic sorting/flattening helpers
- large parsing logic
- repeated ad hoc DOM lookups

### Why this final cleanup matters

This phase confirms that the modularization is complete rather than partial.

### Validation checklist

- `main.js` is readable as high-level orchestration
- module boundaries follow the stated dependency rules
- no large “temporary dumping ground” functions remain
- dashboard behavior still matches the Phase 0 baseline after the Phase 1 folder move
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the cleanup changes comply with `CONTRIBUTING.md`

### Suggested commit boundary

`refactor(eval-dashboard): reduce main entry to orchestration`

______________________________________________________________________

## Phase 12. Broaden smoke and regression coverage

### Goal

By this point, structural smoke tests already exist. Expand them so the refactor finishes with useful ongoing coverage.

### Test locations

```text
tests/
  fixtures/
    eval_dashboard/
      ...
  unit/
    eval_dashboard/
      test_eval_dashboard_entrypoint.py
      test_eval_dashboard_assets.py
      test_dashboard_fixtures.py
      js/
        ...
  integration/
    eval_dashboard/
      test_eval_dashboard_redirects.py
```

### Coverage to make sure now exists

#### Structural / Python-native smoke coverage

- expected CSS/JS files exist
- `docs/eval-dashboard/index.html` references expected external assets
- old-path redirect/shim coverage is still intentional and documented
- no giant inline `<style>` or `<script>` remains after extraction phases
- curated fixtures remain well-formed
- the repo-level docs check still succeeds

#### JS logic coverage

- utilities
- selectors
- normalization/parsing
- any other pure loader-adjacent helpers that were extracted cleanly

That logic coverage should run through the repository's minimal JS-native dashboard test command, while Python continues to run structural/docs/fixture smoke coverage.

### Why this phase still exists

Testing started earlier, but this phase is where the project confirms the final coverage shape and closes remaining gaps.

### Suggested validation

```bash
cd /home/arbi01/projects/kibad-llm
uv run --group cicd pytest tests/unit/eval_dashboard
uv run --group cicd check-mkdocs --config properdocs.yml
```

Also run the repository's minimal JS-native dashboard logic-test command introduced during Phases 5 to 8 (preferably the Node.js built-in test runner).

Before closing Phase 12, update the planning docs in `docs/eval-dashboard/` with the final coverage status and confirm the testing/documentation updates comply with `CONTRIBUTING.md`.

### Suggested commit boundary

`test(eval-dashboard): broaden smoke and logic coverage`

______________________________________________________________________

## Phase 13. Optional follow-up: browser-level UI testing

### Goal

Decide whether the dashboard now justifies dedicated browser-level interaction testing.

### Only do this later if needed

This should be a follow-up, not part of the first modularization pass.

### Consider adding browser tests if:

- the dashboard becomes a frequently used workflow
- rendering regressions become costly
- manual validation becomes too slow
- interactive behavior is changing often

### Possible scope of future browser tests

- load a sample fixture set
- switch tabs
- select prediction groups
- verify JSON pane updates
- verify plot containers render expected content
- verify figure export button enables/disables appropriately

If this optional phase is taken on, update the planning docs in `docs/eval-dashboard/` after the phase decision or implementation lands, and keep the work compliant with `CONTRIBUTING.md`.

______________________________________________________________________

## Recommended PR / commit breakdown

A sensible sequence from scratch would be:

1. baseline artifact + source-fixture audit
1. move to `docs/eval-dashboard/index.html` + update links/redirects
1. curated fixtures + initial smoke tests
1. CSS extraction + structural asset checks
1. external `main.js`
1. utility extraction + first JS logic tests + permanent minimal JS-native runner
1. state/store extraction
1. selector extraction + selector tests
1. parse/normalize extraction + normalization tests
1. local file loader extraction
1. GitHub loader extraction
1. UI module extraction + DOM refs centralization
1. plot/export extraction
1. `main.js` cleanup
1. final smoke/regression coverage pass

If needed, these can be grouped into fewer PRs:

- PR 1: baseline artifact + folder move + links/redirects + curated fixtures + initial smoke tests
- PR 2: CSS + external `main.js`
- PR 3: utilities + permanent JS-native runner + state + selectors + parsing + normalization + logic tests
- PR 4: loaders + UI modules + plot/export modules + final cleanup + coverage pass

From the current repository state, work should first finish the remaining Phase 5 testing-seam work — permanent minimal JS-native runner plus explicit CI wiring — before resuming at the `state/store extraction` step.

After each completed PR or phase in that sequence, refresh the planning docs under `docs/eval-dashboard/` before moving on so the written plan keeps matching the repository state and `CONTRIBUTING.md` expectations.

______________________________________________________________________

## Definition of done

The refactor is complete when:

- `docs/eval-dashboard/index.html` is the thin long-term entry page
- `properdocs.yml` and in-repo docs links point at the new entry page
- old-path handling for `docs/eval-dashboard.html` is intentional, documented, and removable when safe, whether via a shim or a host-supported redirect
- CSS lives under `docs/eval-dashboard/assets/css/`
- JS is split into state, data, UI, plot, and utility modules
- `ui/dom.js` owns shared DOM lookup helpers and `main.js` captures refs once during bootstrap
- `main.js` is only orchestration/bootstrap
- dashboard runtime code remains under `docs/`
- dashboard tests/fixtures live under `tests/`
- fixtures are curated snapshots derived from representative real experiment data, especially newer post-`2026-01-16` sources
- ProperDocs still serves the dashboard correctly
- the refactored dashboard still matches the checked-in baseline artifact
- smoke tests and extracted-logic tests both exist and pass
- the planning docs under `docs/eval-dashboard/` have been updated after each completed phase
- the full refactor history and resulting state comply with `CONTRIBUTING.md`

______________________________________________________________________

## Immediate next implementation step

Given the current repository state, the safest next implementation step is:

1. if `tests/unit/eval_dashboard/js/` still relies on a temporary pytest-driven Node bridge, replace it with the permanent minimal JS-native logic-test runner first
1. add the JS-native dashboard logic-test command to CI as an explicit check
1. re-validate the already extracted Phase 5 utility coverage under that permanent harness
1. then extract the canonical mutable dashboard state from `docs/eval-dashboard/assets/js/main.js` into `docs/eval-dashboard/assets/js/state/store.js`
1. begin moving derived-read helpers into `docs/eval-dashboard/assets/js/state/selectors.js`
1. add selector/state logic coverage under `tests/unit/eval_dashboard/js/` as those seams become importable
1. keep `main.js` behavior-equivalent while beginning the Phase 6 state/selector split
1. update the planning docs in `docs/eval-dashboard/` after Phase 6 lands and confirm the change set complies with `CONTRIBUTING.md`

That finishes the remaining Phase 5 testing-seam work before continuing with the next smallest behavior-preserving extraction boundary: Python for structural/docs/fixture smoke coverage, and a minimal JS-native runner for extracted dashboard logic.
