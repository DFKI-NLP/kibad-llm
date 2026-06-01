import assert from "node:assert/strict";
import test from "node:test";

import {
  flattenObject,
  getValueAtPath,
  omitTopLevelKeys,
} from "../../../../docs/eval-dashboard/assets/js/utils/flatten.js";
import {
  compareSortableValues,
  normalizeSortConfig,
  sortItems,
} from "../../../../docs/eval-dashboard/assets/js/utils/sort.js";
import {
  getFigureTitlePrefix,
  sanitizeFigureFilename,
  splitLabelByLastDot,
} from "../../../../docs/eval-dashboard/assets/js/utils/text.js";
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

test("flattenObject preserves nested-object and array serialization behavior", () => {
  assert.deepEqual(flattenObject({ alpha: { beta: 3 }, gamma: [1, 2], delta: null }, "root"), {
    "root.alpha.beta": 3,
    "root.gamma": "[1,2]",
    "root.delta": null,
  });
});

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

test("sort helpers preserve normalization, blank-last ordering, and stable sorting", () => {
  const items = [
    { name: "item-1", value: "10" },
    { name: "item-2", value: "" },
    { name: "item-3", value: "2" },
    { name: "item-4", value: "2" },
  ];

  assert.deepEqual(
    normalizeSortConfig(
      [
        { column: "value", direction: "asc" },
        { column: "value", direction: "desc" },
        { column: "ignored", direction: "asc" },
        { column: "name", direction: "sideways" },
      ],
      ["value", "name"]
    ),
    [{ column: "value", direction: "asc" }]
  );
  assert.ok(compareSortableValues("", "3") > 0);
  assert.ok(compareSortableValues("2", "10") < 0);
  assert.ok(compareSortableValues("Beta", "alpha") > 0);
  assert.deepEqual(
    sortItems(items, [{ column: "value", direction: "asc" }], (item, column) => item[column]).map(
      (item) => item.name
    ),
    ["item-3", "item-4", "item-1", "item-2"]
  );
});

test("value helpers preserve normalization and defaulting behavior", () => {
  assert.equal(normalizeValue({ foo: "bar" }), '{"foo":"bar"}');
  assert.equal(isMissingValue("   "), true);
  assert.equal(getEffectiveValue("", "fallback"), "fallback");
  assert.deepEqual(collectSuggestionValues(["beta", "", "Alpha", "beta", null]), ["Alpha", "beta"]);
});

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

test("text helpers preserve plot-title and filename sanitization behavior", () => {
  assert.deepEqual(
    {
      titlePrefix: getFigureTitlePrefix("Accuracy (mean ± std) (4 grouped evals per cell)"),
      sanitizedFilename: sanitizeFigureFilename('  bad<>:"/\\|?* name.  '),
      splitLabel: splitLabelByLastDot("metric.section.score"),
    },
    {
      titlePrefix: "Accuracy",
      sanitizedFilename: "bad - name",
      splitLabel: "score",
    }
  );
});
