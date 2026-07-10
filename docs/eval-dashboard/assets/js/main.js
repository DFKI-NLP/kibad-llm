/**
 * Eval-dashboard browser entry point.
 *
 * This module owns the singleton page state, wires DOM events to shared dashboard modules,
 * and coordinates data loading plus prediction/evaluation rendering. Domain logic and
 * reusable UI behavior should stay in the imported modules; this file should remain the
 * orchestration layer for the static dashboard page.
 */
import { normalizeSortConfig } from "./utils/sort.js";
import * as dashboardStore from "./state/store.js";
import * as selectors from "./state/selectors.js";
import { collectLocalEvaluationEntries } from "./data/file-loader.js";
import { ingestRunEntries } from "./data/ingest-runs.js";
import { loadGitHubEntriesFromTreeUrl } from "./data/git-loader.js";
import {
  clearGitUrlQueryParam,
  initializeGitHubTokenInput,
  persistGitHubTokenInputValue,
  runGitUrlQueryParamBootstrap,
  setGitUrlQueryParam,
} from "./browser/session.js";
import { captureDomRefs, setPanelVisibility } from "./ui/dom.js";
import {
  getToggleOnlyColumns,
  renderOptionsPanel,
  renderGroupByButtonState,
  renderSortStatus,
} from "./ui/controls.js";
import {
  bindEvalJsonTabSelection,
  renderEvalJsonPane,
} from "./ui/eval-json-pane.js";
import {
  getNextSortConfig as getSharedNextSortConfig,
  updateStickyControlColumnOffsets,
} from "./ui/table-shared.js";
import {
  buildPredictionColumnSections,
  renderPredictionTable,
} from "./ui/prediction-table.js";
import {
  buildEvaluationColumnSections,
  renderEvaluationTable,
} from "./ui/evaluation-table.js";
import {
  bindDelegatedTabSelection,
  buildCountTabButtonModels,
  renderTabButtons,
  renderStaticTabState,
  resolveActiveTabValue,
} from "./ui/tabs.js";
import {
  clearLoadProgress,
  renderLoadProgress,
  renderLoadStatusStage,
  renderLoadStatusSummary,
  setDownloadFiguresButtonBusy,
} from "./ui/status.js";
import { getEvaluationRunId } from "./utils/runs.js";
import {
  getPlotDisplayLabel as getSharedPlotDisplayLabel,
} from "./plots/shared.js";
import {
  getPlotTitleLabel as getSharedPlotTitleLabel,
} from "./plots/bars.js";
import {
  createTimingCollector,
  isDebugTimingEnabled,
} from "./utils/timing.js";
import {
  createPlotTooltipHandlers,
  downloadVisiblePlotFigures,
  renderDashboardPlotControls,
  renderEvaluationPlotsForDashboard,
  updateDownloadDataButtonState as updatePlotDownloadDataButtonState,
  updateDownloadFiguresButtonState as updatePlotDownloadFiguresButtonState,
} from "./plots/dashboard.js";
import { downloadActivePlotData } from "./plots/download-data.js";

// Central UI state: loaded prediction/evaluation data, current grouping/selection, and per-eval-tab view state.
const state = dashboardStore.createInitialDashboardState();
const debugTimingEnabled = isDebugTimingEnabled({ locationLike: window.location });

const dom = captureDomRefs(document);
const {
  folderInput,
  gitUrlInput,
  githubTokenInput,
  loadGitButton,
  predictionSummary,
  groupByAllButton,
  groupByNoneButton,
  groupByToggleButton,
  predictionSortedByLabel,
  predictionResetSortButton,
  optionsTabs,
  optionsTabButtons,
  optionsTabPanels,
  truncateColumnsList,
  predictionDefaultsPanel,
  predictionDefaultsList,
  truncateDefaultsButton,
  predictionsTable,
  evalTabs,
  evalSummary,
  evalGroupByAllButton,
  evalGroupByNoneButton,
  evalGroupByToggleButton,
  evalSortedByLabel,
  evalResetSortButton,
  evalOptionsTabs,
  evalOptionsTabButtons,
  evalOptionsTabPanels,
  evalTruncateColumnsList,
  evalDefaultsPanel,
  evalDefaultsList,
  evalLayout,
  evalJsonTabEvaluation,
  evalJsonTabPrediction,
  evalJsonTitle,
  evalJsonCode,
  evaluationsTable,
  plotTabsByPrefixButton,
  plotTabsBySuffixButton,
  plotShortenLabels,
  plotRoundingPrecision,
  plotConfusionMinLabelTotal,
  plotTpFpFnMinLabelTotal,
  plotTpFpFnMinDocumentTotal,
  confusionTabsByMetricFieldButton,
  confusionTabsByPredictionGroupButton,
  plotShowLegendOnce,
  downloadFiguresButton,
  downloadDataButton,
  exportOpaqueBackground,
  evalPlotTabs,
  evalPlotContent,
  barTooltip,
} = dom;
const { SORTABLE_CONTROL_COLUMNS } = dashboardStore;
const {
  EVALUATION_PREFIX,
  JOB_RETURN_VALUE_PREFIX,
  PREDICTION_JOB_RETURN_VALUE_PREFIX,
  PREDICTION_OVERRIDES_PREFIX,
} = selectors;

// Helper functions for adapting shared selector/store APIs to this page's singleton UI state.
function getNextSortConfig(currentSort, column, { append = false } = {}) {
  return getSharedNextSortConfig(currentSort, column, {
    append,
    sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
  });
}

function reconstructPredictionContentForEvaluation(evaluation) {
  return selectors.reconstructPredictionContentForEvaluation(state, evaluation);
}

function getPredictionViews() {
  return selectors.getPredictionViews(state);
}

function getCurrentPredictionColumns(predictionViews = getPredictionViews()) {
  return selectors.getCurrentPredictionColumns(state, predictionViews);
}

