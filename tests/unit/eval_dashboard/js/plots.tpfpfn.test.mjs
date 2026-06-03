/**
 * Tests for eval-dashboard TP/FP/FN plot helper seams.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildTpFpFnCellSummary,
  buildTpFpFnTabMap,
  filterTpFpFnAggregationByTotals,
  getTpFpFnCombinedAggregation,
  getTpFpFnOutcomeColor,
  normalizeTpFpFnCollectorData,
  normalizeTpFpFnLikeEvaluations,
} from "../../../../docs/eval-dashboard/assets/js/plots/tpfpfn.js";

const getEvaluationEffectiveValue = (evaluation, column) =>
  evaluation.overrides?.[column] ?? "";

/**
 * Verify both TP/FP/FN input shapes normalize into stable per-record buckets.
 */
test("tpfpfn helpers normalize collector data and aggregate row states", () => {
  assert.deepEqual(
    normalizeTpFpFnCollectorData({
      doc2: { tp: ["B"], fp: ["A"], fn: [] },
      doc1: { tp: ["A", "A"], fp: [], fn: ["C"] },
    }),
    {
      doc1: { tp: ["A"], fp: [], fn: ["C"] },
      doc2: { tp: ["B"], fp: ["A"], fn: [] },
    }
  );

  assert.deepEqual(
    normalizeTpFpFnCollectorData({
      tp: [["doc1", "A"]],
      fp: [["doc2", "B"]],
      fn: [["doc1", "C"]],
    }),
    {
      doc1: { tp: ["A"], fp: [], fn: ["C"] },
      doc2: { tp: [], fp: ["B"], fn: [] },
    }
  );

  const aggregation = getTpFpFnCombinedAggregation([
    { runDir: "r1", data: { doc1: { tp: ["A"], fp: [], fn: ["B"] } } },
    { runDir: "r2", data: { doc1: { tp: [], fp: ["A"], fn: [] }, doc2: { tp: ["C"], fp: [], fn: [] } } },
  ]);
  assert.deepEqual(aggregation.rows, ["doc1", "doc2"]);
  assert.deepEqual(aggregation.cols, ["A", "B", "C"]);
  assert.deepEqual(aggregation.cells.get("doc1|#|A").counts, { tp: 1, fp: 1, fn: 0, empty: 0 });
  assert.deepEqual(aggregation.cells.get("doc2|#|C").counts, { tp: 1, fp: 0, fn: 0, empty: 1 });

  const filtered = filterTpFpFnAggregationByTotals(aggregation, 2, 1);
  assert.deepEqual(filtered.rows, ["doc1"]);
  assert.deepEqual(filtered.cols, ["A"]);
});

/**
 * Verify TP/FP/FN collection expansion, tab grouping, cell summaries, and palette output.
 */
test("tpfpfn helpers expand collection metrics, build tab maps, and summarize cells", () => {
  const expanded = normalizeTpFpFnLikeEvaluations([
    {
      runDir: "run-a",
      jobReturnValue: { type: "TpFpFnCollectorCollection" },
      data: {
        "outer.field_a": { doc: { tp: ["A"] } },
        "outer.field_b": { doc: { fp: ["B"] } },
      },
    },
  ]);
  assert.deepEqual(expanded.map((evaluation) => evaluation.overrides["metric.field"]), ["outer.field_a", "outer.field_b"]);

  const evaluations = expanded.map((evaluation) => ({
    ...evaluation,
    overrides: { ...evaluation.overrides, experiment: "exp" },
  }));
  const tabMap = buildTpFpFnTabMap({
    plotGroups: [{ groupId: "g1", values: { model: "a" }, evaluations }],
    experimentEvaluations: evaluations,
    labelFields: ["model"],
    evalTabState: {},
    confusionTabsBy: "metric_field",
    getEvaluationEffectiveValue,
    displayPlotGroupFieldName: (field) => field,
    shortenLabels: true,
  });
  assert.deepEqual(Array.from(tabMap.keys()), ["outer.field_a", "outer.field_b"]);
  assert.deepEqual(Array.from(tabMap.values()).map((entry) => entry.label), ["field_a", "field_b"]);

  const summary = buildTpFpFnCellSummary(
    "doc",
    "A",
    {
      rowStates: [{ tp: true, fp: false, fn: false }, { tp: false, fp: true, fn: false }],
      counts: { tp: 1, fp: 1, fn: 0, empty: 0 },
    },
    2,
    ["r1", "r2"],
    2
  );
  assert.equal(summary.payload.percentages.tp, 50);
  assert.deepEqual(summary.payload.evaluations.map((entry) => entry.value), ["TP", "FP"]);
  assert.equal(getTpFpFnOutcomeColor("tp"), "rgb(22, 163, 74)");
});
