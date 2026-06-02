/**
 * Browser-free logic tests for eval-dashboard shared table helpers.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  createSortButton,
  createTruncatingCell,
  formatSortLabel,
  getAriaSort,
  getDefaultSortDirection,
  getNextSortConfig,
  updateStickyControlColumnOffsets,
} from "../../../../docs/eval-dashboard/assets/js/ui/table-shared.js";

const SORTABLE_CONTROL_COLUMNS = new Set(["expand", "select", "group_size"]);

/**
 * Format one column name for deterministic label assertions.
 *
 * @param {string} column - Column name to format.
 * @returns {string} Stable display label used by the tests.
 */
function displayColumnName(column) {
  return `label:${column}`;
}

/**
 * Minimal element stub for DOM-free shared-table rendering tests.
 */
class FakeElement {
  /**
   * Create one fake element instance with the properties used by the tests.
   *
   * @param {string} [tagName="div"] - Tag name to expose on the fake element.
   */
  constructor(tagName = "div") {
    this.tagName = tagName.toUpperCase();
    this.type = "";
    this.textContent = "";
    this.title = "";
    this.className = "";
    this.children = [];
    this.attributes = new Map();
    this.listeners = new Map();
    this.style = {
      props: {},
      setProperty: (name, value) => {
        this.style.props[name] = value;
      },
    };
    this.classList = {
      values: new Set(),
      add: (...names) => names.forEach((name) => this.classList.values.add(name)),
      contains: (name) => this.classList.values.has(name),
    };
  }

  /**
   * Append one child element.
   *
   * @param {FakeElement} child - Child element to append.
   * @returns {FakeElement} The appended child.
   */
  appendChild(child) {
    this.children.push(child);
    return child;
  }

  /**
   * Store one attribute value.
   *
   * @param {string} name - Attribute name.
   * @param {unknown} value - Attribute value.
   * @returns {void}
   */
  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  /**
   * Read one stored attribute value.
   *
   * @param {string} name - Attribute name.
   * @returns {string | undefined} Stored attribute value.
   */
  getAttribute(name) {
    return this.attributes.get(name);
  }

  /**
   * Register one event listener.
   *
   * @param {string} type - Event type.
   * @param {Function} listener - Event callback.
   * @returns {void}
   */
  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }
}

/**
 * Build one document-like stub that can create fake elements.
 *
 * @returns {{createElement: (tagName: string) => FakeElement}} Document-like stub.
 */
function createDocumentStub() {
  return {
    createElement(tagName) {
      return new FakeElement(tagName);
    },
  };
}

/**
 * Verify the default sort direction split between control columns and data columns.
 */
test("control columns default to descending while data columns default to ascending", () => {
  assert.equal(getDefaultSortDirection("select", SORTABLE_CONTROL_COLUMNS), "desc");
  assert.equal(getDefaultSortDirection("prediction.content.title", SORTABLE_CONTROL_COLUMNS), "asc");
});

/**
 * Verify the single-column sort toggle cycle across both ascending-first and descending-first columns.
 */
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

/**
 * Verify that append-mode sorting updates one column while preserving the others.
 */
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

  assert.deepEqual(
    getNextSortConfig(
      [
        { column: "prediction.id", direction: "asc" },
        { column: "group_size", direction: "asc" },
      ],
      "group_size",
      {
        append: true,
        sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
      }
    ),
    [{ column: "prediction.id", direction: "asc" }]
  );
});

/**
 * Verify that the shared sort-label formatter reports control labels and sort priorities.
 */
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

/**
 * Verify that `aria-sort` is exposed only for the primary active sort column.
 */
test("getAriaSort reports only the primary active sort column", () => {
  const sortConfig = [
    { column: "prediction.id", direction: "desc" },
    { column: "group_size", direction: "asc" },
  ];

  assert.equal(getAriaSort(sortConfig, "prediction.id"), "descending");
  assert.equal(getAriaSort(sortConfig, "group_size"), "none");
  assert.equal(getAriaSort([], "prediction.id"), "none");
});

/**
 * Verify that the shared sort-button renderer exposes indicator, tooltip, and click behavior.
 */
