/**
 * Dashboard-level plot rendering adapters.
 */

import { renderPlotControls, renderPlotGroupBarChips } from "../ui/controls.js";
import {
  buildCountTabButtonModels,
  renderTabButtons,
  resolveActiveTab,
} from "../ui/tabs.js";
import {
  renderDownloadDataButtonState,
  renderDownloadFiguresButtonState,
} from "../ui/status.js";
import { createTimingCollector } from "../utils/timing.js";
import {
  getGroupLabelForFields,
  getVaryingFields,
} from "./shared.js";
import {
  buildBarsTabMap,
  buildErrorsTabMap,
  buildNumericPlotDefinitions,
  buildNumericPlotEntriesInput,
  createBarPlotSvg,
  createGroupedBarPlotSvg,
  getNumericPlotEntriesFromInput,
  getSortedBarPlotTabKeys,
} from "./bars.js";
import { buildDownloadPlotMetadata } from "./download-data.js";
import {
  buildGroupedLegendModel,
  createPlotLegendElement,
  getLegendItemsForPoints,
} from "./legend.js";
import {
  buildConfusionTabMap,
  countDistinctConfusionMatrixRuns,
  createConfusionMatrixHeatmapSvg,
  filterConfusionMatrixAggregationByLabelTotal,
  getConfusionMatrixAggregationFromInput,
  getConfusionMatrixAggregationInput,
} from "./confusion.js";
import {
  buildTpFpFnTabMap,
  createTpFpFnCombinedMatrixSvg,
  createTpFpFnLegendElement,
  filterTpFpFnAggregationByTotals,
  getTpFpFnAggregationFromInput,
  getTpFpFnAggregationInput,
} from "./tpfpfn.js";
import {
  createZipBlob,
  downloadVisibleFigures,
  getActivePlotTabZipFilename,
  getVisiblePlotFigureCards,
  hideTooltip,
  measureCanvasText,
  positionTooltip,
  resolveOpaqueExportBackgroundColor,
  saveBlob,
  serializeLegendSvg,
  serializeSvgForDownload,
  showTooltip,
  triggerBlobDownload,
  writeTextToClipboard,
} from "./export.js";

/**
 * Creates tooltip callbacks bound to the shared plot tooltip element.
 *
 * Plot renderers should depend on small callbacks rather than the singleton
 * tooltip DOM node, which keeps family SVG helpers reusable in DOM-free tests.
 *
 * @param {object} options - Tooltip element and browser window dependency.
 * @returns {{show: Function, move: Function, hide: Function}} Tooltip callbacks.
 */
export function createPlotTooltipHandlers({ tooltipElement, windowLike = globalThis.window }) {
  return {
    show: (event, lines) => showTooltip({ tooltipElement, windowLike, event, lines }),
    move: (event) => positionTooltip({ tooltipElement, windowLike, event }),
    hide: () => hideTooltip({ tooltipElement }),
  };
}

/**
 * Resolves the background color used when exporting opaque SVG figures.
 *
 * The visible plot container may be transparent, so export code needs one
 * dashboard-owned fallback chain before serializing figures.
 *
 * @param {object} options - Plot content element and browser document/style dependencies.
 * @returns {string} Opaque CSS background color.
 */
export function resolvePlotExportBackgroundColor({
  evalPlotContent,
  documentLike = globalThis.document,
  getStyle = globalThis.getComputedStyle,
}) {
  return resolveOpaqueExportBackgroundColor(
    [evalPlotContent, documentLike.body, documentLike.documentElement],
    getStyle
  );
}

/**
 * Synchronizes the download button with the number of visible SVG plot cards.
 *
 * Deriving the count from rendered cards keeps figure-export availability
 * aligned with what the user can currently see and download.
 *
 * @param {object} options - Download button and plot content container.
 * @returns {void}
 */
export function updateDownloadFiguresButtonState({
  downloadFiguresButton,
  evalPlotContent,
}) {
  renderDownloadFiguresButtonState(
    downloadFiguresButton,
    getVisiblePlotFigureCards(evalPlotContent).length
  );
}

/**
 * Synchronizes the data-download button with the current active plot data payload.
 *
 * This keeps button state derived from the same payload that will be saved, so
 * the UI cannot advertise data when the active render did not produce any.
 *
 * @param {object} options - Button and state dependencies.
 * @returns {void}
 */
export function updateDownloadDataButtonState({ downloadDataButton, state }) {
  const plotCount = Array.isArray(state?.activePlotDownloadData?.plots)
    ? state.activePlotDownloadData.plots.length
    : 0;
  renderDownloadDataButtonState(downloadDataButton, plotCount);
}

