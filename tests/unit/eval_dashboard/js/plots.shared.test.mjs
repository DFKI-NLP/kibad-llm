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
  getLegendItemsForPoints,
  getPlotDisplayLabel,
  getPlotTitleLabel,
  getVaryingFields,
} from "../../../../docs/eval-dashboard/assets/js/plots/shared.js";

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
