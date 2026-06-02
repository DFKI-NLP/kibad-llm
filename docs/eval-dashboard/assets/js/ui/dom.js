/**
 * Shared DOM reference capture and low-level visibility helpers for the eval dashboard.
 */

const DOM_REF_IDS = {
  folderInput: "folderInput",
  gitUrlInput: "gitUrlInput",
  githubTokenInput: "githubTokenInput",
  loadGitButton: "loadGitButton",
  loadStatus: "loadStatus",
  loadProgressWrap: "loadProgressWrap",
  loadProgress: "loadProgress",
  loadProgressLabel: "loadProgressLabel",
  predictionSummary: "predictionSummary",
  groupByAllButton: "groupByAllButton",
  groupByNoneButton: "groupByNoneButton",
  groupByToggleButton: "groupByToggleButton",
  predictionSortedByLabel: "predictionSortedByLabel",
  predictionResetSortButton: "predictionResetSortButton",
  optionsTabs: "optionsTabs",
  truncateColumnsList: "truncateColumnsList",
  predictionDefaultsPanel: "predictionDefaultsPanel",
  predictionDefaultsList: "predictionDefaultsList",
  truncateDefaultsButton: "truncateDefaultsButton",
  predictionsTable: "predictionsTable",
  evalTabs: "evalTabs",
  evalSummary: "evalSummary",
  evalGroupByAllButton: "evalGroupByAllButton",
  evalGroupByNoneButton: "evalGroupByNoneButton",
  evalGroupByToggleButton: "evalGroupByToggleButton",
  evalSortedByLabel: "evalSortedByLabel",
  evalResetSortButton: "evalResetSortButton",
  evalOptionsTabs: "evalOptionsTabs",
  evalTruncateColumnsList: "evalTruncateColumnsList",
  evalDefaultsPanel: "evalDefaultsPanel",
  evalDefaultsList: "evalDefaultsList",
  evalLayout: "evalLayout",
  evalJsonTabEvaluation: "evalJsonTabEvaluation",
  evalJsonTabPrediction: "evalJsonTabPrediction",
  evalJsonTitle: "evalJsonTitle",
  evalJsonCode: "evalJsonCode",
  evaluationsTable: "evaluationsTable",
  plotTabsByPrefixButton: "plotTabsByPrefixButton",
  plotTabsBySuffixButton: "plotTabsBySuffixButton",
  plotShortenLabels: "plotShortenLabels",
  plotRoundingPrecision: "plotRoundingPrecision",
  plotConfusionMinLabelTotalRow: "plotConfusionMinLabelTotalRow",
  plotConfusionMinLabelTotal: "plotConfusionMinLabelTotal",
  plotTpFpFnMinLabelTotalRow: "plotTpFpFnMinLabelTotalRow",
  plotTpFpFnMinLabelTotal: "plotTpFpFnMinLabelTotal",
  plotTpFpFnMinDocumentTotalRow: "plotTpFpFnMinDocumentTotalRow",
  plotTpFpFnMinDocumentTotal: "plotTpFpFnMinDocumentTotal",
  plotTabsByRow: "plotTabsByRow",
  plotConfusionTabsByRow: "plotConfusionTabsByRow",
  confusionTabsByMetricFieldButton: "confusionTabsByMetricFieldButton",
  confusionTabsByPredictionGroupButton: "confusionTabsByPredictionGroupButton",
  plotGroupBarsRow: "plotGroupBarsRow",
  plotGroupBarsList: "plotGroupBarsList",
  plotShowLegendOnceRow: "plotShowLegendOnceRow",
  plotShowLegendOnce: "plotShowLegendOnce",
  downloadFiguresButton: "downloadFiguresButton",
  exportOpaqueBackground: "exportOpaqueBackground",
  evalPlotTabs: "evalPlotTabs",
  evalPlotContent: "evalPlotContent",
  barTooltip: "barTooltip",
};

/**
 * Query all matching elements from one DOM-like root, returning a stable array.
 *
 * @param {{querySelectorAll?: (selector: string) => Iterable<HTMLElement> | ArrayLike<HTMLElement>} | null} rootLike - Root node or document.
 * @param {string} selector - Selector to query.
 * @returns {HTMLElement[]} Matching elements as a plain array.
 */
function queryAll(rootLike, selector) {
  return Array.from(rootLike?.querySelectorAll?.(selector) || []);
}

/**
 * Capture the dashboard's shared DOM references once during bootstrap.
 *
 * @param {Document} documentLike - The document to query.
 * @returns {Record<string, HTMLElement | null | HTMLElement[]>} Captured DOM references keyed by stable helper names.
 */
export function captureDomRefs(documentLike) {
  const refs = Object.fromEntries(
    Object.entries(DOM_REF_IDS).map(([refName, elementId]) => [refName, documentLike.getElementById(elementId)])
  );

  refs.optionsTabButtons = queryAll(refs.optionsTabs, ".options-tab-button");
  refs.optionsTabPanels = queryAll(documentLike, ".options-tab-panel");
  refs.evalOptionsTabButtons = queryAll(refs.evalOptionsTabs, ".options-tab-button");
  refs.evalOptionsTabPanels = queryAll(documentLike, ".options-tab-panel[data-eval-tab-panel]");
  return refs;
}

/**
 * Show or hide a panel element using the dashboard's existing inline display contract.
 *
 * @param {HTMLElement | null} panelElement - The panel element to update.
 * @param {boolean} shouldShow - Whether the element should be visible.
 * @returns {void}
 */
export function setPanelVisibility(panelElement, shouldShow) {
  if (!panelElement) {
    return;
  }
  panelElement.style.display = shouldShow ? "" : "none";
}
