/**
 * Tests for shared eval-dashboard plot helper seams.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildBarsTabMap,
  buildErrorsTabMap,
  buildGroupedLegendModel,
  buildPlotEntries,
  collectNumericMetricLeafPaths,
  collectPreparedNumericMetricPaths,
  getLegendItemsForPoints,
  prepareNumericMetricEvaluationData,
  getPlotDisplayLabel,
  getPlotTitleLabel,
  getVaryingFields,
  fitSvgToContents,
  scheduleAdaptiveSvgFit,
  styleErrorBarSegment,
} from "../../../../docs/eval-dashboard/assets/js/plots/shared.js";
import { createDocumentStub } from "./plots.dom-test-helpers.mjs";

/**
 * Verify numeric metric discovery and plot-entry shaping across grouped evaluations.
 */
test("shared plot helpers collect numeric metric paths and derive plot entries", () => {
  const paths = Array.from(
    collectNumericMetricLeafPaths({
      score: { mean: 0.75, detail: { f1: 0.5 } },
      ignored: "x",
      list: [1],
    }).values()
  );
  assert.deepEqual(paths, [["score", "mean"], ["score", "detail", "f1"]]);

  const plotGroups = [
    {
      values: { model: "a", seed: "1" },
      evaluations: [{ data: { score: { mean: 0.5 } } }, { data: { score: { mean: 0.7 } } }],
    },
    {
      values: { model: "b", seed: "1" },
      evaluations: [{ data: { score: { mean: 0.9 } } }],
    },
  ];

  assert.deepEqual(getVaryingFields(plotGroups, ["model", "seed"]), ["model"]);

  const entries = buildPlotEntries({
    metricPaths: [{ parts: ["score", "mean"], label: "score.mean" }],
    plotGroups,
    groupBarFields: [],
    categoryFields: ["model"],
    displayGroupFieldName: (field) => field.toUpperCase(),
  });

  assert.equal(entries.length, 1);
  assert.equal(entries[0].prefix, "score");
  assert.equal(entries[0].suffix, "mean");
  assert.deepEqual(
    entries[0].points.map((point) => [point.category, point.mean, point.std]),
    [["model=a", 0.6, 0.09999999999999998], ["model=b", 0.9, 0]]
  );
  assert.deepEqual(
    entries[0].points[0].samples.map((sample) => [sample.runDir, sample.metricLabel, sample.value]),
    [["", "score.mean", 0.5], ["", "score.mean", 0.7]]
  );
});

/**
 * Verify numeric metric preparation is cached and reusable for bar/error data export.
 */
test("shared plot helpers lazily prepare numeric metric data for bars and errors", () => {
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
  assert.deepEqual(
    collectPreparedNumericMetricPaths([evaluation]).map((path) => path.label),
    ["errors.by_label.A", "errors.with_error", "score.mean"]
  );

  const entries = buildPlotEntries({
    metricPaths: collectPreparedNumericMetricPaths([evaluation]),
    plotGroups: [{ values: {}, evaluations: [evaluation] }],
    groupBarFields: [],
    categoryFields: [],
  });

  const scoreEntry = entries.find((entry) => entry.metricLabel === "score.mean");
  assert.deepEqual(scoreEntry.points[0].samples.map((sample) => ({
    runDir: sample.runDir,
    metricLabel: sample.metricLabel,
    metricPath: sample.metricPath,
    value: sample.value,
  })), [{
    runDir: "run-a",
    metricLabel: "score.mean",
    metricPath: ["score", "mean"],
    value: 0.75,
  }]);
});

/**
 * Verify tab-map grouping, shortened plot labels, and grouped-series legend models.
 */
test("shared plot helpers derive tab maps, titles, and legend models", () => {
  const entries = [
    { metricLabel: "errors.with_error", prefix: "errors", suffix: "with_error", parts: ["with_error"], points: [] },
    { metricLabel: "details.x", prefix: "details", suffix: "x", parts: ["detail"], points: [] },
  ];

  assert.deepEqual(Array.from(buildBarsTabMap(entries).keys()), ["errors", "details"]);
  assert.deepEqual(Array.from(buildBarsTabMap(entries, { plotTabsBy: "suffix" }).keys()), ["with_error", "x"]);
  assert.deepEqual(Array.from(buildErrorsTabMap(entries).keys()), ["total", "details"]);
  assert.equal(getPlotDisplayLabel("a.b.c", { shortenLabels: true }), "c");
  assert.equal(
    getPlotTitleLabel(
      { prefix: "macro", metricLabel: "field.f1" },
      "F1MicroMultipleFieldsMetric",
      { shortenLabels: true, plotTabsBy: "suffix" }
    ),
    "macro"
  );

  const legend = buildGroupedLegendModel([
    {
      points: [
        { series: "s1", displaySeries: "Series 1" },
        { series: "s2", displaySeries: "Series 2" },
      ],
    },
  ]);
  assert.deepEqual(legend.items.map((item) => item.label), ["Series 1", "Series 2"]);
  assert.deepEqual(getLegendItemsForPoints([{ series: "s2" }], legend).map((item) => item.series), ["s2"]);
});

/**
 * Verify shared SVG helpers style error bars and fit connected SVG content.
 */
test("shared plot helpers style and adapt SVG dimensions", () => {
  const documentLike = createDocumentStub();
  const svg = documentLike.createElementNS("", "svg");
  const group = documentLike.createElementNS("", "g");
  group._bbox = { x: -12, y: -5, width: 140.2, height: 80.1 };
  svg.appendChild(group);

  const line = documentLike.createElementNS("", "line");
  styleErrorBarSegment(line);
  assert.equal(line.getAttribute("stroke"), "currentColor");
  assert.equal(line.getAttribute("stroke-opacity"), "0.78");

  assert.equal(fitSvgToContents(svg, group, 100, 60), true);
  assert.equal(group.getAttribute("transform"), "translate(20, 13)");
  assert.equal(svg.getAttribute("viewBox"), "0 0 157 97");
});

/**
 * Verify adaptive SVG fitting retries disconnected content and refits after fonts load.
 */
test("shared plot helpers schedule adaptive SVG fitting retries", async () => {
  let resolveFonts;
  const documentLike = {
    fonts: {
      ready: new Promise((resolve) => {
        resolveFonts = resolve;
      }),
    },
  };
  const svg = { isConnected: false, setAttribute: () => {} };
  const group = { getBBox: () => ({ x: 0, y: 0, width: 10, height: 10 }), setAttribute: () => {} };
  let frames = 0;

  scheduleAdaptiveSvgFit({
    documentLike,
    requestAnimationFrameLike: (callback) => {
      frames += 1;
      callback();
    },
    svg,
    contentGroup: group,
    minWidth: 20,
    minHeight: 20,
  });
  assert.equal(frames, 5);

  svg.isConnected = true;
  resolveFonts();
  await documentLike.fonts.ready;
  await Promise.resolve();
  assert.equal(frames, 6);
});
