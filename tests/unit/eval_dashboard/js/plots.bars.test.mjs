/**
 * Tests for eval-dashboard bar-plot rendering seams.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildBarsTabMap,
  buildErrorsTabMap,
  buildJsonSafeNumericPlottingData,
  buildNumericDownloadMetadata,
  buildNumericPlotEntriesInput,
  buildPlotEntries,
  createBarPlotSvg,
  createGroupedBarPlotSvg,
  getNumericPlotEntriesFromInput,
  getPlotTitleLabel,
  prepareNumericMetricEvaluationData,
  renderBarPlotTabsAndGrid,
} from "../../../../docs/eval-dashboard/assets/js/plots/bars.js";
import { createDocumentStub } from "./plots.dom-test-helpers.mjs";

/**
 * Verify numeric metric discovery and plot-entry shaping across grouped evaluations.
 */
test("bar plot helpers collect numeric metric paths and derive plot entries", () => {
  const plotGroups = [
    {
      values: { model: "a", seed: "1" },
      evaluations: [
        { runDir: "run-a1", data: { score: { mean: 0.5 } } },
        { runDir: "run-a2", data: { score: { mean: 0.7 } } },
      ],
    },
    {
      values: { model: "b", seed: "1" },
      evaluations: [{ runDir: "run-b1", data: { score: { mean: 0.9 } } }],
    },
  ];

  const entries = buildPlotEntries({
    metricType: "F1MicroMultipleFieldsMetric",
    plotGroups,
    groupBarFields: [],
    categoryFields: ["model"],
    displayGroupFieldName: (field) => field.toUpperCase(),
  });

  assert.equal(entries.length, 1);
  assert.equal(entries[0].metricRoot, "score");
  assert.equal(entries[0].metricPrefix, "score");
  assert.equal(entries[0].metricSuffix, "mean");
  assert.deepEqual(
    entries[0].points.map((point) => [point.category, point.mean, point.std]),
    [["model=a", 0.6, 0.09999999999999998], ["model=b", 0.9, 0]]
  );
  assert.deepEqual(
    entries[0].points[0].samples,
    [0.5, 0.7]
  );
  assert.deepEqual(entries[0].points[0].runDirs, ["run-a1", "run-a2"]);

  assert.throws(
    () => buildNumericPlotEntriesInput({
      plotGroups,
      groupBarFields: [],
      categoryFields: ["model"],
    }),
    /Numeric plot entry construction requires a metric type\./
  );
});

/**
 * Verify numeric plot entry input stays pre-aggregation before render stats are added.
 */
test("bar plot helpers separate sample input from mean/std render entries", () => {
  const inputEntries = buildNumericPlotEntriesInput({
    metricType: "F1MicroMultipleFieldsMetric",
    plotGroups: [{
      values: { model: "a" },
      evaluations: [{ runDir: "run-a", data: { score: 0 } }, { runDir: "run-b", data: { score: 0.7 } }],
    }],
    groupBarFields: [],
    categoryFields: ["model"],
  });
  const renderEntries = getNumericPlotEntriesFromInput(inputEntries);

  assert.deepEqual(inputEntries[0].points[0].samples, [0, 0.7]);
  assert.equal("mean" in inputEntries[0].points[0], false);
  assert.equal("std" in inputEntries[0].points[0], false);
  assert.equal(renderEntries[0].points[0].mean, 0.35);
  assert.equal(renderEntries[0].points[0].std, 0.35);
});

/**
 * Verify sparse ErrorCollector counters contribute zero for every evaluation.
 */
test("bar plot helpers default missing ErrorCollector counters to zero", () => {
  const entries = buildNumericPlotEntriesInput({
    metricType: "ErrorCollector",
    plotGroups: [{
      values: { model: "a" },
      evaluations: [
        { runDir: "run-a", data: { no_error: 90, with_error: 10, MissingResponseContentError: 10 } },
        { runDir: "run-b", data: { no_error: 100 } },
      ],
    }],
    groupBarFields: [],
    categoryFields: ["model"],
  });

  const missingContentEntry = entries.find(
    (entry) => entry.metricLabel === "MissingResponseContentError"
  );
  assert.deepEqual(missingContentEntry.points[0].samples, [10, 0]);
  const renderEntry = getNumericPlotEntriesFromInput([missingContentEntry])[0];
  assert.equal(renderEntry.points[0].mean, 5);
  assert.equal(renderEntry.points[0].std, 5);
});

