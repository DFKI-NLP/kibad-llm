/**
 * Browser-free logic tests for the eval-dashboard tab helpers.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  bindDelegatedTabSelection,
  buildCountTabButtonModels,
  buildTabButtonModels,
  renderStaticTabState,
  renderTabButtons,
  resolveActiveTabValue,
} from "../../../../docs/eval-dashboard/assets/js/ui/tabs.js";

/**
 * Minimal classList stub for DOM-free tab rendering tests.
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
 * Minimal element stub used by the extracted tab-helper tests.
 */
class FakeElement {
  /**
   * Create one fake element instance with the properties used by the tests.
   */
  constructor() {
    this.type = "";
    this.className = "";
    this.textContent = "";
    this.title = "";
    this.children = [];
    this.attributes = new Map();
    this.listeners = new Map();
    this.classList = new FakeClassList();
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

test("resolveActiveTabValue preserves valid tabs and falls back to the first available tab", () => {
  assert.equal(resolveActiveTabValue("beta", ["alpha", "beta"]), "beta");
  assert.equal(resolveActiveTabValue("missing", ["alpha", "beta"]), "alpha");
  assert.equal(resolveActiveTabValue(null, []), null);
});

test("buildTabButtonModels derives labels, titles, and active-state flags", () => {
  assert.deepEqual(
    buildTabButtonModels(["errors", "bars"], {
      activeValue: "bars",
      getLabel: (value) => value.toUpperCase(),
      getTitle: (value) => `tab:${value}`,
    }),
    [
      { value: "errors", label: "ERRORS", title: "tab:errors", isActive: false },
      { value: "bars", label: "BARS", title: "tab:bars", isActive: true },
    ]
  );
});

test("buildCountTabButtonModels appends counts while preserving titles and active-state flags", () => {
  assert.deepEqual(
    buildCountTabButtonModels(["total", "details"], {
      activeValue: "details",
      getLabelText: (value) => value.toUpperCase(),
      getCount: (value) => (value === "total" ? 3 : 7),
      getTitle: (value) => `tab:${value}`,
    }),
    [
      { value: "total", label: "TOTAL (3)", title: "tab:total", isActive: false },
      { value: "details", label: "DETAILS (7)", title: "tab:details", isActive: true },
    ]
  );
});

test("renderTabButtons creates shared tab buttons and wires selection callbacks", () => {
  const documentLike = createDocumentStub();
  const container = new FakeElement("div");
  const selectedValues = [];

  renderTabButtons({
    documentLike,
    containerElement: container,
    tabModels: buildTabButtonModels(["exp-a", "exp-b"], {
      activeValue: "exp-b",
      getLabel: (value) => value,
      getTitle: (value) => `title:${value}`,
    }),
    onSelect(value) {
      selectedValues.push(value);
    },
  });

  assert.equal(container.children.length, 2);
  assert.equal(container.children[0].className, "tab-button");
  assert.equal(container.children[1].className, "tab-button active");
  assert.equal(container.children[1].getAttribute("data-tab-value"), "exp-b");
  assert.equal(container.children[1].title, "title:exp-b");

  container.children[0].listeners.get("click")({ type: "click" });
  assert.deepEqual(selectedValues, ["exp-a"]);
});

test("renderStaticTabState syncs active classes across cached buttons and panels", () => {
  const alphaButton = new FakeElement("button");
  alphaButton.setAttribute("data-tab", "alpha");
  const betaButton = new FakeElement("button");
  betaButton.setAttribute("data-tab", "beta");
  const alphaPanel = new FakeElement("div");
  alphaPanel.setAttribute("data-tab-panel", "alpha");
  const betaPanel = new FakeElement("div");
  betaPanel.setAttribute("data-tab-panel", "beta");

  renderStaticTabState({
    buttonElements: [alphaButton, betaButton],
    panelElements: [alphaPanel, betaPanel],
    activeValue: "beta",
  });

  assert.equal(alphaButton.classList.contains("active"), false);
  assert.equal(betaButton.classList.contains("active"), true);
  assert.equal(alphaPanel.classList.contains("active"), false);
  assert.equal(betaPanel.classList.contains("active"), true);
});

test("bindDelegatedTabSelection forwards only changed tab selections from delegated clicks", () => {
  const container = new FakeElement("div");
  const selectedValues = [];
  let activeValue = "alpha";
  const alphaButton = new FakeElement("button");
  alphaButton.setAttribute("data-tab", "alpha");
  const betaButton = new FakeElement("button");
  betaButton.setAttribute("data-tab", "beta");

  bindDelegatedTabSelection({
    containerElement: container,
    getActiveValue: () => activeValue,
    onSelect(value) {
      activeValue = value;
      selectedValues.push(value);
    },
  });

  container.listeners.get("click")({
    target: {
      closest(selector) {
        return selector === ".options-tab-button" ? alphaButton : null;
      },
    },
  });
  container.listeners.get("click")({
    target: {
      closest(selector) {
        return selector === ".options-tab-button" ? betaButton : null;
      },
    },
  });
  container.listeners.get("click")({
    target: {
      closest() {
        return null;
      },
    },
  });

  assert.deepEqual(selectedValues, ["beta"]);
});