function getPredictionGroups(
  predictionViews = getPredictionViews(),
  groupByFields = state.groupByFields,
  predictionColumns = getCurrentPredictionColumns(predictionViews)
) {
  return selectors.getPredictionGroups(state, predictionViews, groupByFields, predictionColumns);
}

function getSelectedPredictionGroups(groups = getCurrentPredictionGroups()) {
  return selectors.getSelectedPredictionGroups(state, groups);
}

/**
 * Synchronize prediction-group UI state with the currently derived prediction groups.
 * This preserves selections for stable ids, auto-selects newly created groups, and drops stale expanded ids.
 */
function syncPredictionGroupUiState(predictionGroups) {
  dashboardStore.syncPredictionGroupUiState(state, predictionGroups);
}

/**
 * Return current prediction groups and synchronize selection/expansion state against them.
 */
function getCurrentPredictionGroups() {
  const predictionViews = getPredictionViews();
  const predictionColumns = getCurrentPredictionColumns(predictionViews);
  const predictionGroups = getPredictionGroups(predictionViews, state.groupByFields, predictionColumns);
  syncPredictionGroupUiState(predictionGroups);
  return predictionGroups;
}

function getSelectedPredictionViews() {
  return selectors.getSelectedPredictionViews(state);
}

function gatherSelectedEvaluations() {
  return selectors.gatherSelectedEvaluations(state);
}

function getEvaluationsByExperiment(selectedEvaluations = gatherSelectedEvaluations()) {
  return selectors.getEvaluationsByExperiment(state, selectedEvaluations);
}

function getSelectedEvaluationsForExperiment(experiment, selectedEvaluations = gatherSelectedEvaluations()) {
  return selectors.getSelectedEvaluationsForExperiment(state, experiment, selectedEvaluations);
}

const plotTooltipHandlers = createPlotTooltipHandlers({ tooltipElement: barTooltip, windowLike: window });

function createDashboardTiming(label) {
  return createTimingCollector({
    enabled: debugTimingEnabled,
    label,
    performanceLike: performance,
    consoleLike: console,
  });
}

function updateDownloadFiguresButtonState() {
  updatePlotDownloadFiguresButtonState({ downloadFiguresButton, evalPlotContent });
}

function updateDownloadDataButtonState() {
  updatePlotDownloadDataButtonState({ downloadDataButton, state });
}

// Helper functions for labels and default column choices.
function displayPredictionColumnName(column) {
  return selectors.stripPredictionFieldPrefix(column);
}

function displayQualifiedPredictionColumnName(column) {
  return selectors.getPredictionQualifiedDisplayName(column);
}

function displayEvalColumnName(column) {
  const normalizedColumn = selectors.stripEvaluationFieldPrefix(column);
  if (normalizedColumn.startsWith(JOB_RETURN_VALUE_PREFIX)) {
    return normalizedColumn.slice(JOB_RETURN_VALUE_PREFIX.length);
  }
  return normalizedColumn.replace(/^overrides\./, "");
}

function displayGroupFieldName(column) {
  if (
    column.startsWith(EVALUATION_PREFIX) ||
    column.startsWith(JOB_RETURN_VALUE_PREFIX) ||
    column.startsWith("overrides.")
  ) {
    return displayEvalColumnName(column);
  }
  return displayQualifiedPredictionColumnName(column);
}

function getPlotDisplayLabel(label) {
  return getSharedPlotDisplayLabel(label, { shortenLabels: state.plotShortenLabels });
}

function getPlotTitleLabel(plotEntry, metricType) {
  return getSharedPlotTitleLabel(plotEntry, metricType, {
    shortenLabels: state.plotShortenLabels,
    plotTabsBy: state.plotTabsBy,
  });
}

function getDefaultGroupByFields(predictionColumns, predictionViews = getPredictionViews()) {
  return selectors.getDefaultGroupByFields(predictionColumns, predictionViews);
}

function getDefaultTruncateColumns(predictionColumns) {
  return selectors.getDefaultTruncateColumns(predictionColumns);
}

function getDefaultEvalGroupByFields(evalColumns, evaluations = []) {
  return selectors.getDefaultEvalGroupByFields(evalColumns, evaluations);
}

// Helper functions for control value normalization and UI state updates.
function setConfiguredDefault(defaults, column, value) {
  const nextValue = String(value ?? "");
  if (nextValue.trim() === "") {
    delete defaults[column];
  } else {
    defaults[column] = nextValue;
  }
}

function setGroupByFields(columns) {
  state.groupByFields = [...columns];
  renderPredictions();
  renderEvaluations();
}

function getActiveEvalColumns() {
  return selectors.getActiveEvalColumns(state);
}

function setActiveEvalGroupByFields(columns) {
  if (!state.activeEvalTab) {
    return;
  }
  const evalColumns = getActiveEvalColumns();
  const evalTabState = ensureEvalTabState(state.activeEvalTab, evalColumns);
  const validColumns = new Set(evalColumns);
  evalTabState.groupByFields = [...new Set(columns)].filter((column) => validColumns.has(column));
  renderEvaluations();
}

function ensureEvalTabState(
  experiment,
  evalColumns,
  evaluations = getSelectedEvaluationsForExperiment(experiment)
) {
  return dashboardStore.ensureEvalTabState(state, experiment, evalColumns, {
    evaluations,
    getDefaultEvalGroupByFields,
    getDefaultEvalTruncateColumns: () => new Set(),
  });
}

function readClampedIntegerInput(inputElement, { fallback, min = 0, max = Infinity }) {
  const parsed = Number.parseInt(inputElement.value, 10);
  const clamped = Number.isFinite(parsed)
    ? Math.max(min, Math.min(max, parsed))
    : fallback;
  inputElement.value = String(clamped);
  return clamped;
}

function setPlotTabsBy(nextTabsBy) {
  if (state.plotTabsBy === nextTabsBy) {
    return;
  }
  state.plotTabsBy = nextTabsBy;
  state.activeEvalPlotTab = null;
  renderEvaluations();
}

