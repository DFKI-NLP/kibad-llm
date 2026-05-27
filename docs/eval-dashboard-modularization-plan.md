# Eval dashboard modularization plan

## Checklist

- [x] Ground the recommendation in the current repository layout
- [x] Propose a practical dashboard file structure
- [x] Recommend where dashboard tests should live
- [x] Clarify which HTML/CSS/JS files are worth having
- [x] Call out tradeoffs before any refactor

A few repo-specific observations first:

- `docs/eval-dashboard.html` is currently a **single huge static page** with inline CSS and a very large inline `<script>`.
- `properdocs.yml` currently exposes that file directly in navigation, so a future-proof folder move should be done deliberately and early.
- `scripts/build_docs.py` only generates **Python API reference** pages from `src/`, so it is **not** a frontend asset pipeline.
- `pyproject.toml` has **pytest**, but there is **no existing Node/package.json frontend test setup**.

Given that, the recommendation is to keep the dashboard as a docs asset, but organize it as a small self-contained docs section that is testable and easy to evolve.

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
          prediction-table.js
          evaluation-table.js
          eval-json-pane.js
          controls.js
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
          zip.js
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

## 3. Where tests should live

### Short answer

**Not in `docs/`.** They should live under `tests/`, following the repo’s existing pattern.

### Best fit for this repo

```text
tests/
  fixtures/
    eval-dashboard/
      runs/
      predictions/
      evaluations/
      overrides/
  unit/
    eval-dashboard/
      ...
  integration/
    eval-dashboard/
      ...
```

This matches the current structure already used in the repository:

- `tests/unit/...`
- `tests/integration/...`
- `tests/fixtures/...`

### Why not put tests next to the docs files?

Because anything under `docs/` is conceptually publishable site content. Keeping tests there:

- mixes source and test concerns
- risks accidental publication/copying
- makes docs harder to navigate

______________________________________________________________________

## 4. What kinds of tests to have

This is the key architectural decision.

### Option A — lightweight, repo-consistent first step

If the goal is to modularize **without introducing a full frontend stack immediately**:

- Put pure logic into small JS modules:
    - normalization
    - grouping
    - sorting
    - filename generation
    - metric-path extraction
- Test those modules as **unit tests**
- Keep rendering tests minimal at first

This is the cleanest incremental path.

### Option B — if real dashboard confidence is needed

If “tests for the eval-dashboard” means:

- clicking tabs
- loading files
- rendering plots
- selection state
- export behavior

then eventually **browser-style tests** will be more valuable than only Python-side checks.

That usually means:

- JS unit tests for logic
- browser integration tests for UI behavior

### Recommended test split

#### Unit tests

`tests/unit/eval-dashboard/`

- normalization of imported job return values
- grouping/selectors
- sorting
- metric tab map builders
- filename sanitization/export naming
- parsing of overrides
- pure DOM-independent helpers

#### Integration tests

`tests/integration/eval-dashboard/`

- load sample run folders
- render dashboard shell
- switch tabs
- select groups
- verify table row counts / visible panels
- verify plots appear for supported metric types

#### Fixtures

`tests/fixtures/eval-dashboard/`

- minimal valid run dirs
- malformed data
- unsupported versions
- conflicting prediction ids
- multiple experiments
- confusion-matrix and tp/fp/fn examples

______________________________________________________________________

## 5. What HTML files should exist?

For now, there should be **exactly one runtime HTML entry file**, but it should live inside a dedicated dashboard folder.

### Recommended

- `docs/eval-dashboard/index.html`

Make it the public/stable entry point now. Keep it small and let it load external CSS/JS.

### Why only one HTML file?

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

### Why use `index.html` early?

- It gives the dashboard its own namespace immediately.
- It keeps page and assets colocated, which helps future maintenance and git diffs.
- It avoids doing one structure migration now and another one later.

### Avoid this mixed structure

Avoid combining:

```text
docs/
  eval-dashboard.html
  eval-dashboard/
    ...
```

It works technically, but it is easy to confuse and creates an awkward split between the page file and its future folder namespace.

______________________________________________________________________

## 6. What CSS files should exist?

Do not over-split CSS. A small number of concern-based files is enough.

### Good starting set

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

The current inline CSS naturally falls into a few groups:

- theme tokens
- layout wrappers
- controls/tabs
- data tables / JSON panes
- plotting/export styles

That is enough modularity without making CSS maintenance painful.

______________________________________________________________________

## 7. What JS files should exist?

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
    zip.js
