# Eval Dashboard Plot Data Flow Plan

This plan captures the current plotting data flow, the implemented download-data work, and the staged refactor path for the remaining goals:

- reduce latency when changing grouping, plot tabs, or plot options
- keep `Download Data` derived from the exact pre-aggregation inputs used by the downloadable figures
- clarify plot-family orchestration without introducing a universal renderer
- make one selected plot, rather than every card in an active tab, the eventual unit of expensive preparation and rendering

The plan follows the repository guidance in `CONTRIBUTING_CODE.md`: related refactors are acceptable when they clarify responsibilities and provide concrete long-term value, and dashboard logic should stay DOM-free where practical with focused JavaScript tests.

## Current Flow

The plotting path is currently driven from `docs/eval-dashboard/assets/js/main.js`.

1. `main.js` owns the singleton dashboard state and calls `renderEvaluations()` for most evaluation and plot setting changes.

1. `renderEvaluations()` rebuilds evaluation tabs, table, JSON pane, options, summary, and then calls `renderEvaluationPlots()`.

1. `renderEvaluationPlots()` delegates to `renderEvaluationPlotsForDashboard()` in `plots/dashboard.js`.

1. `renderEvaluationPlotsForDashboard()` recomputes selected groups, metric type, plot groups, varying group fields, tab maps, aggregations, and then redraws SVG figures.

1. Metric-specific aggregation happens in the plot modules:

    - numeric bar/error metrics discover lightweight definitions with `buildNumericPlotDefinitions()`, prepare active-tab samples with `buildNumericPlotEntriesInput()`, and aggregate those samples with `getNumericPlotEntriesFromInput()` in `plots/bars.js`
    - confusion matrices use collection views, `getConfusionMatrixAggregationInput()`, and `getConfusionMatrixAggregationFromInput()` in `plots/confusion.js`
    - TP/FP/FN collectors use collection views, `getTpFpFnAggregationInput()`, and `getTpFpFnAggregationFromInput()` in `plots/tpfpfn.js`

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

Active plot-tab clicks already avoid the full table render, but they still rebuild tab maps and prepare, aggregate, and render every plot card in the active tab. Other plot-only controls still call the full `renderEvaluations()` path.

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

- These measurements justify the per-evaluation preparation cache in step 2 as the first optimization because it removes repeated collector normalization and sparse-map construction without requiring a new lifecycle.
- The broader reusable plot-data boundary should remain deferred until active-tab orchestration, active-plot selection, and narrower render entry points establish the intended unit of work. Those lifecycle changes should prevent plot-tab and plot-only controls from repeating unrelated work before higher-level caches are added.

### 2. Cache Per-Evaluation Metric Preparation

Implemented on 2026-06-04 as a targeted cache before introducing the broader plot dataset boundary.

`getConfusionMatrixAggregationInput()` separates the work done for one selected evaluation from the later cross-run aggregation. For each evaluation and normalized `metric.field`, the helper lazily prepares:

- the row-label set observed in that evaluation
- the column-label set observed in that evaluation
- the sparse cell lookup keyed by `${actual}|#|${predicted}`

The prepared result is stored at `evaluation.dataPrepared[fieldLabel]`. When the aggregator receives a collection view, the cache is stored on the wrapped raw evaluation object instead of the temporary collection-view wrapper, so it can be reused after tab maps and collection views are rebuilt. `dataPrepared` is defined as a non-enumerable, null-prototype object to avoid changing normal object iteration or JSON serialization and to keep prototype-named metric fields safe.

`getTpFpFnAggregationInput()` uses the same pattern. For each evaluation and normalized `metric.field`, the helper lazily prepares:

- the document-label row set
- the label column set
- the sparse outcome lookup keyed by `${documentId}|#|${label}`, whose values are `"tp"`, `"fp"`, or `"fn"`

The prepared result is stored at `evaluation.dataPrepared[fieldLabel]`, again preferring the wrapped raw evaluation object for collection views.