function setConfusionTabsBy(nextTabsBy) {
  if (state.confusionTabsBy === nextTabsBy) {
    return;
  }
  state.confusionTabsBy = nextTabsBy;
  state.activeEvalPlotTab = null;
  renderEvaluations();
}

// Helper functions for table sorting and selection changes.
function setPredictionSort(column, event = {}) {
  state.predictionSort = getNextSortConfig(state.predictionSort, column, { append: event.shiftKey });
  renderPredictions();
}

function setEvalSort(column, event = {}) {
  if (!state.activeEvalTab) {
    return;
  }
  const evalTabState = ensureEvalTabState(state.activeEvalTab, getActiveEvalColumns());
  evalTabState.sort = getNextSortConfig(evalTabState.sort, column, { append: event.shiftKey });
  renderEvaluations();
}

function getSortedPredictionGroups(predictionGroups = getCurrentPredictionGroups()) {
  return selectors.getSortedPredictionGroups(state, predictionGroups);
}

function getSortedPredictionMembers(predictions) {
  return selectors.getSortedPredictionMembers(state, predictions);
}

function setSelectedGroupIds(groupIds) {
  state.selectedGroupIds = new Set(groupIds);
  renderPredictions();
  renderEvaluations();
}

// Helper functions for loading local/GitHub evaluation data into canonical dashboard state.
/**
 * Reset load-dependent UI state after new canonical prediction/evaluation data is imported.
 * All prediction/evaluation structures remain selector-derived and are not stored here.
 */
function resetDerivedUiStateAfterLoad(timing = createTimingCollector({ enabled: false })) {
  const predictionViews = timing.time("load derive prediction views", () => getPredictionViews());
  const predictionColumns = timing.time(
    "load derive prediction columns",
    () => getCurrentPredictionColumns(predictionViews)
  );
  const nextGroupByFields = timing.time(
    "load derive default prediction group-by",
    () => getDefaultGroupByFields(predictionColumns, predictionViews)
  );
  const predictionGroups = timing.time(
    "load derive prediction groups",
    () => getPredictionGroups(predictionViews, nextGroupByFields, predictionColumns)
  );
  timing.time("load reset derived ui state", () => {
    dashboardStore.resetDerivedUiStateAfterLoad(state, {
      predictionViews,
      predictionColumns,
      predictionGroups,
      getDefaultGroupByFields,
      getDefaultTruncateColumns,
    });
  });
}

function updateLoadStatusSummary({ candidateRunDirs, loadedCount, skippedSameContent, skippedPredictRuns, skippedMissingJob, skippedUnsupportedVersion, skippedInvalid, skippedMissingPredictionId, skippedConflictingPredictionId }) {
  renderLoadStatusSummary(dom, {
    loadedSources: Array.from(state.loadedFolders).sort(),
    totalEvaluations: state.evaluations.length,
    candidateRunDirs,
    loadedCount,
    skippedSameContent,
    skippedPredictRuns,
    skippedMissingJob,
    skippedUnsupportedVersion,
    skippedInvalid,
    skippedMissingPredictionId,
    skippedConflictingPredictionId,
  });
}

/**
 * Apply a shared-ingestion result to canonical dashboard state and refresh derived UI state.
 */
function applyIngestionResult(sourceLabel, ingestionResult, timing = createTimingCollector({ enabled: false })) {
  state.loadedFolders.add(sourceLabel);
  for (const { runDir, error } of ingestionResult.failures) {
    console.error(`Failed to parse run at ${runDir}`, error);
  }
  timing.time("load apply canonical additions", () => {
    for (const [predictionId, prediction] of Object.entries(ingestionResult.predictionAdditions)) {
      state.predictions[predictionId] = prediction;
    }
    state.evaluations.push(...ingestionResult.evaluationAdditions);
  });
  resetDerivedUiStateAfterLoad(timing);
  timing.time("load render status summary", () => updateLoadStatusSummary(ingestionResult.summary));
}

/**
 * Ingest evaluation-run file entries after filtering out predict runs and incomplete run directories.
 *
 * Selected folder trees can contribute evaluations when a run directory contains both
 * job_return_value.json and .hydra/overrides.yaml. Prediction payloads are canonicalized
 * separately and linked through predictionId.
 */
async function loadEvaluationsFromEntries(entries, rootLabel, timing = createTimingCollector({ enabled: false })) {
  if (!entries.length) {
    renderLoadStatusStage(dom, `No relevant run files found in ${rootLabel}.`);
    return;
  }

  const ingestionResult = await timing.timeAsync(
    "load ingest run entries",
    () => ingestRunEntries(entries, {
      existingPredictions: state.predictions,
      existingEvaluations: state.evaluations,
    }),
    { entry_count: entries.length }
  );
  applyIngestionResult(rootLabel, ingestionResult, timing);
}

async function loadEvaluationsFromFiles(files) {
  const timing = createDashboardTiming("eval-dashboard local folder load");
  hideLoadProgress();
  if (!files.length) {
    renderLoadStatusStage(dom, "No files selected.");
    return;
  }

  const { rootLabel, entries } = await timing.timeAsync(
    "load collect local file entries",
    () => collectLocalEvaluationEntries(files),
    { file_count: files.length }
  );
  await loadEvaluationsFromEntries(entries, rootLabel, timing);
  timing.flush({ source: rootLabel });
}

function updateLoadStatusStage(title, details = []) {
  renderLoadStatusStage(dom, title, details);
}

function hideLoadProgress() {
  clearLoadProgress(dom);
}

function setLoadProgress({ completedFiles = 0, totalFiles = 0, completedBytes = 0, totalBytes = 0, label = "" } = {}) {
  renderLoadProgress(dom, { completedFiles, totalFiles, completedBytes, totalBytes, label });
}

/**
 * Fetch evaluation-run files from a GitHub tree URL and apply them through the shared ingestion path.
 */
