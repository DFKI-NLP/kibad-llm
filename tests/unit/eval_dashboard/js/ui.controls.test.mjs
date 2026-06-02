/**
 * Browser-free logic tests for eval-dashboard control helpers.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildColumnOptions,
  buildMissingDefaultControlModels,
  getToggleOnlyColumns,
  renderCheckboxOptionList,
  renderGroupByButtonState,
  renderMissingDefaultControls,
  renderOptionsPanelControls,
  renderPlotControls,
} from "../../../../docs/eval-dashboard/assets/js/ui/controls.js";

/**
 * Minimal classList stub for DOM-free control rendering tests.
 */
class FakeClassList {
  /**
   * Create one empty class list.
   */
  constructor() {
    this.values = new Set();
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
   * Report whether the class list currently contains one class.
   *
   * @param {string} name - Class name to check.
   * @returns {boolean} Whether the class is present.
   */
  contains(name) {
    return this.values.has(name);
  }
}

/**
 * Minimal element stub used by the extracted control tests.
 */
class FakeElement {
  /**
   * Create one fake element instance with the properties used by the tests.
   */
  constructor() {
    this.type = "";
    this.checked = false;
    this.disabled = false;
    this.textContent = "";
    this.className = "";
    this.children = [];
    this.attributes = new Map();
    this.listeners = new Map();
    this.style = {};
    this.value = "";
    this.placeholder = "";
    this.id = "";
    this._innerHTML = "";
    this.blurCallCount = 0;
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

  /**
   * Track blur calls triggered by keyboard handling tests.
   *
   * @returns {void}
   */
  blur() {
    this.blurCallCount += 1;
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

test("buildColumnOptions preserves column order while applying display labels", () => {
  assert.deepEqual(
    buildColumnOptions(["prediction.run_dir", "prediction.title"], (column) => `label:${column}`),
    [
      { value: "prediction.run_dir", label: "label:prediction.run_dir" },
      { value: "prediction.title", label: "label:prediction.title" },
    ]
  );
});

test("getToggleOnlyColumns returns columns that are not currently active", () => {
  assert.deepEqual(
    getToggleOnlyColumns(["a", "b", "c"], ["b"]),
    ["a", "c"]
  );
});

test("buildMissingDefaultControlModels derives labels, values, suggestions, and missing counts", () => {
  assert.deepEqual(
    buildMissingDefaultControlModels({
      columns: ["prediction.language"],
      getLabel: (column) => `Label:${column}`,
      getValue: () => "de",
      getSuggestions: () => ["de", "en"],
      getMissingCount: () => 3,
    }),
    [
      {
        column: "prediction.language",
        label: "Label:prediction.language",
        value: "de",
        suggestions: ["de", "en"],
        missingCount: 3,
      },
    ]
  );
});

test("renderGroupByButtonState enables or disables all group-by action buttons together", () => {
  const buttonRefs = {
    allButton: new FakeElement("button"),
    toggleButton: new FakeElement("button"),
    noneButton: new FakeElement("button"),
  };

  renderGroupByButtonState(buttonRefs, []);
  assert.equal(buttonRefs.allButton.disabled, true);
  assert.equal(buttonRefs.toggleButton.disabled, true);
  assert.equal(buttonRefs.noneButton.disabled, true);

  renderGroupByButtonState(buttonRefs, ["prediction.title"]);
  assert.equal(buttonRefs.allButton.disabled, false);
  assert.equal(buttonRefs.toggleButton.disabled, false);
  assert.equal(buttonRefs.noneButton.disabled, false);
});

test("renderCheckboxOptionList builds checkbox rows and emits toggle callbacks", () => {
  const documentLike = createDocumentStub();
  const listElement = new FakeElement("div");
  const toggles = [];

  renderCheckboxOptionList({
    documentLike,
    listElement,
    options: buildColumnOptions(["prediction.run_dir"], (column) => `Label:${column}`),
    checkedValues: new Set(["prediction.run_dir"]),
    getAriaLabel: (option) => `Toggle ${option.label}`,
    onToggle(value, checked) {
      toggles.push({ value, checked });
    },
  });

  assert.equal(listElement.children.length, 1);
  const row = listElement.children[0];
  const checkbox = row.children[0];
  const text = row.children[1];
  assert.equal(row.className, "truncate-item");
  assert.equal(checkbox.checked, true);
  assert.equal(checkbox.getAttribute("aria-label"), "Toggle Label:prediction.run_dir");
  assert.equal(text.textContent, "Label:prediction.run_dir");

  checkbox.checked = false;
  checkbox.listeners.get("change")();
  assert.deepEqual(toggles, [{ value: "prediction.run_dir", checked: false }]);
});

test("renderMissingDefaultControls renders inputs, suggestions, and commit handlers", () => {
  const documentLike = createDocumentStub();
  const listElement = new FakeElement("div");
  const panelElement = new FakeElement("section");
  const commits = [];

  renderMissingDefaultControls({
    documentLike,
    listElement,
    panelElement,
    controlModels: [
      {
        column: "prediction.language",
        label: "Language",
        value: "de",
        suggestions: ["de", "en"],
        missingCount: 2,
      },
    ],
    onCommit(column, nextValue) {
      commits.push({ column, nextValue });
    },
    inputIdPrefix: "prediction-default",
  });

  assert.equal(panelElement.style.display, "");
  assert.equal(listElement.children.length, 1);

  const row = listElement.children[0];
  const labelWrap = row.children[0];
  const input = row.children[1];
  const datalist = row.children[2];
  assert.equal(row.className, "missing-default-item");
  assert.equal(labelWrap.children[0].textContent, "Language");
  assert.equal(labelWrap.children[1].textContent, "2 missing values");
  assert.equal(input.value, "de");
  assert.equal(input.placeholder, "Leave empty to keep blanks");
  assert.equal(input.getAttribute("list"), "prediction-default-prediction-language");
  assert.equal(input.getAttribute("aria-label"), "Default value for missing entries in Language");
  assert.equal(datalist.id, "prediction-default-prediction-language");
  assert.deepEqual(
    datalist.children.map((option) => option.value),
    ["de", "en"]
  );

  input.value = "fr";
  input.listeners.get("change")();
  assert.deepEqual(commits, [{ column: "prediction.language", nextValue: "fr" }]);

  let prevented = false;
  input.listeners.get("keydown")({
    key: "Enter",
    preventDefault() {
      prevented = true;
    },
  });
  assert.equal(prevented, true);
  assert.equal(input.blurCallCount, 1);
});

test("renderOptionsPanelControls renders checkbox and default sections through shared helpers", () => {
  const documentLike = createDocumentStub();
  const checkboxListElement = new FakeElement("div");
  const defaultsListElement = new FakeElement("div");
  const defaultsPanelElement = new FakeElement("section");
  const toggles = [];
  const commits = [];

  renderOptionsPanelControls({
    documentLike,
    checkboxListElement,
    checkboxOptions: buildColumnOptions(["prediction.run_dir"], (column) => `Label:${column}`),
    checkedValues: [],
    onCheckboxToggle(value, checked) {
      toggles.push({ value, checked });
    },
    defaultsListElement,
    defaultsPanelElement,
    defaultControlModels: [
      {
        column: "prediction.language",
        label: "Language",
        value: "",
        suggestions: ["de"],
        missingCount: 1,
      },
    ],
    onDefaultCommit(column, nextValue) {
      commits.push({ column, nextValue });
    },
    inputIdPrefix: "prediction-default",
  });

  assert.equal(checkboxListElement.children.length, 1);
  assert.equal(defaultsListElement.children.length, 1);
  assert.equal(defaultsPanelElement.style.display, "");

  const checkbox = checkboxListElement.children[0].children[0];
  checkbox.checked = true;
  checkbox.listeners.get("change")();
  assert.deepEqual(toggles, [{ value: "prediction.run_dir", checked: true }]);

  const defaultInput = defaultsListElement.children[0].children[1];
  defaultInput.value = "fallback";
  defaultInput.listeners.get("change")();
  assert.deepEqual(commits, [{ column: "prediction.language", nextValue: "fallback" }]);
});

test("renderPlotControls synchronizes button state, input values, and plot-control row visibility", () => {
  const refs = {
    plotTabsByPrefixButton: new FakeElement("button"),
    plotTabsBySuffixButton: new FakeElement("button"),
    confusionTabsByMetricFieldButton: new FakeElement("button"),
    confusionTabsByPredictionGroupButton: new FakeElement("button"),
    plotShortenLabelsInput: new FakeElement("input"),
    plotRoundingPrecisionInput: new FakeElement("input"),
    plotConfusionMinLabelTotalRow: new FakeElement("div"),
    plotConfusionMinLabelTotalInput: new FakeElement("input"),
    plotTpFpFnMinLabelTotalRow: new FakeElement("div"),
    plotTpFpFnMinLabelTotalInput: new FakeElement("input"),
    plotTpFpFnMinDocumentTotalRow: new FakeElement("div"),
    plotTpFpFnMinDocumentTotalInput: new FakeElement("input"),
    plotTabsByRow: new FakeElement("div"),
    plotConfusionTabsByRow: new FakeElement("div"),
    plotGroupBarsRow: new FakeElement("div"),
    plotShowLegendOnceRow: new FakeElement("div"),
    plotShowLegendOnceInput: new FakeElement("input"),
    exportOpaqueBackgroundInput: new FakeElement("input"),
  };

  renderPlotControls({
    metricType: "F1MicroMultipleFieldsMetric",
    plotTabsBy: "suffix",
    confusionTabsBy: "prediction_group",
    plotShortenLabels: true,
    plotRoundingPrecision: 4,
    plotConfusionMinLabelTotal: 6,
    plotTpFpFnMinLabelTotal: 7,
    plotTpFpFnMinDocumentTotal: 8,
    plotShowLegendOnce: true,
    exportOpaqueBackground: true,
    ...refs,
  });

  assert.equal(refs.plotTabsByPrefixButton.classList.contains("active"), false);
  assert.equal(refs.plotTabsBySuffixButton.classList.contains("active"), true);
  assert.equal(refs.confusionTabsByMetricFieldButton.classList.contains("active"), false);
  assert.equal(refs.confusionTabsByPredictionGroupButton.classList.contains("active"), true);
  assert.equal(refs.plotShortenLabelsInput.checked, true);
  assert.equal(refs.plotRoundingPrecisionInput.value, "4");
  assert.equal(refs.plotConfusionMinLabelTotalInput.value, "6");
  assert.equal(refs.plotTpFpFnMinLabelTotalInput.value, "7");
  assert.equal(refs.plotTpFpFnMinDocumentTotalInput.value, "8");
  assert.equal(refs.plotShowLegendOnceInput.checked, true);
  assert.equal(refs.exportOpaqueBackgroundInput.checked, true);
  assert.equal(refs.plotTabsByRow.style.display, "");
  assert.equal(refs.plotConfusionMinLabelTotalRow.style.display, "none");
  assert.equal(refs.plotTpFpFnMinLabelTotalRow.style.display, "none");
  assert.equal(refs.plotTpFpFnMinDocumentTotalRow.style.display, "none");
  assert.equal(refs.plotConfusionTabsByRow.style.display, "none");
  assert.equal(refs.plotGroupBarsRow.style.display, "");
  assert.equal(refs.plotShowLegendOnceRow.style.display, "none");

  renderPlotControls({
    metricType: "ConfusionMatrixCollection",
    plotTabsBy: "prefix",
    confusionTabsBy: "metric_field",
    plotShortenLabels: false,
    plotRoundingPrecision: 2,
    plotConfusionMinLabelTotal: 3,
    plotTpFpFnMinLabelTotal: 4,
    plotTpFpFnMinDocumentTotal: 5,
    plotShowLegendOnce: false,
    exportOpaqueBackground: false,
    ...refs,
  });

  assert.equal(refs.plotTabsByPrefixButton.classList.contains("active"), true);
  assert.equal(refs.plotTabsBySuffixButton.classList.contains("active"), false);
  assert.equal(refs.confusionTabsByMetricFieldButton.classList.contains("active"), true);
  assert.equal(refs.confusionTabsByPredictionGroupButton.classList.contains("active"), false);
  assert.equal(refs.plotShortenLabelsInput.checked, false);
  assert.equal(refs.exportOpaqueBackgroundInput.checked, false);
  assert.equal(refs.plotTabsByRow.style.display, "none");
  assert.equal(refs.plotConfusionMinLabelTotalRow.style.display, "");
  assert.equal(refs.plotTpFpFnMinLabelTotalRow.style.display, "none");
  assert.equal(refs.plotTpFpFnMinDocumentTotalRow.style.display, "none");
  assert.equal(refs.plotConfusionTabsByRow.style.display, "");
  assert.equal(refs.plotGroupBarsRow.style.display, "none");
  assert.equal(refs.plotShowLegendOnceRow.style.display, "none");
});
