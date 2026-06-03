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

- **Repository data:** start with [`data/prediction_results`](https://github.com/DFKI-NLP/kibad-llm/tree/main/data/prediction_results). Its [`readme.md`](https://github.com/DFKI-NLP/kibad-llm/blob/main/data/prediction_results/readme.md) contains an overview table of available experiment log folders, and the `logs/` subfolders contain evaluation outputs that can be loaded with the dashboard.
- **Local folder:** select a logs directory with the browser directory picker.
- **GitHub tree URL:** enter a GitHub `tree` URL that points at a folder containing run outputs. An optional token can be stored in the browser for private repositories.

Loaded GitHub URLs can be kept in the page URL through the `git_url` query parameter. GitHub tokens are stored only in the browser and are not added to the URL.

The dashboard loads single evaluation runs. A run directory is loadable when it contains both:

- `job_return_value.json`
- `.hydra/overrides.yaml`

Runs inside `predict` directories are ignored. Prediction payloads are canonicalized separately and linked to evaluations through the prediction id extracted from the normalized run payload.

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
            │   ├── ingest-runs.js            <- Shared raw-entry ingestion, run discovery, duplicate/conflict handling.
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

## Maintenance Notes

- Keep `main.js` as orchestration code. New reusable behavior should go into `data/`, `state/`, `ui/`, `plots/`, `browser/`, or `utils/`.
- Prefer DOM-free helpers and plain data models for code that needs tests.
- Update curated fixtures and baseline contracts when the supported run payload shape changes.
- Keep the dashboard runtime entrypoint `docs/eval-dashboard/index.html` covered by tests.
- Do not make tests depend on mutable live experiment folders such as `data/prediction_results/logs/`; use curated snapshots under `tests/fixtures/eval_dashboard/`.

## Future Work

The modularization refactor is complete through the current orchestration cleanup. Remaining work should be driven by actual maintenance needs.

Known dashboard limitations:

- Unsupported override lines are currently ignored instead of producing a dedicated parser error for the affected run.
- Load-summary error categories are still coarse for some parse/normalization failures.
- Missing prediction ids are currently handled as skipped runs; this policy should be revisited.
- The current `MutationObserver`-driven download-button refresh should be reviewed against an explicit render-lifecycle update.
- Processing many confusion matrix or TP/FP/FN runs is currently very slow. This is probably caused by the normalization logic that unifies single field and collection evaluation run data.

Testing and accessibility:

- Add browser-level UI smoke tests if dashboard interactions start changing often enough to justify Playwright or an equivalent browser harness.
- Cover representative user flows if browser tests are added: local fixture loading, GitHub tree loading with mocked network responses, prediction/evaluation tab switching, plot rendering, and figure-export enablement.
- Run a dedicated accessibility pass for keyboard navigation, focus management, ARIA semantics for tabs/expanders/select-all controls, and copy/export feedback.

Dependency decisions:

- Evaluate whether a real YAML parser is worth adding as a browser-runtime dependency while preserving the no-build default architecture.
- Re-evaluate whether the custom ZIP/CRC/export helpers should remain custom or be replaced with a maintained dependency under the repository's dependency policy and no-build constraints.

Entrypoint maintenance:

- Continue shrinking `main.js` only when a new extraction removes real complexity without hiding orchestration decisions.