The shared bar/error plotting path now uses the same preparation model for numeric metric data. For each evaluation, `prepareNumericMetricEvaluationData()` lazily prepares:

- the numeric metric path metadata
- the flat numeric value lookup keyed by the encoded metric path

The prepared result is stored at `evaluation.dataPrepared.numericMetrics`. `buildNumericPlotDefinitions()` discovers the metric-path union from the evaluations in the selected plot groups. After the definitions are organized into tabs, `buildNumericPlotEntriesInput()` reads the same prepared values for the active definitions and builds aligned, pre-aggregation samples. Missing numeric paths follow an explicit metric-type contract: sparse `ErrorCollector` counters default to zero, while metric types without a declared missing-value default fail loudly. Numeric leaves must be finite; nonnumeric content is not discovered as numeric metric data. Each point carries JSON-friendly `samples` as compact numeric value arrays, which the `Download data` action can expose directly without render-helper metadata.

Cross-run alignment, mean/std calculation, TP/FP/FN outcome counting, and threshold filtering still run per active plot. The numeric definition and pre-aggregation APIs receive definitions and selected plot groups from the same render pass, keeping metric discovery and sample construction tied to the same evaluation population while preparing samples only for the active tab. The cache only removes repeated per-evaluation field extraction, numeric metric-data walks, confusion sparse-map construction, and TP/FP/FN collector normalization/state-map construction.

Focused DOM-free tests cover both cache paths:

- confusion aggregation stores prepared field data on the source evaluation
- TP/FP/FN aggregation stores prepared field data on the source evaluation
- confusion and TP/FP/FN aggregation normalize existing plain `dataPrepared` containers before caching prototype-named fields
- numeric bar/error helpers store prepared metric paths and values on the source evaluation and expose per-point samples

#### Benchmark Results After Per-Evaluation Preparation Cache

The following benchmark was captured on 2026-06-04 in headless Chrome 149.0.7827.53 with `debugTiming=1`, using the same complete top-level folders and benchmark scenarios as the baseline. Delta columns compare current wall-clock duration against the baseline table above; negative values are faster.

| Scenario                                                     | Timing table                                                                                                 |  477_faktencheck_core (Total) | 477_faktencheck_core (Wall-clock, delta) |  481_faktencheck_core (Total) | 481_faktencheck_core (Wall-clock, delta) |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ----------------------------: | ---------------------------------------: | ----------------------------: | ---------------------------------------: |
| complete folder load to usable dashboard                     | `eval-dashboard local folder load` + `eval-dashboard prediction render` + `eval-dashboard evaluation render` | 45.6 ms + 11.0 ms + 1615.0 ms |                   1745.0 ms (-2184.7 ms) | 72.6 ms + 17.6 ms + 1310.5 ms |                    1628.4 ms (-812.7 ms) |
| local import processing                                      | `eval-dashboard local folder load`                                                                           |                       45.6 ms |                                        - |                       72.6 ms |                                        - |
| initial prediction render                                    | `eval-dashboard prediction render`                                                                           |                       11.0 ms |                                        - |                       17.6 ms |                                        - |
| initial evaluation/plot render                               | `eval-dashboard evaluation render`                                                                           |                     1615.0 ms |                                        - |                     1310.5 ms |                                        - |
| fresh post-load switch tab grouping to metric field          | `eval-dashboard evaluation render`                                                                           |                       31.3 ms |                      118.3 ms (+61.6 ms) |                       88.6 ms |                     194.2 ms (-393.2 ms) |
| fresh post-load switch active plot tab                       | `eval-dashboard plot render`                                                                                 |                      537.3 ms |                    586.9 ms (-1029.6 ms) |                      371.9 ms |                     487.4 ms (-288.7 ms) |
| fresh post-load switch to metric-field `german_name` tab     | `eval-dashboard evaluation render` + `eval-dashboard plot render`                                            |            7.2 ms + 3504.4 ms |                   3573.9 ms (-3682.5 ms) |           91.4 ms + 2340.7 ms |                   2736.0 ms (-3004.6 ms) |
| fresh post-load switch to metric-field `scientific_name` tab | `eval-dashboard evaluation render` + `eval-dashboard plot render`                                            |           10.3 ms + 3665.5 ms |                   3737.4 ms (-3213.4 ms) |           87.8 ms + 2675.0 ms |                   3022.1 ms (-2479.6 ms) |
| fresh post-load set evaluation group-by to none              | `eval-dashboard evaluation render`                                                                           |                     1533.5 ms |                   1579.8 ms (-1988.4 ms) |                     1265.1 ms |                   1473.0 ms (-3651.6 ms) |
| fresh post-load deselect evaluation table row                | `eval-dashboard evaluation render`                                                                           |                     1553.4 ms |                    1654.8 ms (-876.6 ms) |                     1200.8 ms |                   1465.1 ms (-1626.2 ms) |
| fresh post-load deselect prediction table row                | `eval-dashboard prediction render` + `eval-dashboard evaluation render`                                      |            5.2 ms + 1576.9 ms |                   1667.3 ms (-1946.3 ms) |            6.4 ms + 1192.0 ms |                   1486.2 ms (-1265.9 ms) |

