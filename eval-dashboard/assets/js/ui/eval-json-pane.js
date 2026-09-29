/**
 * Evaluation JSON side-pane helpers and renderers for the eval dashboard.
 */

/**
 * Escape raw text for safe HTML insertion.
 *
 * @param {unknown} text - Raw text to escape.
 * @returns {string} Escaped HTML text.
 */
export function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

/**
 * Syntax-highlight one JSON-compatible value using the dashboard's existing span classes.
 *
 * @param {unknown} value - Value to stringify and highlight.
 * @returns {string} Highlighted HTML markup.
 */
export function highlightJsonContent(value) {
  const json = JSON.stringify(value ?? {}, null, 2);
  const escaped = escapeHtml(json);
  return escaped.replace(
    /("(?:\\u[0-9a-fA-F]{4}|\\[^u]|[^\\"])*"(?:\s*:)?|\btrue\b|\bfalse\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      if (match.endsWith(":")) {
        return `<span class="json-key">${match}</span>`;
      }
      if (match.startsWith("\"")) {
        return `<span class="json-string">${match}</span>`;
      }
      if (match === "true" || match === "false") {
        return `<span class="json-boolean">${match}</span>`;
      }
      if (match === "null") {
        return `<span class="json-null">${match}</span>`;
      }
      return `<span class="json-number">${match}</span>`;
    }
  );
}

/**
 * Resolve the JSON value that should currently appear in the side pane.
 *
 * @param {object} options - Selected evaluation/group inputs.
 * @param {{data?: object} | null} [options.selectedEvaluation=null] - Selected single evaluation.
 * @param {{evaluations?: Array<object>} | null} [options.selectedGroup=null] - Selected evaluation group.
 * @param {"evaluation" | "prediction"} [options.activeTab="evaluation"] - Active JSON tab.
 * @param {(evaluation: object) => unknown} [options.getPredictionContent] - Prediction-content resolver.
 * @returns {unknown | null} The value to display, or null when nothing is selected.
 */
export function resolveEvalJsonContent({
  selectedEvaluation = null,
  selectedGroup = null,
  activeTab = "evaluation",
  getPredictionContent = (evaluation) => evaluation,
} = {}) {
  if (selectedEvaluation) {
    return activeTab === "prediction"
      ? getPredictionContent(selectedEvaluation)
      : (selectedEvaluation.data || {});
  }
  if (!selectedGroup) {
    return null;
  }
  const evaluations = selectedGroup.evaluations || [];
  return activeTab === "prediction"
    ? evaluations.map((evaluation) => getPredictionContent(evaluation))
    : evaluations.map((evaluation) => evaluation.data || {});
}

/**
 * Render the active-state classes for the two JSON-pane tab buttons.
 *
 * @param {object} options - JSON-tab button refs and active tab id.
 * @param {HTMLElement | null} options.evaluationButton - Evaluation-data tab button.
 * @param {HTMLElement | null} options.predictionButton - Prediction-metadata tab button.
 * @param {"evaluation" | "prediction"} options.activeTab - Active JSON tab id.
 * @returns {void}
 */
export function renderEvalJsonTabState({ evaluationButton, predictionButton, activeTab }) {
  evaluationButton?.classList?.toggle?.("active", activeTab === "evaluation");
  predictionButton?.classList?.toggle?.("active", activeTab === "prediction");
}

/**
 * Bind click handlers for the two JSON-pane tab buttons.
 *
 * @param {object} options - Button refs plus the active-tab lookup.
 * @param {HTMLElement | null} options.evaluationButton - Evaluation-data tab button.
 * @param {HTMLElement | null} options.predictionButton - Prediction-metadata tab button.
 * @param {() => ("evaluation" | "prediction")} [options.getActiveTab] - Current active-tab lookup.
 * @param {(nextTab: "evaluation" | "prediction", event: Event) => void} options.onSelect - Selection callback.
 * @returns {void}
 */
export function bindEvalJsonTabSelection({
  evaluationButton,
  predictionButton,
  getActiveTab = () => "evaluation",
  onSelect,
}) {
  const bindSelection = (button, nextTab) => {
    button?.addEventListener?.("click", (event) => {
      if (getActiveTab() === nextTab) {
        return;
      }
      onSelect(nextTab, event);
    });
  };

  bindSelection(evaluationButton, "evaluation");
  bindSelection(predictionButton, "prediction");
}

/**
 * Render the JSON side pane from the currently selected evaluation or evaluation group.
 *
 * @param {object} options - JSON-pane DOM refs and selected content.
 * @param {HTMLElement | null} options.layoutElement - Parent layout element toggling the split class.
 * @param {HTMLElement | null} options.titleElement - Title element above the JSON block.
 * @param {HTMLElement | null} options.codeElement - Code element receiving highlighted HTML.
 * @param {HTMLElement | null} options.evaluationButton - Evaluation-data tab button.
 * @param {HTMLElement | null} options.predictionButton - Prediction-metadata tab button.
 * @param {"evaluation" | "prediction"} options.activeTab - Active JSON tab id.
 * @param {{data?: object} | null} [options.selectedEvaluation=null] - Selected single evaluation.
 * @param {{evaluations?: Array<object>} | null} [options.selectedGroup=null] - Selected evaluation group.
 * @param {(evaluation: object) => unknown} [options.getPredictionContent] - Prediction-content resolver.
 * @returns {void}
 */
export function renderEvalJsonPane({
  layoutElement,
  titleElement,
  codeElement,
  evaluationButton,
  predictionButton,
  activeTab,
  selectedEvaluation = null,
  selectedGroup = null,
  getPredictionContent = (evaluation) => evaluation,
}) {
  const hasSelection = Boolean(selectedEvaluation || selectedGroup);
  layoutElement?.classList?.toggle?.("split", hasSelection);
  renderEvalJsonTabState({ evaluationButton, predictionButton, activeTab });
  if (titleElement) {
    titleElement.textContent = "";
  }
  if (!codeElement) {
    return;
  }
  if (!hasSelection) {
    codeElement.innerHTML = "";
    return;
  }
  const tabContent = resolveEvalJsonContent({
    selectedEvaluation,
    selectedGroup,
    activeTab,
    getPredictionContent,
  });
  codeElement.innerHTML = highlightJsonContent(tabContent);
}