async function loadEvaluationsFromGitUrl(rawUrl) {
  const timing = createDashboardTiming("eval-dashboard github load");
  const trimmedUrl = String(rawUrl || "").trim();
  if (!trimmedUrl) {
    hideLoadProgress();
    renderLoadStatusStage(dom, "Enter a GitHub tree URL first.");
    return;
  }

  const token = persistGitHubTokenInputValue(githubTokenInput);
  hideLoadProgress();
  const gitLoadResult = await timing.timeAsync(
    "load fetch github entries",
    () => loadGitHubEntriesFromTreeUrl(trimmedUrl, {
      token,
      onStatus: ({ title, details }) => updateLoadStatusStage(title, details),
      onProgress: (progress) => setLoadProgress(progress),
    })
  );
  if (!gitLoadResult.files.length) {
    hideLoadProgress();
    renderLoadStatusStage(dom, `No matching run files found in ${gitLoadResult.sourceLabel}.`);
    return;
  }

  updateLoadStatusStage("Loading evaluation runs from GitHub files", [
    gitLoadResult.sourceLabel,
    `Fetched files: ${gitLoadResult.entries.length}`,
  ]);
  await loadEvaluationsFromEntries(gitLoadResult.entries, gitLoadResult.sourceLabel, timing);
  setLoadProgress({
    completedFiles: gitLoadResult.files.length,
    totalFiles: gitLoadResult.files.length,
    completedBytes: gitLoadResult.totalBytes,
    totalBytes: gitLoadResult.totalBytes,
    label: "GitHub fetch complete",
  });
  timing.flush({ source: gitLoadResult.sourceLabel });
}

async function handleGitLoadRequest() {
  const trimmedUrl = String(gitUrlInput.value || "").trim();
  if (!trimmedUrl) {
    renderLoadStatusStage(dom, "Enter a GitHub tree URL first.");
    return;
  }

  loadGitButton.disabled = true;
  setGitUrlQueryParam(trimmedUrl);
  try {
    await loadEvaluationsFromGitUrl(trimmedUrl);
    renderPredictions();
    renderEvaluations();
  } catch (error) {
    console.error(error);
    renderLoadStatusStage(dom, `GitHub load failed: ${error.message || error}`);
  } finally {
    loadGitButton.disabled = false;
  }
}

async function initializeGitUrlFromQueryParam() {
  await runGitUrlQueryParamBootstrap({
    inputElement: gitUrlInput,
    onLoadRequested: () => handleGitLoadRequest(),
  });
}

// Event wiring for source loading, controls, plot settings, and layout observers.
folderInput.addEventListener("change", async (event) => {
  const files = Array.from(event.target.files || []);
  clearGitUrlQueryParam();
  await loadEvaluationsFromFiles(files);
  renderPredictions();
  renderEvaluations();
});

function bindDataSourceControls() {
  initializeGitHubTokenInput(githubTokenInput);

  githubTokenInput.addEventListener("change", () => {
    persistGitHubTokenInputValue(githubTokenInput);
  });

  gitUrlInput.addEventListener("keydown", async (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    await handleGitLoadRequest();
  });

  loadGitButton.addEventListener("click", async () => {
    await handleGitLoadRequest();
  });
}

function bindPredictionControls() {
  groupByAllButton.addEventListener("click", () => {
    setGroupByFields(getCurrentPredictionColumns());
  });

  groupByNoneButton.addEventListener("click", () => {
    setGroupByFields([]);
  });

  groupByToggleButton.addEventListener("click", () => {
    const predictionColumns = getCurrentPredictionColumns();
    const nextGroupByFields = getToggleOnlyColumns(predictionColumns, state.groupByFields);
    setGroupByFields(nextGroupByFields);
  });

  predictionResetSortButton.addEventListener("click", () => {
    if (!normalizeSortConfig(state.predictionSort).length) {
      return;
    }
    state.predictionSort = [];
    renderPredictions();
  });

  bindDelegatedTabSelection({
    containerElement: optionsTabs,
    getActiveValue: () => state.activeOptionsTab,
    onSelect: (tab) => {
      state.activeOptionsTab = tab;
      renderStaticTabState({
        buttonElements: optionsTabButtons,
        panelElements: optionsTabPanels,
        activeValue: state.activeOptionsTab,
      });
    },
  });

  truncateDefaultsButton.addEventListener("click", () => {
    state.truncateEnabledColumns = getDefaultTruncateColumns(getCurrentPredictionColumns());
    renderPredictions();
  });
}

function bindEvaluationControls() {
  evalGroupByAllButton.addEventListener("click", () => {
    setActiveEvalGroupByFields(getActiveEvalColumns());
  });

  evalGroupByNoneButton.addEventListener("click", () => {
    setActiveEvalGroupByFields([]);
  });

  evalGroupByToggleButton.addEventListener("click", () => {
    if (!state.activeEvalTab) {
      return;
    }
    const evalColumns = getActiveEvalColumns();
    const evalTabState = ensureEvalTabState(state.activeEvalTab, evalColumns);
    const nextGroupByFields = getToggleOnlyColumns(evalColumns, evalTabState.groupByFields);
    setActiveEvalGroupByFields(nextGroupByFields);
  });

  evalResetSortButton.addEventListener("click", () => {
    if (!state.activeEvalTab) {
      return;
    }
    const evalTabState = ensureEvalTabState(state.activeEvalTab, getActiveEvalColumns());
    if (!normalizeSortConfig(evalTabState.sort).length) {
      return;
    }
    evalTabState.sort = [];
    renderEvaluations();
  });

  bindDelegatedTabSelection({
    containerElement: evalOptionsTabs,
    getActiveValue: () => {
      if (!state.activeEvalTab || !state.evalTabStates[state.activeEvalTab]) {
        return null;
      }
      return state.evalTabStates[state.activeEvalTab].activeOptionsTab;
    },
    onSelect: (tab) => {
      if (!state.activeEvalTab || !state.evalTabStates[state.activeEvalTab]) {
        return;
      }
      state.evalTabStates[state.activeEvalTab].activeOptionsTab = tab;
      renderStaticTabState({
        buttonElements: evalOptionsTabButtons,
        panelElements: evalOptionsTabPanels,
        activeValue: state.evalTabStates[state.activeEvalTab].activeOptionsTab,
        buttonAttribute: "data-eval-tab",
        panelAttribute: "data-eval-tab-panel",
      });
    },
    valueAttribute: "data-eval-tab",
  });

  bindEvalJsonTabSelection({
    evaluationButton: evalJsonTabEvaluation,
    predictionButton: evalJsonTabPrediction,
    getActiveTab: () => state.activeEvalJsonTab,
    onSelect: (nextTab) => {
      state.activeEvalJsonTab = nextTab;
      renderEvaluations();
    },
  });
}