A same-day sanity rerun after flattening field caches to `evaluation.dataPrepared[fieldLabel]` and normalizing existing `dataPrepared` containers produced the same overall result: every wall-clock scenario remained faster than the original baseline, with ordinary browser-timing variance across individual rows.

Observations after the cache:

- The cache materially improves the expensive metric-field workflows. Switching to `german_name` dropped from 7256.4 ms to 3573.9 ms for `477_faktencheck_core` and from 5740.6 ms to 2736.0 ms for `481_faktencheck_core`. Switching to `scientific_name` dropped from 6950.8 ms to 3737.4 ms for `477_faktencheck_core` and from 5501.7 ms to 3022.1 ms for `481_faktencheck_core`.
- Initial evaluation/plot rendering also improved because later plots in the same render can reuse prepared per-evaluation field data. `477_faktencheck_core` dropped from 3683.2 ms to 1615.0 ms internally, and `481_faktencheck_core` dropped from 1964.5 ms to 1310.5 ms internally.
- Active plot-tab switching improved substantially, but it still spends hundreds of milliseconds in aggregation and filtering because cross-run alignment and final cell aggregation are still recomputed.
- The `477_faktencheck_core` tab-grouping switch to metric-field was slower in this run than the baseline. This scenario is small enough that browser variance and the extra cache bookkeeping can dominate; it is not the main latency target.
- The slowest stages remain `confusion aggregate and filter` for `taxa.german_name` / `taxa.scientific_name` and `tpfpfn aggregate and filter` for the same large fields, but their per-field costs are lower than the baseline.

Implications after the cache:

- The per-evaluation preparation cache is worth keeping because it directly reduces repeated normalization/sparse-map work while preserving existing aggregation behavior.
- Further latency gains need a higher-level cache for full active plot aggregation or a plot dataset boundary that stores pre-aggregated exportable records. The remaining cost is now mostly cross-run alignment, threshold filtering, and SVG rendering rather than raw collector normalization alone.
- Narrower render entry points are still important. Table-row deselection and grouping changes are faster than baseline, but they still invoke evaluation rendering and active plot aggregation.
- Because the cache mutates evaluation objects with non-enumerable prepared data, future data-revision handling should clear or replace loaded evaluation objects on import rather than trying to reuse stale prepared caches across datasets.

### 3. Add Active Plot Download Payloads

Implemented on 2026-06-04 as an incremental export path before the broader plot dataset module.

The dashboard now keeps the active plot tab's download source in `state.activePlotDownloadData` while rendering the same figures. This state is intentionally not the final public JSON payload: each plot stores allowlisted `metadata` plus an internal `dataSource` object. The family-owned `buildNumericDownloadMetadata()` and `buildMatrixDownloadMetadata()` helpers define the public metadata fields, while `buildDownloadPlotMetadata()` provides the common dispatch interface. A `Download Data` button next to `Download Figures` converts that active source into the public JSON payload in `downloadActivePlotData()` and serializes it as pretty-printed JSON. The button is disabled when no active plot source exists and shows the number of downloadable plots for the active tab.