/**
 * Downloads the currently visible plot figures as a ZIP archive.
 *
 * This adapter keeps browser APIs, dashboard state, and export helpers out of
 * metric-family renderers while preserving active-tab figure and legend scope.
 *
 * @param {object} options - Dashboard state, DOM refs, and browser dependencies.
 * @returns {Promise<boolean>} True when a save/download was started.
 */
export async function downloadVisiblePlotFigures({
  state,
  evalPlotContent,
  evalPlotTabs,
  documentLike = globalThis.document,
  windowLike = globalThis.window,
  urlLike = globalThis.URL,
  setTimeoutLike = globalThis.setTimeout,
  getStyle = globalThis.getComputedStyle,
  consoleLike = globalThis.console,
}) {
  const exportOptions = {
    opaqueBackground: state.exportOpaqueBackground,
    backgroundColor: state.exportOpaqueBackground
      ? resolvePlotExportBackgroundColor({ evalPlotContent, documentLike, getStyle })
      : null,
  };

  return downloadVisibleFigures({
    figureCards: getVisiblePlotFigureCards(evalPlotContent),
    activePlotLegendItems: state.activePlotLegendItems,
    exportOptions,
    serializeLegend: (legendItems, nextExportOptions) => serializeLegendSvg({
      documentLike,
      legendItems,
      computedStyle: getStyle(evalPlotContent),
      measureText: (text, font) => measureCanvasText({ documentLike, text, font }),
      exportOptions: nextExportOptions,
    }),
    serializeSvg: (sourceSvg, nextExportOptions) => serializeSvgForDownload({
      documentLike,
      sourceSvg,
      computedStyle: getStyle(sourceSvg),
      exportOptions: nextExportOptions,
    }),
    createZip: createZipBlob,
    saveZip: (blob, suggestedName, types) => saveBlob({
      windowLike,
      blob,
      suggestedName,
      types,
      triggerDownload: (nextBlob, filename) => triggerBlobDownload({
        documentLike,
        urlLike,
        setTimeoutLike,
        filename,
        blob: nextBlob,
      }),
      consoleLike,
    }),
    getZipFilename: () => getActivePlotTabZipFilename({
      activeEvalTab: state.activeEvalTab,
      evalPlotTabs,
    }),
  });
}

/**
 * Renders the dashboard plot surface from the selected evaluation context.
 *
 * This is the shared lifecycle owner: it clears stale plot state, derives the
 * selected plot groups once, and dispatches to exactly one metric-family branch.
 * Keeping that coordination here prevents family modules from depending on the
 * dashboard singleton or duplicating selection behavior.
 *
 * @param {object} options - State, DOM refs, selector callbacks, and browser dependencies.
 * @returns {void}
 */
