# Eval Dashboard Plot Data Flow Plan

This plan captures the current plotting data flow and a staged refactor path for two future goals:

- reduce latency when changing grouping, plot tabs, or plot options
- add a `Download data` action below the figures that exports the exact data used by the currently downloadable figures, before plot aggregation such as mean and standard deviation

The plan follows the repository guidance in `CONTRIBUTING_CODE.md`: related refactors are acceptable when they clarify responsibilities and provide concrete long-term value, and dashboard logic should stay DOM-free where practical with focused JavaScript tests.

## Current Flow

The plotting path is currently driven from `docs/eval-dashboard/assets/js/main.js`.

1. `main.js` owns the singleton dashboard state and calls `renderEvaluations()` for most evaluation and plot setting changes.
1. `renderEvaluations()` rebuilds evaluation tabs, table, JSON pane, options, summary, and then calls `renderEvaluationPlots()`.
1. `renderEvaluationPlots()` delegates to `renderEvaluationPlotsForDashboard()` in `plots/dashboard.js`.
1. `renderEvaluationPlotsForDashboard()` recomputes selected groups, metric type, plot groups, varying group fields, tab maps, aggregations, and then redraws SVG figures.
1. Metric-specific aggregation happens in the plot modules:
    - numeric bar/error metrics use `collectNumericMetricLeafPaths()` and `buildPlotEntries()` in `plots/shared.js`
    - confusion matrices use collection views and `getConfusionMatrixAggregation()` in `plots/confusion.js`
    - TP/FP/FN collectors use collection views and `getTpFpFnCombinedAggregation()` in `plots/tpfpfn.js`
1. `Download Figures` currently exports visible rendered SVG cards through `plots/export.js`.

## Likely Latency Causes

The main latency risk is that many small UI changes call the full `renderEvaluations()` path. That redraws the evaluation table, options panel, JSON pane, summary, and plots even when only plot state changed.

Repeated selector and plot-data work also contributes:

- selected prediction groups
- selected evaluations
- evaluation context
- evaluation groups
- plot groups
- varying group fields
- numeric metric leaf paths
- confusion and TP/FP/FN collection views
- metric-family aggregation
- SVG rendering

Some plot-tab clicks already avoid the full table render, but they still rebuild tab maps and active plot data before redrawing.

## Latency Candidate Data

The following repository data folders are good candidates for latency investigation because they exercise the large matrix-style plot families and are already present under `data/prediction_results/logs/`:

- `data/prediction_results/logs/477_faktencheck_core`
- `data/prediction_results/logs/481_faktencheck_core`

Both are evaluations over predictions from `397_faktencheck_core_v1_for_chunking` on flattened data.

`477_faktencheck_core` uses `faktencheck_core_confusion_matrix_multiple_fields_flat` and produces `ConfusionMatrixCollection` data. It is a good benchmark candidate for confusion-matrix collection handling, label-union alignment, tab-map construction, aggregation, and matrix SVG rendering.

`481_faktencheck_core` uses `faktencheck_core_tpfpfn_multiple_fields_flat` and produces `TpFpFnCollectorCollection` data. It is a good benchmark candidate for TP/FP/FN collection handling, per-document normalization, tab-map construction, aggregation, and matrix SVG rendering.

Benchmarking should load each complete top-level folder through the same dashboard import path a user would use, not a hand-picked subrun or reduced subset. The two benchmark scenarios should be:

1. **Loading/importing:** measure how long the dashboard takes to import and normalize the complete folder after selection.
1. **Post-load interactions:** after the complete folder has been loaded, measure latency for changes to grouping settings, active plot tabs, tab grouping modes, plot thresholds, grouped-bar controls where applicable, and other plot options.

These folders are useful benchmark inputs because they stress:

- collection-view construction across many metric fields
- large label-union alignment for confusion matrices
- TP/FP/FN normalization across many documents and labels
- tab-map rebuilding for metric-field and prediction-group modes
- large SVG matrix rendering after aggregation

## Refactor Plan

### 1. Add Lightweight Instrumentation

Add temporary or testable timing boundaries around the main expensive stages:

- `getEvaluationContext`
- `getPlotGroups`
- metric path discovery
- collection-view construction
- tab-map construction
- aggregation
- SVG rendering

Use the measurements to confirm which stages dominate before making broad changes. The complete `477_faktencheck_core` and `481_faktencheck_core` folders should be used as benchmark inputs for both loading/importing and post-load interaction measurements because they exercise the highest-risk plot families.

