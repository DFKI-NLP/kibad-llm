/**
 * Browser-free logic tests for eval-dashboard evaluation-table helpers.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildEvaluationColumnSections,
  buildEvaluationGroupRowModel,
  buildEvaluationMemberRowModel,
  renderEvaluationTable,
} from "../../../../docs/eval-dashboard/assets/js/ui/evaluation-table.js";

/**
 * Minimal classList stub for DOM-free evaluation-table tests.
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
 * Minimal element stub used by the extracted evaluation-table tests.
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
 * Verify that evaluation columns are split into override and job_return_value sections by the extracted module.
 */
test("buildEvaluationColumnSections groups override and job_return_value columns", () => {
  assert.deepEqual(
    buildEvaluationColumnSections(
      ["evaluation.overrides.metric", "evaluation.job_return_value.metric_type"],
      {
        isJobReturnValueColumn: (column) => column.startsWith("evaluation.job_return_value."),
      }
    ),
    [
      { label: "overrides", columns: ["evaluation.overrides.metric"] },
      {
        label: "job_return_value",
        columns: ["evaluation.job_return_value.metric_type"],
      },
    ]
  );
});

/**
 * Verify that grouped evaluation rows expose stable values plus the shared run-dir meta cell.
 */
test("buildEvaluationGroupRowModel derives stable grouped-row models", () => {
  const group = {
    groupId: "eval-group-1",
    evaluations: [
      { runId: "run-a-id", runDir: "logs/run-a", values: { "metric.field": "title", "metric.score": "0.70" } },
      { runId: "run-b-id", runDir: "logs/run-b", values: { "metric.field": "title", "metric.score": "0.80" } },
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
    runId: "run-c-id",
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
    runId: "run-c-id",
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

/**
 * Verify that the extracted evaluation-table renderer wires shared headers, accessibility labels, and row callbacks.
 */
test("renderEvaluationTable renders extracted headers and forwards interaction callbacks", () => {
  const documentLike = createDocumentStub();
  const tableElement = new FakeElement("table");
  const callbackLog = {
    sort: [],
    groupBy: [],
    selectAll: [],
    groupRow: [],
    expand: [],
    select: [],
    memberRow: [],
  };
  const evalTabState = {
    groupByFields: ["metric.field"],
    truncateEnabledColumns: new Set(["metric.score", "eval_run_dir"]),
    sort: [{ column: "select", direction: "desc" }],
    selectedGroupIds: new Set(["eval-group-1"]),
    expandedGroupIds: new Set(["eval-group-1"]),
    selectedEvalGroupId: "eval-group-1",
    selectedEvalRunId: "run-a-id",
  };
  const displayedGroups = [
    {
      groupId: "eval-group-1",
      evaluations: [
        { runId: "run-a-id", runDir: "logs/run-a", values: { "metric.field": "title", "metric.score": "0.70" } },
      ],
    },
  ];

  const selectionState = renderEvaluationTable({
    documentLike,
    tableElement,
    evalColumnSections: [{ label: "evaluation", columns: ["metric.field", "metric.score"] }],
    orderedEvalColumns: ["metric.field", "metric.score"],
    displayedGroups,
    evalTabState,
    displayColumnName: (column) => `Label:${column}`,
    onSortToggle(column, event) {
      callbackLog.sort.push({ column, event });
    },
    onToggleGroupByColumn(column, checked) {
      callbackLog.groupBy.push({ column, checked });
    },
    onSelectAllDisplayed(checked, displayedGroupIds) {
      callbackLog.selectAll.push({ checked, displayedGroupIds });
    },
    onGroupRowSelect(groupId) {
      callbackLog.groupRow.push(groupId);
    },
    onToggleGroupExpansion(groupId) {
      callbackLog.expand.push(groupId);
    },
    onToggleGroupSelection(groupId, checked) {
      callbackLog.select.push({ groupId, checked });
    },
    onMemberRowSelect(runId) {
      callbackLog.memberRow.push(runId);
    },
    getGroupValueDisplayFromEvaluations(evaluations, getter) {
      return evaluations.map((evaluation) => getter(evaluation)).join(" | ");
    },
    getEvaluationEffectiveValue(evaluation, column) {
      return evaluation.values[column] || "";
    },
    getSortedEvaluations(evaluations) {
      return evaluations;
    },
    sortableControlColumns: new Set(["expand", "select", "group_size"]),
  });

  assert.deepEqual(selectionState, {
    displayedGroupIds: ["eval-group-1"],
    selectedCount: 1,
    allSelected: true,
    someSelected: false,
  });
  assert.equal(tableElement.children.length, 2);

  const thead = tableElement.children[0];
  const tbody = tableElement.children[1];
  const sectionRow = thead.children[0];
  const columnRow = thead.children[1];
  assert.equal(sectionRow.children[3].textContent, "evaluation");
  assert.equal(sectionRow.children[4].textContent, "meta");

  const selectAllCheckbox = sectionRow.children[1].children[0].children[1];
  assert.equal(
    selectAllCheckbox.getAttribute("aria-label"),
    "Select or deselect all displayed evaluation groups"
  );
  selectAllCheckbox.checked = false;
  selectAllCheckbox.listeners.get("change")({ type: "change" });
  assert.deepEqual(callbackLog.selectAll, [
    { checked: false, displayedGroupIds: ["eval-group-1"] },
  ]);

  const firstDataHeader = columnRow.children[0];
  assert.equal(firstDataHeader.style.minWidth, "144px");
  const groupByToggle = firstDataHeader.children[0].children[1].children[0];
  assert.equal(groupByToggle.getAttribute("aria-label"), "Group by Label:metric.field");
  assert.equal(groupByToggle.checked, true);
  groupByToggle.checked = false;
  groupByToggle.listeners.get("change")({ type: "change" });
  assert.deepEqual(callbackLog.groupBy, [{ column: "metric.field", checked: false }]);

  const runDirHeader = columnRow.children[2];
  assert.equal(runDirHeader.style.minWidth, "240px");
  assert.equal(runDirHeader.classList.contains("truncate-enabled"), true);

  assert.equal(tbody.children.length, 2);
  const groupRow = tbody.children[0];
  assert.equal(groupRow.classList.contains("eval-row-selected"), true);
  groupRow.listeners.get("click")({ type: "click" });
  assert.deepEqual(callbackLog.groupRow, ["eval-group-1"]);

  const expandEvent = {
    stopped: false,
    stopPropagation() {
      this.stopped = true;
    },
  };
  groupRow.children[0].children[0].listeners.get("click")(expandEvent);
  assert.equal(expandEvent.stopped, true);
  assert.deepEqual(callbackLog.expand, ["eval-group-1"]);

  const checkboxClickEvent = {
    stopped: false,
    stopPropagation() {
      this.stopped = true;
    },
  };
  const groupCheckbox = groupRow.children[1].children[0];
  groupCheckbox.listeners.get("click")(checkboxClickEvent);
  assert.equal(checkboxClickEvent.stopped, true);
  groupCheckbox.checked = false;
  groupCheckbox.listeners.get("change")({ type: "change" });
  assert.deepEqual(callbackLog.select, [{ groupId: "eval-group-1", checked: false }]);
  assert.equal(groupRow.children[4].classList.contains("truncate-enabled"), true);

  const memberRow = tbody.children[1];
  assert.equal(memberRow.className, "member-row");
  assert.equal(memberRow.classList.contains("eval-row-selected"), true);
  memberRow.listeners.get("click")({ type: "click" });
  assert.deepEqual(callbackLog.memberRow, ["run-a-id"]);
  assert.equal(memberRow.children[2].textContent, "member");
  assert.equal(memberRow.children[4].classList.contains("truncate-enabled"), true);
});

/**
 * Verify that the extracted evaluation-table renderer preserves the no-columns fallback header/body cells.
 */
test("renderEvaluationTable preserves the no-evaluation-columns fallback path", () => {
  const documentLike = createDocumentStub();
  const tableElement = new FakeElement("table");

  renderEvaluationTable({
    documentLike,
    tableElement,
    evalColumnSections: [],
    orderedEvalColumns: [],
    displayedGroups: [
      {
        groupId: "eval-group-empty",
        evaluations: [{ runId: "run-empty-id", runDir: "logs/run-empty", values: {} }],
      },
    ],
    evalTabState: {
      groupByFields: [],
      truncateEnabledColumns: new Set(),
      sort: [],
      selectedGroupIds: new Set(),
      expandedGroupIds: new Set(),
      selectedEvalGroupId: null,
      selectedEvalRunId: null,
    },
    displayColumnName: (column) => column,
    onSortToggle() {},
    onToggleGroupByColumn() {},
    onSelectAllDisplayed() {},
    onGroupRowSelect() {},
    onToggleGroupExpansion() {},
    onToggleGroupSelection() {},
    onMemberRowSelect() {},
    getGroupValueDisplayFromEvaluations() {
      return "";
    },
    getEvaluationEffectiveValue() {
      return "";
    },
    getSortedEvaluations(evaluations) {
      return evaluations;
    },
    sortableControlColumns: new Set(["expand", "select", "group_size"]),
  });

  const thead = tableElement.children[0];
  const tbody = tableElement.children[1];
  assert.equal(thead.children[1].children[0].textContent, "(no evaluation columns)");
  assert.equal(tbody.children[0].children[3].textContent, "");
});
