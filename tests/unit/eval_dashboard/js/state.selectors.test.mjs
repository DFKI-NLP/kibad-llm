/**
 * Browser-free logic tests for the eval-dashboard state selectors.
 */

import assert from "node:assert/strict";
import test from "node:test";

import { createInitialDashboardState, syncPredictionGroupUiState } from "../../../../docs/eval-dashboard/assets/js/state/store.js";
import {
  EVALUATION_PREFIX,
  JOB_RETURN_VALUE_PREFIX,
  getCurrentPredictionColumns,
  getDefaultEvalGroupByFields,
  getDefaultGroupByFields,
  getDisplayedSelectionState,
  getEvaluationContext,
  getMetricTypeForEvaluationContext,
  getPlotGroups,
  getPredictionContentSignature,
  getPredictionGroups,
  getPredictionViews,
  getSelectedEvaluationGroups,
  getSortedPredictionGroups,
} from "../../../../docs/eval-dashboard/assets/js/state/selectors.js";

function buildState() {
  const state = createInitialDashboardState();
  state.predictions = {
    "pred-a": {
      overrides: { model: "alpha", seed: "1", dataset: "facts" },
      jobReturnValue: { output_file: "pred-a.json" },
    },
    "pred-b": {
      overrides: { model: "beta", seed: "2", dataset: "facts" },
      jobReturnValue: { output_file: "pred-b.json" },
    },
  };
  state.evaluations = [
    {
      runDir: "runs/eval-a1",
      predictionId: "pred-a",
      overrides: { "experiment/evaluate": "f1_micro", split: "dev", metric_variant: "macro" },
      jobReturnValue: { type: "F1MicroMultipleFieldsMetric", score: 0.8 },
      data: { overall: 0.8 },
    },
    {
      runDir: "runs/eval-a2",
      predictionId: "pred-a",
      overrides: { "experiment/evaluate": "f1_micro", split: "test", metric_variant: "macro" },
      jobReturnValue: { type: "F1MicroMultipleFieldsMetric", score: 0.82 },
      data: { overall: 0.82 },
    },
    {
      runDir: "runs/eval-b1",
      predictionId: "pred-b",
      overrides: { "experiment/evaluate": "f1_micro", split: "dev", metric_variant: "macro" },
      jobReturnValue: { type: "F1MicroMultipleFieldsMetric", score: 0.71 },
      data: { overall: 0.71 },
    },
  ];
  return state;
}

/**
 * Ensure prediction views, grouping, and sorting stay behavior-equivalent after selector extraction.
 */
test("selectors derive prediction views, grouping, and selection state", () => {
  const state = buildState();
  const predictionViews = getPredictionViews(state);
  const predictionColumns = getCurrentPredictionColumns(state, predictionViews);

  assert.equal(predictionViews.length, 2);
  assert.ok(predictionColumns.includes("prediction.overrides.model"));
  assert.deepEqual(getDefaultGroupByFields(predictionColumns, predictionViews), ["prediction.overrides.model"]);

  state.groupByFields = ["prediction.overrides.model"];
  const predictionGroups = getPredictionGroups(state, predictionViews, state.groupByFields, predictionColumns);
  syncPredictionGroupUiState(state, predictionGroups);

  assert.deepEqual(predictionGroups.map((group) => group.groupId).sort(), [
    "prediction.overrides.model=alpha",
    "prediction.overrides.model=beta",
  ]);
  assert.deepEqual([...state.selectedGroupIds].sort(), predictionGroups.map((group) => group.groupId).sort());
  assert.deepEqual(getDisplayedSelectionState(state, predictionGroups), {
    displayedGroupIds: ["prediction.overrides.model=alpha", "prediction.overrides.model=beta"],
    selectedCount: 2,
    allSelected: true,
    someSelected: false,
  });

  state.predictionSort = [{ column: "group_size", direction: "desc" }];
  assert.deepEqual(
    getSortedPredictionGroups(state, predictionGroups).map((group) => group.groupId),
    ["prediction.overrides.model=alpha", "prediction.overrides.model=beta"]
  );
  assert.equal(
    getPredictionContentSignature(state.predictions["pred-a"]),
    '{"prediction.job_return_value.output_file":"pred-a.json","prediction.overrides.dataset":"facts","prediction.overrides.model":"alpha","prediction.overrides.seed":"1"}'
  );
});