/**
 * Verify missing required metrics fail when their metric type has no default.
 */
test("bar plot helpers reject missing required numeric values", () => {
  const buildInput = (metricType) => buildNumericPlotEntriesInput({
    metricType,
    plotGroups: [{
      values: {},
      evaluations: [
        { runDir: "run-a", data: { score: { mean: 0.75 } } },
        { runDir: "run-b", data: { score: {} } },
      ],
    }],
    groupBarFields: [],
    categoryFields: [],
  });

  assert.throws(
    () => buildInput("F1MicroMultipleFieldsMetric"),
    /Numeric metric "score\.mean" is missing from evaluation "run-b".*"F1MicroMultipleFieldsMetric" has no missing-value default\./
  );
});

/**
 * Verify metric discovery uses the union of evaluations in the plot groups.
 */
test("bar plot helpers discover metrics from selected plot groups", () => {
  const entries = buildNumericPlotEntriesInput({
    metricType: "ErrorCollector",
    plotGroups: [{
      values: {},
      evaluations: [
        { runDir: "run-a", data: { no_error: 100 } },
        { runDir: "run-b", data: { no_error: 90, ValueError: 10 } },
      ],
    }],
    groupBarFields: [],
    categoryFields: [],
  });

  assert.deepEqual(entries.map((entry) => entry.metricLabel), ["no_error", "ValueError"]);
});

/**
 * Verify numeric download data preserves compact sample values.
 */
test("bar plot helpers build compact JSON-safe numeric plotting data", () => {
  assert.deepEqual(
    buildJsonSafeNumericPlottingData({
      points: [{
        category: "model=a",
        displayCategory: "Model A",
        series: "seed=1",
        displaySeries: "Seed 1",
        label: "model=a",
        displayLabel: "Model A",
        runDirs: ["run-a", "run-b"],
        samples: [0.75, 0.81],
      }],
    }),
    {
      points: [{
        category: "model=a",
        displayCategory: "Model A",
        series: "seed=1",
        displaySeries: "Seed 1",
        runDirs: ["run-a", "run-b"],
        samples: [0.75, 0.81],
      }],
    }
  );

  assert.throws(
    () => buildJsonSafeNumericPlottingData({
      points: [{ runDirs: ["run-a"], samples: [0.75, 0.81] }],
    }),
    /runDirs\.length \(1\) to equal samples\.length \(2\)/
  );
});

/**
 * Verify numeric download metadata uses an explicit public-field allowlist.
 */
test("bar plot helpers build numeric download metadata", () => {
  assert.deepEqual(
    buildNumericDownloadMetadata({
      metricLabel: "score.mean",
      metricRoot: "score",
      metricPrefix: "score",
      metricSuffix: "mean",
      points: [{ samples: [0.75] }],
      internalField: "must not leak",
    }),
    {
      metricLabel: "score.mean",
    }
  );
});

/**
 * Verify numeric metric preparation is cached and reusable for bar/error data export.
 */
test("bar plot helpers lazily prepare numeric metric data for bars and errors", () => {
  const evaluation = {
    runDir: "run-a",
    data: {
      score: { mean: 0.75 },
      errors: { with_error: 2, by_label: { A: 1 } },
      ignored: "x",
    },
  };

  const prepared = prepareNumericMetricEvaluationData(evaluation);

  assert.deepEqual(
    Array.from(prepared.metricPaths.values()).map((path) => [path.key, path.label]),
    [
      ["score|#|mean", "score.mean"],
      ["errors|#|with_error", "errors.with_error"],
      ["errors|#|by_label|#|A", "errors.by_label.A"],
    ]
  );
  assert.equal(prepared.values.get("score|#|mean"), 0.75);
  assert.equal(prepareNumericMetricEvaluationData(evaluation), prepared);
  assert.deepEqual(Object.keys(evaluation), ["runDir", "data"]);
  const entries = buildPlotEntries({
    metricType: "F1MicroMultipleFieldsMetric",
    plotGroups: [{ values: {}, evaluations: [evaluation] }],
    groupBarFields: [],
    categoryFields: [],
  });

  const scoreEntry = entries.find((entry) => entry.metricLabel === "score.mean");
  assert.deepEqual(scoreEntry.points[0].samples, [0.75]);

  assert.throws(
    () => prepareNumericMetricEvaluationData({ data: { score: Number.POSITIVE_INFINITY } }),
    /Numeric metric "score" must be finite\./
  );
});