function bindPlotControls() {
  plotShortenLabels.addEventListener("change", () => {
    state.plotShortenLabels = plotShortenLabels.checked;
    renderEvaluations();
  });

  plotRoundingPrecision.addEventListener("change", () => {
    state.plotRoundingPrecision = readClampedIntegerInput(plotRoundingPrecision, {
      fallback: 2,
      max: 6,
    });
    renderEvaluations();
  });

  plotConfusionMinLabelTotal.addEventListener("change", () => {
    state.plotConfusionMinLabelTotal = readClampedIntegerInput(plotConfusionMinLabelTotal, {
      fallback: 3,
    });
    renderEvaluations();
  });

  plotTpFpFnMinLabelTotal.addEventListener("change", () => {
    state.plotTpFpFnMinLabelTotal = readClampedIntegerInput(plotTpFpFnMinLabelTotal, {
      fallback: 3,
    });
    renderEvaluations();
  });

  plotTpFpFnMinDocumentTotal.addEventListener("change", () => {
    state.plotTpFpFnMinDocumentTotal = readClampedIntegerInput(plotTpFpFnMinDocumentTotal, {
      fallback: 0,
    });
    renderEvaluations();
  });

  plotShowLegendOnce.addEventListener("change", () => {
    state.plotShowLegendOnce = plotShowLegendOnce.checked;
    renderEvaluations();
  });

  exportOpaqueBackground.addEventListener("change", () => {
    state.exportOpaqueBackground = exportOpaqueBackground.checked;
    renderDashboardPlotControls({
      state,
      dom,
      metricType: getMetricTypeForEvaluationContext(state.activeEvalTab || ""),
    });
  });

  downloadFiguresButton.addEventListener("click", async () => {
    if (downloadFiguresButton.disabled) {
      return;
    }
    setDownloadFiguresButtonBusy(downloadFiguresButton);
    try {
      await downloadVisiblePlotFigures({
        state,
        evalPlotContent,
        evalPlotTabs,
        documentLike: document,
        windowLike: window,
        urlLike: URL,
        setTimeoutLike: setTimeout,
        getStyle: getComputedStyle,
        consoleLike: console,
      });
    } finally {
      updateDownloadFiguresButtonState();
    }
  });

  downloadDataButton.addEventListener("click", async () => {
    if (downloadDataButton.disabled) {
      return;
    }
    setDownloadFiguresButtonBusy(downloadDataButton, "Preparing data...");
    try {
      await downloadActivePlotData({
        state,
        documentLike: document,
        windowLike: window,
        urlLike: URL,
        setTimeoutLike: setTimeout,
        consoleLike: console,
      });
    } finally {
      updateDownloadDataButtonState();
    }
  });

  plotTabsByPrefixButton.addEventListener("click", () => setPlotTabsBy("prefix"));
  plotTabsBySuffixButton.addEventListener("click", () => setPlotTabsBy("suffix"));
  confusionTabsByMetricFieldButton.addEventListener("click", () => setConfusionTabsBy("metric_field"));
  confusionTabsByPredictionGroupButton.addEventListener("click", () => setConfusionTabsBy("prediction_group"));
}

function bindLayoutObservers() {
  const evalPlotContentObserver = new MutationObserver(() => {
    updateDownloadFiguresButtonState();
  });
  evalPlotContentObserver.observe(evalPlotContent, { childList: true, subtree: true });
  updateDownloadFiguresButtonState();
  updateDownloadDataButtonState();

  window.addEventListener("resize", () => {
    updateStickyControlColumnOffsets(predictionsTable);
    updateStickyControlColumnOffsets(evaluationsTable);
  });
}

// Startup wiring for the browser page. Keep side effects here so render functions below stay easy to scan.
function initializeDashboard() {
  bindDataSourceControls();
  bindPredictionControls();
  bindEvaluationControls();
  bindPlotControls();
  bindLayoutObservers();
  void initializeGitUrlFromQueryParam();
}

initializeDashboard();

// Render functions for the prediction table, evaluation table, JSON pane, and plots.
/**
 * Render the Predictions table from derived prediction views and prediction groups.
 */