### 2. Split Render Responsibilities

Introduce narrower render entry points:

- `renderEvaluationShell()` for tabs, table, options, JSON pane, and summary
- `renderEvaluationPlotsOnly()` for plot controls, plot tabs, and plot content
- `renderActivePlotTabOnly()` where active-tab changes can reuse already prepared plot data

Plot-only controls should avoid rebuilding the evaluation table unless they affect table state. This applies to controls such as:

- plot tab grouping
- confusion tab grouping
- label shortening
- rounding precision
- plot thresholds
- legend mode
- grouped-bar chip toggles

### 3. Introduce a DOM-Free Plot Dataset Module

Create a module such as `docs/eval-dashboard/assets/js/plots/data.js`.

This module should build a normalized plot dataset from:

- active experiment
- metric type
- evaluation context
- selected evaluation groups
- plot groups
- grouping fields
- active plot tab mode
- display label settings where needed for stable export labels

The dataset should be the shared input for both rendering and the future `Download data` action.

### 4. Define Pre-Aggregated Export Shapes

The exported data should represent the samples used to make the visible figures, before mean, standard deviation, or count aggregation.

For numeric bar/error metrics, use one record per evaluation and numeric metric path:

```json
{
  "metric_label": "score.mean",
  "metric_path": ["score", "mean"],
  "plot_tab": "score",
  "plot_group_id": "model=a",
  "category": "model=a",
  "series": "seed=1",
  "evaluation_run_dir": "run-a",
  "value": 0.75,
  "group_values": {
    "prediction.overrides.model": "a",
    "evaluation.overrides.seed": "1"
  }
}
```

For confusion matrices, use one record per evaluation and matrix cell. If a cell belongs to the plotted aligned label union but is absent in a specific run, represent it explicitly with value `0`.

For TP/FP/FN collectors, use one record per evaluation, document, label, and outcome state. Preserve whether each state is `tp`, `fp`, `fn`, or `empty` so the plotted counts can be reconstructed.

### 5. Move Aggregation After Dataset Creation

Refactor current aggregation helpers so rendering consumes:

- the raw plot dataset
- active tab and filter settings
- aggregated output derived from that dataset

This separates data shaping from aggregation and makes `Download data` a straightforward export of the pre-aggregated dataset.

### 6. Cache Derived Plot Data

Add a small cache for derived plot datasets. The cache key should include state that changes the underlying plotted samples:

- loaded data revision
- selected prediction group ids
- active evaluation tab
- selected evaluation group ids
- prediction group-by fields
- evaluation group-by fields
- default values that affect grouping
- metric type

View-only settings should be kept out of the heavy cache key where possible:

- active plot tab
- rounding precision
- export background
- label shortening, unless labels are stored in the dataset
- thresholds, if raw data can be cached and filtered afterward

### 7. Cache Expensive Metric-Family Sub-Results

Useful targeted caches include:

- numeric metric leaf paths per experiment and metric type
- collection views per evaluation for confusion matrices
- collection views per evaluation for TP/FP/FN collectors
- normalized TP/FP/FN collector data per evaluation and field
- resolved plot-group values after grouping and default resolution

### 8. Add Download Data

After the plot dataset model is stable, add a `Download data` button near `Download Figures`.

The export should match the same visible figure scope as `Download Figures`:

- active evaluation tab
- active plot tab
- selected prediction and evaluation groups
- active grouping mode
- active plot thresholds and filters where they determine which figure cells or points are visible

The export should not include aggregated means, standard deviations, or derived count summaries as the primary data. If useful, metadata may include the active dashboard state and field mappings needed to reconstruct the plot.

JSON is the recommended first format because confusion matrices and TP/FP/FN data are naturally structured. CSV can be added later if users need table-oriented exports.

### 9. Test Coverage

Add DOM-free JavaScript tests under `tests/unit/eval_dashboard/js/` for the new plot dataset module.

Cover:

- numeric pre-aggregated records
- confusion matrix aligned cell records, including explicit zeros
- TP/FP/FN per-evaluation records
- cache invalidation keys
- download file content and filename scope

Keep `plots.dashboard.test.mjs` focused on orchestration and button wiring.

## Recommended Implementation Order

Prefer two PR-sized steps:

1. Refactor plot data preparation and split plot rendering from full evaluation rendering. Include instrumentation and tests.
1. Add `Download data` using the new plot dataset model.

This keeps the latency-focused refactor useful even before the download button lands, and it creates a clear reusable data boundary for future plotting work.
