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

## Refactor Plan

### 1. Add Lightweight Instrumentation

The dashboard now has dev-facing timing instrumentation and a persisted Playwright benchmark. The benchmark setup, benchmark data rationale, scenario definitions, timing semantics, and interpretation caveats are documented in the [Benchmarking section of `eval-dashboard-docs.md`](../eval-dashboard-docs.md#benchmarking).

Keep instrumentation disabled by default. Enable it with the `debugTiming=1` URL query parameter and write structured timing rows to the browser console. The instrumentation should remain lightweight and testable, with timing boundaries around the main expensive stages:

- `getEvaluationContext`
- `getPlotGroups`
- metric path discovery
- collection-view construction or equivalent collection normalization
- tab-map construction
- aggregation
- SVG rendering

Use the measurements to confirm which stages dominate before making broad changes. Benchmarking should continue to load complete top-level folders through the same dashboard import path a user would use, not hand-picked subruns or reduced subsets. The two required benchmark categories are:

1. **Loading/importing:** measure how long the dashboard takes to import, normalize, and initially render the complete folder after selection.
1. **Post-load interactions:** after the complete folder has been loaded, measure latency for changes to grouping settings, active plot tabs, tab grouping modes, plot thresholds, grouped-bar controls where applicable, and other plot options.

The complete `477_faktencheck_core` and `481_faktencheck_core` folders should remain the default benchmark inputs because they exercise the highest-risk plot families: collection-view construction across many metric fields, large label-union alignment for confusion matrices, TP/FP/FN normalization across many documents and labels, tab-map rebuilding for metric-field and prediction-group modes, and large SVG matrix rendering after aggregation.

#### Benchmark Results

The following baseline was captured on 2026-06-04 in headless Chrome 149.0.7827.53 with `debugTiming=1`. The benchmark used the complete top-level folders listed in the dashboard benchmark documentation. The load wall-clock row measures from folder assignment until the dashboard is usable after initial rendering. Post-load interaction rows include Playwright wall-clock duration from action start until the next animation frame after timing-table emission; timing-table totals show the internal instrumented render work.

| Scenario                                                     | Timing table                                                                                                 |  477_faktencheck_core (Total) | 477_faktencheck_core (Wall-clock) |   481_faktencheck_core (Total) | 481_faktencheck_core (Wall-clock) |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ----------------------------: | --------------------------------: | -----------------------------: | --------------------------------: |
| complete folder load to usable dashboard                     | `eval-dashboard local folder load` + `eval-dashboard prediction render` + `eval-dashboard evaluation render` | 87.6 ms + 19.5 ms + 3683.2 ms |                         3929.7 ms | 117.7 ms + 22.7 ms + 1964.5 ms |                         2441.1 ms |
| local import processing                                      | `eval-dashboard local folder load`                                                                           |                       87.6 ms |                                 - |                       117.7 ms |                                 - |
| initial prediction render                                    | `eval-dashboard prediction render`                                                                           |                       19.5 ms |                                 - |                        22.7 ms |                                 - |
| initial evaluation/plot render                               | `eval-dashboard evaluation render`                                                                           |                     3683.2 ms |                                 - |                      1964.5 ms |                                 - |
| fresh post-load switch tab grouping to metric field          | `eval-dashboard evaluation render`                                                                           |                       14.7 ms |                           56.7 ms |                       298.6 ms |                          587.4 ms |
| fresh post-load switch active plot tab                       | `eval-dashboard plot render`                                                                                 |                     1524.6 ms |                         1616.5 ms |                       633.1 ms |                          776.1 ms |
| fresh post-load switch to metric-field `german_name` tab     | `eval-dashboard evaluation render` + `eval-dashboard plot render`                                            |           23.0 ms + 7124.0 ms |                         7256.4 ms |           140.6 ms + 5092.8 ms |                         5740.6 ms |
| fresh post-load switch to metric-field `scientific_name` tab | `eval-dashboard evaluation render` + `eval-dashboard plot render`                                            |           11.1 ms + 6794.4 ms |                         6950.8 ms |           153.7 ms + 4890.2 ms |                         5501.7 ms |
| fresh post-load set evaluation group-by to none              | `eval-dashboard evaluation render`                                                                           |                     3476.5 ms |                         3568.2 ms |                      4499.5 ms |                         5124.6 ms |
| fresh post-load deselect evaluation table row                | `eval-dashboard evaluation render`                                                                           |                     2410.3 ms |                         2531.4 ms |                      2661.7 ms |                         3091.3 ms |
| fresh post-load deselect prediction table row                | `eval-dashboard prediction render` + `eval-dashboard evaluation render`                                      |            9.6 ms + 3403.5 ms |                         3613.6 ms |            12.6 ms + 2310.5 ms |                         2752.1 ms |

Baseline-specific observations:

- The highest-latency rows are all plot-data recomputation paths, not prediction-table rendering. Even prediction-row deselection spends only a small part of its internal timing in `eval-dashboard prediction render`; the expensive work follows in evaluation and plot rendering.
- The mode switch to metric-field tabs is cheap by itself because the first selected metric-field tab is small. The expensive metric-field workflow appears when selecting `german_name` or `scientific_name`, where many plot groups each recompute large collection aggregations.
- `477_faktencheck_core` is dominated by `confusion aggregate and filter` for `taxa.german_name` and `taxa.scientific_name`.
- `481_faktencheck_core` is dominated by `tpfpfn aggregate and filter` for `taxa.scientific_name` and `taxa.german_name`, with additional visible cost in TP/FP/FN SVG rendering.

Implications:

- The immediate optimization target should be reusable plot datasets and cached collection aggregation inputs.
- Narrower render entry points should follow so table selection, plot-tab changes, and grouping controls avoid repeating plot-data work when their underlying samples have not changed.

### 2. Introduce a DOM-Free Plot Dataset Module

Create a module such as `docs/eval-dashboard/assets/js/plots/data.js`.

TODO: double-check parts below! Note that only "changing default values" should change the plot dataset, not the grouping etc. What does this imply?

This module should build a normalized plot dataset from the same state and selector-derived inputs the current plot renderer uses:

- active evaluation experiment and visualization metric type
- selected prediction groups and selected evaluation groups
- evaluation context, including experiment evaluations, evaluation tab state, evaluation group-by fields, selected evaluation group ids, and evaluation default values
- prediction grouping state, including prediction group-by fields and prediction default values used when resolving effective plot-group values
- resolved plot groups, plot-group fields, and varying plot-group fields
- metric-family source data, including numeric metric paths, confusion-matrix collection views, or TP/FP/FN collection views
- plot tab grouping mode, such as prefix/suffix tabs for bar plots and metric-field/prediction-group tabs for confusion and TP/FP/FN plots
- grouped-bar field selections for numeric plots
- display label settings where labels are stored in the dataset or exported schema

The dataset module is the internal shared data boundary. Its output should prioritize rendering reuse, cacheability, and DOM-free tests. Rendering should consume this dataset directly or through small aggregation adapters, and the future `Download data` action should derive its public file format from the same dataset instead of rebuilding plot inputs independently.

DOM dependencies and pure presentation settings should stay outside the raw dataset. Active plot tab, thresholds, rounding precision, export background, and similar view settings should be applied by downstream aggregation, filtering, rendering, or export adapters unless storing them in the dataset is required to make visible-scope export unambiguous.

This should be the next major boundary after instrumentation because the baseline shows the expensive paths are dominated by plot-data recomputation rather than table rendering.

### 3. Make Rendering Aggregation Consume the Plot Dataset

After the dataset boundary exists, refactor current plot aggregation helpers so rendering consumes:

- the raw plot dataset
- active tab and filter settings
- aggregated output derived from that dataset

This makes the dataset boundary real for rendering first, removes remaining duplicated data shaping, and makes render/export behavior easier to compare. It also keeps `Download data` from depending on a parallel data path that only resembles the rendered figures.

### 4. Define Pre-Aggregated Export Shapes

Define the public download schema produced from the internal plot dataset. This schema should prioritize inspectability, stability, and reconstructing the visible figures. It does not need to be identical to the internal dataset shape as long as it is derived from the same data boundary.

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

### 5. Add Download Data

After the plot dataset model and rendering aggregation path are stable, add a `Download data` button near `Download Figures` so the plotted data can be inspected early while the deeper latency refactor continues.

The export should match the same visible figure scope as `Download Figures`:

- active evaluation tab
- active plot tab
- selected prediction and evaluation groups
- active grouping mode
- active plot thresholds and filters where they determine which figure cells or points are visible

The export should not include aggregated means, standard deviations, or derived count summaries as the primary data. If useful, metadata may include the active dashboard state and field mappings needed to reconstruct the plot.

JSON is the recommended first format because confusion matrices and TP/FP/FN data are naturally structured. CSV can be added later if users need table-oriented exports.

### 6. Cache Expensive Metric-Family Sub-Results

Add targeted caches for repeated metric-family work before relying on narrow render entry points for latency gains.

Useful targeted caches include:

- numeric metric leaf paths per experiment and metric type
- collection views per evaluation for confusion matrices
- collection views per evaluation for TP/FP/FN collectors
- normalized TP/FP/FN collector data per evaluation and field
- resolved plot-group values after grouping and default resolution
- aggregation inputs for large collection fields such as `taxa.german_name` and `taxa.scientific_name`

### 7. Cache Derived Plot Data

Add a cache for derived plot datasets. The cache key should include state that changes the underlying plotted samples:

- loaded data revision
- selected prediction group ids
- active evaluation tab
- selected evaluation group ids
- prediction group-by fields
- evaluation group-by fields
- default values that affect grouping
- metric type

View-only settings should be kept out of the heavy raw-dataset cache key where possible:

- rounding precision
- export background
- label shortening, unless labels are stored in the dataset

Treat active plot tab and thresholds carefully. They may not change the underlying raw samples, but the benchmark shows some tab and threshold-dependent paths are expensive. Keep them out of the raw dataset cache key only if the per-tab or post-filter aggregation work is cached separately or can be derived cheaply from cached raw data.

### 8. Split Render Responsibilities

Introduce narrower render entry points after the shared plot dataset and expensive sub-result caches exist:

- `renderEvaluationShell()` for tabs, table, options, JSON pane, and summary
- `renderEvaluationPlotsOnly()` for plot controls, plot tabs, and plot content
- `renderActivePlotTabOnly()` where active-tab changes can reuse already prepared plot data and cached aggregation inputs

Plot-only controls should avoid rebuilding the evaluation table unless they affect table state. This applies to controls such as:

- plot tab grouping
- confusion tab grouping
- label shortening
- rounding precision
- plot thresholds
- legend mode
- grouped-bar chip toggles

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

1. Introduce the shared plot dataset model, make rendering aggregation consume it, and add `Download data` for early inspection. Include focused tests for export shape and visible-scope matching.
1. Add targeted caches and split plot rendering from full evaluation rendering. Use the existing benchmark and instrumentation to compare before/after latency.

This makes plotted-data inspection available early, while the second slice can focus on measurable latency improvements using the same reusable data boundary.
