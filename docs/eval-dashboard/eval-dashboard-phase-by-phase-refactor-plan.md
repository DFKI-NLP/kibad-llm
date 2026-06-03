# Eval dashboard phase-by-phase refactor plan

## Table of contents

- [Checklist](#checklist)
- [Goal](#goal)
- [Current implementation state](#current-implementation-state)
- [Conventions and design rules](#conventions-and-design-rules)
- [Phase 0. Record a concrete baseline and source-fixture audit](#phase-0-record-a-concrete-baseline-and-source-fixture-audit)
- [Phase 1. Move to a future-proof dashboard folder structure without breaking links](#phase-1-move-to-a-future-proof-dashboard-folder-structure-without-breaking-links)
- [Phase 2. Compile curated fixtures from newer experiment data and add first smoke tests](#phase-2-compile-curated-fixtures-from-newer-experiment-data-and-add-first-smoke-tests)
- [Phase 3. Extract CSS only and tighten structural tests](#phase-3-extract-css-only-and-tighten-structural-tests)
- [Phase 4. Move the inline script into one external module](#phase-4-move-the-inline-script-into-one-external-module)
- [Phase 5. Add lightweight JS logic tests and extract pure utilities](#phase-5-add-lightweight-js-logic-tests-and-extract-pure-utilities)
- [Phase 6. Extract state and selectors, then add selector tests](#phase-6-extract-state-and-selectors-then-add-selector-tests)
- [Phase 7. Extract parsing and normalization, then add normalization tests](#phase-7-extract-parsing-and-normalization-then-add-normalization-tests)
- [Phase 8. Extract source loaders and the shared ingestion pipeline](#phase-8-extract-source-loaders-and-the-shared-ingestion-pipeline)
- [Phase 9. Extract UI infrastructure, centralize DOM refs, and move status plus browser-session helpers out of main.js](#phase-9-extract-ui-infrastructure-centralize-dom-refs-and-move-status-plus-browser-session-helpers-out-of-mainjs)
- [Phase 10. Split the remaining UI extraction into 10A and 10B](#phase-10-split-the-remaining-ui-extraction-into-10a-and-10b)
- [Phase 11. Extract plotting and export modules, then add plot-logic tests](#phase-11-extract-plotting-and-export-modules-then-add-plot-logic-tests)
- [Phase 12. Reduce `main.js` to orchestration only and broaden regression coverage](#phase-12-reduce-mainjs-to-orchestration-only-and-broaden-regression-coverage)
- [Phase 13. Optional follow-up: browser-level UI testing](#phase-13-optional-follow-up-browser-level-ui-testing)
- [Recommended PR / commit breakdown](#recommended-pr-commit-breakdown)
- [Definition of done](#definition-of-done)
- [Immediate next implementation step](#immediate-next-implementation-step)

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
- populated runtime assets now exist under `docs/eval-dashboard/assets/`: CSS lives under `assets/css/`, `assets/js/main.js` remains the external entry module, pure helpers live under `assets/js/utils/`, extracted canonical state/selector modules now live under `assets/js/state/`, `assets/js/data/` contains parsing, normalization, source-loader, and shared-ingestion modules, `assets/js/ui/` now contains the Phase 9 shared DOM/table/status infrastructure, the Phase 10A `controls.js`, `tabs.js`, and `eval-json-pane.js` modules, and the Phase 10B `prediction-table.js` and `evaluation-table.js` renderers, while `assets/js/browser/` now contains extracted browser-session helpers
- structural smoke coverage now includes `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py` and `tests/unit/eval_dashboard/test_eval_dashboard_html_contracts.py`
- browser-free JS utility, store, selector, data-normalization, loader/ingestion, and extracted Phase 9/10A/10B UI-helper coverage now exists under `tests/unit/eval_dashboard/js/` via the Node.js built-in test runner, which remains the long-term home for extracted dashboard logic tests in later phases; the current logic-test layer now covers the main source-adapter/shared-ingestion boundaries plus explicit Phase 9 DOM-ref capture, load-status/progress rendering, shared-table helper, and browser-session edge paths, and now also locks in Phase 10A tab-state resolution, option-control rendering helpers, eval-JSON highlighting/content-selection behavior, and Phase 10B shared header-selection helpers plus prediction/evaluation row-model behavior
- curated Phase 2 and Phase 7 fixtures now exist under `tests/fixtures/eval_dashboard/`, including valid version-0/1/2 examples, invalid edge-case fixtures, the dedicated `missing_prediction_id` fixture, and explicit fixtures for all currently supported plot families (`bars`, `errors`, `confusion_matrix`, `tpfpfn`)
- fixture provenance is documented in `tests/fixtures/eval_dashboard/README.md`
- fixture integrity smoke coverage exists at `tests/unit/eval_dashboard/test_dashboard_fixtures.py`
- docs-build validation relies on the repo-level `check-mkdocs (uv)` hook against `properdocs.yml`, rather than a dashboard-specific subprocess test
- old-path coverage currently relies on the compatibility shim; the ProperDocs redirects plugin is **not** being used for this raw HTML page
- Phase 3 CSS extraction remains complete: `docs/eval-dashboard/index.html` still loads `assets/css/index.css` and contains no inline `<style>` block
- Phase 4 JS externalization is complete: `docs/eval-dashboard/index.html` now loads `assets/js/main.js` as a single external `type="module"` script and contains no inline `<script>` block
- the structural smoke tests now assert the external CSS and external module-script contract rather than a Phase 3 inline-script freeze
- the baseline contract now records the Phase 5 utility-module contract, the Phase 6 state/store + selector-module contract, the Phase 7 parsing/normalization contract, the Phase 8 loader/ingestion contract, the Phase 9 UI/browser-helper contract, the Phase 10A tabs/controls/JSON-pane contract, and the new Phase 10B table-renderer contract instead of freezing the full `main.js` file contents

### Status checkpoint

The repository is currently **through Phase 10B and ready for Phase 11**:

- Phase 0 baseline artifacts landed
- Phase 1 folder migration and compatibility shim landed
- Phase 2 curated fixtures and structural smoke coverage landed
- Phase 3 CSS extraction and HTML contract guardrails landed
- Phase 4 JS externalization landed
- Phase 5 utility extraction, the permanent JS-native logic-test runner, and explicit CI wiring landed
- Phase 6 state/store extraction, selector extraction, and selector/store logic tests landed
- Phase 7 overrides parsing extraction, run normalization extraction, missing-prediction-id fixture coverage, and parsing/normalization logic tests landed
- Phase 8 local-file loading extraction, shared raw-entry ingestion extraction, GitHub loading extraction, and loader/ingestion logic tests landed
- Phase 9 DOM-ref capture extraction, shared table-helper extraction, status/progress rendering extraction, browser-session extraction, and targeted JS logic tests landed
- Phase 10A controls extraction, tabs extraction, eval-JSON-pane extraction, and targeted JS logic tests landed
- Phase 10B prediction/evaluation table extraction, shared select-header/static-control helper extraction, and targeted JS logic tests landed

That means the next implementation step is to **start Phase 11**, not to reopen Phase 10B: keep reusing the now-stable Phase 9 DOM/table/status/browser infrastructure, the landed Phase 10A controls/tabs/JSON-pane modules, and the newly landed Phase 10B `ui/prediction-table.js` plus `ui/evaluation-table.js` modules while moving the remaining plot aggregation, legend, and export code behind dedicated `plots/` modules.

The earlier wording here was directionally correct but still too broad. After looking at the actual post-Phase-9 `main.js`, the remaining work is not just “UI”: it is a mix of large prediction/evaluation renderers, JSON highlighting and selection behavior, plot/export implementations, and many one-line pass-through wrappers around already-extracted helpers. The follow-up phases should separate those concerns explicitly and prefer DOM-free helper/view-model extraction wherever possible.

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
- `data/file-loader.js` and `data/git-loader.js` are source adapters: they may use browser file/network APIs, but they must remain DOM-free and state-free
- `data/ingest-runs.js` is the shared ingestion boundary: it turns raw `{ path, text }` entries into canonical predictions/evaluations plus summary data while reusing `parse-overrides.js` and `normalize.js`
- `ui/` consumes selector outputs and DOM refs, but not raw loader modules
- `plots/` consumes selector/data outputs, not broad global DOM state spread across the codebase
- `main.js` orchestrates imports, DOM refs, browser-only persistence, event wiring, source-loader calls, ingestion calls, state application, and render/update flows
- no module should import back from `main.js`

### Source-loader and ingestion boundary rule

Make the Phase 8 seam explicit:

- source loaders should produce plain data or invoke plain callbacks; they should not capture DOM refs or mutate canonical dashboard state directly
- shared ingestion should own run-directory discovery, `predict/` exclusion, duplicate/conflict detection, and load-summary accounting so those behaviors are implemented once for both local and GitHub sources
- browser-session concerns such as `localStorage` token persistence and `git_url` query-parameter synchronization should stay in `main.js` during Phase 8 unless a separate browser-state helper is introduced deliberately later

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

**Status in current repository:** completed.

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

### Landed Phase 6 outcome

The current branch now matches this phase:

- `docs/eval-dashboard/assets/js/state/` contains `store.js` and `selectors.js`
- `docs/eval-dashboard/assets/js/main.js` now bootstraps the canonical dashboard state via `store.js` and delegates the extracted derived-read helpers to `selectors.js` while keeping runtime behavior equivalent
- `tests/unit/eval_dashboard/js/state.store.test.mjs` covers state initialization, selection synchronization, eval-tab-state normalization, and post-load reset behavior
- `tests/unit/eval_dashboard/js/state.selectors.test.mjs` covers prediction grouping, evaluation-context derivation, plot-group derivation, and mixed-metric error handling under the same Node.js-native harness established in Phase 5
- `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py`, `tests/unit/eval_dashboard/test_eval_dashboard_baseline_contract.py`, and `tests/fixtures/eval_dashboard/baseline/baseline-summary.json` now record the Phase 6 state-module contract

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

**Status in current repository:** completed.

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

Phase 7 should preserve the dashboard's **current** override-parsing semantics exactly:

- treat `.hydra/overrides.yaml` as the current lightweight Hydra-override list format rather than introducing a real YAML object parser
- parse only list items shaped like `- key=value`
- strip the current single leading `+` from parsed keys when present
- keep parsed override values as raw strings
- keep the current permissive behavior where lines that are blank, commented, missing the `-` list-item marker plus its required following space, or missing `=` are ignored rather than raising
- add comprehensive JS-native tests that lock in those current semantics before any later behavioral cleanup

### `normalize.js`

Move:

- `job_return_value` version handlers
- `normalizeImportedJobReturnValue(...)`
- prediction-id extraction logic
- canonical normalization of prediction/evaluation payloads
- normalization helpers specific to imported run data

Phase 7 should preserve the current normalization semantics rather than redesigning the data model.

The important normalized-result contract to freeze is the shape that is common across supported versions:

- `normalizeImportedJobReturnValue(...)` returns an object with top-level `prediction` and `evaluation` keys
- `prediction` contains canonical `jobReturnValue` and `overrides` objects
- `evaluation` contains canonical `jobReturnValue`, `overrides`, and `data` keys

That stable normalized result is produced by version-specific internal handlers:

- version 0 and 1 synthesize `evaluation.jobReturnValue` from the inferred metric type plus version metadata
- version 2 derives `evaluation.jobReturnValue` by copying top-level evaluation metadata except `data` and `prediction`

For Phase 7, keep these two statements distinct:

- **Normalized-result contract:** the current normalization produces the same canonical `evaluation.jobReturnValue` format across the currently supported versions
- **Internal implementation detail:** that result is still produced through different version-specific handlers, and Phase 7 should preserve those existing code paths rather than redesigning them during extraction

### Design rule

This layer should convert raw input into the dashboard’s canonical internal shape.

For Phase 7 specifically:

- `parse-overrides.js` and `normalize.js` should stay dependency-free and must not introduce a frontend build step or a browser-runtime parsing dependency
- prediction-id **extraction** belongs in `normalize.js`
- cross-run conflicting-prediction-id detection should remain with the ingestion/orchestration flow until Phase 8 loader extraction
- preserve the current error taxonomy: keep `UnsupportedJobReturnValueVersionError` and `MissingPredictionIdError` as named errors, while other parse/normalization failures may remain generic invalid-input failures for now
- treat the current v0/v1 metric-type inference from `overrides["experiment/evaluate"]` as an intentional supported contract and cover it in tests

### Tests to add in this phase

Use curated fixtures to add logic tests for:

- `data.parse-overrides.test.mjs`

- `data.normalize.test.mjs`

- supported version handling

- current override-parser semantics, including accepted `- key=value` lines, single-leading-`+` stripping, raw string value preservation, and the current permissive skipping of unhandled lines

- unsupported version rejection

- malformed JSON fixtures failing cleanly

- current permissive handling of non-understood override lines being preserved in tests for now

- missing prediction-id handling

- normalization of a dedicated `missing_prediction_id` fixture

- conflicting prediction-id handling should remain covered at the ingestion-flow boundary rather than being pushed into the single-run normalization module during Phase 7

- normalization of newer post-`2026-01-16` experiment-derived fixtures

Keep these as JS-native logic tests under `tests/unit/eval_dashboard/js/`; Python should continue to own fixture/docs/smoke checks around them.

Add a curated fixture directory under `tests/fixtures/eval_dashboard/missing_prediction_id/` so the missing-prediction-id case is checked in and documented like the other supported edge fixtures.

### Why this phase matters

Data normalization is one of the most valuable areas to test independently.

### Landed Phase 7 outcome

The current branch now matches this phase:

- `docs/eval-dashboard/assets/js/data/` contains `parse-overrides.js` and `normalize.js`
- `docs/eval-dashboard/assets/js/main.js` now imports the extracted parsing and normalization helpers while preserving the existing ingestion flow and keeping cross-run conflicting-prediction-id detection in the orchestration layer
- `tests/unit/eval_dashboard/js/data.parse-overrides.test.mjs` locks in the current permissive override-parser semantics, including accepted `- key=value` lines, single-leading-`+` stripping, raw-string value preservation, and permissive skipping of unhandled lines
- `tests/unit/eval_dashboard/js/data.normalize.test.mjs` covers supported versions, unsupported-version rejection, malformed JSON fixture behavior at the JSON parse boundary, missing-prediction-id handling, metric-type inference for v0/v1 runs, and the Phase 7 boundary that leaves conflicting-prediction-id detection outside single-run normalization
- `tests/fixtures/eval_dashboard/missing_prediction_id/` is now checked in and documented alongside the other curated invalid edge fixtures
- `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py`, `tests/unit/eval_dashboard/test_dashboard_fixtures.py`, `tests/unit/eval_dashboard/test_eval_dashboard_baseline_contract.py`, and `tests/fixtures/eval_dashboard/baseline/baseline-summary.json` now record the Phase 7 data-module contract

### Validation checklist

Verify that:

- supported versions still load
- unsupported versions are still rejected correctly
- malformed JSON fixtures still fail cleanly
- current override-parser permissive behavior is preserved exactly in the Phase 7 extraction
- missing prediction ids are still handled correctly
- conflicting prediction ids are still handled correctly without moving cross-run conflict detection out of the ingestion flow prematurely
- normalization tests pass
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the parsing/normalization changes comply with `CONTRIBUTING.md`

### Post-refactor follow-up TODOs surfaced during Phase 7 planning

Do **not** make these behavior changes during Phase 7 itself, but record them for a later cleanup pass after the modularization refactor:

- `parse-overrides.js` should eventually strip up to two leading `+` characters from keys rather than only one
- override lines that the parser cannot understand should eventually raise a dedicated error instead of being skipped silently, and that error should cause the affected run directory to be skipped cleanly
- investigate a more precise parse/normalization error taxonomy beyond the two currently preserved named errors
- tighten the long-term contract around missing prediction ids; the dashboard currently needs to handle them, but a later cleanup should consider disallowing them entirely
- investigate whether a real YAML parser is worthwhile as an optional browser-runtime dependency in a later post-refactor cleanup, without forcing that decision into Phase 7

### Suggested commit boundaries

- `refactor(eval-dashboard): extract overrides parsing`
- `refactor(eval-dashboard): extract run normalization and add tests`

______________________________________________________________________

## Phase 8. Extract source loaders and the shared ingestion pipeline

**Status in current repository:** completed.

### Goal

Separate source-specific I/O from shared run ingestion, while also keeping normalization and rendering boundaries clean.

### Tasks

Create:

```text
docs/eval-dashboard/assets/js/data/
  ingest-runs.js
  file-loader.js
  git-loader.js
```

### Recommended long-term split

This phase should not stop at “one loader module per source”. The long-term-friendly split is:

- `file-loader.js` = local-file source adapter
- `git-loader.js` = GitHub source adapter
- `ingest-runs.js` = shared ingestion boundary used by both sources

That avoids duplicating run discovery, duplicate/conflict handling, and load-summary semantics across both source paths.

### `ingest-runs.js`

Move logic related to:

- converting raw `{ path, text }` entries into canonical prediction/evaluation additions
- determining candidate run directories
- excluding `predict/` runs
- accounting for missing `job_return_value.json`
- parsing JSON payloads
- parsing overrides via `parse-overrides.js`
- normalization via `normalize.js`
- prediction-id extraction
- duplicate run detection
- conflicting-prediction-id detection
- returning load-summary counts and normalized additions as plain data

### `file-loader.js`

Move logic related to:

- reading selected local files
- file text loading
- determining relevant dashboard files
- collecting entries from file/folder input
- deriving a local source label

Do **not** let `file-loader.js` absorb the shared parsing/normalization/deduplication pipeline. It should remain a source adapter that produces raw entries for `ingest-runs.js`.

### `git-loader.js`

Move logic related to:

- GitHub URL parsing
- resolving repo/ref/folder information
- recursive GitHub folder listing
- fetching GitHub files
- deriving a GitHub source label
- emitting progress/status information via plain callbacks or returned plain objects

Do **not** let `git-loader.js` own query-parameter persistence, token persistence, or direct DOM updates. Those are orchestration/browser-session concerns rather than transport concerns.

### Design rule

- source-loader modules fetch raw content
- the shared ingestion module interprets raw entries and produces canonical additions + summary data
- normalization modules stay focused on single-run semantics
- `main.js` applies the returned ingestion result to canonical dashboard state and triggers resets/renders
- UI modules present it

### Tests to add in this phase

Add explicit JS-native tests for the new boundary rather than only “some loader helpers”. At minimum:

- `data.ingest-runs.test.mjs`
- `data.file-loader.test.mjs`
- `data.git-loader.test.mjs`

Focus them on deterministic logic such as:

- GitHub URL parsing
- local entry filtering/relevance checks
- run-directory discovery
- `predict/` exclusion
- duplicate-run detection helpers
- conflicting-prediction-id handling at the ingestion boundary
- progress-state derivation helpers if they are extractable

Keep these loader-adjacent logic tests in the same JS-native test layer established earlier, and avoid growing a second ad hoc harness for them.

Also update the Python-side structural/baseline contract checks so Phase 8 explicitly records:

- the new `data/` modules exist
- the new `*.test.mjs` files exist
- the baseline artifact now has a Phase 8 contract section rather than leaving loaders as an implicit future TODO

Keep end-to-end loader interaction checks in the smoke/manual validation loop unless they can be made deterministic.

### Validation checklist

Verify:

- local fixture folders still load
- GitHub URL loading still works
- progress/status text still updates
- duplicate-run handling still works
- conflicting-prediction-id handling still works at the shared ingestion boundary
- unsupported-version/malformed-run handling still works
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the loader changes comply with `CONTRIBUTING.md`

### Landed Phase 8 outcome

The current branch now matches this phase:

- `docs/eval-dashboard/assets/js/data/` now contains `file-loader.js`, `ingest-runs.js`, and `git-loader.js` alongside the Phase 7 `parse-overrides.js` and `normalize.js` modules
- `docs/eval-dashboard/assets/js/main.js` now delegates local-file source handling to `file-loader.js`, shared raw-entry ingestion plus duplicate/conflict detection to `ingest-runs.js`, and GitHub tree-URL loading to `git-loader.js` while keeping browser-session concerns such as `localStorage` token persistence and `git_url` query-parameter synchronization in the orchestration layer
- `tests/unit/eval_dashboard/js/data.file-loader.test.mjs` locks in local relevant-path filtering, local source-label derivation, browser-compatible file-reading paths, and raw-entry collection semantics without mocking the browser file picker
- `tests/unit/eval_dashboard/js/data.ingest-runs.test.mjs` covers run-directory discovery, `predict/` exclusion, duplicate-run handling, conflicting-prediction-id handling at the shared ingestion boundary, the shared prediction-signature helper used for conflict detection, and shared summary accounting for representative invalid/unsupported edge cases
- `tests/unit/eval_dashboard/js/data.git-loader.test.mjs` covers GitHub tree-URL parsing, ref resolution, contents-URL construction, recursive relevant-file listing, progress callback semantics, high-level GitHub raw-entry loading with mocked transport responses, and key empty/error paths
- `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py`, `tests/unit/eval_dashboard/test_eval_dashboard_baseline_contract.py`, `tests/unit/eval_dashboard/js/README.md`, and `tests/fixtures/eval_dashboard/baseline/baseline-summary.json` now record the Phase 8 loader/ingestion module and test contract explicitly

### Suggested commit boundaries

- `refactor(eval-dashboard): extract shared run-ingestion pipeline`
- `refactor(eval-dashboard): extract local file loader`
- `refactor(eval-dashboard): extract GitHub loader`

______________________________________________________________________

## Phase 9. Extract UI infrastructure, centralize DOM refs, and move status plus browser-session helpers out of main.js

### Goal

Establish the final DOM and browser-only infrastructure boundaries before extracting the larger renderers.

This phase should remove the lowest-level reusable UI/browser helpers from `main.js` first so later table/pane/plot extraction work has stable foundations instead of repeatedly carving helpers out of a moving target.

### Tasks

Create:

```text
docs/eval-dashboard/assets/js/ui/
  dom.js
  table-shared.js
  status.js
docs/eval-dashboard/assets/js/browser/
  session.js
```

Keep the remaining larger renderer modules for Phase 10:

```text
docs/eval-dashboard/assets/js/ui/
  controls.js
  tabs.js
  prediction-table.js
  evaluation-table.js
  eval-json-pane.js
```

### Suggested responsibilities

#### `dom.js`

- `captureDomRefs(document)`
- generic DOM helper functions
- repeated element creation helpers
- generic element show/hide helpers
- low-level class/visibility helpers

#### `table-shared.js`

- shared sort-button creation helpers
- sort-label / sort-state display helpers used by both prediction and evaluation tables
- shared truncating-cell helpers
- shared sticky-column offset helpers if they are too table-specific for `dom.js`
- other small table/header-control helpers that would otherwise be duplicated across `prediction-table.js` and `evaluation-table.js`

This explicit shared-table layer is worth adding because the current `main.js` already contains a real common table subsystem, not two independent renderers.

#### `status.js`

- load status and summary rendering
- progress-bar visibility/value/label rendering
- download button state rendering
- load-button busy/idle state rendering if that is not kept inline in `main.js`
- any small DOM-only formatter helpers for load/progress UI

#### `browser/session.js`

- GitHub token persistence helpers
- `git_url` query-parameter read/write helpers
- bootstrap-time query-parameter parsing helpers
- small browser-session helpers that can be tested with injected `location`/`history`/storage-like adapters

### Design rule

Infrastructure modules in this phase should mostly:

- receive explicit inputs and DOM refs rather than reaching back into global state implicitly
- expose narrow helpers that later renderer modules can compose
- stay free of source-loading and normalization responsibilities

For the Phase 8 → Phase 9 boundary specifically:

- loader modules should emit plain progress/status data only
- `status.js` should become the DOM-owning renderer for that data
- `main.js` should keep orchestration decisions, but stop formatting and mutating status/progress elements ad hoc once `status.js` lands
- `browser/session.js` should implement localStorage/query-parameter mechanics, while `main.js` keeps the decision of when those mechanics are invoked

Avoid hiding state mutations deep inside many rendering functions unless necessary.

### Tests to add in this phase

Prefer JS-native tests only for the extracted helpers that are truly browser-free or adapter-driven, for example:

- `ui.dom.test.mjs` for centralized DOM-ref capture and panel-visibility helpers using stubbed document/element adapters
- `ui.status.test.mjs` for load-status/progress and download-button rendering helpers using plain DOM-ref stubs
- `ui.table-shared.test.mjs` for sort-cycle helpers, sort-label helpers, or any other shared table logic that stays mostly DOM-free
- `browser.session.test.mjs` for query-parameter normalization and storage read/write helpers using injected adapters

Do **not** force a heavy DOM-emulation harness into this phase just to test `status.js` or `dom.js`. If those helpers stay isolated enough for document/element stubs, lightweight JS-native tests are fine; otherwise structural/manual validation is still acceptable there.

### Landed Phase 9 outcome

The current branch now matches this phase:

- `docs/eval-dashboard/assets/js/ui/` now contains `dom.js`, `table-shared.js`, and `status.js`
- `docs/eval-dashboard/assets/js/browser/` now contains `session.js`
- `docs/eval-dashboard/assets/js/main.js` now captures shared DOM refs once through `ui/dom.js`, delegates shared sort/truncation/sticky helpers to `ui/table-shared.js`, delegates load-status/progress plus download-button rendering to `ui/status.js`, and delegates GitHub-token persistence plus `git_url` query-parameter behavior to `browser/session.js`
- `tests/unit/eval_dashboard/js/ui.dom.test.mjs` locks in the centralized DOM-ref capture contract, including the shared options-tab query lookups and the panel-visibility helper without introducing a heavy DOM harness
- `tests/unit/eval_dashboard/js/ui.status.test.mjs` locks in load-status/progress rendering plus download-button state rendering through plain DOM-ref stubs rather than a browser-emulation layer
- `tests/unit/eval_dashboard/js/ui.table-shared.test.mjs` now locks in the shared sort-direction cycle, append-mode behavior, sort-label formatting, `aria-sort` derivation, reusable sort-button rendering, shared truncating-cell behavior, and sticky-column offset calculation without introducing a DOM-emulation harness
- `tests/unit/eval_dashboard/js/browser.session.test.mjs` now locks in token persistence semantics plus `git_url` query-parameter parsing/update behavior using injected storage/history/location adapters, including custom-storage-key and write-failure edge paths
- `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py`, `tests/unit/eval_dashboard/test_eval_dashboard_baseline_contract.py`, `tests/unit/eval_dashboard/js/README.md`, and `tests/fixtures/eval_dashboard/baseline/baseline-summary.json` now record the Phase 9 UI/browser-helper contract explicitly

### Validation checklist

Verify that:

- `main.js` now captures DOM refs once and passes them down
- load status/progress rendering now flows through `ui/status.js` rather than through scattered inline DOM writes in `main.js`
- GitHub-token persistence and `git_url` query-parameter behavior now flow through `browser/session.js` rather than bespoke helpers embedded in `main.js`
- shared table helpers now have one explicit home rather than being split ad hoc between future renderer modules
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the UI-module changes comply with `CONTRIBUTING.md`

### Suggested commit boundaries

- `refactor(eval-dashboard): extract dom refs and shared ui helpers`
- `refactor(eval-dashboard): extract status/progress renderers`
- `refactor(eval-dashboard): extract browser session helpers`

______________________________________________________________________

## Phase 10. Split the remaining UI extraction into 10A and 10B

### Goal

Avoid one oversized “remaining UI” phase.

The current `main.js` is still too large, but the remaining UI code does **not** form one equally sized or equally testable unit. The safest path is to extract the smaller, more reusable UI seams first and move the two large table renderers only after those seams are stable.

### Tasks

The eventual Phase 10 module set is still:

```text
docs/eval-dashboard/assets/js/ui/
  controls.js
  tabs.js
  prediction-table.js
  evaluation-table.js
  eval-json-pane.js
```

But do **not** move all of that in one step.

### Phase 10A first: controls, tabs, and JSON-pane helpers/renderers

Start with:

```text
docs/eval-dashboard/assets/js/ui/
  controls.js
  tabs.js
  eval-json-pane.js
```

#### `controls.js`

- prediction/evaluation options-panel rendering
- truncate/default-value control rendering
- group-by button state/render helpers
- sort-status label helpers if they stay UI-only
- only move plot-control rendering here if it stays thin and does not drag plot aggregation/rendering logic back into this phase

#### `tabs.js`

- experiment-tab rendering
- prediction/evaluation options-tab rendering
- generic active-tab normalization/resolution helpers
- shared tab-button rendering so tab UI does not stay duplicated across experiments and later plot tabs

#### `eval-json-pane.js`

- JSON side-pane rendering
- JSON tab behavior
- `escapeHtml(...)`
- `highlightJsonContent(...)`
- selected evaluation/group → displayed JSON content resolution

### Landed Phase 10A outcome

The current branch now matches Phase 10A:

- `docs/eval-dashboard/assets/js/ui/` now contains `controls.js`, `tabs.js`, and `eval-json-pane.js` alongside the Phase 9 `dom.js`, `table-shared.js`, and `status.js` helpers
- `docs/eval-dashboard/assets/js/main.js` now delegates experiment-tab rendering plus cached options-tab state to `ui/tabs.js`, prediction/evaluation truncate/default/group-by control rendering to `ui/controls.js` at both the panel-composition level and the per-column header-toggle level, also routes prediction/evaluation sort-status label plus reset-button rendering and the thin plot-control surface (including grouped-bar field chips) through `ui/controls.js`, and delegates eval JSON-pane highlighting/content-selection rendering to `ui/eval-json-pane.js`
- `tests/unit/eval_dashboard/js/ui.tabs.test.mjs` locks in active-tab resolution, plain tab-button view-model derivation, shared tab-button rendering, cached tab-state synchronization, and the custom delegated eval-options-tab selection path that reads `data-eval-tab` instead of the default `data-tab`
- `tests/unit/eval_dashboard/js/ui.controls.test.mjs` locks in column-option derivation, toggle-only group-by selection, default-control view-model derivation, group-by button enable/disable behavior, the thin plot-control rendering state including grouped-bar field chips, and shared checkbox-list rendering semantics
- `tests/unit/eval_dashboard/js/ui.eval-json-pane.test.mjs` locks in HTML escaping, JSON highlighting, selected evaluation/group content resolution, and split-pane tab-state rendering
- `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py`, `tests/unit/eval_dashboard/test_eval_dashboard_baseline_contract.py`, `tests/unit/eval_dashboard/js/README.md`, and `tests/fixtures/eval_dashboard/baseline/baseline-summary.json` now record the Phase 10A UI-module contract explicitly

Phase 10A is still close to behavior-preserving overall, but one small intentional improvement should remain documented explicitly: the shared group-by toggle helper now applies explicit `aria-label` text to the evaluation-table header grouping checkboxes, improving accessibility compared with the old inline evaluation-toggle rendering.

### Phase 10B second: prediction and evaluation table renderers

Only after Phase 10A stabilizes, move:

```text
docs/eval-dashboard/assets/js/ui/
  prediction-table.js
  evaluation-table.js
```

### Suggested responsibilities

#### `prediction-table.js`

- prediction table rendering
- prediction grouping-row/member-row rendering
- prediction-table header/row view-model builders where those can be kept DOM-free
- prediction-table event hookup via callbacks exposed to `main.js`

Based on the current `main.js`, the safest first-pass extraction order inside this module is:

1. move the prediction-table header renderer as one unit, including:
    - the section-header row
    - the control-column header cells for `expand`, `select`, and `group_size`
    - the per-column header row for data columns
1. move the prediction grouped-row renderer, including the expand button, group-selection checkbox, and grouped value cells
1. move the prediction member-row renderer for expanded groups
1. only after those renderers are stable, consider smaller DOM-free helpers for any header-cell or row view-model shaping that emerges naturally

The current duplicated prediction-table sub-seams most worth extracting are:

- the `select` header control that combines a sort button with a select-all checkbox
- the repeated static control-header wrapper used for sortable `expand` / `group_size` cells
- the grouped-row expand-button rendering and state wiring
- the grouped-row selection-checkbox rendering and state wiring
- the grouped-row versus member-row cell population split

#### `evaluation-table.js`

- evaluation table rendering
- evaluation grouping-row/member-row rendering
- evaluation selection behavior when it is truly table-specific
- evaluation-table header/row/selection view-model builders where those can be kept DOM-free

Based on the current `main.js`, the safest first-pass extraction order inside this module is:

1. move the evaluation-table header renderer as one unit, including:
    - the section-header row
    - the control-column header cells for `expand`, `select`, and `group_size`
    - the per-column header row for evaluation columns
    - the extra `eval_run_dir` meta column header
1. move the grouped evaluation-row renderer, including row-click selection, expand-button behavior, and group-selection checkbox behavior
1. move the member evaluation-row renderer, including the selected-run highlighting path
1. only after those renderers are stable, split out any DOM-free row/header/selection view-model helpers that prove worth testing in isolation

The current evaluation-table sub-seams most worth extracting are:

- the `select` header control that combines a sort button with a select-all checkbox
- the repeated static control-header wrapper used for sortable `expand` / `group_size` cells
- the `eval_run_dir` meta-column header handling that currently sits outside the main evaluation-column loop
- the grouped-row click-selection behavior that also resets `selectedEvalRunDir` and `activeEvalJsonTab`
- the grouped-row expand-button and group-selection checkbox rendering
- the member-row rendering path, which is similar to but not identical with the prediction member rows

### Design rule

Phase 10 modules should mostly:

- receive selector-derived inputs plus DOM refs/shared helpers
- expose DOM-free helper/view-model functions whenever that creates a stable test seam
- render DOM and expose callbacks on top of those helpers
- avoid owning source loading, normalization, or browser-session persistence
- avoid re-implementing common sort/truncation/sticky logic already extracted in Phase 9
- avoid turning `ui/controls.js` into a second dumping ground for plot-specific implementation logic
- remove existing one-line pass-through wrappers from `main.js` as call sites move; do **not** create fresh wrappers that only rename imported helpers

If shared selection/header/expand-collapse logic becomes obvious while moving the tables, extend `ui/table-shared.js` rather than duplicating the same logic in `prediction-table.js` and `evaluation-table.js`.

Given the current code, the most likely Phase 10B additions to `ui/table-shared.js` are:

- a shared helper for the `select` header control that pairs a sort button with a select-all checkbox
- a shared helper for the static sortable control-header cells (`expand` and `group_size`)
- possibly a shared expand-button helper if the prediction and evaluation renderers can use one callback-driven contract without hiding selection state inside the helper

Do **not** force the grouped-row selection checkbox or the evaluation row-click-selection behavior into `ui/table-shared.js` unless the resulting abstraction stays genuinely callback-driven and clearer than the duplicated inline logic.

Phase-9-specific reminder for this phase:

- the cached options-tab and eval-options-tab button/panel arrays captured during bootstrap are valid only while Phase 10 keeps those tab nodes structurally stable
- if Phase 10 starts replacing those tab buttons or panels wholesale instead of updating them in place, refresh the cached refs explicitly or move that lookup responsibility into the extracted tabs renderer rather than assuming the old arrays stay live forever

### Landed Phase 10B outcome

The current branch now matches Phase 10B:

- `docs/eval-dashboard/assets/js/ui/` now contains `prediction-table.js` and `evaluation-table.js` alongside the earlier Phase 9 and Phase 10A UI modules
- `docs/eval-dashboard/assets/js/main.js` now delegates the prediction-table header/group/member rendering flow to `ui/prediction-table.js` and the evaluation-table header/group/member plus `eval_run_dir` meta-column rendering flow to `ui/evaluation-table.js`
- `docs/eval-dashboard/assets/js/ui/table-shared.js` now also owns the shared displayed-selection summary helper plus the shared `select` header control and static sortable control-header cells used by both table renderers
- `tests/unit/eval_dashboard/js/ui.prediction-table.test.mjs` now locks in the extracted prediction grouped-row and member-row view-model helpers without introducing a DOM-emulation harness
- `tests/unit/eval_dashboard/js/ui.evaluation-table.test.mjs` now locks in the extracted evaluation grouped-row and member-row view-model helpers without introducing a DOM-emulation harness
- `tests/unit/eval_dashboard/js/ui.table-shared.test.mjs` now also locks in the shared displayed-selection state plus the shared `select` and static control-header rendering helpers introduced during Phase 10B
- `tests/unit/eval_dashboard/test_eval_dashboard_entrypoint.py`, `tests/unit/eval_dashboard/test_eval_dashboard_baseline_contract.py`, `tests/unit/eval_dashboard/js/README.md`, and `tests/fixtures/eval_dashboard/baseline/baseline-summary.json` now record the Phase 10B table-renderer contract explicitly
- `tests/unit/eval_dashboard/test_eval_dashboard_main_orchestration_contract.py` already existed before this Phase 10 branch and is not a pure Phase 10B test file. In this phase it was extended with new assertions that mostly lock in the Phase 10A/10B `main.js` delegation boundaries introduced by the tabs/controls/JSON-pane and table-renderer extractions, while the pre-existing file still also covers earlier already-landed browser-session and local-file orchestration seams. That extra breadth is acceptable, but it should be described as Phase 9/10 guardrail coverage rather than as a newly added or purely Phase 10B test artifact.

Phase 10B also carries one small intentional accessibility improvement that should remain documented explicitly: the shared evaluation `select` header control now applies an explicit `aria-label` to the select-all checkbox, improving accessibility compared with the old inline evaluation select-all rendering.

### Tests to add in this phase

Prefer JS-native tests for renderer-adjacent helpers that stay DOM-free.

For Phase 10A, the best candidates are:

- `ui.tabs.test.mjs` for active-tab resolution and shared tab-button state derivation
- `ui.controls.test.mjs` for control-state/view-model helpers such as truncate/default/group-by summaries and thin plot-control toggles
- `ui.eval-json-pane.test.mjs` for HTML escaping, JSON highlighting, and selected-content resolution

For Phase 10B, add JS-native tests only if the table extraction yields stable DOM-free seams such as:

- `ui.prediction-table.test.mjs`
- `ui.evaluation-table.test.mjs`

focused on header/row/selection view-model builders rather than on a broad DOM-emulation harness.

### Validation checklist

Verify:

- Phase 10A keeps experiment/options tabs working
- Phase 10A keeps default/truncate/group-by controls and thin plot-control toggles working
- Phase 10A keeps the JSON pane synchronized with row selection and JSON-tab switching
- prediction table rendering remains correct
- evaluation table rendering remains correct
- group selection still works
- sort buttons still work
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the UI-renderer changes comply with `CONTRIBUTING.md`

### Suggested commit boundaries

- `refactor(eval-dashboard): extract tabs and options controls`
- `refactor(eval-dashboard): extract eval json pane helpers and renderer`
- `refactor(eval-dashboard): extract prediction and evaluation table renderers`

______________________________________________________________________

## Phase 11. Extract plotting and export modules, then add plot-logic tests

### Goal

Move plotting, SVG generation, legend handling, and export/download logic into dedicated modules, with JS-native tests focused on the pure logic seams.

This phase should be more specific than the previous plan version: extract the DOM-free aggregation/tab-map/normalization helpers first, then layer the SVG/DOM rendering helpers on top.

The thin plot-control UI now lives with the other Phase 10A controls. Phase 11 should focus on the remaining plot aggregation, SVG rendering, legend, and export logic rather than pulling basic control rendering back out of `ui/controls.js`.

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
- DOM-free plot-entry/tab-model helpers where practical

#### `bars.js`

- grouped bar plot logic
- standard metric bar rendering
- generic plot-entry-to-bars aggregation

#### `confusion.js`

- confusion-matrix normalization/expansion helpers
- confusion tab-map creation
- confusion heatmap aggregation and rendering

#### `tpfpfn.js`

- TP/FP/FN normalization helpers
- TP/FP/FN tab-map creation
- combined-matrix aggregation and rendering

#### `legend.js`

- grouped legend-model building
- legend element rendering
- legend item filtering

#### `export.js`

- SVG serialization
- ZIP assembly / CRC helpers if they remain custom
- figure download preparation
- browser download/save helpers
- clipboard-export helpers if TP/FP/FN JSON-copy behavior stays part of the dashboard

### Design rule

Plot modules should depend on selector/data outputs, not on raw DOM state spread throughout the codebase.

For testability, prefer each module to expose:

- DOM-free aggregation/tab-map helpers that run under `node --test`
- thin SVG/DOM renderers that can stay under manual/smoke validation until a later browser-test decision

### Tests to add in this phase

Add explicit JS-native tests for the new pure seams. At minimum, consider:

- `plots.shared.test.mjs`
- `plots.confusion.test.mjs`
- `plots.tpfpfn.test.mjs`
- `plots.export.test.mjs`

Focus them on deterministic logic such as:

- metric-path collection / plot-entry building
- tab-map construction
- confusion and TP/FP/FN aggregation/filtering
- legend-model building
- export helper behavior that can be tested without a browser DOM

### Validation checklist

Verify:

- grouped bar plots still render
- confusion tabs still render and switch correctly
- TP/FP/FN tabs still render and switch correctly
- tooltips still work
- legend behavior still works
- figure download/export still works
- newly added plot-logic tests pass under the permanent Node.js-native harness
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the plotting/export changes comply with `CONTRIBUTING.md`

### Suggested commit boundaries

- `refactor(eval-dashboard): extract shared plot helpers`
- `refactor(eval-dashboard): extract confusion and tpfpfn plot modules`
- `refactor(eval-dashboard): extract export and legend helpers`
- `test(eval-dashboard): add plot logic coverage`

______________________________________________________________________

## Phase 12. Reduce `main.js` to orchestration only and broaden regression coverage

### Goal

Make `main.js` the bootstrap layer, not the implementation layer, and close the remaining test/contract gaps after all major module boundaries exist.

### What `main.js` should still do

- import modules
- initialize state
- capture DOM refs
- wire event listeners
- call render/update flows
- coordinate loading pipelines
- invoke browser/session helpers at bootstrap and on user-triggered events

### What `main.js` should ideally no longer contain

- complex normalization logic
- large rendering functions
- plotting implementations
- export/ZIP/CRC implementations
- generic sorting/flattening helpers
- large parsing logic
- repeated ad hoc DOM lookups
- bespoke localStorage/query-parameter helper implementations
- reusable MutationObserver/download-button-state helper logic
- avoidable one-line pass-through wrappers around selector/store/UI helpers once direct module calls are clearer

### Why this final cleanup matters

This phase confirms that the modularization is complete rather than partial.

### Coverage to make sure now exists

#### Structural / Python-native smoke coverage

- expected CSS/JS files exist, including the new `ui/`, `plots/`, and optional `browser/` modules
- `docs/eval-dashboard/index.html` references expected external assets
- old-path redirect/shim coverage is still intentional and documented
- no giant inline `<style>` or `<script>` remains after extraction phases
- curated fixtures remain well-formed
- the repo-level docs check still succeeds

#### JS logic coverage

- utilities
- selectors
- normalization/parsing
- loader/ingestion helpers
- newly extracted plot aggregation/tab-map/export helpers
- any shared table/session helpers that stay DOM-free enough for stable JS-native tests
- lightweight orchestration-level integration helpers around `main.js` composition boundaries such as session bootstrap, local-file query-param clearing, and status/progress callback routing whenever those seams can be isolated without a heavy DOM harness

### Validation checklist

- `main.js` is readable as high-level orchestration
- module boundaries follow the stated dependency rules
- no large “temporary dumping ground” functions or avoidable pass-through wrapper layers remain
- dashboard behavior still matches the Phase 0 baseline after the Phase 1 folder move
- Python-side smoke/contract checks and JS-native logic tests both cover the final module layout
- update the planning docs in `docs/eval-dashboard/` after the phase lands and confirm the cleanup changes comply with `CONTRIBUTING.md`

### Suggested validation

```bash
cd /home/arbi01/projects/kibad-llm
uv run --group cicd pytest tests/unit/eval_dashboard
uv run --group cicd check-mkdocs --config properdocs.yml
node --test tests/unit/eval_dashboard/js/*.test.mjs
```

### Suggested commit boundaries

- `refactor(eval-dashboard): reduce main entry to orchestration`
- `test(eval-dashboard): broaden smoke and logic coverage`

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
1. shared run-ingestion extraction
1. local file loader extraction
1. GitHub loader extraction
1. UI infrastructure extraction + DOM refs centralization + status/browser-session helper extraction
1. controls/tabs/JSON-pane extraction
1. prediction/evaluation table extraction
1. plot/export extraction + plot logic tests
1. `main.js` cleanup + final smoke/regression coverage pass

If needed, these can be grouped into fewer PRs:

- PR 1: baseline artifact + folder move + links/redirects + curated fixtures + initial smoke tests
- PR 2: CSS + external `main.js`
- PR 3: utilities + permanent JS-native runner + state + selectors + parsing + normalization + logic tests
- PR 4: loaders + UI infrastructure + controls/tabs/JSON-pane extraction
- PR 5: prediction/evaluation table extraction + plot/export modules + final cleanup + coverage pass

From the current repository state, work should next continue with **Phase 11**: move the remaining plot aggregation, legend, and export logic behind dedicated `plots/` modules while reusing the now-stable Phase 9 DOM/table/status/browser infrastructure, the landed Phase 10A controls/tabs/JSON-pane modules, the landed Phase 10B table-renderer modules, and the already-stable Phase 8 source-loader/ingestion boundary.

After each completed PR or phase in that sequence, refresh the planning docs under `docs/eval-dashboard/` before moving on so the written plan keeps matching the repository state and `CONTRIBUTING.md` expectations.

______________________________________________________________________

## Definition of done

The refactor is complete when:

- `docs/eval-dashboard/index.html` is the thin long-term entry page
- `properdocs.yml` and in-repo docs links point at the new entry page
- old-path handling for `docs/eval-dashboard.html` is intentional, documented, and removable when safe, whether via a shim or a host-supported redirect
- CSS lives under `docs/eval-dashboard/assets/css/`
- JS is split into state, data, UI, plot, and utility modules
- browser-session mechanics have an explicit home rather than staying embedded in `main.js`
- source-specific loaders and the shared run-ingestion pipeline are separated cleanly
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

1. extract the DOM-free plot aggregation and tab-map helpers into `docs/eval-dashboard/assets/js/plots/shared.js`, `plots/bars.js`, `plots/confusion.js`, and `plots/tpfpfn.js` before splitting out more UI helpers
1. keep the already-landed thin plot-control surface in `ui/controls.js` and move only plot-family-specific aggregation/SVG/legend/export behavior into the new `plots/` modules
1. add JS-native tests for any newly extracted aggregation, tab-map, legend-model, or export-helper seams that stay stable without a heavy DOM harness
1. keep the Phase 9 shared DOM/table/status/browser helpers plus the landed Phase 10A and Phase 10B table/UI modules as stable dependencies rather than reintroducing plot-specific helpers in `main.js`
1. extend structural/docs smoke coverage as needed and keep Python focused on structural/docs/fixture contracts while the permanent Node.js-native runner continues to cover extracted dashboard logic
1. update the planning docs in `docs/eval-dashboard/` after Phase 11 lands, and confirm the change set complies with `CONTRIBUTING.md`

That continues the next smallest behavior-preserving extraction boundary after Phase 10B: keep Python for structural/docs/fixture smoke coverage, keep the minimal JS-native runner for extracted dashboard logic, and next move the remaining plot/export implementation out of `main.js` as coarse module units before the final orchestration-only cleanup pass.
