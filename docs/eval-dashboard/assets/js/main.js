import { normalizeSortConfig } from "./utils/sort.js";
import { normalizeValue } from "./utils/values.js";
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
import {
  getPlotDisplayLabel as getSharedPlotDisplayLabel,
  getPlotTitleLabel as getSharedPlotTitleLabel,
} from "./plots/shared.js";
import {
  createPlotTooltipHandlers,
  downloadVisiblePlotFigures,
  renderDashboardPlotControls,
  renderEvaluationPlotsForDashboard,
  updateDownloadFiguresButtonState as updatePlotDownloadFiguresButtonState,
} from "./plots/dashboard.js";

// Central UI state: loaded prediction/evaluation data, current grouping/selection, and per-eval-tab view state.
const state = dashboardStore.createInitialDashboardState();

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
  plotConfusionMinLabelTotalRow,
  plotConfusionMinLabelTotal,
  plotTpFpFnMinLabelTotalRow,
  plotTpFpFnMinLabelTotal,
  plotTpFpFnMinDocumentTotalRow,
  plotTpFpFnMinDocumentTotal,
  plotTabsByRow,
  plotConfusionTabsByRow,
  confusionTabsByMetricFieldButton,
  confusionTabsByPredictionGroupButton,
  plotGroupBarsRow,
  plotGroupBarsList,
  plotShowLegendOnceRow,
  plotShowLegendOnce,
  downloadFiguresButton,
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

function getNextSortConfig(currentSort, column, { append = false } = {}) {
  return getSharedNextSortConfig(currentSort, column, {
    append,
    sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
  });
}

// Selectors and accessors for the canonical predictions/evaluations state shape.
function isJobReturnValueColumn(column) {
  return selectors.isJobReturnValueColumn(column);
}

function stripEvaluationFieldPrefix(column) {
  return selectors.stripEvaluationFieldPrefix(column);
}

function stripPredictionFieldPrefix(column) {
  return selectors.stripPredictionFieldPrefix(column);
}

function reconstructPredictionContent(prediction) {
  return selectors.reconstructPredictionContent(prediction);
}

function getPredictionById(predictionId) {
  return selectors.getPredictionById(state, predictionId);
}

function getPredictionForEvaluation(evaluation) {
  return selectors.getPredictionForEvaluation(state, evaluation);
}

function reconstructPredictionContentForEvaluation(evaluation) {
  return selectors.reconstructPredictionContentForEvaluation(state, evaluation);
}

function getFlattenedPrediction(prediction) {
  return selectors.getFlattenedPrediction(prediction);
}

function getFlattenedPredictionForEvaluation(evaluation) {
  return selectors.getFlattenedPredictionForEvaluation(state, evaluation);
}

/**
 * Derive one prediction view per canonical prediction id.
 * Each view joins the flattened prediction fields with all linked evaluations.
 */
function getPredictionViews() {
  return selectors.getPredictionViews(state);
}

/**
 * Collect all flattened prediction columns currently present across the given prediction views.
 */
function getPredictionColumns(predictionViews = getPredictionViews()) {
  return selectors.getPredictionColumns(predictionViews);
}

/**
 * Return the current prediction columns derived from canonical prediction state.
 */
function getCurrentPredictionColumns(predictionViews = getPredictionViews()) {
  return selectors.getCurrentPredictionColumns(state, predictionViews);
}

/**
 * Group prediction views according to the active prediction group-by fields.
 * The returned group shape matches the current prediction table/rendering expectations.
 */
function getPredictionGroups(
  predictionViews = getPredictionViews(),
  groupByFields = state.groupByFields,
  predictionColumns = getCurrentPredictionColumns(predictionViews)
) {
  return selectors.getPredictionGroups(state, predictionViews, groupByFields, predictionColumns);
}

/**
 * Filter prediction groups down to the currently selected prediction group ids.
 */
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
 * Return the current prediction groups derived from canonical state and current prediction UI settings.
 */