function renderPredictions() {
  const timing = createDashboardTiming("eval-dashboard prediction render");

  try {
    const predictionViews = timing.time("render derive prediction views", () => getPredictionViews());
    const predictionGroups = timing.time("render derive prediction groups", () => getCurrentPredictionGroups());
    const predictionColumns = timing.time(
      "render derive prediction columns",
      () => getCurrentPredictionColumns(predictionViews)
    );

    timing.time("render clear prediction ui", () => {
      predictionsTable.innerHTML = "";
      predictionDefaultsList.innerHTML = "";
    });
    state.predictionSort = timing.time("render prediction sort status", () =>
      renderSortStatus({
        labelElement: predictionSortedByLabel,
        resetButton: predictionResetSortButton,
        sortConfig: state.predictionSort,
        validColumns: [...SORTABLE_CONTROL_COLUMNS, ...predictionColumns],
        displayColumnName: displayPredictionColumnName,
      })
    );
    if (!predictionGroups.length) {
      timing.time("render empty prediction state", () => {
        renderGroupByButtonState(
          {
            allButton: groupByAllButton,
            toggleButton: groupByToggleButton,
            noneButton: groupByNoneButton,
          },
          []
        );
        setPanelVisibility(predictionDefaultsPanel, false);
        predictionSummary.textContent = "No predictions found. Load a folder containing evaluate run outputs.";
      });
      return;
    }

    timing.time("render prediction summary", () => {
      predictionSummary.textContent =
        `Predictions: ${predictionViews.length} | Groups: ${predictionGroups.length} | Group-by: ` +
        (state.groupByFields.length
          ? state.groupByFields.map((field) => displayPredictionColumnName(field)).join(", ")
          : "(none; one row per unique prediction)");
    });

    const predictionSections = timing.time("render build prediction columns", () =>
      buildPredictionColumnSections({
        predictionColumns,
        predictionJobReturnValuePrefix: PREDICTION_JOB_RETURN_VALUE_PREFIX,
        predictionOverridesPrefix: PREDICTION_OVERRIDES_PREFIX,
      })
    );
    const orderedPredictionColumns = predictionSections.flatMap((section) => section.columns);
    timing.time("render prediction group controls", () => {
      renderGroupByButtonState(
        {
          allButton: groupByAllButton,
          toggleButton: groupByToggleButton,
          noneButton: groupByNoneButton,
        },
        orderedPredictionColumns
      );
      renderStaticTabState({
        buttonElements: optionsTabButtons,
        panelElements: optionsTabPanels,
        activeValue: state.activeOptionsTab,
      });
    });
    const selectedPredictionViews = timing.time(
      "render derive selected prediction views",
      () => getSelectedPredictionViews()
    );
    const predictionDefaultColumns = timing.time("render derive prediction defaults", () =>
      selectors.getPredictionColumnsWithMissingValues(
        state,
        selectedPredictionViews,
        orderedPredictionColumns
      )
    );
    timing.time("render prediction options panel", () => {
      renderOptionsPanel({
        documentLike: document,
        checkboxListElement: truncateColumnsList,
        checkboxColumns: orderedPredictionColumns,
        checkedValues: state.truncateEnabledColumns,
        getCheckboxLabel: displayPredictionColumnName,
        onCheckboxToggle: (column, checked) => {
          if (checked) {
            state.truncateEnabledColumns.add(column);
          } else {
            state.truncateEnabledColumns.delete(column);
          }
          renderPredictions();
        },
        defaultsListElement: predictionDefaultsList,
        defaultsPanelElement: predictionDefaultsPanel,
        defaultColumns: predictionDefaultColumns,
        getDefaultLabel: displayPredictionColumnName,
        getDefaultValue: (column) => selectors.getPredictionDefaultValue(state, column),
        getDefaultSuggestions: (column) =>
          selectors.getPredictionDefaultSuggestions(selectedPredictionViews, column),
        getDefaultMissingCount: (column) =>
          selectors.getPredictionMissingValueCount(selectedPredictionViews, column),
        inputIdPrefix: "prediction-default",
        onDefaultCommit: (column, nextValue) => {
          setConfiguredDefault(state.predictionDefaultValues, column, nextValue);
          renderPredictions();
          renderEvaluations();
        },
      });
    });
    const displayedGroups = timing.time(
      "render sort prediction groups",
      () => getSortedPredictionGroups(predictionGroups)
    );

    timing.time("render prediction table", () => {
      renderPredictionTable({
        documentLike: document,
        tableElement: predictionsTable,
        predictionSections,
        orderedPredictionColumns,
        displayedGroups,
        predictionSort: state.predictionSort,
        truncateEnabledColumns: state.truncateEnabledColumns,
        groupByFields: state.groupByFields,
        selectedGroupIds: state.selectedGroupIds,
        expandedGroupIds: state.expandedGroupIds,
        displayColumnName: displayPredictionColumnName,
        onSortToggle: setPredictionSort,
        onToggleGroupByColumn: (column, checked) => {
          const nextGroupByFields = new Set(state.groupByFields);
          if (checked) {
            nextGroupByFields.add(column);
          } else {
            nextGroupByFields.delete(column);
          }
          setGroupByFields(nextGroupByFields);
        },
        onToggleGroupExpansion: (groupId) => {
          if (state.expandedGroupIds.has(groupId)) {
            state.expandedGroupIds.delete(groupId);
          } else {
            state.expandedGroupIds.add(groupId);
          }
          renderPredictions();
        },
        onToggleGroupSelection: (groupId, checked) => {
          const nextSelectedGroupIds = new Set(state.selectedGroupIds);
          if (checked) {
            nextSelectedGroupIds.add(groupId);
          } else {
            nextSelectedGroupIds.delete(groupId);
          }
          setSelectedGroupIds(nextSelectedGroupIds);
        },
        onSelectAllDisplayed: (checked, displayedGroupIds) => {
          setSelectedGroupIds(checked ? displayedGroupIds : []);
        },
        getGroupValueDisplay: (group, column) =>
          selectors.getGroupValueDisplay(state, group, column),
        getSortedPredictionMembers,
        getPredictionEffectiveValue: (predictionFlat, column) =>
          selectors.getPredictionEffectiveValue(state, predictionFlat, column),
        sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
      });
    });
    timing.time("render prediction sticky offsets", () => {
      updateStickyControlColumnOffsets(predictionsTable);
    });
  } finally {
    timing.flush();
  }
}

// Helper functions for adapting evaluation context and plot-group state to shared renderers.
function getEvaluationContext(
  activeExperiment = state.activeEvalTab,
  selectedEvaluations = gatherSelectedEvaluations()
) {
  return selectors.getEvaluationContext(state, activeExperiment, selectedEvaluations);
}

function getSelectedEvaluationGroups(evaluationContext = getEvaluationContext()) {
  return selectors.getSelectedEvaluationGroups(state, evaluationContext);
}

function getPlotGroups(activeExperiment, selectedEvalGroups, evalGroupByFields, evalTabState) {
  return selectors.getPlotGroups(state, activeExperiment, selectedEvalGroups, evalGroupByFields, evalTabState);
}