The export is intentionally built from the same plot data path used for rendering:

- numeric bar/error plots use `buildNumericPlotDefinitions()` to discover lightweight metric definitions, organize those definitions into tabs, and resolve the active tab before `buildNumericPlotEntriesInput()` constructs grouped samples. Rendering adds mean/std with `getNumericPlotEntriesFromInput()`, while download data retains the same active tab's sample-only input entries
- confusion matrices use `getConfusionMatrixAggregationInput()` for the shared rows, columns, and per-evaluation cell maps; rendering aggregates and threshold-filters that input with `getConfusionMatrixAggregationFromInput()`, while download data intentionally exports the unfiltered pre-aggregation input
- TP/FP/FN matrices use `getTpFpFnAggregationInput()` for the shared rows, columns, and per-evaluation outcome maps; rendering aggregates and threshold-filters that input with `getTpFpFnAggregationFromInput()`, while download data intentionally exports the unfiltered pre-aggregation input

The internal `state.activePlotDownloadData` source uses a small common envelope:

- `metric_family`
- `plot_tab`
- `plot_tab_variant`
- `plots`, each with `metadata` and `dataSource`

`downloadActivePlotData()` turns that source into the public JSON envelope:

- `metric_family`
- `plot_tab`
- `plot_tab_variant`
- `plots`, each with `metadata` and JSON-safe `data`

Experiment, metric type, threshold, and other view state stay outside this envelope unless a later user need requires that metadata in the downloaded JSON.

The current numeric shape stays close to the bar/error plotting data. It exports one plot entry per metric and keeps raw evaluation samples nested under each plotted point:

```json
{
  "metric_family": "numeric",
  "plot_tab": "score",
  "plot_tab_variant": "prefix",
  "plots": [
    {
      "metadata": {
        "metric_label": "score.mean"
      },
      "data": {
        "points": [
          {
            "category": "model=a",
            "display_category": "Model A",
            "series": "seed=1",
            "display_series": "Seed 1",
            "run_dirs": ["run-a", "run-b"],
            "samples": [0.75, 0.81]
          }
        ]
      }
    }
  ]
}
```

Matrix-like exports use the same envelope, but keep matrix metadata in `metadata` and aligned pre-aggregation cells in `data`:

```json
{
  "metric_family": "confusion_matrix",
  "plot_tab": "taxa.german_name",
  "plot_tab_variant": "metric_field",
  "plots": [
    {
      "metadata": {
        "label": "model=a",
        "field_label": "taxa.german_name"
      },
      "data": {
        "rows": ["Birke", "Eiche"],
        "columns": ["Birke", "UNDETECTED"],
        "run_dirs": ["run-a", "run-b"],
        "cells": [
          [
            ["Birke|#|Birke", 12],
            ["Eiche|#|UNDETECTED", 1]
          ],
          [
            ["Birke|#|Birke", 10]
          ]
        ]
      }
    }
  ]
}
```

Numeric exports embed metadata in `metadata` and sample-only pre-aggregation data in `data.points`. Each point keeps public `run_dirs` parallel to `samples`, so `run_dirs[i]` identifies the evaluation that produced `samples[i]`. During rendering, `buildNumericPlotDefinitions()` discovers metric identity for all selected evaluations, tabs are built from those lightweight definitions, and only active-tab definitions are converted to sample-only `buildNumericPlotEntriesInput()` entries. Those entries become `dataSource`; `downloadActivePlotData()` converts them with `buildJsonSafeNumericPlottingData()`.

