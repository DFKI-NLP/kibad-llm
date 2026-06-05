/**
 * Canonical mutable state helpers for the eval dashboard runtime.
 */

import { normalizeSortConfig } from "../utils/sort.js";

/**
 * Synthetic control columns that stay sortable across prediction and evaluation tables.
 */
export const SORTABLE_CONTROL_COLUMNS = new Set(["expand", "select", "group_size"]);

/**
 * Create the canonical dashboard state object with fresh mutable containers.
 *
 * @returns {object} A new dashboard state object.
 */
export function createInitialDashboardState() {
  return {
    predictions: {},
    evaluations: [],
    predictionSort: [],
    loadedFolders: new Set(),
    selectedGroupIds: new Set(),
    availableGroupIds: new Set(),
    expandedGroupIds: new Set(),
    activeEvalTab: null,
    groupByFields: [],
    truncateEnabledColumns: new Set(),
    predictionDefaultValues: {},
    activeOptionsTab: "truncate",
    evalTabStates: {},
    activeEvalJsonTab: "evaluation",
    plotTabsBy: "prefix",
    activeEvalPlotTab: null,
    plotGroupBarFields: new Set(),
    plotShortenLabels: true,
    plotRoundingPrecision: 0,
    plotConfusionMinLabelTotal: 3,
    plotTpFpFnMinLabelTotal: 10,
    plotTpFpFnMinDocumentTotal: 3,
    plotShowLegendOnce: true,
    exportOpaqueBackground: true,
    confusionTabsBy: "prediction_group",
    activePlotLegendItems: [],
    activePlotDownloadData: null,
  };
}

/**
 * Synchronize selected group ids with the current valid group-id set while preserving
 * still-valid selections and auto-selecting newly introduced groups.
 *
 * @param {object} selectionState - State object carrying selection metadata.
 * @param {Iterable<string>} validGroupIds - Group ids that are currently valid.
 */
export function syncSelectedGroupIds(selectionState, validGroupIds) {
  const validIds = new Set(validGroupIds || []);
  if (!(selectionState.availableGroupIds instanceof Set)) {
    selectionState.availableGroupIds = new Set();
  }
  if (selectionState.selectedGroupIds === null) {
    selectionState.selectedGroupIds = new Set(validIds);
  } else {
    const nextSelectedGroupIds = new Set(
      Array.from(selectionState.selectedGroupIds).filter((groupId) => validIds.has(groupId))
    );
    for (const groupId of validIds) {
      if (!selectionState.availableGroupIds.has(groupId)) {
        nextSelectedGroupIds.add(groupId);
      }
    }
    selectionState.selectedGroupIds = nextSelectedGroupIds;
  }
  selectionState.availableGroupIds = new Set(validIds);
}

/**
 * Synchronize prediction-group UI state with the currently derived prediction groups.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Array<{groupId: string}>} predictionGroups - Currently derived prediction groups.
 */
export function syncPredictionGroupUiState(state, predictionGroups) {
  const validIds = new Set((predictionGroups || []).map((group) => group.groupId));
  syncSelectedGroupIds(state, validIds);
  state.expandedGroupIds = new Set(
    Array.from(state.expandedGroupIds).filter((groupId) => validIds.has(groupId))
  );
}

/**
 * Ensure that one evaluation-tab state exists and stays normalized for the provided experiment.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {string} experiment - Evaluation experiment identifier.
 * @param {string[]} evalColumns - Currently known evaluation columns.
 * @param {object} options - Normalization callbacks and evaluation inputs.
 * @param {Array<object>} [options.evaluations=[]] - Evaluations belonging to the experiment.
 * @param {(columns: string[], evaluations: Array<object>) => string[]} [options.getDefaultEvalGroupByFields] - Default group-by callback.
 * @param {() => Set<string>} [options.getDefaultEvalTruncateColumns] - Default truncate callback.
 * @returns {object} The normalized tab state for the experiment.
 */
