/**
 * Dashboard-level plot rendering adapters.
 */

import { renderPlotControls, renderPlotGroupBarChips } from "../ui/controls.js";
import {
  buildCountTabButtonModels,
  renderTabButtons,
  resolveActiveTabValue,
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
  buildNumericPlotEntriesInput,
  createBarPlotSvg,
  createGroupedBarPlotSvg,
  getNumericPlotEntriesFromInput,
  renderBarPlotTabsAndGrid,
} from "./bars.js";
import { buildDownloadPlotMetadata } from "./download-data.js";
import { createPlotLegendElement } from "./legend.js";
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

function appendPlotEmptyMessage(documentLike, containerElement, text) {
  const msg = documentLike.createElement("p");
  msg.className = "plot-empty";
  msg.textContent = text;
  containerElement.appendChild(msg);
}

function isSupportedPlotMetricType(metricType) {
  return (
    metricType === "ConfusionMatrix" ||
    metricType === "ErrorCollector" ||
    metricType === "F1MicroMultipleFieldsMetric" ||
    metricType === "TpFpFnCollector"
  );
}

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

  state.activeEvalPlotTab = resolveActiveTabValue(state.activeEvalPlotTab, sortedConfusionTabKeys);
  renderTabButtons({
    documentLike,
    containerElement: dom.evalPlotTabs,
    tabModels: buildCountTabButtonModels(sortedConfusionTabKeys, {
      activeValue: state.activeEvalPlotTab,
      getLabelText: (key) => confusionTabMap.get(key).label,
      getCount: (key) => {
        const entry = confusionTabMap.get(key);
        return countDistinctConfusionMatrixRuns(entry.plots.flatMap((plot) => plot.collections));
      },
      getTitle: (key) => confusionTabMap.get(key).label,
    }),
    onSelect: (key) => {
      if (state.activeEvalPlotTab === key) {
        return;
      }
      state.activeEvalPlotTab = key;
      rerenderEvaluationPlots(activeExperiment);
    },
  });

  const activeConfusionEntry = confusionTabMap.get(state.activeEvalPlotTab);
  const grid = documentLike.createElement("div");
  grid.className = "plot-grid";
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

    const card = documentLike.createElement("section");
    card.className = "plot-card";
    const title = documentLike.createElement("p");
    title.className = "plot-title";
    const fieldTitle = getPlotDisplayLabel(plotEntry.fieldLabel, { shortenLabels: state.plotShortenLabels });
    title.textContent = state.confusionTabsBy === "metric_field"
      ? `${plotEntry.label} (mean ± std)`
      : `${fieldTitle} (mean ± std)`;
    card.appendChild(title);
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

  state.activePlotDownloadData = {
    metric_family: "confusion_matrix",
    plot_tab: state.activeEvalPlotTab,
    plots: downloadPlots,
  };
  dom.evalPlotContent.appendChild(grid);
}

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

  state.activeEvalPlotTab = resolveActiveTabValue(state.activeEvalPlotTab, sortedTabKeys);
  renderTabButtons({
    documentLike,
    containerElement: dom.evalPlotTabs,
    tabModels: buildCountTabButtonModels(sortedTabKeys, {
      activeValue: state.activeEvalPlotTab,
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
    onSelect: (key) => {
      if (state.activeEvalPlotTab === key) {
        return;
      }
      state.activeEvalPlotTab = key;
      rerenderEvaluationPlots(activeExperiment);
    },
  });

  const activeEntry = tpfpfnTabMap.get(state.activeEvalPlotTab);
  const grid = documentLike.createElement("div");
  grid.className = "plot-grid";
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

    const card = documentLike.createElement("section");
    card.className = "plot-card";
    const title = documentLike.createElement("p");
    title.className = "plot-title";
    const fieldTitle = getPlotDisplayLabel(plotEntry.fieldLabel, { shortenLabels: state.plotShortenLabels });
    title.textContent = state.confusionTabsBy === "metric_field"
      ? `${plotEntry.label} (${aggregation.totalEvaluations} grouped evals)`
      : `${fieldTitle} (${aggregation.totalEvaluations} grouped evals)`;
    card.appendChild(title);
    const svg = timing.time(
      "tpfpfn render svg",
      () => createTpFpFnCombinedMatrixSvg({
        documentLike,
        requestAnimationFrameLike,
        aggregation,
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

  state.activePlotDownloadData = {
    metric_family: "tpfpfn",
    plot_tab: state.activeEvalPlotTab,
    plots: downloadPlots,
  };
  dom.evalPlotContent.appendChild(createTpFpFnLegendElement({ documentLike }));
  dom.evalPlotContent.appendChild(grid);
}

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

  const plotEntriesInput = timing.time(
    "bar plot entry input",
    () => buildNumericPlotEntriesInput({
      metricType,
      plotGroups,
      groupBarFields,
      categoryFields,
      getGroupLabel: (group, fields, fallback, formatter = displayGroupFieldName) =>
        getGroupLabelForFields(group, fields, fallback, formatter),
      displayGroupFieldName: displayPlotGroupFieldName,
    })
  );
  const plotEntries = timing.time(
    "bar aggregate plot entries",
    () => getNumericPlotEntriesFromInput(plotEntriesInput)
  );
  if (!plotEntries.length) {
    appendPlotEmptyMessage(documentLike, dom.evalPlotContent, `No plottable metric values found for ${activeExperiment}.`);
    return;
  }

  const tabMap = timing.time(
    "bar tab map",
    () => metricType === "ErrorCollector"
      ? buildErrorsTabMap(plotEntries)
      : buildBarsTabMap(plotEntries, { plotTabsBy: state.plotTabsBy })
  );
  const downloadTabMap = timing.time(
    "bar download tab map",
    () => metricType === "ErrorCollector"
      ? buildErrorsTabMap(plotEntriesInput)
      : buildBarsTabMap(plotEntriesInput, { plotTabsBy: state.plotTabsBy })
  );

  const result = timing.time(
    "bar render tabs and grid",
    () => renderBarPlotTabsAndGrid({
      documentLike,
      tabMap,
      activeExperiment,
      groupBarFields,
      metricType,
      activeEvalPlotTab: state.activeEvalPlotTab,
      plotShowLegendOnce: state.plotShowLegendOnce,
      plotShowLegendOnceRow: dom.plotShowLegendOnceRow,
      evalPlotTabs: dom.evalPlotTabs,
      evalPlotContent: dom.evalPlotContent,
      buildCountTabButtonModels,
      renderTabButtons,
      resolveActiveTabValue,
      getPlotTitleLabel,
      displayPlotGroupFieldName,
      createLegendElement: createPlotLegendElement,
      createBarSvg: (points) => createBarPlotSvg({
        documentLike,
        requestAnimationFrameLike,
        points,
        showTooltip: plotTooltipHandlers.show,
        moveTooltip: plotTooltipHandlers.move,
        hideTooltip: plotTooltipHandlers.hide,
      }),
      createGroupedBarSvg: (points, legendModel) => createGroupedBarPlotSvg({
        documentLike,
        requestAnimationFrameLike,
        points,
        legendModel,
        showTooltip: plotTooltipHandlers.show,
        moveTooltip: plotTooltipHandlers.move,
        hideTooltip: plotTooltipHandlers.hide,
      }),
      onActiveTabChange: (key) => {
        if (state.activeEvalPlotTab === key) {
          return;
        }
        state.activeEvalPlotTab = key;
        rerenderEvaluationPlots(activeExperiment);
      },
    }),
    { tab_count: tabMap.size, entry_count: plotEntries.length }
  );
  state.activeEvalPlotTab = result.activeEvalPlotTab;
  state.activePlotLegendItems = result.activePlotLegendItems;
  const activePlotEntries = downloadTabMap.get(result.activeEvalPlotTab) || [];
  state.activePlotDownloadData = {
    metric_family: "numeric",
    plot_tab: result.activeEvalPlotTab,
    plots: activePlotEntries.map((entry) => ({
      metadata: buildDownloadPlotMetadata("numeric", entry),
      dataSource: entry,
    })),
  };
}
