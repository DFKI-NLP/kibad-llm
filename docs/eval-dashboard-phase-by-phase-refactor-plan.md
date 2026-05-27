# Eval dashboard phase-by-phase refactor plan

## Checklist

- [x] Define safe, incremental refactor phases
- [x] Keep `docs/eval-dashboard.html` as the stable public entry point
- [x] Specify concrete file extractions per phase
- [x] Add validation steps after each phase
- [x] Suggest sensible commit boundaries
- [x] Keep the initial testing strategy aligned with this Python-first repository

## Goal

Refactor `docs/eval-dashboard.html` in small, behavior-preserving steps.

The guiding idea is:

- keep the dashboard working at every step
- avoid introducing a new frontend toolchain in the first pass
- make the dashboard progressively easier to test
- preserve the current ProperDocs page entry while modularizing CSS and JavaScript underneath it

This plan assumes:

- `docs/eval-dashboard.html` stays the public dashboard page for now
- dashboard runtime assets live under `docs/assets/eval-dashboard/`
- tests live under `tests/`
- the repo remains Python-first unless a later follow-up explicitly adds frontend tooling

______________________________________________________________________

## Phase 0. Baseline and safety net

### Goal

Capture the current dashboard behavior before any extraction work begins.

### Why

The current dashboard is large and tightly coupled. Before moving code around, it helps to define what “still works” means.

### Tasks

- Keep `docs/eval-dashboard.html` unchanged.
- Create a short baseline checklist of current dashboard behavior.
- Identify a minimal set of representative evaluation inputs for future fixture creation.
- Note important features that must remain stable during refactoring.

### Baseline behavior checklist

At minimum, record whether the current dashboard correctly supports:

- loading local evaluation folders/files
- loading from GitHub URL input
- prediction grouping
- evaluation experiment tabs
- JSON side pane behavior
- confusion matrix plots
- TP/FP/FN plots
- grouped bar plots
- figure export/download state
- light/dark styling

### Suggested validation

Build and serve the docs site and manually verify the dashboard once before starting the refactor.

```bash
cd /home/arbi01/projects/kibad-llm
uv run --group cicd properdocs build
uv run --group cicd properdocs serve -w .
```

### Suggested commit boundary

`docs(eval-dashboard): record baseline behavior for modularization`

______________________________________________________________________

## Phase 1. Add dashboard fixtures and refactor notes

### Goal

Create repeatable sample inputs that can later support smoke tests and regression checks.

### Tasks

Add a dedicated fixture area:

```text
tests/
  fixtures/
    dashboard/
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

- existing evaluation-related fixture content under `tests/fixtures/`
- example Hydra run directories already present in this repo
- simplified copies of real `job_return_value.json` + `.hydra/overrides.yaml` pairs

### What to include

At minimum:

- one valid version-0 style run
- one valid version-1 style run
- one valid version-2 style run
- one unsupported version example
- one malformed JSON/YAML example
- one conflicting prediction-id example
- one example that produces confusion-matrix output
- one example that produces TP/FP/FN output

### Why this phase comes early

Fixtures make later module extraction safer and give a stable basis for tests.

### Suggested validation

- verify fixture folders are organized consistently
- verify each “valid” fixture has the expected files
- verify invalid fixtures are intentionally invalid and documented

### Suggested commit boundary

`test(fixtures): add eval dashboard fixture set`

______________________________________________________________________

## Phase 2. Extract CSS only

### Goal

Move all styling out of `docs/eval-dashboard.html` without changing dashboard behavior.

### Tasks

Create:

```text
docs/assets/eval-dashboard/css/
  index.css
  tokens.css
  layout.css
  controls.css
  tables.css
  plots.css
```

Then:

- move the inline `<style>` block from `docs/eval-dashboard.html` into the CSS files
- keep the HTML structure unchanged
- have `docs/eval-dashboard.html` load only the external stylesheet

### Suggested CSS split

- `tokens.css`: root variables, theme colors, typography
- `layout.css`: page spacing, panel layout, split views, grid layout
- `controls.css`: buttons, tabs, form controls, rows, chips
- `tables.css`: table layout, sticky headers, selected rows, JSON pane styles
- `plots.css`: plot cards, tooltips, legends, export-related styles
- `index.css`: imports or central stylesheet entry point

### Important constraint

Do **not** rename classes or change DOM structure in this phase unless absolutely necessary.

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
uv run --group cicd properdocs build
uv run --group cicd properdocs serve -w .
```

### Suggested commit boundary

`docs(eval-dashboard): externalize dashboard CSS`

______________________________________________________________________

## Phase 3. Move the inline script into one external module

### Goal

Reduce HTML complexity first, before splitting JavaScript into many files.