export function ensureEvalTabState(
  state,
  experiment,
  evalColumns,
  {
    evaluations = [],
    getDefaultEvalGroupByFields = () => [],
    getDefaultEvalTruncateColumns = () => new Set(),
  } = {}
) {
  if (!state.evalTabStates[experiment]) {
    state.evalTabStates[experiment] = {
      knownColumns: [...evalColumns],
      groupByFields: getDefaultEvalGroupByFields(evalColumns, evaluations),
      sort: [],
      truncateEnabledColumns: new Set(getDefaultEvalTruncateColumns()),
      defaultValues: {},
      activeOptionsTab: "truncate",
      selectedGroupIds: null,
      availableGroupIds: new Set(),
      expandedGroupIds: new Set(),
      selectedEvalGroupId: null,
      selectedEvalRunDir: null,
    };
    return state.evalTabStates[experiment];
  }

  const tabState = state.evalTabStates[experiment];
  const known = new Set(tabState.knownColumns || []);
  tabState.groupByFields = Array.isArray(tabState.groupByFields) ? tabState.groupByFields : [];
  tabState.sort = Array.isArray(tabState.sort) ? tabState.sort : [];
  if (!(tabState.truncateEnabledColumns instanceof Set)) {
    tabState.truncateEnabledColumns = new Set(getDefaultEvalTruncateColumns());
  }
  if (!tabState.defaultValues || typeof tabState.defaultValues !== "object") {
    tabState.defaultValues = {};
  }
  if (!(tabState.availableGroupIds instanceof Set)) {
    tabState.availableGroupIds = new Set();
  }
  if (!(tabState.expandedGroupIds instanceof Set)) {
    tabState.expandedGroupIds = new Set();
  }

  for (const column of evalColumns) {
    if (!known.has(column)) {
      known.add(column);
      if (getDefaultEvalGroupByFields([column], evaluations).length) {
        tabState.groupByFields = [...new Set([...tabState.groupByFields, column])];
      }
    }
  }

  tabState.knownColumns = [...known];
  tabState.groupByFields = tabState.groupByFields.filter((field) => known.has(field));
  tabState.truncateEnabledColumns = new Set(
    Array.from(tabState.truncateEnabledColumns).filter(
      (field) => known.has(field) || field === "eval_run_dir"
    )
  );
  tabState.sort = normalizeSortConfig(
    tabState.sort,
    new Set([...SORTABLE_CONTROL_COLUMNS, ...known, "eval_run_dir"])
  );
  if (!tabState.activeOptionsTab) {
    tabState.activeOptionsTab = "truncate";
  }
  return tabState;
}

/**
 * Synchronize evaluation-group UI state with the currently derived evaluation groups.
 *
 * @param {object} evalTabState - Per-experiment evaluation tab state.
 * @param {Array<{groupId: string}>} evaluationGroups - Current evaluation groups.
 * @param {Array<{runDir: string}>} experimentEvaluations - Current experiment evaluations.
 */
export function syncEvaluationGroupUiState(evalTabState, evaluationGroups, experimentEvaluations) {
  const validEvalGroupIds = new Set((evaluationGroups || []).map((group) => group.groupId));
  syncSelectedGroupIds(evalTabState, validEvalGroupIds);
  evalTabState.expandedGroupIds = new Set(
    Array.from(evalTabState.expandedGroupIds).filter((groupId) => validEvalGroupIds.has(groupId))
  );
  if (!validEvalGroupIds.has(evalTabState.selectedEvalGroupId)) {
    evalTabState.selectedEvalGroupId = null;
  }
  const validRunDirs = new Set(
    (experimentEvaluations || []).map((evaluation) => evaluation.runDir)
  );
  if (!validRunDirs.has(evalTabState.selectedEvalRunDir)) {
    evalTabState.selectedEvalRunDir = null;
  }
}

/**
 * Reset load-dependent UI state after new canonical prediction/evaluation data is imported.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {object} options - Precomputed selector outputs and default helpers.
 * @param {Array<object>} options.predictionViews - Current prediction views.
 * @param {string[]} options.predictionColumns - Current prediction columns.
 * @param {Array<object>} options.predictionGroups - Current prediction groups.
 * @param {(columns: string[], predictionViews: Array<object>) => string[]} options.getDefaultGroupByFields - Default group-by helper.
 * @param {(columns: string[]) => Set<string>} options.getDefaultTruncateColumns - Default truncate helper.
 */
export function resetDerivedUiStateAfterLoad(
  state,
  {
    predictionViews,
    predictionColumns,
    predictionGroups,
    getDefaultGroupByFields,
    getDefaultTruncateColumns,
  }
) {
  state.groupByFields = getDefaultGroupByFields(predictionColumns, predictionViews);
  state.predictionSort = [];
  state.truncateEnabledColumns = getDefaultTruncateColumns(predictionColumns);
  state.predictionDefaultValues = {};
  state.selectedGroupIds = new Set();
  state.availableGroupIds = new Set();
  state.expandedGroupIds = new Set();
  state.activeEvalTab = null;
  state.evalTabStates = {};
  state.activeEvalJsonTab = "evaluation";
  state.activeEvalPlotTab = null;
  state.plotGroupBarFields = new Set();
  state.activePlotLegendItems = [];
  state.activePlotDownloadData = null;
  syncPredictionGroupUiState(state, predictionGroups);
}