export function renderEvaluationPlotsForDashboard({
  state,
  dom,
  activeExperiment,
  evaluationContext,
  documentLike = globalThis.document,
  requestAnimationFrameLike = globalThis.requestAnimationFrame,
  navigatorLike = globalThis.navigator,
  consoleLike = globalThis.console,
  plotTooltipHandlers,
  getSelectedPredictionGroups,
  getSelectedEvaluationGroups,
  getMetricTypeForEvaluationContext,
  getPlotGroups,
  getEvaluationEffectiveValue,
  getEvaluationExperiment,
  displayPlotGroupFieldName,
  displayGroupFieldName,
  getPlotDisplayLabel,
  getPlotTitleLabel,
  rerenderEvaluationPlots,
  timing = null,
}) {
  const { evalPlotTabs, evalPlotContent, plotGroupBarsList } = dom;
  const plotTiming = timing || createTimingCollector({ enabled: false });
  state.activePlotDownloadData = null;

  renderDashboardPlotControls({ state, dom, metricType: null });
  evalPlotTabs.innerHTML = "";
  evalPlotContent.innerHTML = "";
  plotGroupBarsList.innerHTML = "";
  state.activePlotLegendItems = [];

  const selectedPredictionGroups = plotTiming.time(
    "plots selected prediction groups",
    () => getSelectedPredictionGroups()
  );
  if (selectedPredictionGroups.length === 0) {
    appendPlotEmptyMessage(documentLike, evalPlotContent, "Select prediction groups to generate plots.");
    return;
  }

  if (!evaluationContext) {
    appendPlotEmptyMessage(documentLike, evalPlotContent, "Select one or more prediction groups to generate plots.");
    return;
  }

  const { evalTabState } = evaluationContext;
  const metricType = plotTiming.time(
    "plots metric type",
    () => getMetricTypeForEvaluationContext(activeExperiment, evaluationContext)
  );
  renderDashboardPlotControls({ state, dom, metricType });

  const selectedEvalGroups = plotTiming.time(
    "plots selected evaluation groups",
    () => getSelectedEvaluationGroups(evaluationContext)
  );
  if (selectedEvalGroups.length === 0) {
    appendPlotEmptyMessage(documentLike, evalPlotContent, "Select evaluation groups to generate plots.");
    return;
  }

  if (!isSupportedPlotMetricType(metricType)) {
    appendPlotEmptyMessage(
      documentLike,
      evalPlotContent,
      `(unknown metric type: ${metricType || "(missing)"}, data visualization not yet implemented)`
    );
    return;
  }

  const combined = plotTiming.time(
    "plots group selected evaluations",
    () => getPlotGroups(
      activeExperiment,
      selectedEvalGroups,
      evalTabState.groupByFields,
      evalTabState
    )
  );
  const plotGroups = combined.groups;
  const plotGroupFields = combined.fields;
  const varyingPlotGroupFields = plotTiming.time(
    "plots varying group fields",
    () => getVaryingFields(plotGroups, plotGroupFields)
  );

  if (metricType === "ConfusionMatrix") {
    renderConfusionMatrixPlots({
      state,
      dom,
      activeExperiment,
      evalTabState,
      plotGroups,
      plotGroupFields,
      varyingPlotGroupFields,
      documentLike,
      plotTooltipHandlers,
      getEvaluationEffectiveValue,
      getEvaluationExperiment,
      displayPlotGroupFieldName,
      getPlotDisplayLabel,
      rerenderEvaluationPlots,
      timing: plotTiming,
    });
    return;
  }

  if (metricType === "TpFpFnCollector") {
    renderTpFpFnPlots({
      state,
      dom,
      activeExperiment,
      evalTabState,
      plotGroups,
      plotGroupFields,
      varyingPlotGroupFields,
      documentLike,
      requestAnimationFrameLike,
      navigatorLike,
      consoleLike,
      plotTooltipHandlers,
      getEvaluationEffectiveValue,
      displayPlotGroupFieldName,
      getPlotDisplayLabel,
      rerenderEvaluationPlots,
      timing: plotTiming,
    });
    return;
  }

  renderBarLikePlots({
    state,
    dom,
    activeExperiment,
    plotGroups,
    varyingPlotGroupFields,
    metricType,
    documentLike,
    requestAnimationFrameLike,
    plotTooltipHandlers,
    displayPlotGroupFieldName,
    displayGroupFieldName,
    getPlotTitleLabel,
    rerenderEvaluationPlots,
    timing: plotTiming,
  });
}

/**
 * Synchronizes plot-control DOM refs from the current dashboard state.
 *
 * Centralizing this projection ensures early empty/error returns still leave
 * all controls consistent with the active metric family and stored settings.
 *
 * @param {object} options - Dashboard state, DOM refs, and active metric type.
 * @returns {void}
 */
export function renderDashboardPlotControls({ state, dom, metricType }) {
  renderPlotControls({
    metricType,
    plotTabsBy: state.plotTabsBy,
    confusionTabsBy: state.confusionTabsBy,
    plotShortenLabels: state.plotShortenLabels,
    plotRoundingPrecision: state.plotRoundingPrecision,
    plotConfusionMinLabelTotal: state.plotConfusionMinLabelTotal,
    plotTpFpFnMinLabelTotal: state.plotTpFpFnMinLabelTotal,
    plotTpFpFnMinDocumentTotal: state.plotTpFpFnMinDocumentTotal,
    plotShowLegendOnce: state.plotShowLegendOnce,
    exportOpaqueBackground: state.exportOpaqueBackground,
    plotTabsByPrefixButton: dom.plotTabsByPrefixButton,
    plotTabsBySuffixButton: dom.plotTabsBySuffixButton,
    confusionTabsByMetricFieldButton: dom.confusionTabsByMetricFieldButton,
    confusionTabsByPredictionGroupButton: dom.confusionTabsByPredictionGroupButton,
    plotShortenLabelsInput: dom.plotShortenLabels,
    plotRoundingPrecisionInput: dom.plotRoundingPrecision,
    plotConfusionMinLabelTotalRow: dom.plotConfusionMinLabelTotalRow,
    plotConfusionMinLabelTotalInput: dom.plotConfusionMinLabelTotal,
    plotTpFpFnMinLabelTotalRow: dom.plotTpFpFnMinLabelTotalRow,
    plotTpFpFnMinLabelTotalInput: dom.plotTpFpFnMinLabelTotal,
    plotTpFpFnMinDocumentTotalRow: dom.plotTpFpFnMinDocumentTotalRow,
    plotTpFpFnMinDocumentTotalInput: dom.plotTpFpFnMinDocumentTotal,
    plotTabsByRow: dom.plotTabsByRow,
    plotConfusionTabsByRow: dom.plotConfusionTabsByRow,
    plotGroupBarsRow: dom.plotGroupBarsRow,
    plotShowLegendOnceRow: dom.plotShowLegendOnceRow,
    plotShowLegendOnceInput: dom.plotShowLegendOnce,
    exportOpaqueBackgroundInput: dom.exportOpaqueBackground,
  });
}