function getCurrentPredictionGroups() {
  const predictionViews = getPredictionViews();
  const predictionColumns = getCurrentPredictionColumns(predictionViews);
  const predictionGroups = getPredictionGroups(predictionViews, state.groupByFields, predictionColumns);
  syncPredictionGroupUiState(predictionGroups);
  return predictionGroups;
}

/**
 * Flatten the evaluations reachable from the selected prediction groups.
 */
function getSelectedEvaluations(selectedPredictionGroups = getSelectedPredictionGroups()) {
  return selectors.getSelectedEvaluations(selectedPredictionGroups);
}

function getFlattenedEvaluationJobReturnValue(evaluation) {
  return selectors.getFlattenedEvaluationJobReturnValue(evaluation);
}

function getEvaluationColumnRawValue(evaluation, column) {
  return selectors.getEvaluationColumnRawValue(evaluation, column);
}

function getEvaluationEffectiveValue(evaluation, column, evalTabState) {
  return selectors.getEvaluationEffectiveValue(evaluation, column, evalTabState);
}

function getEvaluationExperiment(evaluation) {
  return selectors.getEvaluationExperiment(evaluation);
}

/**
 * Flatten the currently selected prediction groups into their member prediction views.
 */
function getSelectedPredictionViews() {
  return selectors.getSelectedPredictionViews(state);
}

function gatherSelectedEvaluations() {
  return selectors.gatherSelectedEvaluations(state);
}

/**
 * Group the currently selected evaluations by evaluation experiment.
 */
function getEvaluationsByExperiment(selectedEvaluations = gatherSelectedEvaluations()) {
  return selectors.getEvaluationsByExperiment(state, selectedEvaluations);
}

/**
 * Return the selected evaluations that belong to one evaluation experiment.
 */
function getSelectedEvaluationsForExperiment(experiment, selectedEvaluations = gatherSelectedEvaluations()) {
  return selectors.getSelectedEvaluationsForExperiment(state, experiment, selectedEvaluations);
}

/**
 * Collect all evaluation columns currently present across the given evaluations.
 */
function getEvaluationColumns(evaluations = []) {
  return selectors.getEvaluationColumns(evaluations);
}

const plotTooltipHandlers = createPlotTooltipHandlers({ tooltipElement: barTooltip, windowLike: window });

function updateDownloadFiguresButtonState() {
  updatePlotDownloadFiguresButtonState({ downloadFiguresButton, evalPlotContent });
}

const evalPlotContentObserver = new MutationObserver(() => {
  updateDownloadFiguresButtonState();
});
evalPlotContentObserver.observe(evalPlotContent, { childList: true, subtree: true });
updateDownloadFiguresButtonState();

bindEvalJsonTabSelection({
  evaluationButton: evalJsonTabEvaluation,
  predictionButton: evalJsonTabPrediction,
  getActiveTab: () => state.activeEvalJsonTab,
  onSelect: (nextTab) => {
    state.activeEvalJsonTab = nextTab;
    renderEvaluations();
  },
});

initializeGitHubTokenInput(githubTokenInput);

folderInput.addEventListener("change", async (event) => {
  const files = Array.from(event.target.files || []);
  clearGitUrlQueryParam();
  await loadEvaluationsFromFiles(files);
  renderPredictions();
  renderEvaluations();
});

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

function displayPredictionColumnName(column) {
  return stripPredictionFieldPrefix(column);
}