test("createSortButton exposes indicator, aria metadata, and click handling", () => {
  const documentLike = createDocumentStub();
  const events = [];
  const button = createSortButton({
    documentLike,
    label: "select",
    column: "select",
    sortConfig: [
      { column: "prediction.id", direction: "asc" },
      { column: "select", direction: "desc" },
    ],
    onToggle(event) {
      events.push(event);
    },
    sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
  });

  assert.equal(button.tagName, "BUTTON");
  assert.equal(button.type, "button");
  assert.equal(button.className, "header-sort-button active");
  assert.equal(
    button.title,
    "Click: sort only by select ascending. Shift-click: add, toggle, or remove select in multi-column sorting."
  );
  assert.equal(button.getAttribute("aria-label"), "select, sort priority 2, descending");
  assert.equal(button.children[0].textContent, "select");
  assert.equal(button.children[1].textContent, "▼2");
  assert.equal(button.children[1].getAttribute("aria-hidden"), "true");

  let propagationStopped = false;
  const clickEvent = {
    stopPropagation() {
      propagationStopped = true;
    },
  };
  button.listeners.get("click")(clickEvent);

  assert.equal(propagationStopped, true);
  assert.deepEqual(events, [clickEvent]);
});

/**
 * Verify that unsorted columns render the inactive shared sort-button state.
 */
test("createSortButton renders the inactive button state when the column is not sorted", () => {
  const documentLike = createDocumentStub();
  const button = createSortButton({
    documentLike,
    label: "title",
    column: "prediction.content.title",
    sortConfig: [],
    onToggle() {},
    sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
  });

  assert.equal(button.className, "header-sort-button");
  assert.equal(button.getAttribute("aria-label"), "title, not sorted");
  assert.equal(button.children[1].textContent, "↕");
});

/**
 * Verify that truncating-cell rendering preserves text and toggles the shared truncation class.
 */
test("createTruncatingCell keeps text content and the shared truncation class semantics", () => {
  const documentLike = createDocumentStub();
  const truncatedCell = createTruncatingCell({
    documentLike,
    content: "long value",
    columnKey: "prediction.id",
    truncateEnabledColumns: new Set(["prediction.id"]),
  });
  const normalCell = createTruncatingCell({
    documentLike,
    content: "short value",
    columnKey: "prediction.id",
    truncateEnabledColumns: new Set(),
  });

  assert.equal(truncatedCell.tagName, "TD");
  assert.equal(truncatedCell.textContent, "long value");
  assert.equal(truncatedCell.classList.contains("truncate-enabled"), true);
  assert.equal(normalCell.classList.contains("truncate-enabled"), false);
});

/**
 * Verify that sticky control-column offsets are computed and reset according to measured headers.
 */
test("updateStickyControlColumnOffsets computes sticky offsets and resets missing headers", () => {
  assert.doesNotThrow(() => updateStickyControlColumnOffsets(null));

  const shortTable = new FakeElement("table");
  shortTable.tHead = { rows: [{ cells: [new FakeElement("th")] }] };

  updateStickyControlColumnOffsets(shortTable);
  assert.deepEqual(shortTable.style.props, {
    "--sticky-col-1-left": "0px",
    "--sticky-col-2-left": "0px",
    "--sticky-col-3-left": "0px",
    "--sticky-header-row-1-height": "0px",
  });

  const makeCell = (width, height, rowSpan = 2) => ({
    rowSpan,
    getBoundingClientRect() {
      return { width, height };
    },
  });
  const measuredTable = new FakeElement("table");
  measuredTable.tHead = {
    rows: [
      {
        cells: [
          makeCell(12.1, 20),
          makeCell(18.2, 20),
          makeCell(25.9, 20),
          makeCell(40, 10.1, 1),
        ],
      },
    ],
  };

  updateStickyControlColumnOffsets(measuredTable);
  assert.deepEqual(measuredTable.style.props, {
    "--sticky-col-1-left": "0px",
    "--sticky-col-2-left": "13px",
    "--sticky-col-3-left": "32px",
    "--sticky-header-row-1-height": "11px",
  });
});
