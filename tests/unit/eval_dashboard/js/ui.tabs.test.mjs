import test from "node:test";
import assert from "node:assert/strict";

import {
  buildTabButtonModels,
  renderStaticTabState,
  renderTabButtons,
  resolveActiveTabValue,
} from "../../../../docs/eval-dashboard/assets/js/ui/tabs.js";

class FakeClassList {
  constructor() {
    this.values = new Set();
  }

  toggle(name, force) {
    if (force) {
      this.values.add(name);
    } else {
      this.values.delete(name);
    }
  }

  contains(name) {
    return this.values.has(name);
  }
}

class FakeElement {
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