Confusion-matrix exports use one plot object per visible heatmap. Matrix `run_dirs` stay parallel to `cells`, so `run_dirs[i]` identifies `cells[i]`. During rendering, each source plot embeds allowlisted `metadata` without `collections` and keeps the raw `getConfusionMatrixAggregationInput()` result as `dataSource`. On download, `buildJsonSafeMatrixPlottingData()` converts each sparse cell `Map` to an array of `[cellKey, value]` pairs because JSON does not serialize `Map` entries.

TP/FP/FN exports use the same matrix alignment contract. `getTpFpFnAggregationInput()` carries internal `runDirs` for both downloads and cell tooltip/copy summaries, preserving the original run identity for every outcome. Each sparse cell value is exactly one of `"tp"`, `"fp"`, or `"fn"`; a missing entry represents `empty`. On download, `buildJsonSafeMatrixPlottingData()` converts each sparse outcome `Map` to an array of `[cellKey, outcome]` pairs.

Matrix download data intentionally remains pre-filter and sparse:

- Threshold controls determine the rendered matrix cells, but the JSON keeps the full aligned aggregation input for the active plot. This preserves the raw material needed to recompute alternative thresholds without re-exporting.
- Matrix row and column labels may not contain the reserved `|#|` delimiter used by sparse cell keys. This is validated once during per-evaluation preparation so aggregation and rendering can construct keys without repeated checks.
- Missing sparse confusion entries mean `0` for that evaluation/cell when aggregating.
- Missing sparse TP/FP/FN entries mean the evaluation/cell has no TP, FP, or FN state and is counted as `empty` during aggregation.

Focused tests cover the new path:

- shared confusion and TP/FP/FN aggregation-input helpers
- dashboard button state for active plot data
- click-time conversion, JSON serialization, unsupported metric-family rejection, and filename generation in `downloadActivePlotData()`
- active plot sources populated by the bar/error, confusion, and TP/FP/FN render branches

Observations:

- Rendering stores the active download sources without converting them to JSON-safe arrays. This avoids `Map` and point-array conversion for users who never click `Download Data`.
- The click path performs JSON-safe conversion from the active `dataSource` values and then serializes the public payload.
- The exported numeric samples are nested where plotting keeps them, rather than flattened into separate records. This keeps the JSON close to the rendered point structure and avoids including `mean` or `std`.
- Matrix exports intentionally do not apply threshold-filtered visible rows and columns; thresholds are a render-time view over the exported pre-aggregation input.

Implications:

- The implemented button gives immediate inspectability while the broader plot dataset boundary remains future work.
- The public JSON schema is now an active contract covered by unit tests. Future dataset refactors should preserve the current visible-scope behavior or update the schema deliberately.
- Full-figure export parity is still scoped to the active plot tab, matching `Download Figures`; broader multi-tab or CSV exports can be considered separately.

TODO:

- [x] cleanup download data:
    - [x] remove duplicate matrix `fieldLabel` from `data`; keep it only in `metadata`
    - [x] numeric data has
        - [x] remove redundant `parts`, `prefix`, and `suffix` from `metadata`
        - [x] `metricLabel` and `metricPath` in each sample, which are also redundant with the plot entry and with each other
        - [x] remove `runDir` from each sample
- [x] (P1) add aligned run directories to plot data: numeric points keep `runDirs` parallel to `samples`; matrix plots keep `runDirs` parallel to `cells`.
- [x] optimization: call buildJsonSafeMatrixPlottingData / buildJsonSafeNumericPlottingData in downloadActivePlotData instead of during rendering in dashboard.js
- [x] (P0) restore TP/FP/FN cell-summary run directories by carrying `runDirs` through the shared aggregation input and reusing them for tooltip/copy payloads.
    - [x] Keep only counts and `presentCount` in aggregated cells. Preserve source `cells` on the aggregation input and reconstruct one cell's aligned outcomes only on click.