/**
 * Verify bar-specific tab maps and title labels.
 */
test("bar plot helpers derive tab maps and titles", () => {
  const entries = [
    { metricLabel: "errors.with_error", metricRoot: "with_error", metricPrefix: "errors", metricSuffix: "with_error", points: [] },
    { metricLabel: "details.x", metricRoot: "detail", metricPrefix: "details", metricSuffix: "x", points: [] },
  ];

  const prefixTabs = buildBarsTabMap(entries, "prefix");
  const suffixTabs = buildBarsTabMap(entries, "suffix");
  const errorTabs = buildErrorsTabMap(entries);
  assert.deepEqual(Array.from(prefixTabs.keys()), ["errors", "details"]);
  assert.deepEqual(
    {
      label: prefixTabs.get("errors").label,
      plotTab: prefixTabs.get("errors").plotTab,
      plotTabVariant: prefixTabs.get("errors").plotTabVariant,
      plots: prefixTabs.get("errors").plots,
    },
    {
      label: "errors",
      plotTab: "errors",
      plotTabVariant: "prefix",
      plots: [entries[0]],
    }
  );
  assert.deepEqual(Array.from(suffixTabs.keys()), ["with_error", "x"]);
  assert.equal(suffixTabs.get("with_error").plotTabVariant, "suffix");
  assert.deepEqual(Array.from(errorTabs.keys()), ["total", "details"]);
  assert.equal(errorTabs.get("total").plotTabVariant, "error_section");
  assert.deepEqual(errorTabs.get("total").plots, [entries[0]]);
  assert.throws(
    () => buildBarsTabMap(entries),
    /Unsupported numeric plot tab variant: \(missing\)/
  );
  assert.throws(
    () => buildBarsTabMap(entries, "unknown"),
    /Unsupported numeric plot tab variant: unknown/
  );
  assert.equal(
    getPlotTitleLabel(
      { metricPrefix: "macro", metricLabel: "field.f1" },
      "F1MicroMultipleFieldsMetric",
      { shortenLabels: true, plotTabsBy: "suffix" }
    ),
    "macro"
  );
});

/**
 * Verify single-series bar SVGs wire tooltip events and adaptive fitting.
 */
test("bar plot renderer creates interactive SVG bars", () => {
  const documentLike = createDocumentStub();
  const shown = [];
  const svg = createBarPlotSvg({
    documentLike,
    requestAnimationFrameLike: (callback) => callback(),
    points: [{ label: "model=a", displayLabel: "a", mean: 0.75, std: 0.05 }],
    showTooltip: (_event, lines) => shown.push(lines),
    moveTooltip: () => {},
    hideTooltip: () => {},
  });

  assert.equal(svg.tagName, "svg");
  assert.equal(svg.getAttribute("viewBox"), "0 0 728 328");
  const rect = svg.querySelector("rect");
  rect.dispatch("mouseover", { clientX: 10, clientY: 10 });
  assert.deepEqual(shown[0], ["model=a", "mean: 0.7500", "std:  0.0500"]);
});

/**
 * Verify grouped bars use legend colors and include series names in tooltips.
 */
test("grouped bar renderer applies legend colors and grouped tooltips", () => {
  const documentLike = createDocumentStub();
  const shown = [];
  const legendModel = {
    seriesOrder: ["seed=1", "seed=2"],
    colorBySeries: new Map([["seed=1", "#111111"], ["seed=2", "#222222"]]),
    displayBySeries: new Map([["seed=1", "Seed 1"], ["seed=2", "Seed 2"]]),
  };

  const svg = createGroupedBarPlotSvg({
    documentLike,
    requestAnimationFrameLike: (callback) => callback(),
    legendModel,
    points: [
      { category: "model=a", displayCategory: "Model A", series: "seed=1", mean: 0.5, std: 0.1 },
      { category: "model=a", displayCategory: "Model A", series: "seed=2", mean: 0.7, std: 0.1 },
    ],
    showTooltip: (_event, lines) => shown.push(lines),
    moveTooltip: () => {},
    hideTooltip: () => {},
  });

  const bars = svg.querySelectorAll("rect").filter((rect) => rect.getAttribute("fill")?.startsWith("#"));
  assert.equal(bars[0].getAttribute("fill"), "#111111");
  bars[0].dispatch("mouseover", { clientX: 10, clientY: 10 });
  assert.deepEqual(shown[0], ["model=a", "series: Seed 1", "mean: 0.5000", "std:  0.1000"]);
});