function getMetricTypeForEvaluationContext(
  activeExperiment,
  evaluationContext = getEvaluationContext(activeExperiment)
) {
  return selectors.getMetricTypeForEvaluationContext(state, activeExperiment, evaluationContext);
}

/**
 * Render evaluation plots from the current selector-derived evaluation context.
 */
function renderEvaluationPlots(
  activeExperiment,
  evaluationContext = null,
  timing = null
) {
  const ownsTiming = !timing;
  const plotTiming = timing || createDashboardTiming("eval-dashboard plot render");
  const resolvedEvaluationContext = evaluationContext || plotTiming.time(
    "render get evaluation context",
    () => getEvaluationContext(activeExperiment)
  );
  renderEvaluationPlotsForDashboard({
    state,
    dom,
    activeExperiment,
    evaluationContext: resolvedEvaluationContext,
    documentLike: document,
    requestAnimationFrameLike: requestAnimationFrame,
    navigatorLike: navigator,
    consoleLike: console,
    plotTooltipHandlers,
    getSelectedPredictionGroups,
    getSelectedEvaluationGroups,
    getMetricTypeForEvaluationContext,
    getPlotGroups,
    getEvaluationEffectiveValue: selectors.getEvaluationEffectiveValue,
    getEvaluationExperiment: selectors.getEvaluationExperiment,
    displayPlotGroupFieldName: (column) => getPlotDisplayLabel(displayGroupFieldName(column)),
    displayGroupFieldName,
    getPlotDisplayLabel,
    getPlotTitleLabel,
    rerenderEvaluationPlots: renderEvaluationPlots,
    timing: plotTiming,
  });
  updateDownloadDataButtonState();
  if (ownsTiming) {
    plotTiming.flush({ active_experiment: activeExperiment || "" });
  }
}

/**
 * Render the evaluation table, JSON pane, and plots from selector-derived evaluation state.
 */