```

### What goes where

#### `main.js`

- bootstrapping
- wiring event listeners
- initializing persisted settings
- calling top-level render/update functions

#### `state/store.js`

- canonical mutable state object
- small state reset helpers

#### `state/selectors.js`

- derived reads from state
- group builders
- current columns
- selected evaluations/predictions
- experiment grouping

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

#### `ui/*.js`

- DOM rendering for controls/tables/panes/tabs/status
- ideally as stateless render functions fed from selectors

#### `plots/*.js`

- plot-specific aggregation + SVG creation
- legend behavior
- confusion-specific paths
- tp/fp/fn-specific paths
- export/download helpers

#### `utils/*.js`

- pure generic helpers only

______________________________________________________________________

## 8. Concrete test layout recommendation

A practical target structure would be:

```text
tests/
  fixtures/
    eval-dashboard/
      run_v0/
        .hydra/overrides.yaml
        job_return_value.json
      run_v1/
        .hydra/overrides.yaml
        job_return_value.json
      run_v2/
        .hydra/overrides.yaml
        job_return_value.json
      conflicting_prediction_ids/
        ...
      unsupported_version/
        ...
      malformed/
        ...
  unit/
    eval-dashboard/
      test_normalize_imported_job_return_value.*
      test_selectors_and_grouping.*
      test_sorting_helpers.*
      test_plot_tab_builders.*
      test_export_filename_helpers.*
      test_parse_overrides.*
  integration/
    eval-dashboard/
      test_load_local_runs.*
      test_load_git_runs.*
      test_prediction_selection_to_eval_view.*
      test_confusion_plot_rendering.*
      test_tpfpfn_plot_rendering.*
```

The `*` here is intentional: the exact extension depends on whether the dashboard tests eventually use a JS-based test runner, browser tooling, or some hybrid approach.

______________________________________________________________________

## 9. One important decision: Python-only testing vs adding frontend tooling

Because the repo currently does **not** have a JS toolchain, there are two realistic paths.

### Path 1: stay minimal for now

- Modularize into JS files under `docs/eval-dashboard/assets/js`
- Keep tests limited initially
- Maybe add only lightweight smoke/integration checks later

Good if the main goal is reducing dashboard complexity with low tooling overhead.

### Path 2: treat the dashboard as a tested frontend subproject

- add a minimal frontend test setup later
- keep runtime assets in `docs/eval-dashboard/assets/`
- keep tests under `tests/unit/eval-dashboard/` and `tests/integration/eval-dashboard/`

Good if the dashboard matters enough that UI regressions would be costly.

### Recommendation

If tests are explicitly a goal, it makes sense to design the file structure **as if Path 2 is coming**, even if the tooling is introduced later.

That means:

- keep runtime code in `docs/eval-dashboard/assets/`
- keep tests in `tests/...`
- keep fixtures in `tests/fixtures/eval-dashboard/`
- split logic into pure modules so it becomes testable

______________________________________________________________________

## 10. What to avoid

Avoid these patterns:

### Avoid putting dashboard runtime JS under `src/kibad_llm/`

Unless the dashboard is intentionally being turned into package/application code.

### Avoid putting tests under `docs/`

Because docs content and test content will get mixed.

### Avoid too many HTML files

Static docs sites usually do not benefit much from partial/template proliferation.

### Avoid splitting by arbitrary line count

Split by responsibility, not “every N lines”.

### Avoid making every module touch the DOM directly

The more DOM-free logic that is extracted, the easier testing becomes.

______________________________________________________________________

## 11. Practical recommendation for this repository

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
          zip.js

tests/
  fixtures/
    eval-dashboard/
      ...
  unit/
    eval-dashboard/
      ...
  integration/
    eval-dashboard/
      ...
```

### Guiding principle

- `docs/` = shipped static dashboard assets
- `tests/` = all tests, never mixed into docs
- one HTML shell inside a dedicated dashboard folder
- modular JS by responsibility
- CSS split by concern
- fixtures mirror real dashboard inputs

______________________________________________________________________

## 12. Suggested next step

Before editing the dashboard implementation, the cleanest next step would be to turn this structure into a **phase-by-phase refactor plan**, starting with the folder move to `docs/eval-dashboard/index.html`, for example:

1. extract CSS first
1. extract state/selectors next
1. extract loaders/normalization
1. extract renderers
1. extract plots/export
1. add fixtures and initial tests

That keeps the refactor incremental and makes it easier to validate after each step.
