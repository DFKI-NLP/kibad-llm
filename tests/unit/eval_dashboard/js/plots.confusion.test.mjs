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
  getConfusionMatrixAggregationFromInput,
  getConfusionMatrixAggregationInput,
  getConfusionMatrixCollectionViews,
} from "../../../../docs/eval-dashboard/assets/js/plots/confusion.js";
import { createDocumentStub } from "./plots.dom-test-helpers.mjs";

const getEvaluationEffectiveValue = (evaluation, column) =>
  evaluation.overrides?.[column] ?? "";

const aggregateConfusionMatrix = (collections, fieldLabel) =>
  getConfusionMatrixAggregationFromInput(
    getConfusionMatrixAggregationInput(collections, fieldLabel)
  );

/**
 * Verify collection views and aligned mean/std aggregation for confusion matrices.
 */
test("confusion helpers wrap collection metrics and aggregate aligned cells", () => {
  const collectionData = {
    field_a: { gold: { pred: 2 } },
    field_b: { gold: { pred: 4 } },
  };
  const collections = getConfusionMatrixCollectionViews([
    {
      runDir: "run-a",
      jobReturnValue: { type: "ConfusionMatrixCollection" },
      overrides: { experiment: "exp" },
      data: collectionData,
    },
  ]);

  assert.equal(collections.length, 1);
  assert.deepEqual(Array.from(collections[0].fields.keys()), ["field_a", "field_b"]);
  assert.equal(collections[0].fields.get("field_a"), collectionData.field_a);
  assert.equal(countDistinctConfusionMatrixRuns(collections), 1);

  const aggregation = aggregateConfusionMatrix([
    { runDir: "r1", fields: new Map([["field_a", { b: { x: 2 }, UNASSIGNABLE: { UNDETECTED: 1 } }]]) },
    { runDir: "r2", fields: new Map([["field_a", { b: { x: 4 }, a: { x: 2 } }]]) },
  ], "field_a");
  assert.deepEqual(aggregation.rows, ["a", "b", "UNASSIGNABLE"]);
  assert.deepEqual(aggregation.cols, ["x", "UNDETECTED"]);
  assert.equal(aggregation.cells.get("b|#|x").mean, 3);
  assert.equal(aggregation.cells.get("a|#|x").mean, 1);

  const filtered = filterConfusionMatrixAggregationByLabelTotal(aggregation, 2);
  assert.deepEqual(filtered.rows, ["b"]);
  assert.deepEqual(filtered.cols, ["x"]);
});

/**
 * Verify confusion aggregation caches prepared per-evaluation field data lazily.
 */
test("confusion aggregation stores prepared field data on the source evaluation", () => {
  const evaluation = {
    runDir: "r1",
    jobReturnValue: { type: "ConfusionMatrixCollection" },
    data: { field_a: { gold: { pred: 2 } } },
  };
  const [collection] = getConfusionMatrixCollectionViews([evaluation]);

  const aggregation = aggregateConfusionMatrix([collection], "field_a");

  assert.equal(aggregation.cells.get("gold|#|pred").mean, 2);
  assert.ok(evaluation.dataPrepared.field_a);
  assert.deepEqual(Object.keys(evaluation), ["runDir", "jobReturnValue", "data"]);
  assert.equal(evaluation.dataPrepared.field_a.cells.get("gold|#|pred"), 2);
});

/**
 * Verify cache lookup handles metric fields that collide with object prototype names.
 */
test("confusion aggregation caches prototype-named metric fields safely", () => {
  const evaluation = {
    runDir: "r1",
    jobReturnValue: { type: "ConfusionMatrixCollection" },
    data: { toString: { gold: { pred: 3 } } },
  };
  const [collection] = getConfusionMatrixCollectionViews([evaluation]);

  const aggregation = aggregateConfusionMatrix([collection], "toString");

  assert.equal(aggregation.cells.get("gold|#|pred").mean, 3);
  assert.equal(evaluation.dataPrepared.toString.cells.get("gold|#|pred"), 3);
});

/**
 * Verify existing plain prepared-data containers are normalized before caching.
 */
test("confusion aggregation normalizes existing prepared containers for prototype keys", () => {
  const data = {};
  Object.defineProperty(data, "__proto__", {
    value: { gold: { pred: 4 } },
    enumerable: true,
    configurable: true,
  });
  const evaluation = {
    runDir: "r1",
    jobReturnValue: { type: "ConfusionMatrixCollection" },
    dataPrepared: {},
    data,
  };
  const [collection] = getConfusionMatrixCollectionViews([evaluation]);

  const aggregation = aggregateConfusionMatrix([collection], "__proto__");

  assert.equal(aggregation.cells.get("gold|#|pred").mean, 4);
  assert.equal(Object.getPrototypeOf(evaluation.dataPrepared), null);
  assert.equal(evaluation.dataPrepared.__proto__.cells.get("gold|#|pred"), 4);
});

/**
 * Verify confusion aggregation exposes reusable aligned inputs.
 */
