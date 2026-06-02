import test from "node:test";
import assert from "node:assert/strict";

import {
  formatSortLabel,
  getAriaSort,
  getDefaultSortDirection,
  getNextSortConfig,
} from "../../../../docs/eval-dashboard/assets/js/ui/table-shared.js";

const SORTABLE_CONTROL_COLUMNS = new Set(["expand", "select", "group_size"]);

function displayColumnName(column) {
  return `label:${column}`;
}

test("control columns default to descending while data columns default to ascending", () => {
  assert.equal(getDefaultSortDirection("select", SORTABLE_CONTROL_COLUMNS), "desc");
  assert.equal(getDefaultSortDirection("prediction.content.title", SORTABLE_CONTROL_COLUMNS), "asc");
});

test("single-column sort toggles cycle through default direction, opposite direction, then cleared", () => {
  const ascendingColumn = "prediction.content.title";
  const descendingColumn = "select";

  assert.deepEqual(
    getNextSortConfig([], ascendingColumn, { sortableControlColumns: SORTABLE_CONTROL_COLUMNS }),
    [{ column: ascendingColumn, direction: "asc" }]
  );
  assert.deepEqual(
    getNextSortConfig([{ column: ascendingColumn, direction: "asc" }], ascendingColumn, {
      sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
    }),
    [{ column: ascendingColumn, direction: "desc" }]
  );
  assert.deepEqual(
    getNextSortConfig([{ column: ascendingColumn, direction: "desc" }], ascendingColumn, {
      sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
    }),
    []
  );

  assert.deepEqual(
    getNextSortConfig([], descendingColumn, { sortableControlColumns: SORTABLE_CONTROL_COLUMNS }),
    [{ column: descendingColumn, direction: "desc" }]
  );
  assert.deepEqual(
    getNextSortConfig([{ column: descendingColumn, direction: "desc" }], descendingColumn, {
      sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
    }),
    [{ column: descendingColumn, direction: "asc" }]
  );
  assert.deepEqual(
    getNextSortConfig([{ column: descendingColumn, direction: "asc" }], descendingColumn, {
      sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
    }),
    []
  );
});

test("append mode preserves existing sorts while toggling one column", () => {
  const currentSort = [{ column: "prediction.id", direction: "asc" }];

  assert.deepEqual(
    getNextSortConfig(currentSort, "group_size", {
      append: true,
      sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
    }),
    [
      { column: "prediction.id", direction: "asc" },
      { column: "group_size", direction: "desc" },
    ]
  );

  assert.deepEqual(
    getNextSortConfig(
      [
        { column: "prediction.id", direction: "asc" },
        { column: "group_size", direction: "desc" },
      ],
      "group_size",
      {
        append: true,
        sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
      }
    ),
    [
      { column: "prediction.id", direction: "asc" },
      { column: "group_size", direction: "asc" },
    ]
  );
});

test("formatSortLabel renders special control-column labels and priorities", () => {
  assert.equal(formatSortLabel([], displayColumnName), "(none)");
  assert.equal(
    formatSortLabel(
      [
        { column: "select", direction: "desc" },
        { column: "prediction.id", direction: "asc" },
      ],
      displayColumnName
    ),
    "selected ↓ (1), label:prediction.id ↑ (2)"
  );
});

test("getAriaSort reports only the primary active sort column", () => {
  const sortConfig = [
    { column: "prediction.id", direction: "desc" },
    { column: "group_size", direction: "asc" },
  ];

  assert.equal(getAriaSort(sortConfig, "prediction.id"), "descending");
  assert.equal(getAriaSort(sortConfig, "group_size"), "none");
  assert.equal(getAriaSort([], "prediction.id"), "none");
});