- [x] (P1) add `"plot_tab_variant"` (values: `"prefix"`, `"suffix"`, `"error_section"`, `"metric_field"`, or `"prediction_group"`) to root level download data so downstream consumers can disambiguate grouping modes without guessing from the plot tab name. Prediction-group downloads expose the raw group ID as `"plot_tab"` instead of the internal tab-map key.
- [x] (P2) use consistent snake_case keys in downloaded plot data and rename internal matrix input `evaluationCells` to `cells`.
- [x] (P1) align numeric and matrix preparation around a definition-first pipeline: build tabs from lightweight plot definitions, resolve the active tab, and prepare numeric samples only for active definitions.
- [ ] (P2, current PR) Unify plot-family orchestration around a shared active-tab contract without changing visible behavior or download scope.
    - [ ] Make every family follow the same explicit sequence: build lightweight definitions and tabs, order tabs, resolve the active tab once, prepare only definitions in that active tab, aggregate/filter prepared inputs, render cards, and construct downloads from those same inputs.
    - [ ] Introduce a small DOM-free active-tab result, for example `{orderedKeys, activeKey, activeTab}`, rather than adding a normalized all-family prepared-data model.
    - [ ] Extract small concrete helpers for rendering precomputed tab-button models, appending empty states, creating plot cards/grids, and constructing lazy active-tab download envelopes.
    - [ ] Remove the numeric-only orchestration ownership from `renderBarPlotTabsAndGrid()` and make numeric, confusion, and TP/FP/FN branches use the same lifecycle helpers. Family modules should continue to own preparation, aggregation, filtering, sorting details, titles, legends, and SVG rendering.
    - [ ] Keep JSON-safe conversion on the download click path. Rendering should retain references to the exact active-tab pre-aggregation inputs and must not eagerly convert `Map` or point data.
    - [ ] Preserve current matrix empty-state behavior: a plot filtered to no visible rows or columns is neither rendered nor included in the active download envelope.
    - [ ] Do not prepare, aggregate, filter, create cards, or build download inputs for inactive tabs. Add focused call-count or sentinel tests that fail if inactive-tab preparation occurs.
    - [ ] Avoid a universal callback-heavy renderer, a rigid cross-family prepared-plot schema, caches tied to complete active-tab arrays, or APIs that make rendering every active-tab plot a permanent requirement.
    - [ ] Keep this step compatible with a later `active tab -> active plot` extension. The card/grid helper may later render one card, but active-tab resolution and shared lifecycle ownership should remain reusable.
    - [ ] Verify with the complete eval-dashboard JavaScript test suite and dashboard-specific Python tests. Use the benchmark as a regression check for confusion and TP/FP/FN paths; do not claim numeric timing improvements until representative numeric benchmark scenarios exist.

The current PR should end after this orchestration cleanup. It completes the download-data feature and its related plot-module cleanup without mixing in the larger behavior and render-lifecycle changes below.

### 4. Make One Plot the Active Unit of Work

In the next PR, deliberately relax the current active-tab-wide rendering behavior. An active tab can currently contain many expensive plot definitions:

- a matrix metric-field tab contains one matrix per prediction group
- a matrix prediction-group tab contains one matrix per metric field
- a numeric tab contains one card per metric path

Today every definition in the active tab is prepared, aggregated, filtered, rendered as SVG, and included in downloads. Replace that with a two-level selection contract:

```text
plot family
  -> active tab
    -> active plot
```

Required behavior changes:

- Show one selected plot card at a time instead of rendering the complete active-tab grid.
- Expose the other plot definitions through a lightweight secondary tab row, selector, or equivalent control.
- Resolve the active plot after resolving the active tab and before expensive preparation.
- Give every plot definition a stable key derived from raw family identifiers, never display labels. Numeric plot keys should use the encoded metric path; matrix plot keys should use the raw prediction-group id when choosing among groups and the normalized raw metric field when choosing among fields.
- Retain active-plot selection per evaluation experiment, metric family, tab variant, and raw tab key rather than in one global value. Changing grouping mode therefore enters a separate selection context; returning to a previously visited family/tab context restores its prior plot when that key still exists.
- When a stored key is absent, select the first plot in the family's deterministic definition order and persist that fallback for the current context.
- Prepare, aggregate, filter, and render only the active plot definition.
- Scope `Download Figures` and `Download Data` to the selected active plot.
- Keep access to every existing plot; this is a presentation and work-scheduling change, not removal of a plot mode.
- If matrix thresholds filter the selected plot to no visible rows or columns, show that plot's empty state and do not search or prepare later plots. Keep `Download Data` enabled for the selected plot's pre-filter input, but disable `Download Figures` because no SVG was rendered.