test("confusion helpers build reusable aligned aggregation inputs", () => {
  const collections = [
    {
      runDir: "run-a",
      sourceRunDir: "source-a",
      fields: new Map([["field_a", { actual: { predicted: 2 }, filtered: { hidden: 5 } }]]),
    },
    {
      runDir: "run-b",
      sourceRunDir: "source-b",
      fields: new Map([["field_a", { actual: { predicted: 4 } }]]),
    },
  ];
  const input = getConfusionMatrixAggregationInput(collections, "field_a");
  const aggregation = getConfusionMatrixAggregationFromInput(input);

  assert.deepEqual(input.rows, ["actual", "filtered"]);
  assert.deepEqual(input.cols, ["hidden", "predicted"]);
  assert.deepEqual(input.runDirs, ["source-a", "source-b"]);
  assert.equal(input.evaluationCells[0].get("actual|#|predicted"), 2);
  assert.equal(input.evaluationCells[1].get("actual|#|predicted"), 4);
  assert.equal(aggregation.cells.get("actual|#|predicted").mean, 3);
  assert.equal(aggregation.cells.get("filtered|#|hidden").mean, 2.5);

  assert.throws(
    () => getConfusionMatrixAggregationFromInput({
      rows: [],
      cols: [],
      runDirs: ["source-a"],
      evaluationCells: [],
    }),
    /runDirs\.length \(1\) to equal evaluationCells\.length \(0\)/
  );
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
    labelFields: ["model"],
    evalTabState: {},
    matrixTabsBy: "metric_field",
    getEvaluationEffectiveValue,
    getEvaluationExperiment: (evaluation) => evaluation.overrides.experiment,
    displayPlotGroupFieldName: (field) => field,
  });
  assert.deepEqual(Array.from(metricFieldTabs.keys()), ["field_a", "field_b"]);
  assert.equal(metricFieldTabs.get("field_a").plotTab, "field_a");
  assert.equal(metricFieldTabs.get("field_a").plotTabVariant, "metric_field");
  assert.equal(metricFieldTabs.get("field_a").plots[0].label, "model=a");
  assert.equal(metricFieldTabs.get("field_a").plots[0].collections[0].fields.get("field_a"), evaluations[0].data);

  const groupTabs = buildConfusionTabMap({
    activeExperiment: "exp",
    plotGroups,
    labelFields: ["model"],
    evalTabState: {},
    matrixTabsBy: "prediction_group",
    getEvaluationEffectiveValue,
    getEvaluationExperiment: (evaluation) => evaluation.overrides.experiment,
    displayPlotGroupFieldName: (field) => field,
  });
  assert.deepEqual(Array.from(groupTabs.keys()), ["group|#|g1"]);
  assert.equal(groupTabs.get("group|#|g1").plotTab, "g1");
  assert.equal(groupTabs.get("group|#|g1").plotTabVariant, "prediction_group");
  assert.deepEqual(groupTabs.get("group|#|g1").plots.map((plot) => plot.label), ["field_a", "field_b"]);

  const buildTabsWithMode = (matrixTabsBy) => buildConfusionTabMap({
    activeExperiment: "exp",
    plotGroups,
    labelFields: ["model"],
    evalTabState: {},
    matrixTabsBy,
    getEvaluationEffectiveValue,
    getEvaluationExperiment: (evaluation) => evaluation.overrides.experiment,
    displayPlotGroupFieldName: (field) => field,
  });
  assert.throws(
    () => buildTabsWithMode(),
    /Unsupported matrix plot tab variant: \(missing\)/
  );
  assert.throws(
    () => buildTabsWithMode("unknown"),
    /Unsupported matrix plot tab variant: unknown/
  );
});

/**
 * Verify malformed confusion-matrix metric records fail at the adapter boundary.
 */
test("confusion collection views reject missing fields and malformed collection data", () => {
  assert.throws(
    () => getConfusionMatrixCollectionViews([
      { runDir: "r1", overrides: {}, jobReturnValue: { type: "ConfusionMatrix" }, data: {} },
    ], { evalTabState: {}, getEvaluationEffectiveValue }),
    /ConfusionMatrix evaluation must define a non-empty metric\.field\./
  );

  assert.throws(
    () => getConfusionMatrixCollectionViews([
      { runDir: "r1", jobReturnValue: { type: "ConfusionMatrixCollection" }, data: [] },
    ]),
    /ConfusionMatrixCollection data must be an object mapping metric fields to metric data\./
  );

  assert.throws(
    () => getConfusionMatrixCollectionViews([
      {
        runDir: "r1",
        jobReturnValue: { type: "ConfusionMatrixCollection" },
        data: { " field_a ": {}, field_a: {} },
      },
    ]),
    /ConfusionMatrixCollection data contains duplicate metric field "field_a" after normalization\./
  );

  assert.throws(
    () => aggregateConfusionMatrix([
      { runDir: "r1", fields: new Map([["field_b", {}]]) },
    ], "field_a"),
    /ConfusionMatrix collection view is missing metric field "field_a"\./
  );

  assert.throws(
    () => aggregateConfusionMatrix([
      { runDir: "r1", fields: new Map([["field_a", { actual: [] }]]) },
    ], "field_a"),
    /ConfusionMatrix field "field_a" actual label "actual" must map to object predicted-label data\./
  );

  assert.throws(
    () => aggregateConfusionMatrix([
      { runDir: "r1", fields: new Map([["field_a", { actual: { predicted: "1" } }]]) },
    ], "field_a"),
    /ConfusionMatrix field "field_a" cell "actual" -> "predicted" must be a finite number\./
  );

  assert.throws(
    () => aggregateConfusionMatrix([
      {
        runDir: "r1",
        fields: new Map([["field_a", { actual: { "predicted|#|label": 1 } }]]),
      },
    ], "field_a"),
    /predicted label "predicted\|#\|label" must not contain reserved matrix key delimiter "\|#\|"/
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