/**
 * Appends the shared empty-state message used by plot surfaces.
 *
 * All family branches use the same markup contract so styling and download-card
 * discovery do not need family-specific empty-state handling.
 *
 * @param {Document} documentLike - Document-like element factory.
 * @param {HTMLElement} containerElement - Plot container receiving the message.
 * @param {string} text - Visible empty-state text.
 * @returns {void}
 */
export function appendPlotEmptyMessage(documentLike, containerElement, text) {
  const msg = documentLike.createElement("p");
  msg.className = "plot-empty";
  msg.textContent = text;
  containerElement.appendChild(msg);
}

/**
 * Renders precomputed plot-tab button models with the shared selection guard.
 *
 * Active-tab resolution happens before DOM work; this adapter only renders the
 * resulting models and avoids an unnecessary rerender when the active tab is clicked.
 *
 * @param {object} options - Tab DOM, models, state, and rerender callback.
 * @returns {void}
 */
export function renderPlotTabButtonModels({
  documentLike,
  containerElement,
  tabModels,
  activeKey,
  onActiveTabChange,
}) {
  renderTabButtons({
    documentLike,
    containerElement,
    tabModels,
    onSelect: (key) => {
      if (key !== activeKey) {
        onActiveTabChange(key);
      }
    },
  });
}

/**
 * Creates the shared plot-card shell with its visible title.
 *
 * Family branches supply semantic titles and SVG content while this helper
 * preserves the common card markup required by figure export.
 *
 * @param {Document} documentLike - Document-like element factory.
 * @param {string} titleText - Visible plot title.
 * @returns {HTMLElement} Plot card element.
 */
export function createPlotCard(documentLike, titleText) {
  const card = documentLike.createElement("section");
  card.className = "plot-card";
  const title = documentLike.createElement("p");
  title.className = "plot-title";
  title.textContent = titleText;
  card.appendChild(title);
  return card;
}

/**
 * Creates the shared grid used for active-tab plot cards.
 *
 * Keeping grid construction independent from family rendering makes the
 * active-tab lifecycle reusable when rendering is later narrowed to one plot.
 *
 * @param {Document} documentLike - Document-like element factory.
 * @returns {HTMLElement} Empty plot grid.
 */
export function createPlotGrid(documentLike) {
  const grid = documentLike.createElement("div");
  grid.className = "plot-grid";
  return grid;
}

/**
 * Builds the lazy download envelope for rendered plots in one active tab.
 *
 * The envelope retains exact pre-aggregation data references; JSON-safe
 * conversion remains deferred until download so ordinary rendering avoids that cost.
 *
 * @param {string} metricFamily - Public metric-family identifier.
 * @param {object} activeTab - Resolved active tab definition.
 * @param {Array<object>} plots - Rendered plot download sources.
 * @returns {{metric_family: string, plot_tab: string, plot_tab_variant: string, plots: Array<object>}} Download envelope.
 */
export function buildActiveTabDownloadEnvelope(metricFamily, activeTab, plots) {
  return {
    metric_family: metricFamily,
    plot_tab: activeTab.plotTab,
    plot_tab_variant: activeTab.plotTabVariant,
    plots,
  };
}

/**
 * Reports whether the dashboard has an implemented plot-family branch.
 *
 * An explicit allowlist makes unsupported metric types fail into the visible
 * empty state instead of accidentally entering the numeric fallback branch.
 *
 * @param {string | null} metricType - Metric type derived from the evaluation context.
 * @returns {boolean} Whether plot rendering is implemented for the metric type.
 */
function isSupportedPlotMetricType(metricType) {
  return (
    metricType === "ConfusionMatrix" ||
    metricType === "ErrorCollector" ||
    metricType === "F1MicroMultipleFieldsMetric" ||
    metricType === "TpFpFnCollector"
  );
}