The resulting shared lifecycle should be:

1. Build lightweight family definitions.
1. Group and order definitions into tabs.
1. Resolve the active tab.
1. Build lightweight plot choices for that tab.
1. Resolve the active plot.
1. Prepare its pre-aggregation input.
1. Aggregate and apply view filters.
1. Render one card.
1. Store one lazy download source derived from the same preparation input.

This bounds aggregation, SVG creation, adaptive layout, event-listener creation, DOM size, and download state to one plot. It also turns the current active-tab contract into a reusable foundation instead of replacing it.

As part of this behavior change, evaluate changing the default matrix grouping from `prediction_group` to `metric_field`. The benchmark datasets often make metric-field mode cheaper on initial render, but this is data-dependent and should be benchmarked rather than assumed. Keep both grouping modes unless there is a separate product decision to remove one.

### 5. Split Plot Rendering From Evaluation Rendering

Several plot-only controls currently call `renderEvaluations()`, which rebuilds evaluation tabs, defaults, options, table rows, JSON pane, sticky-column offsets, summary text, plot groups, and plots. These include numeric prefix/suffix grouping, matrix metric-field/prediction-group grouping, label shortening, rounding precision, matrix thresholds, and legend mode.

Active plot-tab clicks and grouped-bar chip toggles already call `renderEvaluationPlots()` rather than rebuilding the evaluation table, but they still rebuild tab maps and excessive active-tab plot work. Introduce explicit render entry points and route both categories to the narrowest valid one:

- `renderEvaluationShell()` for evaluation tabs, defaults, table, JSON pane, sticky offsets, and summary
- `renderEvaluationPlotsOnly()` for plot controls and lightweight tab/plot definition selection
- `renderActivePlotOnly()` for active-plot preparation, aggregation, filtering, SVG rendering, legends, and download state

Controls that currently trigger a full evaluation render must stop rebuilding the evaluation table:

- numeric prefix/suffix grouping
- matrix metric-field/prediction-group grouping
- label shortening
- rounding precision
- confusion and TP/FP/FN thresholds
- legend mode

Controls that are already plot-only must use the narrower active-tab or active-plot path instead of recomputing all plot orchestration:

- active plot tab
- grouped-bar chip toggles

The new active plot selection introduced in step 4 must call `renderActivePlotOnly()` directly.

Use explicit render completion to update both download buttons and remove the plot-content `MutationObserver`. This makes button state part of the render lifecycle instead of an indirect DOM side effect.

This split does not require a visible behavior change beyond the active-plot selection introduced in step 4, but it is a major architectural and interaction-latency improvement.

### 6. Introduce the Smallest Useful DOM-Free Plot Data Boundary

Do not start with a universal normalized dataset for all families. After active-plot selection and narrow render entry points establish the real unit of work, extract the smallest DOM-free models needed for reuse and caching:

- a lightweight plot-definition index for tabs and active-plot choices
- the active plot's family-owned pre-aggregation input
- optional cached active-plot aggregation output
- the lazy download source referencing the same pre-aggregation input

The boundary should include state that changes definitions or underlying samples:

- loaded data revision
- active evaluation experiment and metric family
- selected prediction and evaluation group ids
- prediction and evaluation group-by fields
- effective defaults that affect grouping
- numeric grouped-bar field selections where they change point construction
- plot-tab grouping mode where it changes definition organization

Keep presentation-only state outside the heavy preparation key:

- rounding precision
- export background
- legend placement
- label shortening where raw labels remain available