function displayEvalColumnName(column) {
  const normalizedColumn = stripEvaluationFieldPrefix(column);
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
  return displayPredictionColumnName(column);
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

function displayPlotGroupFieldName(column) {
  return getPlotDisplayLabel(displayGroupFieldName(column));
}

function getDefaultTruncateColumns(predictionColumns) {
  return selectors.getDefaultTruncateColumns(predictionColumns);
}

/**
 * Choose default prediction group-by fields from varying non-seed override columns.
 */
function getDefaultGroupByFields(predictionColumns, predictionViews = getPredictionViews()) {
  return selectors.getDefaultGroupByFields(predictionColumns, predictionViews);
}

function getDefaultEvalGroupByFields(evalColumns, evaluations = []) {
  return selectors.getDefaultEvalGroupByFields(evalColumns, evaluations);
}

function getDefaultEvalTruncateColumns() {
  return new Set();
}

function setConfiguredDefault(defaults, column, value) {
  const nextValue = String(value ?? "");
  if (nextValue.trim() === "") {
    delete defaults[column];
  } else {
    defaults[column] = nextValue;
  }
}

function getPredictionDefaultValue(column) {
  return selectors.getPredictionDefaultValue(state, column);
}

function getPredictionEffectiveValue(predictionFlat, column) {
  return selectors.getPredictionEffectiveValue(state, predictionFlat, column);
}

/**
 * Build a stable signature from the effective prediction values for the provided columns.
 */
function getPredictionEffectiveSignature(
  predictionFlat,
  predictionColumns = getCurrentPredictionColumns()
) {
  return selectors.getPredictionEffectiveSignature(state, predictionFlat, predictionColumns);
}

function getEvalDefaultValue(evalTabState, column) {
  return selectors.getEvalDefaultValue(evalTabState, column);
}

/**
 * Return prediction columns whose selected prediction views still contain missing values.
 */
function getPredictionColumnsWithMissingValues(
  predictionViews,
  predictionColumns = getCurrentPredictionColumns(predictionViews)
) {
  return selectors.getPredictionColumnsWithMissingValues(state, predictionViews, predictionColumns);
}

/**
 * Collect non-empty suggestion values for a prediction column from the current prediction views.
 */
function getPredictionDefaultSuggestions(predictionViews, column) {
  return selectors.getPredictionDefaultSuggestions(predictionViews, column);
}

/**
 * Count how many prediction views are missing a value for the given prediction column.
 */
function getPredictionMissingValueCount(predictionViews, column) {
  return selectors.getPredictionMissingValueCount(predictionViews, column);
}

function getEvalColumnsWithMissingValues(evaluations, evalColumns) {
  return selectors.getEvalColumnsWithMissingValues(evaluations, evalColumns);
}

function getEvalDefaultSuggestions(evaluations, column) {
  return selectors.getEvalDefaultSuggestions(evaluations, column);
}

function getEvalMissingValueCount(evaluations, column) {
  return selectors.getEvalMissingValueCount(evaluations, column);
}


function setGroupByFields(columns) {
  state.groupByFields = [...columns];
  renderPredictions();
  renderEvaluations();
}


/**
 * Return the evaluation columns for the currently active evaluation experiment.
 */
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
    getDefaultEvalTruncateColumns,
  });
}

/**
 * Synchronize selected group ids with the current valid group-id set while preserving
 * still-valid selections and auto-selecting newly introduced groups.
 */
function syncSelectedGroupIds(selectionState, validGroupIds) {
  dashboardStore.syncSelectedGroupIds(selectionState, validGroupIds);
}

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