/**
 * Renders the resolved active confusion-matrix tab.
 *
 * Confusion-specific preparation, aggregation, filtering, and SVG semantics
 * stay in `confusion.js`; this branch owns dashboard lifecycle concerns such as
 * tabs, cards, visible empty states, and active-tab download scope.
 *
 * @param {object} options - Dashboard state, plot definitions, DOM dependencies, and callbacks.
 * @returns {void}
 */
function renderConfusionMatrixPlots({
  state,
  dom,
  activeExperiment,
  evalTabState,
  plotGroups,
  plotGroupFields,
  varyingPlotGroupFields,
  documentLike,
  plotTooltipHandlers,
  getEvaluationEffectiveValue,
  getEvaluationExperiment,
  displayPlotGroupFieldName,
  getPlotDisplayLabel,
  rerenderEvaluationPlots,
  timing,
}) {
  const labelFields = varyingPlotGroupFields.length ? varyingPlotGroupFields : plotGroupFields;
  const confusionTabMap = timing.time(
    "confusion tab map",
    () => buildConfusionTabMap({
      activeExperiment,
      plotGroups,
      labelFields,
      evalTabState,
      matrixTabsBy: state.confusionTabsBy,
      getEvaluationEffectiveValue,
      getEvaluationExperiment,
      displayPlotGroupFieldName,
      shortenLabels: state.plotShortenLabels,
    })
  );
  const sortedConfusionTabKeys = timing.time(
    "confusion sort tabs",
    () => Array.from(confusionTabMap.keys()).sort((a, b) =>
      confusionTabMap.get(a).label.localeCompare(confusionTabMap.get(b).label)
    )
  );
  if (sortedConfusionTabKeys.length === 0) {
    appendPlotEmptyMessage(documentLike, dom.evalPlotContent, `No confusion matrix data found for ${activeExperiment}.`);
    return;
  }

  const activeTabResult = resolveActiveTab(
    confusionTabMap,
    sortedConfusionTabKeys,
    state.activeEvalPlotTab
  );
  state.activeEvalPlotTab = activeTabResult.activeKey;
  renderPlotTabButtonModels({
    documentLike,
    containerElement: dom.evalPlotTabs,
    tabModels: buildCountTabButtonModels(activeTabResult.orderedKeys, {
      activeValue: activeTabResult.activeKey,
      getLabelText: (key) => confusionTabMap.get(key).label,
      getCount: (key) => {
        const entry = confusionTabMap.get(key);
        return countDistinctConfusionMatrixRuns(entry.plots.flatMap((plot) => plot.collections));
      },
      getTitle: (key) => confusionTabMap.get(key).label,
    }),
    activeKey: activeTabResult.activeKey,
    onActiveTabChange: (key) => {
      state.activeEvalPlotTab = key;
      rerenderEvaluationPlots(activeExperiment);
    },
  });

  const activeConfusionEntry = activeTabResult.activeTab;
  const grid = createPlotGrid(documentLike);
  const downloadPlots = [];

  for (const plotEntry of activeConfusionEntry.plots) {
    const aggregationInput = timing.time(
      "confusion aggregation input",
      () => getConfusionMatrixAggregationInput(plotEntry.collections, plotEntry.fieldLabel),
      { plot: plotEntry.label, field: plotEntry.fieldLabel }
    );
    const aggregation = timing.time(
      "confusion aggregate and filter",
      () => filterConfusionMatrixAggregationByLabelTotal(
        getConfusionMatrixAggregationFromInput(aggregationInput),
        state.plotConfusionMinLabelTotal
      ),
      { plot: plotEntry.label, field: plotEntry.fieldLabel }
    );
    if (!aggregation.rows.length || !aggregation.cols.length) {
      continue;
    }
    downloadPlots.push({
      metadata: buildDownloadPlotMetadata("confusion_matrix", plotEntry),
      dataSource: aggregationInput,
    });

    const fieldTitle = getPlotDisplayLabel(plotEntry.fieldLabel, { shortenLabels: state.plotShortenLabels });
    const titleText = state.confusionTabsBy === "metric_field"
      ? `${plotEntry.label} (mean ± std)`
      : `${fieldTitle} (mean ± std)`;
    const card = createPlotCard(documentLike, titleText);
    const svg = timing.time(
      "confusion render svg",
      () => createConfusionMatrixHeatmapSvg({
        documentLike,
        aggregation,
        precision: state.plotRoundingPrecision,
        getDisplayLabel: getPlotDisplayLabel,
        showTooltip: plotTooltipHandlers.show,
        moveTooltip: plotTooltipHandlers.move,
        hideTooltip: plotTooltipHandlers.hide,
      }),
      { plot: plotEntry.label, field: plotEntry.fieldLabel }
    );
    card.appendChild(svg);
    grid.appendChild(card);
  }

  if (!grid.childElementCount) {
    appendPlotEmptyMessage(
      documentLike,
      dom.evalPlotContent,
      `No confusion matrix values found for ${activeConfusionEntry.label} with minimum label total ${state.plotConfusionMinLabelTotal}.`
    );
    return;
  }

  state.activePlotDownloadData = buildActiveTabDownloadEnvelope(
    "confusion_matrix",
    activeConfusionEntry,
    downloadPlots
  );
  dom.evalPlotContent.appendChild(grid);
}

