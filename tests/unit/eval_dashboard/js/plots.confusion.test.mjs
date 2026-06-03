/**
 * Tests for eval-dashboard confusion-matrix plot helper seams.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildConfusionTabMap,
  countDistinctConfusionMatrixRuns,
  createConfusionMatrixHeatmapSvg,
  filterConfusionMatrixAggregationByLabelTotal,
  getConfusionMatrixAggregation,
  getConfusionMatrixTitle,
  normalizeConfusionMatrixLikeEvaluations,
} from "../../../../docs/eval-dashboard/assets/js/plots/confusion.js";
import { createDocumentStub } from "./plots.dom-test-helpers.mjs";

const getEvaluationEffectiveValue = (evaluation, column) =>
  evaluation.overrides?.[column] ?? "";

/**
 * Verify collection expansion and aligned mean/std aggregation for confusion matrices.
 */
test("confusion helpers expand collection metrics and aggregate aligned cells", () => {
  const expanded = normalizeConfusionMatrixLikeEvaluations([
    {
      runDir: "run-a",
      jobReturnValue: { type: "ConfusionMatrixCollection" },
      overrides: { experiment: "exp" },
      data: {
        field_a: { gold: { pred: 2 } },
        field_b: { gold: { pred: 4 } },
      },
    },
  ]);

  assert.deepEqual(expanded.map((evaluation) => evaluation.runDir), ["run-a#field_a", "run-a#field_b"]);
  assert.deepEqual(expanded.map((evaluation) => evaluation.overrides["metric.field"]), ["field_a", "field_b"]);
  assert.equal(countDistinctConfusionMatrixRuns(expanded), 1);

  const aggregation = getConfusionMatrixAggregation([
    { data: { b: { x: 2 }, UNASSIGNABLE: { UNDETECTED: 1 } } },
    { data: { b: { x: 4 }, a: { x: 2 } } },
  ]);
  assert.deepEqual(aggregation.rows, ["a", "b", "UNASSIGNABLE"]);
  assert.deepEqual(aggregation.cols, ["x", "UNDETECTED"]);
  assert.equal(aggregation.cells.get("b|#|x").mean, 3);
  assert.equal(aggregation.cells.get("a|#|x").mean, 1);

  const filtered = filterConfusionMatrixAggregationByLabelTotal(aggregation, 2);
  assert.deepEqual(filtered.rows, ["b"]);
  assert.deepEqual(filtered.cols, ["x"]);
});

/**
 * Verify confusion tab-map construction for both metric-field and prediction-group modes.
 */
test("confusion helpers build tab maps for metric-field and group-tab modes", () => {
  const evaluations = [
    { runDir: "r1", overrides: { "metric.field": "field_a", experiment: "exp" }, jobReturnValue: { type: "ConfusionMatrix" }, data: {} },
    { runDir: "r2", overrides: { "metric.field": "field_b", experiment: "exp" }, jobReturnValue: { type: "ConfusionMatrix" }, data: {} },
  ];
  const plotGroups = [
    { groupId: "g1", values: { model: "a" }, evaluations },
  ];

  const metricFieldTabs = buildConfusionTabMap({
    activeExperiment: "exp",
    plotGroups,
    experimentEvaluations: evaluations,
    labelFields: ["model"],
    evalTabState: {},
    confusionTabsBy: "metric_field",
    getEvaluationEffectiveValue,
    getEvaluationExperiment: (evaluation) => evaluation.overrides.experiment,
    displayPlotGroupFieldName: (field) => field,
  });
  assert.deepEqual(Array.from(metricFieldTabs.keys()), ["field_a", "field_b"]);
  assert.equal(metricFieldTabs.get("field_a").plots[0].label, "model=a");

  const groupTabs = buildConfusionTabMap({
    activeExperiment: "exp",
    plotGroups,
    experimentEvaluations: evaluations,
    labelFields: ["model"],
    evalTabState: {},
    confusionTabsBy: "prediction_group",
    getEvaluationEffectiveValue,
    getEvaluationExperiment: (evaluation) => evaluation.overrides.experiment,
    displayPlotGroupFieldName: (field) => field,
  });
  assert.deepEqual(Array.from(groupTabs.keys()), ["group|#|g1"]);
  assert.deepEqual(groupTabs.get("group|#|g1").plots.map((plot) => plot.label), ["field_a", "field_b"]);

  assert.equal(
    getConfusionMatrixTitle({
      experimentEvaluations: evaluations,
      evalTabState: {},
      getEvaluationEffectiveValue,
    }),
    "mixed metric.field: field_a, field_b"
  );
});

/**
 * Verify confusion heatmap SVG rendering wires labels, values, and tooltip events.
 */
test("confusion renderer creates labelled interactive heatmap cells", () => {
  const documentLike = createDocumentStub();
  const shown = [];
  const svg = createConfusionMatrixHeatmapSvg({
    documentLike,
    aggregation: {
      rows: ["outer.actual"],
      cols: ["outer.predicted"],
      cells: new Map([["outer.actual|#|outer.predicted", { mean: 0.75, std: 0.125 }]]),
    },
    precision: 2,
    getDisplayLabel: (label) => label.split(".").at(-1),
    showTooltip: (_event, lines) => shown.push(lines),
    moveTooltip: () => {},
    hideTooltip: () => {},
  });

  assert.equal(svg.getAttribute("viewBox"), "0 0 396 246");
  assert.ok(svg.querySelectorAll("text").some((text) => text.textContent === "actual"));
  assert.ok(svg.querySelectorAll("text").some((text) => text.textContent === "predicted"));
  assert.ok(svg.querySelectorAll("text").some((text) => text.textContent === "0.75±0.13"));

  const heatmapCell = svg.querySelectorAll("rect").find((rect) => rect.style.cursor === "crosshair");
  heatmapCell.dispatch("mouseover", { clientX: 10, clientY: 10 });
  assert.deepEqual(shown[0], [
    "actual:    outer.actual",
    "predicted: outer.predicted",
    "mean: 0.75",
    "std:  0.13",
  ]);
});
