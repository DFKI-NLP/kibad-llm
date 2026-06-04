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

### Benchmark Methodology

The persisted benchmark lives in `docs/eval-dashboard/benchmark/`. It is a manual Playwright benchmark, not a CI gate. It starts a local static server for `docs/eval-dashboard`, opens the dashboard with `debugTiming=1`, loads local folders through the browser file-input path, records dashboard console timing tables, records wall-clock interaction durations, and writes a JSON report.

Each default benchmark folder is loaded as a complete top-level folder. The browser receives the folder files through Playwright's file input support with browser-relative paths preserved, so local import processing follows the same dashboard code path as a user selecting the folder. The benchmark does not measure native OS file-picker overhead, user think time, browser-cache variability across different manual sessions, or visual perception beyond waiting for one animation frame after the dashboard emits the expected timing table.

The benchmark records two timing concepts:

- **Timing table total:** the sum of instrumented, non-overlapping dashboard timing rows emitted for a render or load phase. These rows are useful for diagnosing which dashboard stages dominate.
- **Wall-clock:** elapsed browser `performance.now()` time from the benchmark action start until the next animation frame after the relevant timing table has been emitted. This better approximates interaction latency but can include event dispatch, layout, paint, and uninstrumented work.

The current scenarios measure:

- `local import processing`: local file collection, run ingestion, canonical state updates, derived prediction state reset, and load-status rendering for the complete folder.
- `initial prediction render`: the first prediction-table render after import, including prediction selectors, controls, table rendering, and sticky-column offset work.
- `initial evaluation/plot render`: the first evaluation render after import, including evaluation selection/grouping, evaluation controls/table/JSON pane, plot controls, active plot-tab data preparation, aggregation, and SVG rendering.
- `fresh post-load switch tab grouping to metric field`: on a freshly loaded page, click the confusion/TP-FP-FN tab-grouping control from prediction-group mode to metric-field mode. This resets the active plot tab and renders the first metric-field tab selected by the dashboard, which is usually a small field. It measures the mode switch itself, not the worst metric-field tab.
- `fresh post-load switch active plot tab`: on a freshly loaded page in the default tab mode, click the first inactive plot tab. This measures changing between prediction-group tabs, with the target tab determined by current tab ordering.
- `fresh post-load switch to metric-field german_name tab`: on a freshly loaded page, switch to metric-field mode, then click the `german_name` metric-field tab. This measures the complete user workflow needed to reach that large metric-field tab. The scenario emits one timing table for the mode switch and one timing table for the target-tab render.
- `fresh post-load switch to metric-field scientific_name tab`: same as the `german_name` scenario, but targets `scientific_name`.
- `fresh post-load set evaluation group-by to none`: on a freshly loaded page, click the evaluation group-by `none` control. This changes evaluation grouping and forces a full evaluation and plot render while the expensive default plot tab is still active.
- `fresh post-load deselect evaluation table row`: on a freshly loaded page, click the first selected evaluation-group checkbox. This changes selected evaluation groups and forces a full evaluation and plot render while the expensive default plot tab is still active.
- `fresh post-load deselect prediction table row`: on a freshly loaded page, click the first selected prediction-group checkbox. This first renders the prediction table, then renders evaluations and plots because selected evaluations depend on selected predictions.

The post-load scenarios are intentionally isolated from each other. Each scenario reloads the complete folder into a fresh page before performing its interaction. This avoids hidden interdependencies where an earlier cheapening action, such as switching to a smaller plot tab or changing grouping, would make later scenarios look faster than the corresponding manual workflow immediately after loading.

Important interpretation details:

- The exact active plot tab matters. Large fields such as `german_name` and `scientific_name` are much more expensive than small fields such as `biodiversity_level`.
- Some scenarios intentionally produce multiple timing tables. For example, prediction-row deselection emits prediction render timing and evaluation render timing; metric-field target-tab scenarios emit the mode-switch render and the target-tab render.
- Timing table totals should not be compared to wall-clock numbers as if they measured the same thing. Timing table totals are diagnostic; wall-clock values are closer to user-perceived latency.
- The benchmark captures only the current default viewport, browser channel, and tab ordering. Changes to viewport size, active tab defaults, plot-tab sorting, or selected data can materially change scenario cost.
- The benchmark currently focuses on confusion-matrix and TP/FP/FN collection workflows. Numeric bar/error plot workflows should get their own representative data and scenarios before using this benchmark to reason about them.