Thresholds should not invalidate pre-aggregation input. Cache filtered or aggregated views separately only if measurement shows that this is useful and invalidation remains clear.

Rendering and downloads must consume this boundary directly. Do not create a parallel export-only reconstruction path.

### 7. Add Targeted Higher-Level Caches

Retain the implemented per-evaluation preparation caches. Add higher-level caches only around measured repeated work:

- lightweight numeric definition indexes per selected data population
- matrix collection-view/definition indexes
- resolved plot-group values after grouping and default resolution
- active-plot aggregation inputs for large fields such as `taxa.german_name` and `taxa.scientific_name`
- active-plot aggregation output when only rounding, labels, legends, or export settings change

Cache keys must be explicit and testable. They should include the data and grouping state that changes samples, and exclude view-only state whenever possible. Loaded evaluation objects should be replaced or their prepared caches cleared on data revision; stale caches must not survive imports.

Do not cache complete active-tab arrays merely because the current UI once rendered all cards. The active plot is the intended expensive-work and cache unit.

### 8. Revisit Export Scope and Schema Deliberately

The current public JSON schema is an active contract. Step 4 intentionally changes visible/download scope from all cards in the active tab to one active plot. Update tests and documentation deliberately when making that change.

Continue to export pre-aggregation data:

- numeric points retain aligned `samples` and `run_dirs`
- confusion matrices retain aligned sparse per-evaluation cells, with missing entries interpreted as zero
- TP/FP/FN matrices retain aligned sparse per-evaluation outcomes, with missing entries interpreted as empty

Do not add aggregated means, standard deviations, or derived count summaries as the primary payload. Keep JSON as the structured format; add CSV only in response to a concrete downstream need.

Changing the download envelope from a `plots` array to a singular plot object may simplify the new contract, but it is optional. A one-element `plots` array may be retained to reduce schema churn if it remains clear.

### 9. Test and Benchmark the New Lifecycle

Keep `plots.dashboard.test.mjs` focused on orchestration and button wiring. Add DOM-free tests for:

- active-tab fallback and active-plot fallback
- stable raw plot keys and per-experiment/family/tab selection retention across grouping-mode transitions
- inactive tabs and inactive plots never invoking expensive preparation
- one active plot producing one render card and one matching download source
- filtered-empty matrix plots retaining pre-filter download data while producing no figure download
- plot-only controls avoiding evaluation-table rendering
- cache-key invalidation and reuse
- explicit download-button lifecycle updates
- public download content and filename scope after the active-plot behavior change

Run:

- `node --test tests/unit/eval_dashboard/js/*.test.mjs`
- `uv run --group cicd pytest tests/unit/eval_dashboard`
- the repository checks required by `CONTRIBUTING.md` before claiming CI readiness

Extend the persisted benchmark with:

- active plot selection inside one tab
- threshold, rounding, and label-only changes
- representative numeric bar/error fixtures and scenarios

Compare both timing-table totals and wall-clock latency. The key acceptance condition is that active-plot and plot-only interactions no longer perform inactive-plot aggregation or evaluation-table rendering.

## Recommended Implementation Order

1. **Current PR:** finish step 3 by unifying plot-family orchestration around the behavior-preserving shared active-tab contract. Keep current active-tab-wide cards and downloads, and verify inactive tabs remain lazy.
1. **Next PR:** implement steps 4 and 5 together: add active-plot selection, render one card at a time, scope downloads to that card, split plot rendering from evaluation rendering, and replace observer-driven download-button updates.
1. **Following PR:** implement steps 6 and 7 based on benchmark evidence: extract the smallest useful DOM-free active-plot data boundary and add targeted higher-level caches.
1. **Schema/performance follow-up:** complete steps 8 and 9, preserving pre-aggregation export semantics while documenting and testing the intentional active-plot scope change.

This order finishes the current download-data PR at a coherent architectural boundary. The active-tab work remains valuable because the later active-plot contract extends it rather than replacing it, while the behavior and caching changes stay isolated in follow-up reviews with measurable performance goals.