function renderEvaluations() {
  const timing = createDashboardTiming("eval-dashboard evaluation render");
  evalTabs.innerHTML = "";
  evaluationsTable.innerHTML = "";
  renderEvalJsonPane({
    layoutElement: evalLayout,
    titleElement: evalJsonTitle,
    codeElement: evalJsonCode,
    evaluationButton: evalJsonTabEvaluation,
    predictionButton: evalJsonTabPrediction,
    activeTab: state.activeEvalJsonTab,
  });
  renderGroupByButtonState(
    {
      allButton: evalGroupByAllButton,
      toggleButton: evalGroupByToggleButton,
      noneButton: evalGroupByNoneButton,
    },
    []
  );
  renderSortStatus({
    labelElement: evalSortedByLabel,
    resetButton: evalResetSortButton,
    sortConfig: [],
    validColumns: [],
    displayColumnName: displayEvalColumnName,
  });
  evalDefaultsList.innerHTML = "";

  const selectedEvaluations = timing.time(
    "render gather selected evaluations",
    () => gatherSelectedEvaluations()
  );
  if (!selectedEvaluations.length) {
    setPanelVisibility(evalDefaultsPanel, false);
    evalSummary.textContent = "Select one or more prediction groups to view evaluation overrides and job_return_value fields.";
    renderEvaluationPlots(state.activeEvalTab || "", null, timing);
    timing.flush({ active_experiment: state.activeEvalTab || "" });
    return;
  }

  const byExperiment = timing.time(
    "render group evaluations by experiment",
    () => getEvaluationsByExperiment(selectedEvaluations)
  );

  const experiments = Array.from(byExperiment.keys()).sort();
  state.activeEvalTab = resolveActiveTabValue(state.activeEvalTab, experiments);
  renderTabButtons({
    documentLike: document,
    containerElement: evalTabs,
    tabModels: buildCountTabButtonModels(experiments, {
      activeValue: state.activeEvalTab,
      getLabelText: (experiment) => experiment,
      getCount: (experiment) => byExperiment.get(experiment).length,
    }),
    onSelect: (experiment) => {
      if (state.activeEvalTab === experiment) {
        return;
      }
      state.activeEvalTab = experiment;
      renderEvaluations();
    },
  });

  const evaluationContext = timing.time(
    "render get evaluation context",
    () => getEvaluationContext(state.activeEvalTab, selectedEvaluations)
  );
  const {
    experimentEvaluations,
    evalColumns,
    evalTabState,
    evaluationGroups,
  } = evaluationContext;
  const evalColumnSections = buildEvaluationColumnSections(evalColumns, {
    isJobReturnValueColumn: selectors.isJobReturnValueColumn,
  });
  const orderedEvalColumns = evalColumnSections.flatMap((section) => section.columns);
  evalTabState.sort = renderSortStatus({
    labelElement: evalSortedByLabel,
    resetButton: evalResetSortButton,
    sortConfig: evalTabState.sort,
    validColumns: [...SORTABLE_CONTROL_COLUMNS, ...orderedEvalColumns, "eval_run_dir"],
    displayColumnName: displayEvalColumnName,
  });
  renderGroupByButtonState(
    {
      allButton: evalGroupByAllButton,
      toggleButton: evalGroupByToggleButton,
      noneButton: evalGroupByNoneButton,
    },
    orderedEvalColumns
  );
  renderStaticTabState({
    buttonElements: evalOptionsTabButtons,
    panelElements: evalOptionsTabPanels,
    activeValue: state.evalTabStates[state.activeEvalTab].activeOptionsTab,
    buttonAttribute: "data-eval-tab",
    panelAttribute: "data-eval-tab-panel",
  });
  const selectedEvaluationsForDefaults = timing.time(
    "render selected evaluations for defaults",
    () => getSelectedEvaluationGroups(evaluationContext).flatMap(
      (group) => group.evaluations
    )
  );
  const evalDefaultColumns = selectors.getEvalColumnsWithMissingValues(
    selectedEvaluationsForDefaults,
    evalColumns
  );
  timing.time("render evaluation options panel", () => {
    renderOptionsPanel({
      documentLike: document,
      checkboxListElement: evalTruncateColumnsList,
      checkboxColumns: [...new Set([...orderedEvalColumns, "eval_run_dir"])],
      checkedValues: evalTabState.truncateEnabledColumns,
      getCheckboxLabel: displayEvalColumnName,
      onCheckboxToggle: (column, checked) => {
        if (checked) {
          evalTabState.truncateEnabledColumns.add(column);
        } else {
          evalTabState.truncateEnabledColumns.delete(column);
        }
        renderEvaluations();
      },
      defaultsListElement: evalDefaultsList,
      defaultsPanelElement: evalDefaultsPanel,
      defaultColumns: evalDefaultColumns,
      getDefaultLabel: displayEvalColumnName,
      getDefaultValue: (column) => selectors.getEvalDefaultValue(evalTabState, column),
      getDefaultSuggestions: (column) =>
        selectors.getEvalDefaultSuggestions(selectedEvaluationsForDefaults, column),
      getDefaultMissingCount: (column) =>
        selectors.getEvalMissingValueCount(selectedEvaluationsForDefaults, column),
      inputIdPrefix: `eval-default-${state.activeEvalTab.replace(/[^a-zA-Z0-9_-]+/g, "-")}`,
      onDefaultCommit: (column, nextValue) => {
        setConfiguredDefault(evalTabState.defaultValues, column, nextValue);
        renderEvaluations();
      },
    });
  });

  const displayedEvalGroups = timing.time(
    "render sort evaluation groups",
    () => selectors.getSortedEvaluationGroups(evaluationGroups, evalTabState)
  );

  timing.time("render evaluation table", () => {
    renderEvaluationTable({
      documentLike: document,
      tableElement: evaluationsTable,
      evalColumnSections,
      orderedEvalColumns,
      displayedGroups: displayedEvalGroups,
      evalTabState,
      displayColumnName: displayEvalColumnName,
      onSortToggle: setEvalSort,
      onToggleGroupByColumn: (column, checked) => {
        const next = new Set(evalTabState.groupByFields);
        if (checked) {
          next.add(column);
        } else {
          next.delete(column);
        }
        setActiveEvalGroupByFields(next);
      },
      onSelectAllDisplayed: (checked, displayedGroupIds) => {
        evalTabState.selectedGroupIds = checked ? new Set(displayedGroupIds) : new Set();
        renderEvaluations();
      },
      onGroupRowSelect: (groupId) => {
        if (evalTabState.selectedEvalGroupId === groupId) {
          evalTabState.selectedEvalGroupId = null;
        } else {
          evalTabState.selectedEvalGroupId = groupId;
          evalTabState.selectedEvalRunId = null;
          state.activeEvalJsonTab = "evaluation";
        }
        renderEvaluations();
      },
      onToggleGroupExpansion: (groupId) => {
        if (evalTabState.expandedGroupIds.has(groupId)) {
          evalTabState.expandedGroupIds.delete(groupId);
        } else {
          evalTabState.expandedGroupIds.add(groupId);
        }
        renderEvaluations();
      },
      onToggleGroupSelection: (groupId, checked) => {
        if (checked) {
          evalTabState.selectedGroupIds.add(groupId);
        } else {
          evalTabState.selectedGroupIds.delete(groupId);
        }
        renderEvaluations();
      },
      onMemberRowSelect: (runId) => {
        if (evalTabState.selectedEvalRunId === runId) {
          evalTabState.selectedEvalRunId = null;
        } else {
          evalTabState.selectedEvalRunId = runId;
          evalTabState.selectedEvalGroupId = null;
          state.activeEvalJsonTab = "evaluation";
        }
        renderEvaluations();
      },
      getGroupValueDisplayFromEvaluations: selectors.getGroupValueDisplayFromEvaluations,
      getEvaluationEffectiveValue: selectors.getEvaluationEffectiveValue,
      getSortedEvaluations: selectors.getSortedEvaluations,
      sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
    });
  });

  const selectedEvaluation = experimentEvaluations.find(
    (evaluation) => getEvaluationRunId(evaluation) === evalTabState.selectedEvalRunId
  ) || null;
  const selectedGroup = displayedEvalGroups.find(
    (group) => group.groupId === evalTabState.selectedEvalGroupId
  ) || null;
  timing.time("render evaluation json pane", () => {
    renderEvalJsonPane({
      layoutElement: evalLayout,
      titleElement: evalJsonTitle,
      codeElement: evalJsonCode,
      evaluationButton: evalJsonTabEvaluation,
      predictionButton: evalJsonTabPrediction,
      activeTab: state.activeEvalJsonTab,
      selectedEvaluation,
      selectedGroup,
      getPredictionContent: reconstructPredictionContentForEvaluation,
    });
  });

  updateStickyControlColumnOffsets(evaluationsTable);
  requestAnimationFrame(() => updateStickyControlColumnOffsets(evaluationsTable));

  const selectedEvaluationsCount = displayedEvalGroups
    .filter((group) => evalTabState.selectedGroupIds.has(group.groupId))
    .reduce((sum, group) => sum + group.evaluations.length, 0);
  const evalGroupByText = evalTabState.groupByFields.length
    ? evalTabState.groupByFields.map((field) => displayEvalColumnName(field)).join(", ")
    : "(none; one row per evaluation)";
  const predictionGroupByText = state.groupByFields.length
    ? state.groupByFields.map((field) => displayPredictionColumnName(field)).join(", ")
    : "(none)";
  evalSummary.textContent =
    `Selected evaluations: ${selectedEvaluationsCount} | Active tab: ${state.activeEvalTab} | Groups: ${displayedEvalGroups.length} | Group-by: ${evalGroupByText} (+ prediction group-by: ${predictionGroupByText})`;

  renderEvaluationPlots(state.activeEvalTab, evaluationContext, timing);
  timing.flush({ active_experiment: state.activeEvalTab || "" });
}