### Tasks

Create:

```text
docs/assets/eval-dashboard/js/
  main.js
```

Then:

- move the full inline `<script>` body from `docs/eval-dashboard.html` into `docs/assets/eval-dashboard/js/main.js`
- replace the inline block with a single external script reference
- use module loading if appropriate for later splitting

### Important constraint

This phase should still be **behavior-preserving**.
Do not split logic yet. Keep:

- the current `state`
- DOM element lookups
- current functions
- current event wiring

all together in `main.js`.

### Why this phase matters

Once the script is externalized, future refactors stop rewriting a huge HTML file and start operating on normal JS modules.

### Validation checklist

Verify that all existing interactions still work:

- local folder load
- GitHub load
- prediction table rendering
- evaluation table rendering
- plot rendering
- figure download button state

### Suggested commit boundary

`docs(eval-dashboard): move inline dashboard script to external module`

______________________________________________________________________

## Phase 4. Extract pure utilities

### Goal

Separate small, reusable, DOM-independent helpers from the main module.

### Tasks

Create:

```text
docs/assets/eval-dashboard/js/utils/
  flatten.js
  sort.js
  values.js
  text.js
  zip.js
```

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

#### `zip.js`

- zip blob construction helpers
- generic file packaging helpers used by export

### Important constraint

Only move functions that are truly low-coupling and mostly independent of the DOM.

### Why this phase is early

It creates reusable building blocks without forcing large architectural decisions yet.

### Validation checklist

- imports still resolve
- sorting behavior remains unchanged
- filename generation remains unchanged
- export helper behavior remains unchanged
- flattening/grouping-dependent logic still behaves the same

### Suggested commit boundary

`refactor(eval-dashboard): extract pure utility modules`

______________________________________________________________________

## Phase 5. Extract state and selectors

### Goal

Separate canonical state from derived data access.

### Tasks

Create:

```text
docs/assets/eval-dashboard/js/state/
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

### Why this phase matters

This is the major step that makes the dashboard testable at the logic layer.

### Validation checklist

Verify no regression in:

- grouping behavior
- selection behavior
- experiment tab behavior
- sorting state
- plot-group selection inputs

### Suggested test addition in this phase

Add lightweight smoke checks under:

```text
tests/unit/dashboard/
  test_eval_dashboard_assets.py
```

Potential initial checks:

- required dashboard asset files exist
- `docs/eval-dashboard.html` references expected external files
- fixture directories exist and have expected required files

### Suggested commit boundaries

- `refactor(eval-dashboard): extract state store`
- `refactor(eval-dashboard): extract selector logic`

______________________________________________________________________

## Phase 6. Extract parsing and normalization

### Goal

Make imported dashboard data handling testable and clearly separated from rendering.

### Tasks

Create:

```text
docs/assets/eval-dashboard/js/data/
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

### Why this phase matters

Data normalization is one of the most valuable areas to test independently.

### Validation checklist

Verify that:

- supported versions still load
- unsupported versions are still rejected correctly
- malformed files still fail cleanly
- missing prediction ids are still handled correctly
- conflicting prediction ids are still handled correctly

### Suggested commit boundaries

- `refactor(eval-dashboard): extract overrides parsing`
- `refactor(eval-dashboard): extract run normalization`

______________________________________________________________________

## Phase 7. Extract local file loading and GitHub loading

### Goal

Separate all ingestion flows from normalization and rendering.

### Tasks

Create:

```text
docs/assets/eval-dashboard/js/data/
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

### Validation checklist

Verify:

- local fixture folders still load
- GitHub URL loading still works
- progress/status text still updates
- duplicate-run handling still works
- unsupported-version/malformed-run handling still works

### Suggested commit boundaries

- `refactor(eval-dashboard): extract local file loader`
- `refactor(eval-dashboard): extract GitHub loader`

______________________________________________________________________

## Phase 8. Extract UI modules

### Goal

Separate rendering concerns from state/data logic.

### Tasks

Create:

```text
docs/assets/eval-dashboard/js/ui/
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

- receive state-derived inputs
- render DOM
- expose event callbacks to `main.js`

Avoid hiding state mutations deep inside many rendering functions unless necessary.

### Validation checklist

Verify that:

- table rendering remains correct
- group selection still works
- JSON pane still syncs with row selection
- options tabs still work
- default/truncate controls still work
- sort buttons still work

### Suggested commit boundaries

- `refactor(eval-dashboard): extract shared ui helpers`
- `refactor(eval-dashboard): extract prediction and evaluation renderers`
- `refactor(eval-dashboard): extract json pane and control renderers`

______________________________________________________________________

## Phase 9. Extract plotting and export modules

### Goal

