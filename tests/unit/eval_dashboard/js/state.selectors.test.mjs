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
  getEvaluationColumnRawValue,
  getEvaluationGroups,
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
 * Ensure all equivalent dataset.predictions.log-style eval columns stay excluded from
 * default eval group-by selection after the Phase 6 extraction.
 */
test("selectors exclude dataset.predictions.log across equivalent eval column shapes", () => {
  const evalColumns = [
    "dataset.predictions.log",
    "overrides.dataset.predictions.log",
    `${JOB_RETURN_VALUE_PREFIX}dataset.predictions.log`,
    `${EVALUATION_PREFIX}dataset.predictions.log`,
    `${EVALUATION_PREFIX}${JOB_RETURN_VALUE_PREFIX}dataset.predictions.log`,
    "split",
  ];
  const evaluations = [
    {
      runDir: "runs/eval-a1",
      overrides: {
        split: "dev",
        "dataset.predictions.log": "raw-log-a",
        "overrides.dataset.predictions.log": "override-log-a",
      },
      jobReturnValue: { dataset: { predictions: { log: "job-log-a" } } },
    },
    {
      runDir: "runs/eval-a2",
      overrides: {
        split: "test",
        "dataset.predictions.log": "raw-log-b",
        "overrides.dataset.predictions.log": "override-log-b",
      },
      jobReturnValue: { dataset: { predictions: { log: "job-log-b" } } },
    },
  ];

  assert.deepEqual(getDefaultEvalGroupByFields(evalColumns, evaluations), ["split"]);
});

/**
 * Ensure evaluation column access resolves run-dir, job-return-value, override, and
 * missing fields through the extracted selector helper.
 */
test("selectors resolve raw evaluation column values across supported namespaces", () => {
  const evaluation = {
    runDir: "runs/eval-a1",
    overrides: { split: "dev", "dataset.predictions.log": "raw-log" },
    jobReturnValue: { score: 0.8, nested: { leaf: "value" } },
  };

  assert.equal(getEvaluationColumnRawValue(evaluation, "eval_run_dir"), "runs/eval-a1");
  assert.equal(getEvaluationColumnRawValue(evaluation, "split"), "dev");
  assert.equal(getEvaluationColumnRawValue(evaluation, "dataset.predictions.log"), "raw-log");
  assert.equal(getEvaluationColumnRawValue(evaluation, `${JOB_RETURN_VALUE_PREFIX}score`), 0.8);
  assert.equal(
    getEvaluationColumnRawValue(evaluation, `${EVALUATION_PREFIX}${JOB_RETURN_VALUE_PREFIX}nested.leaf`),
    "value"
  );
  assert.equal(getEvaluationColumnRawValue(evaluation, "missing.field"), undefined);
});

/**
 * Ensure prediction-view derivation ignores evaluations whose prediction id no longer
 * exists in canonical prediction state.
 */
test("selectors ignore orphaned evaluations when building prediction views", () => {
  const state = createInitialDashboardState();
  state.predictions = {
    "pred-a": {
      overrides: { model: "alpha" },
      jobReturnValue: { output_file: "pred-a.json" },
    },
  };
  state.evaluations = [
    {
      runDir: "runs/eval-a1",
      predictionId: "pred-a",
      overrides: { "experiment/evaluate": "f1_micro" },
      jobReturnValue: { type: "F1MicroMultipleFieldsMetric" },
      data: {},
    },
    {
      runDir: "runs/eval-missing",
      predictionId: "missing-prediction",
      overrides: { "experiment/evaluate": "f1_micro" },
      jobReturnValue: { type: "F1MicroMultipleFieldsMetric" },
      data: {},
    },
  ];

  const predictionViews = getPredictionViews(state);

  assert.equal(predictionViews.length, 1);
  assert.equal(predictionViews[0].predictionId, "pred-a");
  assert.deepEqual(predictionViews[0].evaluations.map((evaluation) => evaluation.runDir), ["runs/eval-a1"]);
});

/**
 * Ensure grouping semantics continue to respect configured effective default values.
 */
test("selectors group predictions and evaluations by effective default values", () => {
  const state = createInitialDashboardState();
  state.predictions = {
    "pred-a": {
      overrides: {},
      jobReturnValue: { output_file: "pred-a.json" },
    },
    "pred-b": {
      overrides: { variant: "fallback" },
      jobReturnValue: { output_file: "pred-b.json" },
    },
  };
  state.evaluations = [
    {
      runDir: "runs/eval-a1",
      predictionId: "pred-a",
      overrides: { "experiment/evaluate": "f1_micro" },
      jobReturnValue: { type: "F1MicroMultipleFieldsMetric" },
      data: {},
    },
    {
      runDir: "runs/eval-b1",
      predictionId: "pred-b",
      overrides: { "experiment/evaluate": "f1_micro", split: "fallback" },
      jobReturnValue: { type: "F1MicroMultipleFieldsMetric" },
      data: {},
    },
  ];

  state.predictionDefaultValues["prediction.overrides.variant"] = "fallback";
  const predictionViews = getPredictionViews(state);
  const predictionGroups = getPredictionGroups(
    state,
    predictionViews,
    ["prediction.overrides.variant"],
    ["prediction.overrides.variant"]
  );

  assert.equal(predictionGroups.length, 1);
  assert.equal(predictionGroups[0].groupId, "prediction.overrides.variant=fallback");
  assert.equal(predictionGroups[0].predictions.length, 2);

  const evalTabState = {
    defaultValues: { split: "fallback" },
    selectedGroupIds: new Set(),
    expandedGroupIds: new Set(),
    sort: [],
  };
  const evaluationGroups = getEvaluationGroups(state, state.evaluations, ["split"], [], evalTabState);

  assert.equal(evaluationGroups.length, 1);
  assert.equal(evaluationGroups[0].groupId, "eval.split=fallback");
  assert.equal(evaluationGroups[0].evaluations.length, 2);
});

/**
 * Ensure empty selection and empty active-evaluation states still derive a stable,
 * non-throwing evaluation context.
 */
test("selectors derive empty evaluation contexts without crashing", () => {
  const state = buildState();

  assert.equal(getEvaluationContext(state), null);
  assert.deepEqual(getSelectedEvaluationGroups(state), []);

  state.activeEvalTab = "f1_micro";
  const evaluationContext = getEvaluationContext(state);

  assert.equal(evaluationContext.activeExperiment, "f1_micro");
  assert.deepEqual(evaluationContext.experimentEvaluations, []);
  assert.deepEqual(evaluationContext.evalColumns, []);
  assert.deepEqual(evaluationContext.evaluationGroups, []);
  assert.deepEqual(getSelectedEvaluationGroups(state, evaluationContext), []);
  assert.equal(getMetricTypeForEvaluationContext(state, "f1_micro", evaluationContext), "");
});

/**
 * Ensure plot-group derivation falls back to evaluation run dirs when neither prediction
 * nor evaluation grouping contributes any plot-group fields.
 */
test("selectors fall back to runDir when plot groups have no grouping fields", () => {
  const state = buildState();
  const selectedEvalGroups = [{ evaluations: state.evaluations.slice(0, 2) }];

  const plotGroups = getPlotGroups(state, "f1_micro", selectedEvalGroups, [], { defaultValues: {} });

  assert.deepEqual(plotGroups.fields, []);
  assert.deepEqual(
    plotGroups.groups.map((group) => group.groupId).sort(),
    ["runs/eval-a1", "runs/eval-a2"]
  );
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
