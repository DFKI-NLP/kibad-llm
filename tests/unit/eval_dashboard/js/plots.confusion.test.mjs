import test from "node:test";
import assert from "node:assert/strict";

import {
  buildConfusionTabMap,
  countDistinctConfusionMatrixRuns,
  filterConfusionMatrixAggregationByLabelTotal,
  getConfusionMatrixAggregation,
  getConfusionMatrixTitle,
  normalizeConfusionMatrixLikeEvaluations,
} from "../../../../docs/eval-dashboard/assets/js/plots/confusion.js";

const getEvaluationEffectiveValue = (evaluation, column) =>
  evaluation.overrides?.[column] ?? "";

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
