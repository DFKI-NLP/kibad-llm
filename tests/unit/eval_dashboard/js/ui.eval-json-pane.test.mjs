/**
 * Browser-free logic tests for the eval-dashboard JSON-pane helpers.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  escapeHtml,
  highlightJsonContent,
  renderEvalJsonPane,
  resolveEvalJsonContent,
} from "../../../../docs/eval-dashboard/assets/js/ui/eval-json-pane.js";

/**
 * Minimal classList stub for DOM-free JSON-pane rendering tests.
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
 * Minimal element stub used by the extracted JSON-pane tests.
 */
class FakeElement {
  /**
   * Create one fake element instance with the properties used by the tests.
   */
  constructor() {
    this.textContent = "";
    this.innerHTML = "";
    this.classList = new FakeClassList();
  }
}

test("escapeHtml escapes ampersands and angle brackets", () => {
  assert.equal(escapeHtml('<tag attr="x">&</tag>'), '&lt;tag attr="x"&gt;&amp;&lt;/tag&gt;');
});

test("highlightJsonContent wraps keys and primitive values in dashboard highlight spans", () => {
  const html = highlightJsonContent({ answer: 42, ok: true, nothing: null, label: "alpha" });

  assert.match(html, /<span class="json-key">"answer":<\/span>/);
  assert.match(html, /<span class="json-number">42<\/span>/);
  assert.match(html, /<span class="json-boolean">true<\/span>/);
  assert.match(html, /<span class="json-null">null<\/span>/);
  assert.match(html, /<span class="json-string">"alpha"<\/span>/);
});

test("resolveEvalJsonContent chooses evaluation data or reconstructed prediction content", () => {
  const selectedEvaluation = { data: { metric: 0.5 }, predictionId: "pred-1" };
  const selectedGroup = {
    evaluations: [
      { data: { metric: 1 }, predictionId: "pred-a" },
      { data: { metric: 2 }, predictionId: "pred-b" },
    ],
  };
  const getPredictionContent = (evaluation) => ({ prediction: evaluation.predictionId });

  assert.deepEqual(
    resolveEvalJsonContent({ selectedEvaluation, activeTab: "evaluation", getPredictionContent }),
    { metric: 0.5 }
  );
  assert.deepEqual(
    resolveEvalJsonContent({ selectedEvaluation, activeTab: "prediction", getPredictionContent }),
    { prediction: "pred-1" }
  );
  assert.deepEqual(
    resolveEvalJsonContent({ selectedGroup, activeTab: "prediction", getPredictionContent }),
    [{ prediction: "pred-a" }, { prediction: "pred-b" }]
  );
  assert.equal(resolveEvalJsonContent(), null);
});

test("renderEvalJsonPane toggles split layout, tab state, and highlighted content", () => {
  const layoutElement = new FakeElement();
  const titleElement = new FakeElement();
  const codeElement = new FakeElement();
  const evaluationButton = new FakeElement();
  const predictionButton = new FakeElement();

  renderEvalJsonPane({
    layoutElement,
    titleElement,
    codeElement,
    evaluationButton,
    predictionButton,
    activeTab: "prediction",
    selectedEvaluation: { data: { metric: 1 }, predictionId: "pred-7" },
    getPredictionContent: (evaluation) => ({ prediction: evaluation.predictionId }),
  });

  assert.equal(layoutElement.classList.contains("split"), true);
  assert.equal(titleElement.textContent, "");
  assert.equal(evaluationButton.classList.contains("active"), false);
  assert.equal(predictionButton.classList.contains("active"), true);
  assert.match(codeElement.innerHTML, /pred-7/);

  renderEvalJsonPane({
    layoutElement,
    titleElement,
    codeElement,
    evaluationButton,
    predictionButton,
    activeTab: "evaluation",
  });

  assert.equal(layoutElement.classList.contains("split"), false);
  assert.equal(codeElement.innerHTML, "");
  assert.equal(evaluationButton.classList.contains("active"), true);
  assert.equal(predictionButton.classList.contains("active"), false);
});