Move plotting logic into dedicated modules and leave `main.js` as orchestration only.

### Tasks

Create:

```text
docs/assets/eval-dashboard/js/plots/
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
- zip export orchestration

### Design rule

Plot modules should depend on selector/data outputs, not on raw DOM state spread throughout the codebase.

### Validation checklist

Verify:

- grouped bar plots still render
- confusion tabs still render and switch correctly
- TP/FP/FN tabs still render and switch correctly
- tooltips still work
- legend behavior still works
- figure ZIP download still works

### Suggested commit boundaries

- `refactor(eval-dashboard): extract shared plot helpers`
- `refactor(eval-dashboard): extract confusion and tpfpfn plot modules`
- `refactor(eval-dashboard): extract export and legend helpers`

______________________________________________________________________

## Phase 10. Reduce `main.js` to orchestration only

### Goal

Make `main.js` the bootstrap layer, not the implementation layer.

### What `main.js` should still do

- import modules
- initialize state
- capture DOM references
- wire event listeners
- call render/update flows
- coordinate loading pipelines

### What `main.js` should ideally no longer contain

- complex normalization logic
- large rendering functions
- plotting implementations
- generic sorting/flattening helpers
- large parsing logic

### Why this final cleanup matters

This phase confirms that the modularization is complete rather than partial.

### Validation checklist

- `main.js` is readable as high-level orchestration
- module boundaries feel natural
- no large “temporary dumping ground” functions remain
- dashboard behavior still matches the Phase 0 baseline

### Suggested commit boundary

`refactor(eval-dashboard): reduce main entry to orchestration`

______________________________________________________________________

## Phase 11. Add repo-native smoke tests

### Goal

Add modest but useful test coverage without introducing a full browser test stack yet.

### Test locations

```text
tests/
  fixtures/
    dashboard/
      ...
  unit/
    dashboard/
      test_eval_dashboard_assets.py
      test_dashboard_fixtures.py
  integration/
    dashboard/
      test_eval_dashboard_docs_build.py
```

### Early test ideas

#### `tests/unit/dashboard/test_eval_dashboard_assets.py`

- verify expected CSS/JS files exist
- verify `docs/eval-dashboard.html` references expected external assets
- verify no giant inline `<style>` or `<script>` remains after extraction phases

#### `tests/unit/dashboard/test_dashboard_fixtures.py`

- verify valid fixture folders contain required files
- verify malformed/unsupported fixtures are intentionally structured as expected

#### `tests/integration/dashboard/test_eval_dashboard_docs_build.py`

- verify docs build succeeds with the dashboard present
- optionally assert built output contains expected asset references

### Why smoke tests first

This repo is currently Python-first and already uses `pytest`. Smoke tests give immediate value without committing yet to a separate frontend ecosystem.

### Suggested validation

```bash
cd /home/arbi01/projects/kibad-llm
uv run --group cicd pytest tests/unit/dashboard tests/integration/dashboard
uv run --group cicd properdocs build
```

### Suggested commit boundary

`test(eval-dashboard): add docs and fixture smoke coverage`

______________________________________________________________________

## Phase 12. Optional follow-up: browser-level UI testing

### Goal

Decide whether the dashboard now justifies dedicated frontend testing.

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

______________________________________________________________________

## Recommended PR / commit breakdown

A sensible sequence would be:

1. baseline notes + fixture addition
1. CSS extraction
1. external `main.js`
1. utility extraction
1. state/store extraction
1. selector extraction
1. parse/normalize extraction
1. local file loader extraction
1. GitHub loader extraction
1. UI module extraction
1. plot/export extraction
1. `main.js` cleanup
1. smoke tests

If needed, these can be grouped into fewer PRs:

- PR 1: fixtures + CSS + external `main.js`
- PR 2: utilities + state + selectors + normalization
- PR 3: loaders + UI modules
- PR 4: plot/export modules + smoke tests + final cleanup

______________________________________________________________________

## Definition of done

The refactor is complete when:

- `docs/eval-dashboard.html` is a thin entry page
- CSS lives under `docs/assets/eval-dashboard/css/`
- JS is split into state, data, UI, plot, and utility modules
- `main.js` is only orchestration/bootstrap
- dashboard runtime code remains under `docs/`
- dashboard tests/fixtures live under `tests/`
- ProperDocs still serves the dashboard correctly
- the refactored dashboard still matches the original baseline behavior

______________________________________________________________________

## Immediate next implementation step

If starting now, the safest first implementation step is:

1. add `tests/fixtures/dashboard/`
1. extract CSS only
1. move the inline script into `docs/assets/eval-dashboard/js/main.js`

That gives a cleaner base for all later extraction work while minimizing the risk of functional regressions.
