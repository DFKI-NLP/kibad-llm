# Eval dashboard modularization plan

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
- `docs/eval-dashboard/index.html` is still a **single huge static page**, but Phases 3 to 5 have now moved styling and the first low-coupling helpers into external assets; the page loads `assets/css/index.css`, `assets/js/main.js`, and the new utility modules under `assets/js/utils/` while most JavaScript logic still remains in one orchestration file for now.
- `properdocs.yml` and `docs/index.md` already point to the new folder-based entrypoint.
- `scripts/build_docs.py` only generates **Python API reference** pages from `src/`, so it is **not** a frontend asset pipeline.
- `docs/eval-dashboard/assets/css/` now contains `index.css`, `tokens.css`, `layout.css`, `controls.css`, `tables.css`, and `plots.css`; `docs/eval-dashboard/assets/js/` now contains `main.js` as the externalized monolith reserved for later splitting.
- `pyproject.toml` has **pytest**, and the repo now has dashboard smoke coverage under `tests/unit/eval_dashboard/`, including entrypoint checks plus HTML-contract checks that enforce external CSS, the external `assets/js/main.js` module reference, and the absence of inline runtime CSS/JS; `tests/unit/eval_dashboard/js/` is now the reserved location for extracted dashboard logic tests, and the long-term harness there is the minimal Node.js built-in test runner (`node --test tests/unit/eval_dashboard/js/*.test.mjs`).
- `data/prediction_results/readme.md` documents real experiment folders under `data/prediction_results/logs/`; those runs are useful fixture sources, but tests should use curated snapshots rather than reach into mutable live data folders.
- curated dashboard fixtures now exist under `tests/fixtures/eval_dashboard/`, including valid version coverage, invalid edge-case fixtures, and explicit examples for all current plot families (`bars`, `errors`, `confusion_matrix`, `tpfpfn`).

Given that, the recommendation is to keep the dashboard as a docs asset, but organize it as a small self-contained docs section that is testable and easy to evolve.

In other words, the repository is now effectively **through Phase 5 and ready for Phase 6**: entrypoint migration, compatibility coverage, curated fixtures, baseline artifacts, structural smoke tests, CSS extraction, the external-`main.js` step, the first utility extractions, the permanent JS-native logic-test runner, and explicit CI wiring have all landed.

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
          file-loader.js
          git-loader.js
          parse-overrides.js
        ui/
          dom.js
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
    file-loader.js
    git-loader.js
    parse-overrides.js
  ui/
    dom.js
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

#### `data/file-loader.js`

- folder/file input handling
- reading `job_return_value.json`
- reading `.hydra/overrides.yaml`

#### `data/git-loader.js`

- GitHub URL parsing
- GitHub content listing/fetching
- token handling if that remains client-side

#### `data/parse-overrides.js`

- overrides parsing logic

#### `ui/dom.js`

- shared DOM helpers
- one central `captureDomRefs(...)` or `getDomRefs(...)` function
- shared element creation/toggling helpers
- sticky-column offset helpers

#### `ui/*.js`

- DOM rendering for controls/tables/panes/tabs/status
- ideally as stateless render functions fed from selectors and DOM refs

#### `plots/*.js`

- plot-specific aggregation + SVG creation
- legend behavior
- confusion-specific paths
- tp/fp/fn-specific paths
- export/download helpers

#### `utils/*.js`

- pure generic helpers only

### Module dependency rules

Make the intended dependency direction explicit:

- `utils/` imports nothing dashboard-specific
- `state/` depends only on plain data shapes and `utils/`
- `data/` depends on `utils/` and canonical state/data shapes, not on UI modules
- `ui/` consumes selector outputs and DOM refs, but not raw loaders
- `plots/` consumes selector/data outputs, not broad global DOM state spread across the codebase
- `main.js` is the top-level orchestrator and should not become a dumping ground again
- no module should import back from `main.js`

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
        data.normalize.test.mjs
        data.parse-overrides.test.mjs
  integration/
    eval_dashboard/
      test_eval_dashboard_redirects.py
```

The repository has now standardized on flat `*.test.mjs` files under `tests/unit/eval_dashboard/js/`, so `node --test tests/unit/eval_dashboard/js/*.test.mjs` remains stable without recursive globbing or another harness migration.

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
          file-loader.js
          git-loader.js
          parse-overrides.js
        ui/
          dom.js
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

1. extract state/store helpers from `docs/eval-dashboard/assets/js/main.js`
1. extract selectors and add selector tests under `tests/unit/eval_dashboard/js/` using `node --test tests/unit/eval_dashboard/js/*.test.mjs`
1. extract normalization/parsing and add normalization tests under the same JS-native harness
1. extract loaders, UI modules, and plot/export modules
1. reduce `main.js` to orchestration only
1. after each completed phase above, update the planning docs under `docs/eval-dashboard/` and confirm the landed changes comply with `CONTRIBUTING.md`

That keeps the refactor incremental, builds directly on the already-landed migration, fixture, smoke-test, CSS-extraction, and Phase 5 JS-harness groundwork, and preserves the test-first direction of the overall plan while deeper JS extraction begins.
