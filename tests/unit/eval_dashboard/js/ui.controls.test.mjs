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
} from "../../../../docs/eval-dashboard/assets/js/ui/controls.js";

class FakeElement {
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
  }

  set innerHTML(value) {
    this._innerHTML = String(value);
    if (value === "") {
      this.children = [];
    }
  }

  get innerHTML() {
    return this._innerHTML;
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  getAttribute(name) {
    return this.attributes.get(name);
  }

  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }

  blur() {
    this.blurCallCount += 1;
  }
}

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
