/**
 * Browser-free logic tests for the eval-dashboard flattening utilities.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  flattenObject,
  getValueAtPath,
  omitTopLevelKeys,
} from "../../../../docs/eval-dashboard/assets/js/utils/flatten.js";

/**
 * Ensure nested objects and arrays keep the Phase 5 flattening contract.
 */
test("flattenObject preserves nested-object and array serialization behavior", () => {
  assert.deepEqual(flattenObject({ alpha: { beta: 3 }, gamma: [1, 2], delta: null }, "root"), {
    "root.alpha.beta": 3,
    "root.gamma": "[1,2]",
    "root.delta": null,
  });
});

/**
 * Ensure omission and path traversal helpers keep their current lookup semantics.
 */
test("flatten helpers preserve shallow omit and path lookup behavior", () => {
  assert.deepEqual(
    {
      omitted: omitTopLevelKeys({ keep: 1, drop: 2, nested: { x: 3 } }, new Set(["drop"])),
      nestedValue: getValueAtPath({ alpha: { beta: { gamma: 7 } } }, ["alpha", "beta", "gamma"]),
      missingValue: getValueAtPath({ alpha: {} }, ["alpha", "beta"]),
    },
    {
      omitted: { keep: 1, nested: { x: 3 } },
      nestedValue: 7,
      missingValue: null,
    }
  );
});
