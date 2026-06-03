/**
 * Browser-free logic tests for eval-dashboard evaluation-table helpers.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildEvaluationGroupRowModel,
  buildEvaluationMemberRowModel,
} from "../../../../docs/eval-dashboard/assets/js/ui/evaluation-table.js";

/**
 * Verify that grouped evaluation rows expose stable values plus the shared run-dir meta cell.
 */
test("buildEvaluationGroupRowModel derives stable grouped-row models", () => {
  const group = {
    groupId: "eval-group-1",
    evaluations: [
      { runDir: "logs/run-a", values: { "metric.field": "title", "metric.score": "0.70" } },
      { runDir: "logs/run-b", values: { "metric.field": "title", "metric.score": "0.80" } },
    ],
  };
  const evalTabState = {
    truncateEnabledColumns: new Set(),
  };

  const model = buildEvaluationGroupRowModel({
    group,
    orderedColumns: ["metric.field", "metric.score"],
    evalTabState,
    isExpanded: false,
    isSelected: true,
    getGroupValueDisplayFromEvaluations: (evaluations, getter) =>
      evaluations.map((evaluation) => getter(evaluation)).join(" | "),
    getEvaluationEffectiveValue: (evaluation, column) => evaluation.values[column] || "",
  });

  assert.deepEqual(model, {
    groupId: "eval-group-1",
    groupSize: 2,
    isExpanded: false,
    isSelected: true,
    valueCells: [
      {
        column: "metric.field",
        content: "title | title",
      },
      {
        column: "metric.score",
        content: "0.70 | 0.80",
      },
    ],
    runDirValue: "logs/run-a | logs/run-b",
  });
});

/**
 * Verify that expanded evaluation-member rows preserve selection state and normalize the run-dir cell.
 */
test("buildEvaluationMemberRowModel derives stable expanded-member models", () => {
  const evaluation = {
    runDir: " logs/run-c ",
    values: {
      "metric.field": "summary",
      "metric.score": "0.95",
    },
  };
  const evalTabState = {
    truncateEnabledColumns: new Set(),
  };

  const model = buildEvaluationMemberRowModel({
    evaluation,
    orderedColumns: ["metric.field", "metric.score"],
    evalTabState,
    isSelected: true,
    getEvaluationEffectiveValue: (candidateEvaluation, column) => candidateEvaluation.values[column] || "",
  });

  assert.deepEqual(model, {
    runDir: " logs/run-c ",
    runDirValue: " logs/run-c ",
    isSelected: true,
    groupSizeLabel: "member",
    valueCells: [
      {
        column: "metric.field",
        content: "summary",
      },
      {
        column: "metric.score",
        content: "0.95",
      },
    ],
  });
});
