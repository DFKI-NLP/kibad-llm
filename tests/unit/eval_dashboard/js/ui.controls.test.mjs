import test from "node:test";
import assert from "node:assert/strict";

import {
  buildColumnOptions,
  buildMissingDefaultControlModels,
  getToggleOnlyColumns,
  renderCheckboxOptionList,
  renderGroupByButtonState,
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
