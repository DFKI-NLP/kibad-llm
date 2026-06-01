/**
 * Browser-free logic tests for the eval-dashboard sorting utilities.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  compareSortableValues,
  normalizeSortConfig,
  sortItems,
} from "../../../../docs/eval-dashboard/assets/js/utils/sort.js";

/**
 * Ensure sort normalization and stable ordering remain behavior-equivalent after extraction.
 */
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