/**
 * Renders the resolved active TP/FP/FN tab.
 *
 * TP/FP/FN normalization and matrix rendering remain family-owned while this
 * branch composes dashboard tabs, cards, the shared legend, and lazy downloads.
 * This mirrors the confusion lifecycle without forcing both families into one
 * callback-heavy renderer.
 *
 * @param {object} options - Dashboard state, plot definitions, DOM dependencies, and callbacks.
 * @returns {void}
 */
function renderTpFpFnPlots({
  state,
  dom,
  activeExperiment,
  evalTabState,
  plotGroups,
  plotGroupFields,
  varyingPlotGroupFields,
  documentLike,
  requestAnimationFrameLike,
  navigatorLike,
  consoleLike,
  plotTooltipHandlers,
  getEvaluationEffectiveValue,
  displayPlotGroupFieldName,
  getPlotDisplayLabel,
  rerenderEvaluationPlots,
  timing,
}) {
  const labelFields = varyingPlotGroupFields.length ? varyingPlotGroupFields : plotGroupFields;
  const tpfpfnTabMap = timing.time(
    "tpfpfn tab map",
    () => buildTpFpFnTabMap({
      plotGroups,
      labelFields,
      evalTabState,
      matrixTabsBy: state.confusionTabsBy,
      getEvaluationEffectiveValue,
      displayPlotGroupFieldName,
      shortenLabels: state.plotShortenLabels,
    })
  );
  const sortedTabKeys = timing.time(
    "tpfpfn sort tabs",
    () => Array.from(tpfpfnTabMap.keys()).sort((a, b) =>
      tpfpfnTabMap.get(a).label.localeCompare(tpfpfnTabMap.get(b).label)
    )
  );
  if (!sortedTabKeys.length) {
    appendPlotEmptyMessage(documentLike, dom.evalPlotContent, "No TpFpFnCollector data found for " + activeExperiment + ".");
    return;
  }

  const activeTabResult = resolveActiveTab(tpfpfnTabMap, sortedTabKeys, state.activeEvalPlotTab);
  state.activeEvalPlotTab = activeTabResult.activeKey;
  renderPlotTabButtonModels({
    documentLike,
    containerElement: dom.evalPlotTabs,
    tabModels: buildCountTabButtonModels(activeTabResult.orderedKeys, {
      activeValue: activeTabResult.activeKey,
      getLabelText: (key) => tpfpfnTabMap.get(key).label,
      getCount: (key) => {
        const entry = tpfpfnTabMap.get(key);
        return entry.plots.reduce((sum, plot) => sum + plot.collections.length, 0);
      },
      getTitle: (key) => {
        const entry = tpfpfnTabMap.get(key);
        const evaluationCount = entry.plots.reduce((sum, plot) => sum + plot.collections.length, 0);
        return `${entry.label} (${evaluationCount} grouped evaluations)`;
      },
    }),
    activeKey: activeTabResult.activeKey,
    onActiveTabChange: (key) => {
      state.activeEvalPlotTab = key;
      rerenderEvaluationPlots(activeExperiment);
    },
  });

  const activeEntry = activeTabResult.activeTab;
  const grid = createPlotGrid(documentLike);
  const downloadPlots = [];

  for (const plotEntry of activeEntry.plots) {
    const aggregationInput = timing.time(
      "tpfpfn aggregation input",
      () => getTpFpFnAggregationInput(plotEntry.collections, plotEntry.fieldLabel),
      { plot: plotEntry.label, field: plotEntry.fieldLabel }
    );
    const aggregation = timing.time(
      "tpfpfn aggregate and filter",
      () => filterTpFpFnAggregationByTotals(
        getTpFpFnAggregationFromInput(aggregationInput),
        state.plotTpFpFnMinLabelTotal,
        state.plotTpFpFnMinDocumentTotal
      ),
      { plot: plotEntry.label, field: plotEntry.fieldLabel }
    );
    if (!aggregation.rows.length || !aggregation.cols.length) {
      continue;
    }
    downloadPlots.push({
      metadata: buildDownloadPlotMetadata("tpfpfn", plotEntry),
      dataSource: aggregationInput,
    });

    const fieldTitle = getPlotDisplayLabel(plotEntry.fieldLabel, { shortenLabels: state.plotShortenLabels });
    const titleText = state.confusionTabsBy === "metric_field"
      ? `${plotEntry.label} (${aggregation.totalEvaluations} grouped evals)`
      : `${fieldTitle} (${aggregation.totalEvaluations} grouped evals)`;
    const card = createPlotCard(documentLike, titleText);
    const svg = timing.time(
      "tpfpfn render svg",
      () => createTpFpFnCombinedMatrixSvg({
        documentLike,
        requestAnimationFrameLike,
        aggregation,
        aggregationInput,
        precision: state.plotRoundingPrecision,
        getDisplayLabel: getPlotDisplayLabel,
        showTooltip: plotTooltipHandlers.show,
        moveTooltip: plotTooltipHandlers.move,
        hideTooltip: plotTooltipHandlers.hide,
        writeTextToClipboard: (text) => writeTextToClipboard({
          documentLike,
          navigatorLike,
          text,
        }),
        consoleLike,
      }),
      { plot: plotEntry.label, field: plotEntry.fieldLabel }
    );
    card.appendChild(svg);
    grid.appendChild(card);
  }

  if (!grid.childElementCount) {
    appendPlotEmptyMessage(
      documentLike,
      dom.evalPlotContent,
      `No TP/FP/FN values found for ${activeEntry.label} with minimum label total ${state.plotTpFpFnMinLabelTotal} and minimum document total ${state.plotTpFpFnMinDocumentTotal}.`
    );
    return;
  }

  state.activePlotDownloadData = buildActiveTabDownloadEnvelope(
    "tpfpfn",
    activeEntry,
    downloadPlots
  );
  dom.evalPlotContent.appendChild(createTpFpFnLegendElement({ documentLike }));
  dom.evalPlotContent.appendChild(grid);
}

