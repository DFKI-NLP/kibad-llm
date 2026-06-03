# Evaluation Dashboard

The evaluation dashboard is a static documentation page for inspecting evaluation run outputs. It runs entirely in the browser from `docs/eval-dashboard/index.html` and does not require a frontend build step.

Use it to load one or more evaluation-run folders, compare prediction groups, inspect evaluation outputs, visualize metric families, and export the visible plot figures.

**Open the dashboard:** [docs/eval-dashboard/index.html](eval-dashboard/index.html)

## Running the Dashboard

Open `docs/eval-dashboard/index.html` through the docs site or directly from the repository checkout.

The page supports two data sources:

- **Local folder:** select a logs directory with the browser directory picker.
- **GitHub tree URL:** enter a GitHub `tree` URL that points at a folder containing run outputs. An optional token can be stored in the browser for private repositories.

Loaded GitHub URLs can be kept in the page URL through the `git_url` query parameter. GitHub tokens are stored only in the browser and are not added to the URL.

## Input Shape

The dashboard loads single evaluation runs. A run directory is considered loadable when it contains both:

- `job_return_value.json`
- `.hydra/overrides.yaml`

Runs inside `predict` directories are ignored. Prediction payloads are canonicalized separately and linked to evaluations through the prediction id extracted from the normalized run payload.

The ingestion path supports the current curated fixture versions under `tests/fixtures/eval_dashboard/`, including bars, errors, confusion-matrix, and TP/FP/FN metric families.

For real repository data, see [`data/prediction_results`](https://github.com/DFKI-NLP/kibad-llm/tree/main/data/prediction_results). Its [`readme.md`](https://github.com/DFKI-NLP/kibad-llm/blob/main/data/prediction_results/readme.md) keeps an overview of available experiment log folders, and the `logs/` subfolders contain evaluation outputs that can be loaded with the dashboard.

## Architecture

The dashboard is intentionally kept as a docs asset, not Python package code. Runtime files live under `docs/eval-dashboard/`:

```text
docs/eval-dashboard/
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
      browser/
        session.js
      data/
        file-loader.js
        git-loader.js
        ingest-runs.js
        normalize.js
        parse-overrides.js
      plots/
        bars.js
        confusion.js
        dashboard.js
        export.js
        legend.js
        shared.js
        tpfpfn.js
      state/
        selectors.js
        store.js
      ui/
        controls.js
        dom.js
        eval-json-pane.js
        evaluation-table.js
        prediction-table.js
        status.js
        table-shared.js
        tabs.js
      utils/
        flatten.js
        sort.js
        text.js
        values.js
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

The modularization refactor is complete through the current orchestration cleanup. Remaining work is optional and should be driven by actual maintenance needs.

Browser-level coverage:

- Add browser-level UI smoke tests if dashboard interactions start changing often enough to justify Playwright or an equivalent browser harness.
- Cover representative user flows if browser tests are added: local fixture loading, GitHub tree loading with mocked network responses, prediction/evaluation tab switching, plot rendering, and figure-export enablement.

Parser and data-policy cleanup:

- Decide whether override-key parsing should strip up to two leading `+` characters instead of the current single leading `+`.
- Decide whether unsupported override lines should raise a dedicated parser error and skip the affected run cleanly instead of being silently ignored.
- Revisit the parse/normalization error taxonomy if load summaries need more precise failure categories.
- Revisit whether missing prediction ids should remain tolerated as skipped runs or become disallowed entirely.
- Evaluate whether a real YAML parser is worth adding as a browser-runtime dependency while preserving the no-build default architecture.

Accessibility and export cleanup:

- Run a dedicated accessibility pass for keyboard navigation, focus management, ARIA semantics for tabs/expanders/select-all controls, and copy/export feedback.
- Re-evaluate whether the custom ZIP/CRC/export helpers should remain custom or be replaced with a maintained dependency under the repository's dependency policy and no-build constraints.
- Re-evaluate whether the current `MutationObserver`-driven download-button refresh should remain DOM-observer-based or be replaced with an explicit render-lifecycle update.

Entrypoint maintenance:

- Continue shrinking `main.js` only when a new extraction removes real complexity without hiding orchestration decisions.