/**
 * Verify the extracted tab/grid renderer preserves tab state, legends, and selection callbacks.
 */
test("bar grid renderer renders tabs, shared legends, and cards", () => {
  const documentLike = createDocumentStub();
  const evalPlotTabs = documentLike.createElement("div");
  const evalPlotContent = documentLike.createElement("div");
  let selected = null;

  const result = renderBarPlotTabsAndGrid({
    documentLike,
    tabMap: new Map([
      [
        "score",
        {
          label: "score",
          plotTab: "score",
          plotTabVariant: "prefix",
          plots: [
            {
              metricLabel: "score.mean",
              metricPrefix: "score",
              metricSuffix: "mean",
              points: [
                { category: "model=a", displayCategory: "Model A", series: "seed=1", displaySeries: "Seed 1", mean: 0.5, std: 0 },
                { category: "model=a", displayCategory: "Model A", series: "seed=2", displaySeries: "Seed 2", mean: 0.6, std: 0 },
              ],
            },
          ],
        },
      ],
    ]),
    activeExperiment: "exp",
    groupBarFields: ["seed"],
    metricType: "Metric",
    activeEvalPlotTab: null,
    plotShowLegendOnce: true,
    plotShowLegendOnceRow: documentLike.createElement("div"),
    evalPlotTabs,
    evalPlotContent,
    buildCountTabButtonModels: (values, options) => Array.from(values).map((value) => ({
      value,
      label: `${options.getLabelText(value)} (${options.getCount(value)})`,
      title: options.getTitle(value),
      isActive: value === options.activeValue,
    })),
    renderTabButtons: ({ containerElement, tabModels, onSelect }) => {
      for (const tab of tabModels) {
        const button = documentLike.createElement("button");
        button.textContent = tab.label;
        button.setAttribute("title", tab.title);
        button.addEventListener("click", () => onSelect(tab.value));
        containerElement.appendChild(button);
      }
    },
    resolveActiveTabValue: (_active, values) => Array.from(values)[0],
    getPlotTitleLabel: (entry, metricType) => `${metricType}:${entry.metricLabel}`,
    displayPlotGroupFieldName: (field) => field,
    createBarSvg: () => documentLike.createElementNS("", "svg"),
    createGroupedBarSvg: () => documentLike.createElementNS("", "svg"),
    onActiveTabChange: (key) => {
      selected = key;
    },
  });

  assert.equal(result.activeEvalPlotTab, "score");
  assert.equal(result.activePlotLegendItems.length, 2);
  assert.equal(evalPlotTabs.querySelector("button").textContent, "score (1)");
  assert.equal(evalPlotContent.querySelector(".plot-legend").children.length, 2);
  assert.equal(evalPlotContent.querySelector(".plot-card").querySelector(".plot-title").textContent, "Metric:score.mean (mean ± std) | grouped by: seed");
  evalPlotTabs.querySelector("button").click();
  assert.equal(selected, "score");
});

/**
 * Verify per-card legend rendering does not drop shared legend items used by exports.
 */