### Initial Baseline

The following baseline was captured on 2026-06-04 in headless Chrome 149 with `debugTiming=1`. The benchmark used the complete top-level folders listed above. It injected all relevant folder files into the dashboard as browser `File` objects with their `webkitRelativePath` values preserved, so it measures dashboard import processing and rendering work but not native OS file-picker overhead. Post-load interaction rows include Playwright wall-clock duration from action start until the next animation frame after timing-table emission; timing-table totals show the internal instrumented render work. Each post-load interaction scenario is measured on a fresh post-load page before changing plot tab or grouping state.

| Scenario | Timing table | 477_faktencheck_core (Total) | 477_faktencheck_core (Wall-clock) | 481_faktencheck_core (Total) | 481_faktencheck_core (Wall-clock) |
| --- | --- | ---: | ---: | ---: | ---: |
| local import processing | `eval-dashboard local folder load` | 36.0 ms | - | 70.8 ms | - |
| initial prediction render | `eval-dashboard prediction render` | 11.4 ms | - | 13.5 ms | - |
| initial evaluation/plot render | `eval-dashboard evaluation render` | 1584.3 ms | - | 1365.2 ms | - |
| fresh post-load switch tab grouping to metric field | `eval-dashboard evaluation render` | 5.9 ms | 34.0 ms | 99.9 ms | 236.9 ms |
| fresh post-load switch active plot tab | `eval-dashboard plot render` | 463.2 ms | 499.1 ms | 407.9 ms | 505.7 ms |
| fresh post-load switch to metric-field `german_name` tab | `eval-dashboard evaluation render` + `eval-dashboard plot render` | 5.6 ms + 3384.2 ms | 3455.6 ms | 93.4 ms + 2603.7 ms | 3007.4 ms |
| fresh post-load switch to metric-field `scientific_name` tab | `eval-dashboard evaluation render` + `eval-dashboard plot render` | 5.4 ms + 3471.3 ms | 3546.7 ms | 94.2 ms + 2771.8 ms | 3137.8 ms |
| fresh post-load set evaluation group-by to none | `eval-dashboard evaluation render` | 1662.9 ms | 1736.5 ms | 1137.8 ms | 1325.0 ms |
| fresh post-load deselect evaluation table row | `eval-dashboard evaluation render` | 1649.4 ms | 1737.3 ms | 1295.7 ms | 1587.8 ms |
| fresh post-load deselect prediction table row | `eval-dashboard prediction render` + `eval-dashboard evaluation render` | 5.1 ms + 1643.7 ms | 1743.0 ms | 7.5 ms + 1340.1 ms | 1662.6 ms |

Baseline-specific observations:

- The highest-latency rows are all plot-data recomputation paths, not prediction-table rendering. Even prediction-row deselection spends only a small part of its internal timing in `eval-dashboard prediction render`; the expensive work follows in evaluation and plot rendering.
- The mode switch to metric-field tabs is cheap by itself because the first selected metric-field tab is small. The expensive metric-field workflow appears when selecting `german_name` or `scientific_name`, where many plot groups each recompute large collection aggregations.
- `477_faktencheck_core` is dominated by `confusion aggregate and filter` for `taxa.german_name` and `taxa.scientific_name`.
- `481_faktencheck_core` is dominated by `tpfpfn aggregate and filter` for `taxa.scientific_name` and `taxa.german_name`, with additional visible cost in TP/FP/FN SVG rendering.

Implications:

- The immediate optimization target should be reusable plot datasets and cached collection aggregation inputs.
- Narrower render entry points should follow so table selection, plot-tab changes, and grouping controls avoid repeating plot-data work when their underlying samples have not changed.

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

Keep instrumentation dev-facing and disabled by default. Enable it with the `debugTiming=1` URL query parameter and write structured timing rows to the browser console.

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
