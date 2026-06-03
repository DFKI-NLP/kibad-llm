/**
 * Browser-free logic tests for eval-dashboard prediction-table helpers.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildPredictionGroupRowModel,
  buildPredictionMemberRowModel,
} from "../../../../docs/eval-dashboard/assets/js/ui/prediction-table.js";

/**
 * Verify that grouped prediction rows expose stable size, expansion, selection, and value-cell models.
 */
test("buildPredictionGroupRowModel derives stable grouped-row models", () => {
  const group = {
    groupId: "prediction-group-1",
    predictions: [{ id: "p1" }, { id: "p2" }],
    values: {
      "prediction.language": "de",
      "prediction.run_dir": "run-1",
    },
  };

  const model = buildPredictionGroupRowModel({
    group,
    orderedColumns: ["prediction.language", "prediction.run_dir"],
    isExpanded: true,
    isSelected: false,
    getGroupValueDisplay: (candidateGroup, column) => `${candidateGroup.groupId}:${column}`,
  });

  assert.deepEqual(model, {
    groupId: "prediction-group-1",
    groupSize: 2,
    isExpanded: true,
    isSelected: false,
    valueCells: [
      {
        column: "prediction.language",
        content: "prediction-group-1:prediction.language",
      },
      {
        column: "prediction.run_dir",
        content: "prediction-group-1:prediction.run_dir",
      },
    ],
  });
});

/**
 * Verify that expanded prediction-member rows expose the stable member label and effective-value cells.
 */
test("buildPredictionMemberRowModel derives stable expanded-member models", () => {
  const member = {
    predictionFlat: {
      "prediction.language": "en",
      "prediction.run_dir": "run-2",
    },
  };

  const model = buildPredictionMemberRowModel({
    member,
    orderedColumns: ["prediction.language", "prediction.run_dir"],
    getPredictionEffectiveValue: (predictionFlat, column) => predictionFlat[column] || "",
  });

  assert.deepEqual(model, {
    groupSizeLabel: "member",
    valueCells: [
      {
        column: "prediction.language",
        content: "en",
      },
      {
        column: "prediction.run_dir",
        content: "run-2",
      },
    ],
  });
});