/**
 * Renders the resolved active numeric bar/error tab.
 *
 * Numeric discovery, sample preparation, aggregation, and SVG primitives stay
 * in `bars.js`. This branch coordinates dashboard-only grouping controls,
 * shared or per-card legends, card composition, and active-tab download state.
 *
 * @param {object} options - Dashboard state, numeric plot groups, DOM dependencies, and callbacks.
 * @returns {void}
 */
function renderBarLikePlots({
  state,
  dom,
  activeExperiment,
  plotGroups,
  varyingPlotGroupFields,
  metricType,
  documentLike,
  requestAnimationFrameLike,
  plotTooltipHandlers,
  displayPlotGroupFieldName,
  displayGroupFieldName,
  getPlotTitleLabel,
  rerenderEvaluationPlots,
  timing,
}) {
  const varyingGroupByFields = varyingPlotGroupFields;
  state.plotGroupBarFields = new Set(
    Array.from(state.plotGroupBarFields).filter((field) => new Set(varyingGroupByFields).has(field))
  );
  renderPlotGroupBarChips({
    documentLike,
    listElement: dom.plotGroupBarsList,
    availableFields: varyingGroupByFields,
    checkedValues: state.plotGroupBarFields,
    getLabel: displayPlotGroupFieldName,
    onToggle: (field, checked) => {
      if (checked) {
        state.plotGroupBarFields.add(field);
      } else {
        state.plotGroupBarFields.delete(field);
      }
      rerenderEvaluationPlots(activeExperiment);
    },
  });

  const groupBarFields = varyingGroupByFields.filter((field) => state.plotGroupBarFields.has(field));
  const categoryFields = varyingGroupByFields.filter((field) => !groupBarFields.includes(field));

  const plotDefinitions = timing.time(
    "bar plot definitions",
    () => buildNumericPlotDefinitions(plotGroups)
  );
  if (!plotDefinitions.length) {
    appendPlotEmptyMessage(documentLike, dom.evalPlotContent, `No plottable metric values found for ${activeExperiment}.`);
    return;
  }

  const tabMap = timing.time(
    "bar tab map",
    () => metricType === "ErrorCollector"
      ? buildErrorsTabMap(plotDefinitions)
      : buildBarsTabMap(plotDefinitions, state.plotTabsBy)
  );
  const sortedTabKeys = getSortedBarPlotTabKeys(tabMap);
  const activeTabResult = resolveActiveTab(tabMap, sortedTabKeys, state.activeEvalPlotTab);
  state.activeEvalPlotTab = activeTabResult.activeKey;
  renderPlotTabButtonModels({
    documentLike,
    containerElement: dom.evalPlotTabs,
    tabModels: buildCountTabButtonModels(activeTabResult.orderedKeys, {
      activeValue: activeTabResult.activeKey,
      getLabelText: (key) => tabMap.get(key).label,
      getCount: (key) => tabMap.get(key).plots.length,
      getTitle: (key) => tabMap.get(key).label,
    }),
    activeKey: activeTabResult.activeKey,
    onActiveTabChange: (key) => {
      state.activeEvalPlotTab = key;
      rerenderEvaluationPlots(activeExperiment);
    },
  });
  const activeDefinitions = activeTabResult.activeTab.plots;
  const plotEntriesInput = timing.time(
    "bar active plot entry input",
    () => buildNumericPlotEntriesInput({
      metricType,
      plotDefinitions: activeDefinitions,
      plotGroups,
      groupBarFields,
      categoryFields,
      getGroupLabel: (group, fields, fallback, formatter = displayGroupFieldName) =>
        getGroupLabelForFields(group, fields, fallback, formatter),
      displayGroupFieldName: displayPlotGroupFieldName,
    })
  );
  const plotEntries = timing.time(
    "bar aggregate active plot entries",
    () => getNumericPlotEntriesFromInput(plotEntriesInput)
  );

  const groupedLegendModel = groupBarFields.length
    ? buildGroupedLegendModel(plotEntries)
    : null;
  if (dom.plotShowLegendOnceRow) {
    dom.plotShowLegendOnceRow.style.display = groupedLegendModel?.items.length > 1 ? "" : "none";
  }
  const hasSharedLegend = Boolean(groupedLegendModel && groupedLegendModel.items.length > 1);
  if (hasSharedLegend && state.plotShowLegendOnce) {
    dom.evalPlotContent.appendChild(createPlotLegendElement({
      documentLike,
      legendItems: groupedLegendModel.items,
    }));
  }

  const grid = createPlotGrid(documentLike);
  timing.time(
    "bar render active plot grid",
    () => {
      for (const entry of plotEntries) {
        const groupedByText = groupBarFields.length
          ? ` | grouped by: ${groupBarFields.map((field) => displayPlotGroupFieldName(field)).join(", ")}`
          : "";
        const card = createPlotCard(
          documentLike,
          `${getPlotTitleLabel(entry, metricType)} (mean ± std)${groupedByText}`
        );
        if (groupBarFields.length) {
          const plotLegendItems = getLegendItemsForPoints(entry.points, groupedLegendModel);
          if (plotLegendItems.length > 1 && !state.plotShowLegendOnce) {
            card.appendChild(createPlotLegendElement({
              documentLike,
              legendItems: plotLegendItems,
            }));
          }
          card.appendChild(createGroupedBarPlotSvg({
            documentLike,
            requestAnimationFrameLike,
            points: entry.points,
            legendModel: groupedLegendModel,
            showTooltip: plotTooltipHandlers.show,
            moveTooltip: plotTooltipHandlers.move,
            hideTooltip: plotTooltipHandlers.hide,
          }));
        } else {
          card.appendChild(createBarPlotSvg({
            documentLike,
            requestAnimationFrameLike,
            points: entry.points,
            showTooltip: plotTooltipHandlers.show,
            moveTooltip: plotTooltipHandlers.move,
            hideTooltip: plotTooltipHandlers.hide,
          }));
        }
        grid.appendChild(card);
      }
    },
    { tab_count: tabMap.size, entry_count: plotEntries.length }
  );
  if (!grid.childElementCount) {
    appendPlotEmptyMessage(
      documentLike,
      dom.evalPlotContent,
      "No plottable metric values found for the active tab."
    );
  } else {
    dom.evalPlotContent.appendChild(grid);
  }
  state.activePlotLegendItems = hasSharedLegend ? groupedLegendModel.items : [];
  state.activePlotDownloadData = buildActiveTabDownloadEnvelope(
    "numeric",
    activeTabResult.activeTab,
    plotEntriesInput.map((entry) => ({
      metadata: buildDownloadPlotMetadata("numeric", entry),
      dataSource: entry,
    }))
  );
}