test("bar grid renderer preserves export legend items when shared legend is not rendered", () => {
  const documentLike = createDocumentStub();
  const evalPlotContent = documentLike.createElement("div");
  const result = renderBarPlotTabsAndGrid({
    documentLike,
    tabMap: new Map([
      [
        "score",
        {
          label: "score",
          plotTab: "score",
          plotTabVariant: "prefix",
          plots: [
            {
              metricLabel: "score.mean",
              metricPrefix: "score",
              metricSuffix: "mean",
              points: [
                { category: "model=a", displayCategory: "Model A", series: "seed=1", displaySeries: "Seed 1", mean: 0.5, std: 0 },
              ],
            },
            {
              metricLabel: "score.mean",
              metricPrefix: "score",
              metricSuffix: "mean",
              points: [
                { category: "model=b", displayCategory: "Model B", series: "seed=2", displaySeries: "Seed 2", mean: 0.7, std: 0 },
              ],
            },
          ],
        },
      ],
    ]),
    activeExperiment: "exp",
    groupBarFields: ["seed"],
    metricType: "Metric",
    activeEvalPlotTab: "score",
    plotShowLegendOnce: false,
    plotShowLegendOnceRow: documentLike.createElement("div"),
    evalPlotTabs: documentLike.createElement("div"),
    evalPlotContent,
    buildCountTabButtonModels: (values) => Array.from(values).map((value) => ({ value, label: value })),
    renderTabButtons: () => {},
    resolveActiveTabValue: (_active, values) => Array.from(values)[0],
    getPlotTitleLabel: (entry) => entry.metricLabel,
    displayPlotGroupFieldName: (field) => field,
    createGroupedBarSvg: () => documentLike.createElementNS("", "svg"),
  });

  assert.equal(evalPlotContent.querySelector(".plot-legend"), null);
  assert.deepEqual(result.activePlotLegendItems.map((item) => item.label), ["Seed 1", "Seed 2"]);
});

/**
 * Verify the extracted grid renderer's default SVG callbacks work without injection.
 */
test("bar grid renderer defaults create SVGs for ungrouped and grouped entries", () => {
  const documentLike = createDocumentStub();

  for (const groupBarFields of [[], ["seed"]]) {
    const evalPlotContent = documentLike.createElement("div");
    const result = renderBarPlotTabsAndGrid({
      documentLike,
      tabMap: new Map([
        [
          "score",
          {
            label: "score",
            plotTab: "score",
            plotTabVariant: "prefix",
            plots: [
              {
                metricLabel: "score.mean",
                metricPrefix: "score",
                metricSuffix: "mean",
                points: [
                  {
                    label: "model=a",
                    displayLabel: "Model A",
                    category: "model=a",
                    displayCategory: "Model A",
                    series: "seed=1",
                    displaySeries: "Seed 1",
                    mean: 0.5,
                    std: 0,
                  },
                ],
              },
            ],
          },
        ],
      ]),
      activeExperiment: "exp",
      groupBarFields,
      metricType: "Metric",
      activeEvalPlotTab: null,
      plotShowLegendOnce: false,
      plotShowLegendOnceRow: documentLike.createElement("div"),
      evalPlotTabs: documentLike.createElement("div"),
      evalPlotContent,
      buildCountTabButtonModels: (values) => Array.from(values).map((value) => ({ value, label: value })),
      renderTabButtons: () => {},
      resolveActiveTabValue: (_active, values) => Array.from(values)[0],
      getPlotTitleLabel: (entry) => entry.metricLabel,
      displayPlotGroupFieldName: (field) => field,
    });

    assert.equal(result.activeEvalPlotTab, "score");
    assert.equal(evalPlotContent.querySelector(".plot-card").querySelector("svg").tagName, "svg");
  }
});

/**
 * Verify the extracted grid renderer reports an empty active tab without cards.
 */
test("bar grid renderer shows an empty message for empty tabs", () => {
  const documentLike = createDocumentStub();
  const evalPlotContent = documentLike.createElement("div");
  const result = renderBarPlotTabsAndGrid({
    documentLike,
    tabMap: new Map([["score", {
      label: "score",
      plotTab: "score",
      plotTabVariant: "prefix",
      plots: [],
    }]]),
    activeExperiment: "exp",
    groupBarFields: [],
    metricType: "Metric",
    activeEvalPlotTab: "score",
    plotShowLegendOnce: false,
    plotShowLegendOnceRow: documentLike.createElement("div"),
    evalPlotTabs: documentLike.createElement("div"),
    evalPlotContent,
    buildCountTabButtonModels: (values) => Array.from(values).map((value) => ({ value, label: value })),
    renderTabButtons: () => {},
    resolveActiveTabValue: (_active, values) => Array.from(values)[0],
    getPlotTitleLabel: () => "",
    displayPlotGroupFieldName: (field) => field,
  });

  assert.equal(result.activeEvalPlotTab, "score");
  assert.equal(evalPlotContent.querySelector(".plot-empty").textContent, "No plottable metric values found for the active tab.");
});
