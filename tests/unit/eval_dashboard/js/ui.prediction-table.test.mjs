/**
 * Browser-free logic tests for eval-dashboard prediction-table helpers.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildPredictionColumnSections,
  buildPredictionGroupRowModel,
  buildPredictionMemberRowModel,
  renderPredictionTable,
} from "../../../../docs/eval-dashboard/assets/js/ui/prediction-table.js";

/**
 * Minimal classList stub for DOM-free prediction-table tests.
 */
class FakeClassList {
  /**
   * Create one empty class list.
   */
  constructor() {
    this.values = new Set();
  }

  /**
   * Add one or more class names.
   *
   * @param {...string} names - Class names to add.
   * @returns {void}
   */
  add(...names) {
    names.forEach((name) => this.values.add(name));
  }

  /**
   * Toggle one class name according to the provided force value.
   *
   * @param {string} name - Class name to update.
   * @param {boolean} force - Whether the class should be present.
   * @returns {void}
   */
  toggle(name, force) {
    if (force) {
      this.values.add(name);
    } else {
      this.values.delete(name);
    }
  }

  /**
   * Report whether the class list contains one class.
   *
   * @param {string} name - Class name to check.
   * @returns {boolean} Whether the class is present.
   */
  contains(name) {
    return this.values.has(name);
  }
}

/**
 * Minimal element stub used by the extracted prediction-table tests.
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
    this.className = "";
    this.textContent = "";
    this.title = "";
    this.children = [];
    this.attributes = new Map();
    this.listeners = new Map();
    this.style = {};
    this.checked = false;
    this.indeterminate = false;
    this.rowSpan = 1;
    this._innerHTML = "";
    this.classList = new FakeClassList();
  }

  /**
   * Reset child nodes when the test clears innerHTML.
   *
   * @param {unknown} value - Assigned HTML value.
   */
  set innerHTML(value) {
    this._innerHTML = String(value);
    if (value === "") {
      this.children = [];
    }
  }

  /**
   * Return the last assigned innerHTML value.
   *
   * @returns {string} Stored HTML content.
   */
  get innerHTML() {
    return this._innerHTML;
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
 * Verify that prediction columns are split into the same section ordering now rendered by the extracted module.
 */
test("buildPredictionColumnSections groups override, job_return_value, and other columns", () => {
  assert.deepEqual(
    buildPredictionColumnSections({
      predictionColumns: [
        "prediction.content.title",
        "prediction.job_return_value.output_file",
        "prediction.overrides.dataset",
      ],
      predictionJobReturnValuePrefix: "prediction.job_return_value.",
      predictionOverridesPrefix: "prediction.overrides.",
    }),
    [
      { label: "overrides", columns: ["prediction.overrides.dataset"] },
      {
        label: "job_return_value",
        columns: ["prediction.job_return_value.output_file"],
      },
      { label: "other", columns: ["prediction.content.title"] },
    ]
  );
});

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

/**
 * Verify that the extracted prediction-table renderer wires shared headers, toggles, and expanded member rows.
 */
test("renderPredictionTable renders extracted headers and forwards interaction callbacks", () => {
  const documentLike = createDocumentStub();
  const tableElement = new FakeElement("table");
  const callbackLog = {
    sort: [],
    groupBy: [],
    selectAll: [],
    expand: [],
    select: [],
  };
  const displayedGroups = [
    {
      groupId: "prediction-group-1",
      predictions: [
        { predictionFlat: { "prediction.language": "de", "prediction.run_dir": "run-a" } },
      ],
    },
  ];

  const selectionState = renderPredictionTable({
    documentLike,
    tableElement,
    predictionSections: [
      { label: "other", columns: ["prediction.language", "prediction.run_dir"] },
    ],
    orderedPredictionColumns: ["prediction.language", "prediction.run_dir"],
    displayedGroups,
    predictionSort: [{ column: "prediction.language", direction: "asc" }],
    truncateEnabledColumns: new Set(["prediction.language"]),
    groupByFields: ["prediction.language"],
    selectedGroupIds: new Set(),
    expandedGroupIds: new Set(["prediction-group-1"]),
    displayColumnName: (column) => `Label:${column}`,
    onSortToggle(column, event) {
      callbackLog.sort.push({ column, event });
    },
    onToggleGroupByColumn(column, checked) {
      callbackLog.groupBy.push({ column, checked });
    },
    onToggleGroupExpansion(groupId) {
      callbackLog.expand.push(groupId);
    },
    onToggleGroupSelection(groupId, checked) {
      callbackLog.select.push({ groupId, checked });
    },
    onSelectAllDisplayed(checked, displayedGroupIds) {
      callbackLog.selectAll.push({ checked, displayedGroupIds });
    },
    getGroupValueDisplay(group, column) {
      return `${group.groupId}:${column}`;
    },
    getSortedPredictionMembers(predictions) {
      return predictions;
    },
    getPredictionEffectiveValue(predictionFlat, column) {
      return predictionFlat[column] || "";
    },
    sortableControlColumns: new Set(["expand", "select", "group_size"]),
  });

  assert.deepEqual(selectionState, {
    displayedGroupIds: ["prediction-group-1"],
    selectedCount: 0,
    allSelected: false,
    someSelected: false,
  });
  assert.equal(tableElement.children.length, 2);

  const thead = tableElement.children[0];
  const tbody = tableElement.children[1];
  const sectionRow = thead.children[0];
  const columnRow = thead.children[1];
  assert.equal(sectionRow.children[3].textContent, "other");
  assert.equal(columnRow.children.length, 2);

  const languageHeader = columnRow.children[0];
  assert.equal(languageHeader.getAttribute("aria-sort"), "ascending");
  assert.equal(languageHeader.classList.contains("truncate-enabled"), true);
  const groupByToggle = languageHeader.children[0].children[1].children[0];
  assert.equal(groupByToggle.getAttribute("aria-label"), "Group by Label:prediction.language");
  assert.equal(groupByToggle.checked, true);
  groupByToggle.checked = false;
  groupByToggle.listeners.get("change")({ type: "change" });
  assert.deepEqual(callbackLog.groupBy, [{ column: "prediction.language", checked: false }]);

  const selectAllCheckbox = sectionRow.children[1].children[0].children[1];
  selectAllCheckbox.checked = true;
  selectAllCheckbox.listeners.get("change")({ type: "change" });
  assert.deepEqual(callbackLog.selectAll, [
    { checked: true, displayedGroupIds: ["prediction-group-1"] },
  ]);

  assert.equal(tbody.children.length, 2);
  const groupRow = tbody.children[0];
  const expandButton = groupRow.children[0].children[0];
  assert.equal(expandButton.textContent, "-");
  expandButton.listeners.get("click")({ type: "click" });
  assert.deepEqual(callbackLog.expand, ["prediction-group-1"]);

  const selectionCheckbox = groupRow.children[1].children[0];
  selectionCheckbox.checked = true;
  selectionCheckbox.listeners.get("change")({ type: "change" });
  assert.deepEqual(callbackLog.select, [{ groupId: "prediction-group-1", checked: true }]);

  assert.equal(groupRow.children[3].classList.contains("truncate-enabled"), true);
  const memberRow = tbody.children[1];
  assert.equal(memberRow.className, "member-row");
  assert.equal(memberRow.children[2].textContent, "member");
  assert.equal(memberRow.children[3].textContent, "de");
});
