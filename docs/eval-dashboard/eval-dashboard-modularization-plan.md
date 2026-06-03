# Eval dashboard modularization plan

## Table of contents

- [Checklist](#checklist)
- [Process guardrails](#process-guardrails)
- [1. Keep the dashboard as a docs asset, not package code](#1-keep-the-dashboard-as-a-docs-asset-not-package-code)
- [2. Recommended top-level structure](#2-recommended-top-level-structure)
- [3. Migration strategy for the dashboard entry page](#3-migration-strategy-for-the-dashboard-entry-page)
- [4. Where tests should live](#4-where-tests-should-live)
- [5. Testing strategy: testability-first, without a full frontend build pipeline](#5-testing-strategy-testability-first-without-a-full-frontend-build-pipeline)
- [6. Baseline artifact and fixture curation](#6-baseline-artifact-and-fixture-curation)
- [7. What HTML files should exist?](#7-what-html-files-should-exist)
- [8. What CSS files should exist?](#8-what-css-files-should-exist)
- [9. What JS files should exist?](#9-what-js-files-should-exist)
- [10. Concrete test layout recommendation](#10-concrete-test-layout-recommendation)
- [11. What to avoid](#11-what-to-avoid)
- [12. Practical recommendation for this repository](#12-practical-recommendation-for-this-repository)
- [13. Suggested next step sequence](#13-suggested-next-step-sequence)
- [14. Post-refactor cleanup TODOs](#14-post-refactor-cleanup-todos)

## Checklist

- [x] Ground the recommendation in the current repository layout
- [x] Propose a practical dashboard file structure
- [x] Recommend where dashboard tests should live
- [x] Clarify which HTML/CSS/JS files are worth having
- [x] Call out tradeoffs before any refactor
- [x] Front-load a testability-first strategy
- [x] Make the entry-page migration and link/redirect work explicit
- [x] Add a concrete baseline artifact and fixture-curation recommendation
- [x] Require post-phase planning-doc updates and compliance with `CONTRIBUTING.md`

A few repo-specific observations first:

- the canonical runtime page now lives at `docs/eval-dashboard/index.html`.
- `docs/eval-dashboard.html` is currently a temporary compatibility shim for the old path.
- `docs/eval-dashboard/index.html` is still a **single huge static page**, but Phases 3 to 10B have now moved styling, first low-coupling helpers, canonical state/selector logic, parsing/normalization helpers, source loaders, the shared ingestion pipeline, shared DOM/status/table helpers, browser-session helpers, the smaller controls/tabs/eval-JSON-pane seams, and the prediction/evaluation table renderers into external assets; the page loads `assets/css/index.css`, `assets/js/main.js`, the utility modules under `assets/js/utils/`, the state modules under `assets/js/state/`, the data modules under `assets/js/data/`, the shared plus Phase 10A/10B UI modules under `assets/js/ui/`, and the browser-session helpers under `assets/js/browser/` while the larger plot/export implementations still remain inside a very large `main.js`; the Phase 10A controls extraction still covers higher-level options-panel composition, per-column group-by header toggles, and sort-status label/reset-button rendering instead of leaving those control seams duplicated inline in `main.js`, and Phase 10B now also routes both large table renderers through dedicated UI modules.
- `properdocs.yml` and `docs/index.md` already point to the new folder-based entrypoint.
- `scripts/build_docs.py` only generates **Python API reference** pages from `src/`, so it is **not** a frontend asset pipeline.
- `docs/eval-dashboard/assets/css/` now contains `index.css`, `tokens.css`, `layout.css`, `controls.css`, `tables.css`, and `plots.css`; `docs/eval-dashboard/assets/js/` now contains `main.js`, `utils/`, `state/`, the data modules (`parse-overrides.js`, `normalize.js`, `file-loader.js`, `ingest-runs.js`, and `git-loader.js`), the Phase 9 `ui/` infrastructure modules (`dom.js`, `table-shared.js`, and `status.js`), the Phase 10A `controls.js`, `tabs.js`, and `eval-json-pane.js` modules, the Phase 10B `prediction-table.js` and `evaluation-table.js` modules, and the Phase 9 `browser/session.js` helper already split out of the original monolith.
- `pyproject.toml` has **pytest**, and the repo now has dashboard smoke coverage under `tests/unit/eval_dashboard/`, including entrypoint checks plus HTML-contract checks that enforce external CSS, the external `assets/js/main.js` module reference, and the absence of inline runtime CSS/JS; `tests/unit/eval_dashboard/js/` is now the reserved location for extracted dashboard logic tests, and the long-term harness there is the minimal Node.js built-in test runner (`node --test tests/unit/eval_dashboard/js/*.test.mjs`) covering utilities, Phase 6 state/store + selector modules, the Phase 7 parsing/normalization modules, the Phase 8 loader/ingestion modules, the Phase 9 DOM/status/shared-table/browser-session helpers, the Phase 10A controls/tabs/eval-JSON-pane helpers, and the new Phase 10B prediction/evaluation table row-model plus shared-header helpers, including the thin plot-control UI boundary, the custom delegated eval-options-tab path that reads `data-eval-tab`, and representative edge-path coverage.
- because the remaining renderer code is still large, the old combined Phase 10 has now been split successfully: Phase 10A extracted the smaller controls/tabs/JSON-pane seams plus the thin plot-control surface, and Phase 10B moved the two large table renderers behind dedicated modules with DOM-free row-model coverage first, so the next follow-up step is the Phase 11 plot/export extraction.
- two small non-perfectly-behavior-preserving accessibility improvements should stay documented explicitly: the Phase 10A shared group-by toggle helper now gives the evaluation-table header grouping checkboxes explicit `aria-label` text, and the Phase 10B shared evaluation select-header control now also gives the select-all checkbox an explicit `aria-label`, improving accessibility compared with the old inline evaluation-toggle/select-all rendering.
- `data/prediction_results/readme.md` documents real experiment folders under `data/prediction_results/logs/`; those runs are useful fixture sources, but tests should use curated snapshots rather than reach into mutable live data folders.
- curated dashboard fixtures now exist under `tests/fixtures/eval_dashboard/`, including valid version coverage, invalid edge-case fixtures, the dedicated `missing_prediction_id` fixture, and explicit examples for all current plot families (`bars`, `errors`, `confusion_matrix`, `tpfpfn`).

Given that, the recommendation is to keep the dashboard as a docs asset, but organize it as a small self-contained docs section that is testable and easy to evolve.

In other words, the repository is now effectively **through Phase 10B and ready for Phase 11**: entrypoint migration, compatibility coverage, curated fixtures, baseline artifacts, structural smoke tests, CSS extraction, the external-`main.js` step, the utility extractions, the permanent JS-native logic-test runner, explicit CI wiring, the state/store + selector extractions, the parsing/normalization extraction plus missing-prediction-id coverage, the source-loader/shared-ingestion extraction, the shared DOM/table/status/browser-session extraction, the smaller controls/tabs/eval-JSON-pane plus thin plot-control extraction, and the larger prediction/evaluation table extraction have all landed.

All work performed from this plan should comply with `CONTRIBUTING.md`, and after each completed refactor phase the planning docs under `docs/eval-dashboard/` should be updated so the recorded status, sequencing, and next steps stay accurate.

______________________________________________________________________

## Process guardrails

- Treat `CONTRIBUTING.md` as a standing requirement for every eval-dashboard refactor change, including expectations around documentation, testing, and review readiness.
- After each completed phase, update both `docs/eval-dashboard/eval-dashboard-modularization-plan.md` and `docs/eval-dashboard/eval-dashboard-phase-by-phase-refactor-plan.md` before starting the next phase.
- Those updates should record the current implementation state, what phase is next, and any scope or validation adjustments discovered during the completed phase.

______________________________________________________________________

## 1. Keep the dashboard as a docs asset, not package code

Since the dashboard is currently a docs page and not part of the Python library API, its runtime files should stay under `docs/`, not under `src/kibad_llm/`.

### Why

- It is served as documentation/static site content.
- `src/` should stay focused on importable Python package code.
- Putting dashboard JS/CSS into `src/` would blur the boundary between package code and docs/site code.

______________________________________________________________________

## 2. Recommended top-level structure

A good target structure would be:

```text
docs/
  eval-dashboard/
    index.html                     # thin entry page for the dashboard section
    assets/
      css/
        index.css
        tokens.css
        layout.css
        controls.css
        tables.css
        plots.css
      js/
        main.js
        state/
          store.js
          selectors.js
        data/
          normalize.js
          ingest-runs.js
          file-loader.js
          git-loader.js
          parse-overrides.js
        browser/
          session.js
        ui/
          dom.js
          table-shared.js
          controls.js
          prediction-table.js
          evaluation-table.js
          eval-json-pane.js
          tabs.js
          status.js
        plots/
          shared.js
          bars.js
          confusion.js
          tpfpfn.js
          legend.js
          export.js
        utils/
          flatten.js
          sort.js
          values.js
          text.js
```

This gives:

- a **thin HTML shell**
- a dedicated folder/namespace for the dashboard from the beginning
- external CSS
- external JS in modules
- clear separation between:
    - state/selectors
    - data import/normalization
    - UI rendering
    - plotting/export
    - generic utilities

______________________________________________________________________

## 3. Migration strategy for the dashboard entry page

The move from `docs/eval-dashboard.html` to `docs/eval-dashboard/index.html` should be treated as a **small migration**, not just a rename.

### Required updates

At minimum, update:

- `properdocs.yml` navigation
- `docs/index.md` links
- any other in-repo references to `eval-dashboard.html`

### Redirect/compatibility strategy

To reduce the risk of broken bookmarks and stale links, prefer the safest option that the docs host actually supports.

For this repository, the most reliable baseline is usually:

1. keep a temporary compatibility shim at `docs/eval-dashboard.html`
1. only add a redirect entry in `properdocs.yml` if the docs host cleanly supports redirects for this raw HTML path

### Important nuance

A mixed structure like this should **not** be the long-term runtime layout:

```text
docs/
  eval-dashboard.html
  eval-dashboard/
    ...
```

But a short-lived compatibility shim is still worthwhile during the migration window if it lowers breakage risk.

______________________________________________________________________

## 4. Where tests should live

### Short answer

**Not in `docs/`.** They should live under `tests/`, following the repo’s existing pattern.

### Best fit for this repo

Use Python-friendly test directory names even though the runtime docs path keeps the hyphenated page name:

```text
tests/
  fixtures/
    eval_dashboard/
      ...
  unit/
    eval_dashboard/
      ...
  integration/
    eval_dashboard/
      ...
```

### Why use `eval_dashboard` in tests?

- It matches the repo’s broader Python-oriented naming conventions better than `eval-dashboard`.
- It avoids awkward path naming if future helper code, scripts, or imports reference these locations.
- It keeps a clean separation between:
    - docs URL/file naming (`eval-dashboard`)
    - test directory naming (`eval_dashboard`)

### Why not put tests next to the docs files?

Because anything under `docs/` is conceptually publishable site content. Keeping tests there:

- mixes source and test concerns
- risks accidental publication/copying
- makes docs harder to navigate

______________________________________________________________________

## 5. Testing strategy: testability-first, without a full frontend build pipeline

This is the key architectural decision.

### Recommended approach

Take a **testability-first pass**:

- add smoke/build/link checks early
- curate representative dashboard fixtures early
- extract pure JS modules early enough that logic tests can begin during modularization
- still avoid a full frontend bundling/transpilation pipeline in the first pass
- after each completed phase, refresh the planning docs in `docs/eval-dashboard/` so the test strategy notes remain current

Just as important: **do not try to build a full-fledged dashboard test suite against the current monolithic page before extraction starts**.

At the current repository state, that would likely create brittle tests tied to unstable DOM/layout details, require premature browser/tooling decisions, and duplicate work once the dashboard is split into CSS/JS modules.

### What “testability-first” means here

#### Early Python-native smoke checks

These should arrive near the beginning of the refactor and cover things like:

- the repo-level docs check still succeeds
- the dashboard entry point is referenced correctly
- redirects/compatibility links exist
- expected asset references are present
- fixture folders contain required files
- valid curated JSON/YAML fixtures parse successfully
- intentionally invalid fixtures fail in the intended way
- key durable HTML anchors/controls exist in `docs/eval-dashboard/index.html`
- baseline feature expectations are backed by curated fixtures or structural page contracts
- fixture provenance remains documented in a checked-in README

#### Lightweight JS logic tests once pure modules exist

As soon as utility, selector, or normalization logic is extracted into pure ES modules, add logic-level tests for those modules.

The important point is architectural, not tool-specific:

- test **pure extracted logic** early
- do **not** wait until the entire modularization is finished
- keep the first test harness lightweight and browser-free if possible
- make that harness the long-term home for dashboard JS logic tests, not a temporary dead end
- defer browser-level UI automation until a later follow-up if it becomes necessary

For this repository, the recommended default is:

- keep **Python/pytest** for docs/build/fixture/HTML-contract smoke tests
- run extracted dashboard logic tests with a **minimal JS-native runner**
- prefer the **Node.js built-in test runner** over a larger frontend stack in the first pass
- do **not** grow a pytest-driven Node subprocess bridge into the permanent JS test architecture

### Recommended test split

#### Smoke / structural tests

`tests/unit/eval_dashboard/` plus the repo-level docs hook

Examples:

- entry-page references and redirects
- no inline `<style>` after Phase 3, and no inline runtime `<script>` after Phase 4
- fixture integrity checks

#### Logic tests for extracted JS modules

`tests/unit/eval_dashboard/js/`

Treat this directory as the long-term location for JS-native logic tests, even though the surrounding repository remains Python-first.

Examples:

- normalization of imported job return values
- grouping/selectors
- sorting helpers
- filename sanitization/export naming
- parsing of overrides
- pure DOM-independent helpers

#### Browser-level tests later only if needed

Those are valuable if the dashboard becomes important enough that interaction regressions are costly, but they should be a follow-up decision, not a prerequisite for the first modularization pass.

In other words, pre-refactor tests should primarily protect **stable contracts**; deeper behavior tests should follow the creation of stable module boundaries.

______________________________________________________________________

## 6. Baseline artifact and fixture curation

“Behavior-preserving” should not rely on memory alone. Create a small checked-in baseline artifact and derive fixtures from curated real experiment data.

### Recommended baseline artifact

Use a dedicated baseline area under:

```text
tests/
  fixtures/
    eval_dashboard/
      baseline/
        baseline-manifest.md
        baseline-summary.json
        optional-screenshots/
```

### What the baseline artifact should record

At minimum:

- representative source fixture/run names
- which dashboard features each source is expected to exercise
- expected visible tabs/panels/plot families
- whether export should be enabled
- known caveats or intentionally unsupported cases

A simple `baseline-summary.json` can hold machine-checkable expectations, while `baseline-manifest.md` explains the rationale in prose.

### Fixture sourcing rule

Prefer curated snapshots derived from experiment folders documented in `data/prediction_results/readme.md` with dates **later than `2026-01-16`**.

Good representative source candidates include runs such as:

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

### Important constraint

Do **not** point tests directly at `data/prediction_results/logs/` at runtime.

Instead:

- copy a minimal subset into `tests/fixtures/eval_dashboard/`
- document where each curated fixture came from
- keep the fixture set intentionally small, stable, and reviewable

That gives the refactor coverage against newer data shapes without coupling tests to mutable repo data.

### Pre-refactor fixture/testing nuance

Before modular extraction, treat these curated fixtures mainly as:

- a stable regression corpus for later normalization/selector tests
- a source of lightweight smoke assertions for currently supported plot families
- a way to ensure baseline feature claims stay grounded in checked-in data

They should not tempt the project into premature end-to-end browser coverage of the current monolith.

______________________________________________________________________

## 7. What HTML files should exist?

For runtime, there should be **exactly one long-term HTML entry file**, and it should live inside a dedicated dashboard folder.

### Recommended long-term runtime entry

- `docs/eval-dashboard/index.html`

Make it the public/stable entry point now. Keep it small over time; in the current Phase 4 state it already loads external CSS and the external `assets/js/main.js` entry module.

### Why only one long-term runtime HTML file?

Because with static docs hosting, multiple HTML partials/templates often create more complexity than value:

- more relative-path issues
- more fetch/load logic
- harder testing
- harder docs-tool integration

So it is better **not** to start with:

- many HTML partial files
- templating fragments
- client-side HTML includes

Instead:

- keep HTML as a stable shell
- build repeated UI pieces in JS
- optionally use `<template>` tags later if repeated markup becomes annoying

### Migration exception

A temporary compatibility shim at `docs/eval-dashboard.html` is acceptable during the transition, but it should be removed once redirects and links are stable.

______________________________________________________________________

## 8. What CSS files should exist?

Do not over-split CSS. A small number of concern-based files is enough.

### Good starting set

This starting set now exists in the repository and is a good long-lived baseline for further cleanup:

```text
docs/eval-dashboard/assets/css/
  index.css       # imports the others or serves as main bundle
  tokens.css      # colors, spacing, typography, CSS variables
  layout.css      # page layout, panels, grids
  controls.css    # forms, tabs, buttons, chips
  tables.css      # tables, sticky headers, selected rows, JSON pane layout
  plots.css       # plot cards, legends, tooltip, export visuals
```

### Why this split?

The extracted CSS naturally falls into a few groups:

- theme tokens
- layout wrappers
- controls/tabs
- data tables / JSON panes
- plotting/export styles

That is enough modularity without making CSS maintenance painful.

______________________________________________________________________

## 9. What JS files should exist?

This is where the biggest win will be.

The current script appears to contain at least these concerns:

1. global state
1. data import and normalization
1. selectors/grouping logic
1. prediction table rendering
1. evaluation table rendering
1. eval JSON pane rendering
1. plot generation
1. figure export
1. low-level utilities

So the JS should be split by responsibility, not by arbitrary size.

### Suggested JS layout

```text
docs/eval-dashboard/assets/js/
  main.js
  state/
    store.js
    selectors.js
  data/
    normalize.js
    ingest-runs.js
    file-loader.js
    git-loader.js
    parse-overrides.js
  browser/
    session.js
  ui/
    dom.js
    table-shared.js
    controls.js
    tabs.js
    status.js
    prediction-table.js
    evaluation-table.js
    eval-json-pane.js
  plots/
    shared.js
    bars.js
    confusion.js
    tpfpfn.js
    legend.js
    export.js
  utils/
    flatten.js
    sort.js
    values.js
    text.js
```

### What goes where

#### `main.js`

- bootstrapping
- wiring event listeners
- initializing persisted settings
- calling top-level render/update functions
- coordinating loader → normalize → state → render flows

#### `state/store.js`

- canonical mutable state object
- small state reset helpers
- small state mutation helpers that do not render directly

#### `state/selectors.js`

- derived reads from state
- group builders
- current columns
- selected evaluations/predictions
- experiment grouping
- plot grouping/selectors

This is likely one of the biggest extraction targets.

#### `data/normalize.js`

- `normalizeImportedJobReturnValue(...)`
- version handlers
- prediction id extraction
- canonical imported data shape

For the Phase 7 extraction, preserve the current normalization behavior exactly.

The stable normalized-result contract to freeze is the shared outer normalized shape:

- top-level `prediction` and `evaluation`
- `prediction.jobReturnValue` and `prediction.overrides`
- `evaluation.jobReturnValue`, `evaluation.overrides`, and `evaluation.data`

That stable normalized result is still produced by intentionally different internal version handlers:

- v0/v1 synthesize `evaluation.jobReturnValue` from inferred metric-type/version metadata
- v2 derives `evaluation.jobReturnValue` by copying top-level evaluation metadata except `data` and `prediction`

For Phase 7, keep these two statements distinct:

- **Normalized-result contract:** the current normalization produces the same canonical `evaluation.jobReturnValue` format across the currently supported versions
- **Internal implementation detail:** that result is still produced through different version-specific handlers, and the refactor should preserve those existing code paths rather than redesigning them during extraction

#### `data/ingest-runs.js`

- shared ingestion from raw `{ path, text }` entries into canonical dashboard runs
- run-directory discovery
- `predict/` exclusion
- missing-`job_return_value.json` accounting
- JSON parsing
- overrides parsing through `parse-overrides.js`
- normalization through `normalize.js`
- prediction-id extraction
- duplicate run detection
- conflicting prediction-id detection
- load-summary counts and other ingestion results returned as plain data

This shared ingestion boundary is worth naming explicitly rather than forcing identical logic into both source-specific loader modules. Both local-file loading and GitHub loading should feed the same ingestion pipeline.

#### `data/file-loader.js`

- browser file/folder input handling
- filtering browser `File` objects down to relevant dashboard files
- reading file text
- converting selected local files into raw `{ path, text }` entries plus a source label

This module should stay **source-adapter-only**. It should not mutate dashboard state, parse JSON, normalize runs, or write to DOM elements directly.

#### `data/git-loader.js`

- GitHub URL parsing
- GitHub content listing/fetching
- converting GitHub content into raw `{ path, text }` entries plus a source label
- emitting progress/status data via callbacks or returned plain objects rather than mutating DOM directly

This module should stay **source-adapter-only** as well. It may use `fetch` and browser/network APIs, but it should not mutate dashboard state or own status/progress DOM updates.

Keep browser-session concerns such as query-parameter synchronization and `localStorage` token persistence out of `git-loader.js` during Phase 8. Those behaviors belong with top-level orchestration unless and until a later browser-state helper is introduced deliberately.

#### `data/parse-overrides.js`

- overrides parsing logic

For Phase 7, treat this as the current lightweight Hydra-override parser, not a full YAML-object parser:

- accept the existing `- key=value` list-item format
- strip the current single leading `+` from keys when present
- keep values as raw strings
- keep current permissive skipping semantics for non-understood lines during the modularization pass
- add explicit JS-native tests that lock in those semantics before any later cleanup

Do not add a new parser dependency or a frontend build step just for this extraction.

#### `browser/session.js`

- GitHub token persistence helpers
- `git_url` query-parameter read/write helpers
- small browser-session normalization helpers that can be tested with injected `location`/`history`/storage-like adapters

This module should exist so the final cleanup phase can really leave `main.js` as orchestration-only. The important boundary is:

- `main.js` decides **when** to persist/sync browser session state
- `browser/session.js` implements **how** that persistence/synchronization works
- neither loader modules nor UI modules should absorb those concerns

#### `ui/dom.js`

- shared DOM helpers
- one central `captureDomRefs(...)` or `getDomRefs(...)` function
- shared element creation/toggling helpers
- sticky-column offset helpers

#### `ui/table-shared.js`

- shared sort-button creation and sort-label helpers used by both prediction and evaluation tables
- shared truncating-cell helpers
- shared sticky-column-offset helpers if they become too table-specific for `ui/dom.js`

This is worth naming explicitly because the current remaining UI code has a real shared table layer. Without a dedicated home for it, Phase 9 risks duplicating the same extraction work across `prediction-table.js` and `evaluation-table.js`.

#### `ui/*.js`

- DOM rendering for controls/tables/panes/tabs/status
- the already-landed thin plot-control UI belongs with `ui/controls.js`, while heavier plot-specific aggregation, SVG, legend, and export behavior belongs in `plots/`
- ideally as stateless render functions fed from selectors and DOM refs

#### `plots/*.js`

- plot-specific aggregation + SVG creation
- legend behavior
- confusion-specific paths
- tp/fp/fn-specific paths
- export/download helpers

For the post-Phase-8 work, prefer a split where each plot area exposes:

- DOM-free aggregation / tab-map / normalization helpers that are easy to lock in with the Node.js test runner
- thin SVG/DOM rendering functions layered on top of those pure helpers
- keep basic control rendering that is not plot-family-specific in `ui/controls.js` rather than moving it back into `plots/`

#### `utils/*.js`

- pure generic helpers only

### Module dependency rules

Make the intended dependency direction explicit:

- `utils/` imports nothing dashboard-specific
- `state/` depends only on plain data shapes and `utils/`
- `data/` depends on `utils/` and canonical state/data shapes, not on UI modules
- `browser/` depends only on standard browser APIs plus plain inputs/outputs; it should not mutate canonical dashboard state by itself
- `data/file-loader.js` and `data/git-loader.js` are source adapters: they may touch browser file/network APIs, but they should remain DOM-free and state-free
- `data/ingest-runs.js` is the shared ingestion boundary: it turns raw entries into canonical predictions/evaluations plus summary data, while reusing `parse-overrides.js` and `normalize.js`
- `ui/` consumes selector outputs and DOM refs, but not raw loaders
- `plots/` consumes selector/data outputs, not broad global DOM state spread across the codebase
- `main.js` is the top-level orchestrator: it wires events, invokes browser/session helpers, invokes source loaders + ingestion, applies returned data to canonical state, and triggers render/update flows
- no module should import back from `main.js`

For Phase 7 specifically, also preserve the current error contract during extraction:

- keep `UnsupportedJobReturnValueVersionError` and `MissingPredictionIdError` as the named normalization errors relied on by the runtime load-summary flow
- other parse/normalization failures may remain generic invalid-input errors for now
- treat v0/v1 metric-type inference from `overrides["experiment/evaluate"]` as an intentional supported contract

For Phase 8 specifically, also make these boundaries explicit:

- loader modules should communicate load progress/status via callbacks or returned plain progress events, not by capturing DOM refs themselves
- the shared ingestion layer may return summary counts and normalized run additions, but `main.js` should remain responsible for mutating canonical dashboard state and triggering UI resets/renders
- GitHub token persistence and `git_url` query-parameter behavior should stay in `main.js` during Phase 8 so browser-session behavior does not get buried inside a transport-specific loader

### DOM reference ownership

The best boundary for shared element lookup is:

- `ui/dom.js` owns the lookup helper itself
- `main.js` calls it once during bootstrap
- `main.js` owns the returned refs object and passes it to render/update functions as needed

That keeps selectors/data modules DOM-free while preventing repeated ad hoc global lookups all over the UI layer.

______________________________________________________________________

## 10. Concrete test layout recommendation

A practical target structure would be:

```text
tests/
  fixtures/
    eval_dashboard/
      baseline/
        baseline-manifest.md
        baseline-summary.json
      run_v0/
        .hydra/overrides.yaml
        job_return_value.json
      run_v1/
        .hydra/overrides.yaml
        job_return_value.json
      run_v2/
        .hydra/overrides.yaml
        job_return_value.json
      confusion_matrix/
        ...
      tpfpfn/
        ...
      malformed/
        ...
      missing_prediction_id/
        ...
      unsupported_version/
        ...
      conflicting_prediction_ids/
        ...
  unit/
    eval_dashboard/
      test_eval_dashboard_entrypoint.py
      test_eval_dashboard_assets.py
      test_dashboard_fixtures.py
      js/
        utils.flatten.test.mjs
        utils.sort.test.mjs
        utils.text.test.mjs
        utils.values.test.mjs
        state.selectors.test.mjs
        ui.controls.test.mjs
        ui.dom.test.mjs
        ui.eval-json-pane.test.mjs
        ui.evaluation-table.test.mjs
        ui.prediction-table.test.mjs
        ui.status.test.mjs
        ui.table-shared.test.mjs
        ui.tabs.test.mjs
        browser.session.test.mjs
        data.normalize.test.mjs
        data.parse-overrides.test.mjs
        data.ingest-runs.test.mjs
        data.file-loader.test.mjs
        data.git-loader.test.mjs
        plots.shared.test.mjs
        plots.confusion.test.mjs
        plots.tpfpfn.test.mjs
        plots.export.test.mjs
  integration/
    eval_dashboard/
      test_eval_dashboard_redirects.py
```

The repository has now standardized on flat `*.test.mjs` files under `tests/unit/eval_dashboard/js/`, so `node --test tests/unit/eval_dashboard/js/*.test.mjs` remains stable without recursive globbing or another harness migration.

For the Phase 7 data-module tests, prefer to lock in the current semantics before cleanup. In particular:

- test the current permissive override-parser behavior explicitly, even where a later cleanup may want stricter failures
- cover missing prediction ids with a dedicated curated fixture rather than only inline synthetic test data
- keep conflicting-prediction-id behavior asserted at the ingestion-flow boundary until loader extraction lands

For Phase 8, extend that same pattern rather than inventing a second loader-test strategy:

- `data.ingest-runs.test.mjs` should lock in run-directory discovery, `predict/` exclusion, missing-job accounting, duplicate-run detection, conflicting-prediction-id handling, and the shared summary accounting for representative invalid/unsupported edge cases on curated/synthetic entry sets
- `data.file-loader.test.mjs` should focus on DOM-free local-file helper logic such as relevant-path filtering, relative-path/source-label derivation, and the main browser-compatibility read paths, rather than trying to mock the full browser file picker
- `data.git-loader.test.mjs` should focus on GitHub tree-URL parsing, ref/path resolution helpers, contents-URL construction, recursive relevant-file listing, and high-level source-loading paths with mocked transport responses; full browser UI orchestration can still stay in manual/smoke validation unless isolated cleanly

For Phase 9 and beyond, keep following the same rule:

- prefer JS-native tests for DOM-free shared helpers that emerge from UI/plot extraction
- do **not** force a broad DOM-emulation harness just to claim UI coverage early
- add `ui.dom.test.mjs`, `ui.status.test.mjs`, `ui.table-shared.test.mjs`, and `browser.session.test.mjs` when those helpers expose stable behavior that can be exercised with simple document/element/storage/history stubs rather than a heavy DOM harness
- for the next UI steps, add `ui.tabs.test.mjs`, `ui.controls.test.mjs`, `ui.eval-json-pane.test.mjs`, `ui.prediction-table.test.mjs`, and `ui.evaluation-table.test.mjs` only when the extraction yields stable DOM-free helpers such as active-tab resolution, JSON highlighting/content selection, selection summaries, or header/row view-model builders
- for `ui.controls.test.mjs`, include control-state seams such as column-option derivation, missing-default models, group-by toggles, and other thin control toggles that stay UI-only without pulling plot implementation logic into the control module
- add plot-module tests first at the aggregation/tab-map/export-helper layer, even if full SVG rendering still relies on manual/smoke validation initially
- add lightweight orchestration-level integration helpers around `main.js` composition seams such as session bootstrap, local-file query-param clearing, and status/progress callback routing whenever those paths can be isolated cleanly without introducing a broad DOM harness

______________________________________________________________________

## 11. What to avoid

Avoid these patterns:

### Avoid putting dashboard runtime JS under `src/kibad_llm/`

Unless the dashboard is intentionally being turned into package/application code.

### Avoid putting tests under `docs/`

Because docs content and test content will get mixed.

### Avoid relying only on manual verification for “behavior-preserving”

Use a checked-in baseline artifact, curated fixtures, smoke tests, and logic tests as early as possible.

### Avoid too many HTML files

Static docs sites usually do not benefit much from partial/template proliferation.

### Avoid splitting by arbitrary line count

Split by responsibility, not “every N lines”.

### Avoid making every module touch the DOM directly

The more DOM-free logic that is extracted, the easier testing becomes.

### Avoid coupling tests to mutable live experiment folders

Curate snapshots from real runs; do not treat `data/prediction_results/logs/` as the runtime test fixture directory.

______________________________________________________________________

## 12. Practical recommendation for this repository

If a single target structure is needed, it should be this:

```text
docs/
  eval-dashboard/
    index.html
    assets/
      css/
        index.css
        tokens.css
        layout.css
        controls.css
        tables.css
        plots.css
      js/
        main.js
        state/
          store.js
          selectors.js
        data/
          normalize.js
          ingest-runs.js
          file-loader.js
          git-loader.js
          parse-overrides.js
        browser/
          session.js
        ui/
          dom.js
          table-shared.js
          controls.js
          prediction-table.js
          evaluation-table.js
          eval-json-pane.js
          tabs.js
          status.js
        plots/
          shared.js
          bars.js
          confusion.js
          tpfpfn.js
          legend.js
          export.js
        utils/
          flatten.js
          sort.js
          values.js
          text.js

tests/
  fixtures/
    eval_dashboard/
      ...
  unit/
    eval_dashboard/
      ...
  integration/
    eval_dashboard/
      ...
```

### Guiding principle

- `docs/` = shipped static dashboard assets
- `tests/` = all tests, never mixed into docs
- one HTML shell inside a dedicated dashboard folder
- modular JS by responsibility
- CSS split by concern
- curated fixtures mirror real dashboard inputs without depending on mutable live data
- tests start early and expand as pure modules are extracted
- every phase updates the planning docs in `docs/eval-dashboard/`
- every phase remains compliant with `CONTRIBUTING.md`

______________________________________________________________________

## 13. Suggested next step sequence

From the current repository state, the cleanest next sequence would be:

1. extract plot data-shaping / aggregation / tab-map logic first and add JS-native plot tests for those helpers; keep the already-extracted thin plot-control UI in `ui/controls.js`, and move only the remaining plot-specific implementation logic into the later `plots/` modules
1. extract SVG/export/rendering helpers into `plots/` modules
1. keep extending `tests/unit/eval_dashboard/js/*.test.mjs` for any newly extracted DOM-free plot/export helpers while preserving the existing Phase 8 loader/ingestion coverage, Phase 9 infrastructure coverage, and the current Phase 10A/10B orchestration-contract checks
1. reduce `main.js` to orchestration only, with no remaining reusable render/math/browser helper layer or avoidable pass-through wrappers embedded in it
1. after each completed phase above, update the planning docs under `docs/eval-dashboard/` and confirm the landed changes comply with `CONTRIBUTING.md`

That keeps the refactor incremental, builds directly on the already-landed migration, fixture, smoke-test, CSS-extraction, JS-harness, Phase 8 loader/ingestion groundwork, Phase 9 DOM/table/status/browser-session groundwork, and the landed Phase 10A/10B UI groundwork, and preserves the test-first direction of the overall plan while avoiding a long-term trap where plotting/export logic and orchestration still remain coupled in `main.js`.

## 14. Post-refactor cleanup TODOs

deferred beyond Phase 8:

- allow override-key parsing to strip up to two leading `+` characters rather than only one
- stop silently skipping override lines that the lightweight parser cannot understand; instead raise a dedicated error and skip the affected run cleanly
- investigate a more exact parse/normalization error taxonomy
- revisit whether missing prediction ids should remain tolerated or should become disallowed entirely
- evaluate whether a real YAML parser is worth adding later as a browser-runtime dependency without compromising the no-build default architecture
- remove the temporary `docs/eval-dashboard.html` compatibility shim once link stability and hosting behavior have been verified well enough to retire it safely
- run a dedicated dashboard accessibility pass after modularization, covering keyboard navigation, focus management, ARIA semantics for tabs/expanders/select-all controls, and user feedback for copy/export actions
- re-evaluate whether the handwritten ZIP/CRC/export helper implementation should remain custom or later be replaced with a maintained dependency if that can be justified under the repository's dependency policy and no-build constraints
- once renderer extraction is complete, remove remaining one-line selector/store/table-helper pass-through wrappers in `main.js` where direct module calls improve readability instead of preserving them as accidental long-term seams
- after plot extraction, re-evaluate whether the current `MutationObserver`-driven download-button refresh should remain DOM-observer-based or be replaced with an explicit render-lifecycle update that is easier to reason about and test