predictionResetSortButton.addEventListener("click", () => {
  if (!normalizeSortConfig(state.predictionSort).length) {
    return;
  }
  state.predictionSort = [];
  renderPredictions();
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

truncateDefaultsButton.addEventListener("click", () => {
  state.truncateEnabledColumns = getDefaultTruncateColumns(getCurrentPredictionColumns());
  renderPredictions();
})

plotShortenLabels.addEventListener("change", () => {
  state.plotShortenLabels = plotShortenLabels.checked;
  renderEvaluations();
});

plotRoundingPrecision.addEventListener("change", () => {
  const parsed = Number.parseInt(plotRoundingPrecision.value, 10);
  const clamped = Number.isFinite(parsed) ? Math.max(0, Math.min(6, parsed)) : 2;
  state.plotRoundingPrecision = clamped;
  plotRoundingPrecision.value = String(clamped);
  renderEvaluations();
});

plotConfusionMinLabelTotal.addEventListener("change", () => {
  const parsed = Number.parseInt(plotConfusionMinLabelTotal.value, 10);
  const clamped = Number.isFinite(parsed) ? Math.max(0, parsed) : 3;
  state.plotConfusionMinLabelTotal = clamped;
  plotConfusionMinLabelTotal.value = String(clamped);
  renderEvaluations();
});

plotTpFpFnMinLabelTotal.addEventListener("change", () => {
  const parsed = Number.parseInt(plotTpFpFnMinLabelTotal.value, 10);
  const clamped = Number.isFinite(parsed) ? Math.max(0, parsed) : 3;
  state.plotTpFpFnMinLabelTotal = clamped;
  plotTpFpFnMinLabelTotal.value = String(clamped);
  renderEvaluations();
});

plotTpFpFnMinDocumentTotal.addEventListener("change", () => {
  const parsed = Number.parseInt(plotTpFpFnMinDocumentTotal.value, 10);
  const clamped = Number.isFinite(parsed) ? Math.max(0, parsed) : 0;
  state.plotTpFpFnMinDocumentTotal = clamped;
  plotTpFpFnMinDocumentTotal.value = String(clamped);
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

plotTabsByPrefixButton.addEventListener("click", () => {
  if (state.plotTabsBy === "prefix") {
    return;
  }
  state.plotTabsBy = "prefix";
  state.activeEvalPlotTab = null;
  renderEvaluations();
});

plotTabsBySuffixButton.addEventListener("click", () => {
  if (state.plotTabsBy === "suffix") {
    return;
  }
  state.plotTabsBy = "suffix";
  state.activeEvalPlotTab = null;
  renderEvaluations();
});

confusionTabsByMetricFieldButton.addEventListener("click", () => {
  if (state.confusionTabsBy === "metric_field") {
    return;
  }
  state.confusionTabsBy = "metric_field";
  state.activeEvalPlotTab = null;
  renderEvaluations();
});

confusionTabsByPredictionGroupButton.addEventListener("click", () => {
  if (state.confusionTabsBy === "prediction_group") {
    return;
  }
  state.confusionTabsBy = "prediction_group";
  state.activeEvalPlotTab = null;
  renderEvaluations();
});

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

/**
 * Reset load-dependent UI state after new canonical prediction/evaluation data is imported.
 * All prediction/evaluation structures remain selector-derived and are not stored here.
 */
function resetDerivedUiStateAfterLoad() {
  const predictionViews = getPredictionViews();
  const predictionColumns = getCurrentPredictionColumns(predictionViews);
  const nextGroupByFields = getDefaultGroupByFields(predictionColumns, predictionViews);
  dashboardStore.resetDerivedUiStateAfterLoad(state, {
    predictionViews,
    predictionColumns,
    predictionGroups: getPredictionGroups(predictionViews, nextGroupByFields, predictionColumns),
    getDefaultGroupByFields,
    getDefaultTruncateColumns,
  });
}

function updateLoadStatusSummary({ candidateRunDirs, loadedCount, skippedDuplicate, skippedPredictRuns, skippedMissingJob, skippedUnsupportedVersion, skippedInvalid, skippedMissingPredictionId, skippedConflictingPredictionId }) {
  renderLoadStatusSummary(dom, {
    loadedSources: Array.from(state.loadedFolders).sort(),
    totalEvaluations: state.evaluations.length,
    candidateRunDirs,
    loadedCount,
    skippedDuplicate,
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
 *
 * @param {string} sourceLabel - Loaded source label.
 * @param {{predictionAdditions: Record<string, object>, evaluationAdditions: Array<object>, failures: Array<{runDir: string, error: Error}>, summary: object}} ingestionResult - Shared ingestion result.
 */
function applyIngestionResult(sourceLabel, ingestionResult) {
  state.loadedFolders.add(sourceLabel);
  for (const { runDir, error } of ingestionResult.failures) {
    console.error(`Failed to parse run at ${runDir}`, error);
  }
  for (const [predictionId, prediction] of Object.entries(ingestionResult.predictionAdditions)) {
    state.predictions[predictionId] = prediction;
  }
  state.evaluations.push(...ingestionResult.evaluationAdditions);
  resetDerivedUiStateAfterLoad();
  updateLoadStatusSummary(ingestionResult.summary);
}

// Load only single evaluation runs: any selected folder tree can contribute evaluations as long as a run
// directory contains both job_return_value.json and .hydra/overrides.yaml. predict runs are excluded,
// while prediction payloads are canonicalized separately and linked via predictionId.
async function loadEvaluationsFromEntries(entries, rootLabel) {
  if (!entries.length) {
    renderLoadStatusStage(dom, `No relevant run files found in ${rootLabel}.`);
    return;
  }

  applyIngestionResult(rootLabel, ingestRunEntries(entries, {
    existingPredictions: state.predictions,
    existingEvaluations: state.evaluations,
  }));
}

async function loadEvaluationsFromFiles(files) {
  hideLoadProgress();
  if (!files.length) {
    renderLoadStatusStage(dom, "No files selected.");
    return;
  }

  const { rootLabel, entries } = await collectLocalEvaluationEntries(files);
  await loadEvaluationsFromEntries(entries, rootLabel);
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

async function loadEvaluationsFromGitUrl(rawUrl) {
  const trimmedUrl = String(rawUrl || "").trim();
  if (!trimmedUrl) {
    hideLoadProgress();
    renderLoadStatusStage(dom, "Enter a GitHub tree URL first.");
    return;
  }

  const token = persistGitHubTokenInputValue(githubTokenInput);
  hideLoadProgress();
  const gitLoadResult = await loadGitHubEntriesFromTreeUrl(trimmedUrl, {
    token,
    onStatus: ({ title, details }) => updateLoadStatusStage(title, details),
    onProgress: (progress) => setLoadProgress(progress),
  });
  if (!gitLoadResult.files.length) {
    hideLoadProgress();
    renderLoadStatusStage(dom, `No matching run files found in ${gitLoadResult.sourceLabel}.`);
    return;
  }

  updateLoadStatusStage("Loading evaluation runs from GitHub files", [
    gitLoadResult.sourceLabel,
    `Fetched files: ${gitLoadResult.entries.length}`,
  ]);
  await loadEvaluationsFromEntries(gitLoadResult.entries, gitLoadResult.sourceLabel);
  setLoadProgress({
    completedFiles: gitLoadResult.files.length,
    totalFiles: gitLoadResult.files.length,
    completedBytes: gitLoadResult.totalBytes,
    totalBytes: gitLoadResult.totalBytes,
    label: "GitHub fetch complete",
  });
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

void initializeGitUrlFromQueryParam();

function getPredictionGroupSortValue(group, column) {
  return selectors.getPredictionGroupSortValue(state, group, column);
}

function getPredictionMemberSortValue(predictionView, column) {
  return selectors.getPredictionMemberSortValue(state, predictionView, column);
}

/**
 * Return prediction groups sorted according to the active prediction sort config.
 */
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


window.addEventListener("resize", () => {
  updateStickyControlColumnOffsets(predictionsTable);
  updateStickyControlColumnOffsets(evaluationsTable);
});

function getGroupValueDisplay(group, column) {
  return selectors.getGroupValueDisplay(state, group, column);
}

/**
 * Render the Predictions table from derived prediction views and prediction groups.
 */
function renderPredictions() {
  const predictionViews = getPredictionViews();
  const predictionGroups = getCurrentPredictionGroups();

  predictionsTable.innerHTML = "";
  predictionDefaultsList.innerHTML = "";
  state.predictionSort = renderSortStatus({
    labelElement: predictionSortedByLabel,
    resetButton: predictionResetSortButton,
    sortConfig: state.predictionSort,
    validColumns: [...SORTABLE_CONTROL_COLUMNS, ...getCurrentPredictionColumns()],
    displayColumnName: displayPredictionColumnName,
  });
  if (!predictionGroups.length) {
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
    return;
  }

  predictionSummary.textContent =
    `Predictions: ${predictionViews.length} | Groups: ${predictionGroups.length} | Group-by: ` +
    (state.groupByFields.length
      ? state.groupByFields.map((field) => displayPredictionColumnName(field)).join(", ")
      : "(none; one row per unique prediction)");

  const predictionSections = buildPredictionColumnSections({
    predictionColumns: getCurrentPredictionColumns(predictionViews),
    predictionJobReturnValuePrefix: PREDICTION_JOB_RETURN_VALUE_PREFIX,
    predictionOverridesPrefix: PREDICTION_OVERRIDES_PREFIX,
  });
  const orderedPredictionColumns = predictionSections.flatMap((section) => section.columns);
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
  const selectedPredictionViews = getSelectedPredictionViews();
  const predictionDefaultColumns = getPredictionColumnsWithMissingValues(
    selectedPredictionViews,
    orderedPredictionColumns
  );
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
    getDefaultValue: getPredictionDefaultValue,
    getDefaultSuggestions: (column) => getPredictionDefaultSuggestions(selectedPredictionViews, column),
    getDefaultMissingCount: (column) =>
      getPredictionMissingValueCount(selectedPredictionViews, column),
    inputIdPrefix: "prediction-default",
    onDefaultCommit: (column, nextValue) => {
      setConfiguredDefault(state.predictionDefaultValues, column, nextValue);
      renderPredictions();
      renderEvaluations();
    },
  });
  const displayedGroups = getSortedPredictionGroups(predictionGroups);

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
    getGroupValueDisplay,
    getSortedPredictionMembers,
    getPredictionEffectiveValue,
    sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
  });
  updateStickyControlColumnOffsets(predictionsTable);
}

/**
 * Group evaluations by the active prediction and evaluation grouping fields.
 * The returned group shape matches the current evaluation table/rendering expectations.
 */
function getEvaluationGroups(
  evaluations,
  groupByFields,
  predictionGroupByFields = state.groupByFields,
  evalTabState = state.activeEvalTab ? state.evalTabStates[state.activeEvalTab] : null
) {
  return selectors.getEvaluationGroups(state, evaluations, groupByFields, predictionGroupByFields, evalTabState);
}

function getEvaluationGroupSortValue(group, column, evalTabState) {
  return selectors.getEvaluationGroupSortValue(group, column, evalTabState);
}

function getEvaluationRunSortValue(evaluation, column, evalTabState) {
  return selectors.getEvaluationRunSortValue(evaluation, column, evalTabState);
}

function getSortedEvaluationGroups(groups, evalTabState) {
  return selectors.getSortedEvaluationGroups(groups, evalTabState);
}

function getSortedEvaluations(evaluations, evalTabState) {
  return selectors.getSortedEvaluations(evaluations, evalTabState);
}

/**
 * Synchronize evaluation-group UI state with the currently derived evaluation groups
 * and experiment evaluations.
 */
function syncEvaluationGroupUiState(evalTabState, evaluationGroups, experimentEvaluations) {
  dashboardStore.syncEvaluationGroupUiState(evalTabState, evaluationGroups, experimentEvaluations);
}

/**
 * Return the current evaluation context derived from canonical state and current evaluation UI settings.
 */
function getEvaluationContext(
  activeExperiment = state.activeEvalTab,
  selectedEvaluations = gatherSelectedEvaluations()
) {
  return selectors.getEvaluationContext(state, activeExperiment, selectedEvaluations);
}

/**
 * Filter evaluation groups down to the currently selected evaluation group ids.
 */
function getSelectedEvaluationGroups(evaluationContext = getEvaluationContext()) {
  return selectors.getSelectedEvaluationGroups(state, evaluationContext);
}

function getGroupValueDisplayFromEvaluations(evaluations, getter) {
  return selectors.getGroupValueDisplayFromEvaluations(evaluations, getter);
}

/**
 * Combine prediction grouping and evaluation grouping into the plot-group shape
 * consumed by plot and confusion-matrix rendering.
 */
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
  evaluationContext = getEvaluationContext(activeExperiment)
) {
  renderEvaluationPlotsForDashboard({
    state,
    dom,
    activeExperiment,
    evaluationContext,
    documentLike: document,
    requestAnimationFrameLike: requestAnimationFrame,
    navigatorLike: navigator,
    consoleLike: console,
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
    rerenderEvaluationPlots: renderEvaluationPlots,
  });
}

/**
 * Render the evaluation table, JSON pane, and plots from selector-derived evaluation state.
 */
function renderEvaluations() {
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

  const selectedEvaluations = gatherSelectedEvaluations();
  if (!selectedEvaluations.length) {
    setPanelVisibility(evalDefaultsPanel, false);
    evalSummary.textContent = "Select one or more prediction groups to view evaluation overrides and job_return_value fields.";
    renderEvaluationPlots(state.activeEvalTab || "");
    return;
  }

  const byExperiment = getEvaluationsByExperiment(selectedEvaluations);

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

  const evaluationContext = getEvaluationContext(state.activeEvalTab, selectedEvaluations);
  const {
    experimentEvaluations,
    evalColumns,
    evalTabState,
    evaluationGroups,
  } = evaluationContext;
  const evalColumnSections = buildEvaluationColumnSections(evalColumns, {
    isJobReturnValueColumn,
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
  const selectedEvaluationsForDefaults = getSelectedEvaluationGroups(evaluationContext).flatMap(
    (group) => group.evaluations
  );
  const evalDefaultColumns = getEvalColumnsWithMissingValues(
    selectedEvaluationsForDefaults,
    evalColumns
  );
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
    getDefaultValue: (column) => getEvalDefaultValue(evalTabState, column),
    getDefaultSuggestions: (column) =>
      getEvalDefaultSuggestions(selectedEvaluationsForDefaults, column),
    getDefaultMissingCount: (column) =>
      getEvalMissingValueCount(selectedEvaluationsForDefaults, column),
    inputIdPrefix: `eval-default-${state.activeEvalTab.replace(/[^a-zA-Z0-9_-]+/g, "-")}`,
    onDefaultCommit: (column, nextValue) => {
      setConfiguredDefault(evalTabState.defaultValues, column, nextValue);
      renderEvaluations();
    },
  });

  const displayedEvalGroups = getSortedEvaluationGroups(evaluationGroups, evalTabState);

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
        evalTabState.selectedEvalRunDir = null;
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
    onMemberRowSelect: (runDir) => {
      if (evalTabState.selectedEvalRunDir === runDir) {
        evalTabState.selectedEvalRunDir = null;
      } else {
        evalTabState.selectedEvalRunDir = runDir;
        evalTabState.selectedEvalGroupId = null;
        state.activeEvalJsonTab = "evaluation";
      }
      renderEvaluations();
    },
    getGroupValueDisplayFromEvaluations,
    getEvaluationEffectiveValue,
    getSortedEvaluations,
    sortableControlColumns: SORTABLE_CONTROL_COLUMNS,
  });

  const selectedEvaluation = experimentEvaluations.find(
    (evaluation) => evaluation.runDir === evalTabState.selectedEvalRunDir
  ) || null;
  const selectedGroup = displayedEvalGroups.find(
    (group) => group.groupId === evalTabState.selectedEvalGroupId
  ) || null;
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

  renderEvaluationPlots(state.activeEvalTab, evaluationContext);
}