/**
 * Ensure evaluation contexts, selection, and plot grouping derive from canonical state.
 */
test("selectors derive evaluation context and plot groups", () => {
  const state = buildState();
  const predictionViews = getPredictionViews(state);
  const predictionColumns = getCurrentPredictionColumns(state, predictionViews);

  state.groupByFields = ["prediction.overrides.model"];
  syncPredictionGroupUiState(
    state,
    getPredictionGroups(state, predictionViews, state.groupByFields, predictionColumns)
  );
  state.activeEvalTab = "f1_micro";

  const evaluationContext = getEvaluationContext(state);

  assert.equal(evaluationContext.activeExperiment, "f1_micro");
  assert.deepEqual(
    getDefaultEvalGroupByFields(evaluationContext.evalColumns, evaluationContext.experimentEvaluations),
    [`${JOB_RETURN_VALUE_PREFIX}score`, "split"]
  );
  assert.ok(evaluationContext.evalColumns.includes(`${JOB_RETURN_VALUE_PREFIX}score`));
  assert.deepEqual(evaluationContext.evalTabState.groupByFields, [`${JOB_RETURN_VALUE_PREFIX}score`, "split"]);
  assert.equal(getMetricTypeForEvaluationContext(state, "f1_micro", evaluationContext), "F1MicroMultipleFieldsMetric");

  const selectedEvaluationGroups = getSelectedEvaluationGroups(state, evaluationContext);
  const plotGroups = getPlotGroups(
    state,
    evaluationContext.activeExperiment,
    selectedEvaluationGroups,
    evaluationContext.evalTabState.groupByFields,
    evaluationContext.evalTabState
  );

  assert.deepEqual(plotGroups.fields, [
    "prediction.overrides.model",
    `${EVALUATION_PREFIX}${JOB_RETURN_VALUE_PREFIX}score`,
    `${EVALUATION_PREFIX}split`,
  ]);
  assert.equal(plotGroups.groups.length, 3);
  assert.deepEqual(
    plotGroups.groups.map((group) => group.groupId).sort(),
    [
      "prediction.overrides.model=alpha | evaluation.job_return_value.score=0.8 | evaluation.split=dev",
      "prediction.overrides.model=alpha | evaluation.job_return_value.score=0.82 | evaluation.split=test",
      "prediction.overrides.model=beta | evaluation.job_return_value.score=0.71 | evaluation.split=dev",
    ]
  );
});

/**
 * Ensure default eval group-by selection still excludes dataset.predictions.log even
 * when it is sourced from flattened job_return_value content.
 */
test("selectors exclude job_return_value.dataset.predictions.log from default eval group-by fields", () => {
  const evalColumns = [`${JOB_RETURN_VALUE_PREFIX}dataset.predictions.log`, "split"];
  const evaluations = [
    {
      runDir: "runs/eval-a1",
      overrides: { split: "dev" },
      jobReturnValue: { dataset: { predictions: { log: "very-large-log-a" } } },
    },
    {
      runDir: "runs/eval-a2",
      overrides: { split: "test" },
      jobReturnValue: { dataset: { predictions: { log: "very-large-log-b" } } },
    },
  ];

  assert.deepEqual(getDefaultEvalGroupByFields(evalColumns, evaluations), ["split"]);
});

/**
 * Ensure mixed metric types still fail early when deriving the active evaluation metric type.
 */
test("selectors reject evaluation contexts with mixed metric types", () => {
  const state = buildState();
  state.groupByFields = [];
  syncPredictionGroupUiState(state, getPredictionGroups(state));
  state.activeEvalTab = "f1_micro";
  state.evaluations.push({
    runDir: "runs/eval-b2",
    predictionId: "pred-b",
    overrides: { "experiment/evaluate": "f1_micro", split: "test" },
    jobReturnValue: { type: "ConfusionMatrix", score: 0.5 },
    data: {},
  });

  const evaluationContext = getEvaluationContext(state);

  assert.throws(
    () => getMetricTypeForEvaluationContext(state, "f1_micro", evaluationContext),
    /Multiple evaluation metric types found/
  );
});
