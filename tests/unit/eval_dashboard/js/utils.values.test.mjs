/**
 * Browser-free logic tests for the eval-dashboard value utilities.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  collectSuggestionValues,
  formatRounded,
  getColumnsWithMultipleValues,
  getEffectiveValue,
  getStableObjectSignature,
  interpolateColor,
  isMissingValue,
  meanAndStd,
  normalizeValue,
} from "../../../../docs/eval-dashboard/assets/js/utils/values.js";

/**
 * Ensure value normalization, missing-value handling, and defaulting stay unchanged.
 */
test("value helpers preserve normalization and defaulting behavior", () => {
  assert.equal(normalizeValue({ foo: "bar" }), '{"foo":"bar"}');
  assert.equal(isMissingValue("   "), true);
  assert.equal(getEffectiveValue("", "fallback"), "fallback");
  assert.deepEqual(collectSuggestionValues(["beta", "", "Alpha", "beta", null]), ["Alpha", "beta"]);
});

/**
 * Ensure signature-building and numeric display helpers keep their current semantics.
 */
test("value helpers preserve signatures and numeric helper semantics", () => {
  assert.deepEqual(
    {
      varyingColumns: getColumnsWithMultipleValues(
        [
          { values: { a: "same", b: 1 } },
          { values: { a: "same", b: 2 } },
          { values: { a: "same", b: 2 } },
        ],
        ["a", "b"],
        (item, column) => item.values[column]
      ),
      stableSignature: getStableObjectSignature({ b: 2, a: null, c: { nested: true } }),
      stats: meanAndStd([2, 4, 4, 4, 5, 5, 7, 9]),
      rounded: formatRounded(3.14159, 2),
      interpolated: interpolateColor([0, 0, 0], [255, 255, 255], 0.5),
    },
    {
      varyingColumns: ["b"],
      stableSignature: '{"a":"","b":"2","c":"{\\"nested\\":true}"}',
      stats: { mean: 5.0, std: 2.0 },
      rounded: "3.14",
      interpolated: "rgb(128, 128, 128)",
    }
  );
});
