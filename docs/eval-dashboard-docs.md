# Evaluation Dashboard

The evaluation dashboard helps inspect and compare evaluation run outputs directly in the browser. It uses linked prediction metadata to group and select the evaluations shown in tables and plots.

**Open the dashboard:** [docs/eval-dashboard/index.html](eval-dashboard/index.html)

## What It Is For

Use the dashboard when you want to:

- compare multiple evaluation runs side by side
- group and select evaluations by prediction metadata, evaluation metadata, or Hydra override values
- inspect the normalized evaluation JSON and linked prediction metadata behind a selected row
- visualize bar, error, confusion-matrix, and TP/FP/FN metric families
- export the currently visible plot figures

The dashboard is a static docs asset. It runs entirely in the browser and does not require a frontend build step.

## Data Sources and Run Format

The dashboard can load evaluation outputs from:

- **Repository data:** start with [`data/results`](/data/results). Its [`readme.md`](https://github.com/DFKI-NLP/kibad-llm-results/blob/main/readme.md) contains an overview table of available experiment log folders, and the `logs/` subfolders contain evaluation outputs that can be loaded with the dashboard.
- **Local folder:** select a logs directory with the browser directory picker.
- **GitHub tree URL:** enter a GitHub `tree` URL that points at a folder containing run outputs. An optional token can be stored in the browser for private repositories.

Loaded GitHub URLs can be kept in the page URL through the `git_url` query parameter. GitHub tokens are stored only in the browser and are not added to the URL.

The dashboard loads single evaluation runs. A run directory is loadable when it contains both:

- `job_return_value.json`
- `.hydra/overrides.yaml`

Runs inside `predict` directories are ignored. Prediction payloads are canonicalized separately and linked to evaluations through the prediction id extracted from the normalized run payload.

Imported evaluation runs are deduplicated by normalized content, not by folder path. The dashboard parses `job_return_value.json` and `.hydra/overrides.yaml`, derives a content-based `runId`, and skips later imports with matching content. The original `runDir` path remains visible in the evaluation table and error messages, but it does not determine run identity.

Downloaded plot-data JSON includes `run_dirs` alongside per-run samples or sparse matrix cells so users can identify each value's source folder. These paths are provenance only, not semantic identifiers: the same path can contain different runs, and matching paths do not imply matching content. The dashboard uses the content-derived `runId` internally to align and deduplicate evaluations, but intentionally omits it from public download payloads.

The checked-in dashboard fixtures under `tests/fixtures/eval_dashboard/` cover the currently supported fixture versions and metric families, including bars, errors, confusion matrices, and TP/FP/FN outputs. They are intended for tests and development rather than as the main user data source.

## Architecture

The dashboard is intentionally kept as a docs asset, not Python package code. Runtime files live under `docs/eval-dashboard/`, while the user-facing documentation page lives at `docs/eval-dashboard-docs.md`.

```text
docs/
├── eval-dashboard-docs.md                    <- User-facing dashboard documentation and link to the runtime page.
└── eval-dashboard/
    ├── index.html                            <- Static browser entrypoint for the dashboard UI.
    └── assets/
        ├── css/                              <- Dashboard-only styles split by concern.
        │   ├── index.css                     <- Stylesheet entrypoint imported by `index.html`.
        │   ├── tokens.css                    <- Theme variables and shared visual tokens.
        │   ├── layout.css                    <- Page layout, panes, panels, and responsive structure.
        │   ├── controls.css                  <- Form controls, buttons, tabs, and option panels.
        │   ├── tables.css                    <- Prediction/evaluation table layout and sticky controls.
        │   └── plots.css                     <- Plot cards, SVG containers, legends, and tooltips.
        └── js/                               <- Browser ES modules; no bundler or transpilation step.
            ├── main.js                       <- Page bootstrap, state ownership, event wiring, and render orchestration.
            ├── browser/
            │   └── session.js                <- Browser-session helpers for GitHub tokens and `git_url` query state.
            ├── data/
            │   ├── file-loader.js            <- Local folder/file filtering and text extraction.
            │   ├── git-loader.js             <- GitHub tree URL parsing plus GitHub content listing/fetching.
            │   ├── ingest-runs.js            <- Shared raw-entry ingestion, run discovery, content-based duplicate/conflict handling.
            │   ├── normalize.js              <- Supported `job_return_value.json` version normalization.
            │   └── parse-overrides.js        <- Lightweight parser for Hydra `.hydra/overrides.yaml` list entries.
            ├── plots/
            │   ├── bars.js                   <- Bar and grouped-bar plot rendering.
            │   ├── confusion.js              <- Confusion-matrix expansion, aggregation, tabs, and rendering.
            │   ├── dashboard.js              <- Dashboard-level plot controls, plot rendering adapter, and downloads.
            │   ├── export.js                 <- SVG serialization, clipboard helpers, ZIP/CRC creation, and save flow.
            │   ├── legend.js                 <- Legend models and legend DOM rendering.
            │   ├── shared.js                 <- Shared plot labels, metric paths, tab maps, and SVG helpers.
            │   └── tpfpfn.js                 <- TP/FP/FN aggregation, tabs, copy summaries, and rendering.
            ├── state/
            │   ├── selectors.js              <- Derived prediction/evaluation views, grouping, sorting, and plot inputs.
            │   └── store.js                  <- Canonical dashboard state container and state-reset/sync helpers.
            ├── ui/
            │   ├── controls.js               <- Shared option panels, group-by controls, and plot-control state.
            │   ├── dom.js                    <- DOM reference capture and low-level DOM helpers.
            │   ├── eval-json-pane.js         <- Evaluation/prediction JSON side-pane rendering.
            │   ├── evaluation-table.js       <- Evaluation table header, group row, and member row rendering.
            │   ├── prediction-table.js       <- Prediction table header, group row, and member row rendering.
            │   ├── status.js                 <- Load status, progress, and download-button labels.
            │   ├── table-shared.js           <- Shared table sorting, selection, truncation, and sticky-column helpers.
            │   └── tabs.js                   <- Shared tab button models, rendering, and delegated tab selection.
            └── utils/
                ├── flatten.js                <- Object flattening and nested path lookup helpers.
                ├── runs.js                   <- Semantic run-id derivation and evaluation identity helpers.
                ├── sort.js                   <- Sort config normalization and stable compare helpers.
                ├── text.js                   <- Display text, plot-title, and filename helpers.
                └── values.js                 <- Value normalization, signatures, numeric guards, and defaults.
```

`assets/js/main.js` is the browser entry point and composition layer. It owns the singleton page state, captures DOM refs, wires user events, calls loaders and ingestion helpers, mutates canonical state, and triggers rendering. Domain logic, reusable rendering behavior, data parsing, plotting, export helpers, and browser-session mechanics should stay in imported modules.

Dependency direction should remain one-way: helper modules must not import from `main.js`.

## Testing

The dashboard has Python structural/contract tests and JavaScript unit tests for extracted browser logic.

Run the dashboard-specific Python tests:

```bash
uv run --group cicd pytest tests/unit/eval_dashboard
```

Run the JavaScript tests:

```bash
node --test tests/unit/eval_dashboard/js/*.test.mjs
```

The JavaScript tests use Node's built-in test runner. There is no bundler or frontend package install step.

The most relevant test locations are:

- `tests/unit/eval_dashboard/` for HTML, fixture, baseline, and orchestration contracts.
- `tests/unit/eval_dashboard/js/` for extracted module behavior.
- `tests/fixtures/eval_dashboard/` for curated dashboard input fixtures and baseline artifacts.

## Benchmarking

The dashboard has a manual Playwright benchmark for latency investigation. It is not part of the normal test suite and should not be treated as a strict pass/fail gate because browser timings are hardware- and load-dependent.

The persisted benchmark lives in `docs/eval-dashboard/benchmark/`. It starts a local static server for `docs/eval-dashboard`, opens the dashboard with `debugTiming=1`, loads local folders through the browser file-input path, records dashboard console timing tables, records folder-load and interaction wall-clock durations, records the browser version, and writes a JSON report.

Install the optional Node dev dependency:

```bash
cd docs/eval-dashboard/benchmark
npm install
```

Run the default benchmark:

```bash
npm run benchmark
```

By default, the benchmark loads the complete local folders:

- `data/results/logs/477_faktencheck_core`
- `data/results/logs/481_faktencheck_core`

Both folders contain evaluations over predictions from `397_faktencheck_core_v1_for_chunking` on flattened data. `477_faktencheck_core` uses `faktencheck_core_confusion_matrix_multiple_fields_flat` and produces `ConfusionMatrixCollection` data. It stresses confusion-matrix collection handling, label-union alignment, tab-map construction, aggregation, and matrix SVG rendering. `481_faktencheck_core` uses `faktencheck_core_tpfpfn_multiple_fields_flat` and produces `TpFpFnCollectorCollection` data. It stresses TP/FP/FN collection handling, per-document normalization, tab-map construction, aggregation, and matrix SVG rendering.

The default folders are intentionally loaded as complete top-level folders through the same dashboard import path a user would use, not as hand-picked subruns or reduced subsets. The browser receives the folder files through Playwright's file input support with browser-relative paths preserved, so local import processing follows the same dashboard code path as a user selecting the folder. The benchmark does not measure native OS file-picker overhead, user think time, browser-cache variability across different manual sessions, or visual perception beyond waiting for one animation frame after the dashboard emits the expected timing table.

Useful options:

```bash
npm run benchmark -- --headed
npm run benchmark -- --output /tmp/dashboard-benchmark.json
npm run benchmark -- ../../../data/results/logs/477_faktencheck_core
```

The benchmark currently measures:

- `complete folder load to usable dashboard`: after a fresh page load, set the complete folder on the local file input and wait until local import processing, initial prediction rendering, initial evaluation/plot rendering, and download-button state updates have completed.
- `local import processing`: local file collection, run ingestion, canonical state updates, derived prediction state reset, and load-status rendering for the complete folder.
- `initial prediction render`: the first prediction-table render after import, including prediction selectors, controls, table rendering, and sticky-column offset work.
- `initial evaluation/plot render`: the first evaluation render after import, including evaluation selection/grouping, evaluation controls/table/JSON pane, plot controls, active plot-tab data preparation, aggregation, and SVG rendering.
- `fresh post-load switch tab grouping to metric field`: on a freshly loaded page, click the confusion/TP-FP-FN tab-grouping control from prediction-group mode to metric-field mode. This resets the active plot tab and renders the first metric-field tab selected by the dashboard, which is usually a small field.
- `fresh post-load switch active plot tab`: on a freshly loaded page in the default tab mode, click the first inactive plot tab. This measures changing between prediction-group tabs, with the target tab determined by current tab ordering.
- `fresh post-load switch to metric-field german_name tab`: on a freshly loaded page, switch to metric-field mode, then click the `german_name` metric-field tab. This measures the complete user workflow needed to reach that large metric-field tab and emits one timing table for the mode switch and one timing table for the target-tab render.
- `fresh post-load switch to metric-field scientific_name tab`: same as the `german_name` scenario, but targets `scientific_name`.
- `fresh post-load set evaluation group-by to none`: on a freshly loaded page, click the evaluation group-by `none` control. This changes evaluation grouping and forces a full evaluation and plot render while the expensive default plot tab is still active.
- `fresh post-load deselect evaluation table row`: on a freshly loaded page, click the first selected evaluation-group checkbox. This changes selected evaluation groups and forces a full evaluation and plot render while the expensive default plot tab is still active.
- `fresh post-load deselect prediction table row`: on a freshly loaded page, click the first selected prediction-group checkbox. This first renders the prediction table, then renders evaluations and plots because selected evaluations depend on selected predictions.

Each folder result in the JSON report includes `initial_load.wall_ms` and the timing-table indexes emitted by the initial load. Each interaction record includes `wall_ms` and the timing-table indexes emitted by that interaction.

The benchmark records two timing concepts:

- **Timing table total:** the sum of instrumented, non-overlapping dashboard timing rows emitted for a render or load phase. These rows are useful for diagnosing which dashboard stages dominate.
- **Wall-clock:** elapsed browser `performance.now()` time from the benchmark action start until the next animation frame after the relevant timing table has been emitted. This better approximates interaction latency but can include event dispatch, layout, paint, and uninstrumented work.

The post-load scenarios are intentionally isolated from each other. Each scenario reloads the complete folder into a fresh page before performing its interaction. This avoids hidden interdependencies where an earlier cheapening action, such as switching to a smaller plot tab or changing grouping, would make later scenarios look faster than the corresponding manual workflow immediately after loading.

Important interpretation details:

- The exact active plot tab matters. Large fields such as `german_name` and `scientific_name` are much more expensive than small fields such as `biodiversity_level`.
- Some scenarios intentionally produce multiple timing tables. For example, prediction-row deselection emits prediction render timing and evaluation render timing; metric-field target-tab scenarios emit the mode-switch render and the target-tab render.
- Timing table totals should not be compared to wall-clock numbers as if they measured the same thing. Timing table totals are diagnostic; wall-clock values are closer to user-perceived latency.
- The benchmark captures only the current default viewport, browser channel, and tab ordering. Changes to viewport size, active tab defaults, plot-tab sorting, or selected data can materially change scenario cost.
- The benchmark currently focuses on confusion-matrix and TP/FP/FN collection workflows. Numeric bar/error plot workflows should get their own representative data and scenarios before using this benchmark to reason about them.

Timing instrumentation is disabled in normal dashboard use. Add `debugTiming=1` to the dashboard URL to emit structured timing rows manually in the browser console.

## Maintenance Notes

- Keep `main.js` as orchestration code. New reusable behavior should go into `data/`, `state/`, `ui/`, `plots/`, `browser/`, or `utils/`.
- Prefer DOM-free helpers and plain data models for code that needs tests.
- Update curated fixtures and baseline contracts when the supported run payload shape changes.
- Keep the dashboard runtime entrypoint `docs/eval-dashboard/index.html` covered by tests.
- Do not make tests depend on mutable live experiment folders such as `data/results/logs/`; use curated snapshots under `tests/fixtures/eval_dashboard/`.

## Future Work

The modularization refactor is complete through the current orchestration cleanup. Remaining work should be driven by actual maintenance needs.

Known dashboard limitations:

- Unsupported override lines are currently ignored instead of producing a dedicated parser error for the affected run.
- Load-summary error categories are still coarse for some parse/normalization failures.
- Missing prediction ids are currently handled as skipped runs; this policy should be revisited.
- The current `MutationObserver`-driven download-button refresh should be reviewed against an explicit render-lifecycle update.
- Processing many confusion matrix or TP/FP/FN runs is currently very slow.
    - This is probably caused by the normalization logic that unifies single field and collection evaluation run data. Edit: Some improvements have been made in this area, but further review is needed.
    - And/or by re-calculating all data preparation each time some grouping or plot option changes.

Testing and accessibility:

- Add browser-level UI smoke tests if dashboard interactions start changing often enough to justify Playwright or an equivalent browser harness.
- Cover representative user flows if browser tests are added: local fixture loading, GitHub tree loading with mocked network responses, prediction/evaluation tab switching, plot rendering, and figure-export enablement.
- Run a dedicated accessibility pass for keyboard navigation, focus management, ARIA semantics for tabs/expanders/select-all controls, and copy/export feedback.

Dependency decisions:

- Evaluate whether a real YAML parser is worth adding as a browser-runtime dependency while preserving the no-build default architecture.
- Re-evaluate whether the custom ZIP/CRC/export helpers should remain custom or be replaced with a maintained dependency under the repository's dependency policy and no-build constraints.

Entrypoint maintenance:

- Continue shrinking `main.js` only when a new extraction removes real complexity without hiding orchestration decisions.
