/**
 * Derived state and selector helpers for the eval dashboard runtime.
 */

import { flattenObject } from "../utils/flatten.js";
import { normalizeSortConfig, sortItems } from "../utils/sort.js";
import {
  collectSuggestionValues,
  getColumnsWithMultipleValues,
  getEffectiveValue,
  getStableObjectSignature,
  isMissingValue,
  normalizeValue,
} from "../utils/values.js";
import { getEvaluationRunId } from "../utils/runs.js";
import {
  SORTABLE_CONTROL_COLUMNS,
  ensureEvalTabState,
  syncEvaluationGroupUiState,
} from "./store.js";

/** Prefix used by prediction job-return-value columns. */
export const PREDICTION_JOB_RETURN_VALUE_PREFIX = "prediction.job_return_value.";
/** Prefix used by prediction overrides columns. */
export const PREDICTION_OVERRIDES_PREFIX = "prediction.overrides.";
/** Prefix used by evaluation job-return-value columns. */
export const JOB_RETURN_VALUE_PREFIX = "job_return_value.";
/** Synthetic namespace for evaluation group-by fields. */
export const EVALUATION_PREFIX = "evaluation.";

/**
 * Check whether a column points into flattened evaluation job-return-value content.
 *
 * @param {string} column - Column identifier.
 * @returns {boolean} Whether the column is a job-return-value column.
 */
export function isJobReturnValueColumn(column) {
  return column.startsWith(JOB_RETURN_VALUE_PREFIX);
}

/**
 * Remove the synthetic evaluation prefix when present.
 *
 * @param {string} column - Column identifier.
 * @returns {string} The unprefixed column identifier.
 */
export function stripEvaluationFieldPrefix(column) {
  return column.startsWith(EVALUATION_PREFIX)
    ? column.slice(EVALUATION_PREFIX.length)
    : column;
}

/**
 * Normalize an evaluation column to the same display-oriented name used by the
 * pre-Phase-6 default-group-by filtering logic.
 *
 * @param {string} column - Evaluation column identifier.
 * @returns {string} The display-oriented column name.
 */
export function getDisplayEvalColumnName(column) {
  const normalizedColumn = stripEvaluationFieldPrefix(column);
  if (normalizedColumn.startsWith(JOB_RETURN_VALUE_PREFIX)) {
    return normalizedColumn.slice(JOB_RETURN_VALUE_PREFIX.length);
  }
  return normalizedColumn.replace(/^overrides\./, "");
}

/**
 * Remove prediction namespace prefixes used in the flattened prediction table.
 *
 * @param {string} column - Column identifier.
 * @returns {string} The display-oriented unprefixed column identifier.
 */
export function stripPredictionFieldPrefix(column) {
  if (column.startsWith(PREDICTION_JOB_RETURN_VALUE_PREFIX)) {
    return column.slice(PREDICTION_JOB_RETURN_VALUE_PREFIX.length);
  }
  if (column.startsWith(PREDICTION_OVERRIDES_PREFIX)) {
    return column.slice(PREDICTION_OVERRIDES_PREFIX.length);
  }
  return column.replace(/^predictions?\./, "");
}

/**
 * Format prediction columns for mixed prediction/evaluation labels.
 *
 * @param {string} column - Column identifier.
 * @returns {string} The display-oriented prediction-prefixed column identifier.
 */
export function getPredictionQualifiedDisplayName(column) {
  return `prediction.${stripPredictionFieldPrefix(column)}`;
}

/**
 * Reconstruct the dashboard's serialized prediction payload shape.
 *
 * @param {object | null | undefined} prediction - Canonical prediction object.
 * @returns {{overrides: object, job_return_value: object}} Serialized prediction content.
 */
export function reconstructPredictionContent(prediction) {
  return {
    overrides: prediction?.overrides || {},
    job_return_value: prediction?.jobReturnValue || {},
  };
}

/**
 * Return one prediction by canonical prediction id.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {string | null | undefined} predictionId - Prediction identifier.
 * @returns {object | null} The prediction, if present.
 */
export function getPredictionById(state, predictionId) {
  if (!predictionId) {
    return null;
  }
  return state.predictions?.[predictionId] || null;
}

/**
 * Return the prediction linked from one evaluation entry.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {object | null | undefined} evaluation - Evaluation entry.
 * @returns {object | null} The linked prediction, if present.
 */
export function getPredictionForEvaluation(state, evaluation) {
  return getPredictionById(state, evaluation?.predictionId);
}

/**
 * Reconstruct the serialized prediction content for one evaluation entry.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {object | null | undefined} evaluation - Evaluation entry.
 * @returns {{overrides: object, job_return_value: object}} Serialized prediction content.
 */
export function reconstructPredictionContentForEvaluation(state, evaluation) {
  return reconstructPredictionContent(getPredictionForEvaluation(state, evaluation));
}

/**
 * Flatten prediction overrides and job-return-value fields into one table row shape.
 *
 * @param {object | null | undefined} prediction - Canonical prediction object.
 * @returns {Record<string, unknown>} Flattened prediction content.
 */
export function getFlattenedPrediction(prediction) {
  return {
    ...flattenObject(prediction?.overrides || {}, "prediction.overrides"),
    ...flattenObject(prediction?.jobReturnValue || {}, "prediction.job_return_value"),
  };
}

/**
 * Flatten the prediction linked from one evaluation entry.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {object | null | undefined} evaluation - Evaluation entry.
 * @returns {Record<string, unknown>} Flattened prediction content.
 */
export function getFlattenedPredictionForEvaluation(state, evaluation) {
  return getFlattenedPrediction(getPredictionForEvaluation(state, evaluation));
}

/**
 * Derive one prediction view per canonical prediction id.
 *
 * @param {object} state - Canonical dashboard state.
 * @returns {Array<object>} Prediction views joined with linked evaluations.
 */
export function getPredictionViews(state) {
  const predictionViewsById = new Map();
  for (const evaluation of state.evaluations || []) {
    const prediction = getPredictionById(state, evaluation.predictionId);
    if (!prediction) {
      continue;
    }
    if (!predictionViewsById.has(evaluation.predictionId)) {
      predictionViewsById.set(evaluation.predictionId, {
        predictionId: evaluation.predictionId,
        predictionFlat: getFlattenedPrediction(prediction),
        evaluations: [],
      });
    }
    predictionViewsById.get(evaluation.predictionId).evaluations.push(evaluation);
  }
  return Array.from(predictionViewsById.values());
}

/**
 * Collect all flattened prediction columns present across the given prediction views.
 *
 * @param {Array<object>} predictionViews - Prediction view rows.
 * @returns {string[]} Sorted prediction columns.
 */
export function getPredictionColumns(predictionViews = []) {
  const predictionColumns = new Set();
  for (const predictionView of predictionViews) {
    for (const key of Object.keys(predictionView.predictionFlat || {})) {
      predictionColumns.add(key);
    }
  }
  return Array.from(predictionColumns).sort();
}

/**
 * Return the current prediction columns derived from canonical state.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Array<object> | null} [predictionViews=null] - Optional precomputed prediction views.
 * @returns {string[]} Sorted prediction columns.
 */
export function getCurrentPredictionColumns(state, predictionViews = null) {
  return getPredictionColumns(predictionViews || getPredictionViews(state));
}

/**
 * Return the configured default value for one prediction column.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {string} column - Prediction column identifier.
 * @returns {string} The configured default value.
 */
export function getPredictionDefaultValue(state, column) {
  return state.predictionDefaultValues?.[column] ?? "";
}

/**
 * Return the effective prediction value after applying configured defaults.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Record<string, unknown>} predictionFlat - Flattened prediction row.
 * @param {string} column - Prediction column identifier.
 * @returns {string} The effective display value.
 */
export function getPredictionEffectiveValue(state, predictionFlat, column) {
  return getEffectiveValue(predictionFlat?.[column], getPredictionDefaultValue(state, column));
}

/**
 * Group prediction views according to the active prediction group-by fields.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Array<object> | null} [predictionViews=null] - Optional precomputed prediction views.
 * @param {string[] | null} [groupByFields=null] - Optional group-by fields.
 * @param {string[] | null} [predictionColumns=null] - Optional prediction columns.
 * @returns {Array<object>} Prediction groups.
 */
export function getPredictionGroups(
  state,
  predictionViews = null,
  groupByFields = null,
  predictionColumns = null
) {
  const resolvedPredictionViews = predictionViews || getPredictionViews(state);
  const resolvedGroupByFields = groupByFields || state.groupByFields || [];
  const resolvedPredictionColumns = predictionColumns || getCurrentPredictionColumns(state, resolvedPredictionViews);
  const map = new Map();

  for (const predictionView of resolvedPredictionViews) {
    const groupId = !resolvedGroupByFields.length
      ? getPredictionEffectiveSignature(state, predictionView.predictionFlat, resolvedPredictionColumns)
      : resolvedGroupByFields
        .map((field) => `${field}=${getPredictionEffectiveValue(state, predictionView.predictionFlat, field)}`)
        .join(" | ");

    if (!map.has(groupId)) {
      map.set(groupId, {
        groupId,
        predictions: [],
        values: Object.fromEntries(
          resolvedGroupByFields.map((field) => [field, getPredictionEffectiveValue(state, predictionView.predictionFlat, field)])
        ),
      });
    }
    map.get(groupId).predictions.push(predictionView);
  }

  return Array.from(map.values()).sort((a, b) => b.predictions.length - a.predictions.length);
}

/**
 * Filter prediction groups down to the selected group ids.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Array<object> | null} [groups=null] - Optional precomputed prediction groups.
 * @returns {Array<object>} Selected prediction groups.
 */
export function getSelectedPredictionGroups(state, groups = null) {
  const resolvedGroups = groups || getPredictionGroups(state);
  return resolvedGroups.filter((group) => state.selectedGroupIds.has(group.groupId));
}

/**
 * Flatten evaluations reachable from the selected prediction groups.
 *
 * @param {Array<object>} selectedPredictionGroups - Selected prediction groups.
 * @returns {Array<object>} Flattened evaluation entries.
 */
export function getSelectedEvaluations(selectedPredictionGroups = []) {
  return selectedPredictionGroups.flatMap((group) =>
    group.predictions.flatMap((prediction) => prediction.evaluations)
  );
}

/**
 * Flatten one evaluation's job-return-value object.
 *
 * @param {object | null | undefined} evaluation - Evaluation entry.
 * @returns {Record<string, unknown>} Flattened evaluation job-return-value content.
 */
export function getFlattenedEvaluationJobReturnValue(evaluation) {
  return flattenObject(evaluation?.jobReturnValue || {});
}

/**
 * Resolve the raw value for one evaluation column.
 *
 * @param {object | null | undefined} evaluation - Evaluation entry.
 * @param {string} column - Evaluation column identifier.
 * @returns {unknown} The raw column value.
 */
export function getEvaluationColumnRawValue(evaluation, column) {
  if (!evaluation || typeof evaluation !== "object") {
    return undefined;
  }
  const normalizedColumn = stripEvaluationFieldPrefix(column);
  if (normalizedColumn === "eval_run_dir") {
    return evaluation.runDir;
  }
  if (isJobReturnValueColumn(normalizedColumn)) {
    return getFlattenedEvaluationJobReturnValue(evaluation)[normalizedColumn.slice(JOB_RETURN_VALUE_PREFIX.length)];
  }
  return evaluation?.overrides?.[normalizedColumn];
}

/**
 * Return the configured default value for one evaluation column.
 *
 * @param {object | null | undefined} evalTabState - Per-experiment evaluation tab state.
 * @param {string} column - Evaluation column identifier.
 * @returns {string} The configured default value.
 */
export function getEvalDefaultValue(evalTabState, column) {
  return evalTabState?.defaultValues?.[column] ?? "";
}

/**
 * Return the effective evaluation value after applying configured defaults.
 *
 * @param {object} evaluation - Evaluation entry.
 * @param {string} column - Evaluation column identifier.
 * @param {object | null | undefined} evalTabState - Per-experiment evaluation tab state.
 * @returns {string} The effective display value.
 */
export function getEvaluationEffectiveValue(evaluation, column, evalTabState) {
  return getEffectiveValue(getEvaluationColumnRawValue(evaluation, column), getEvalDefaultValue(evalTabState, column));
}

/**
 * Return the evaluation experiment identifier for one evaluation entry.
 *
 * @param {object} evaluation - Evaluation entry.
 * @returns {string} The effective experiment identifier.
 */
export function getEvaluationExperiment(evaluation) {
  return getEffectiveValue(
    evaluation?.overrides?.["experiment/evaluate"],
    "(missing experiment/evaluate)"
  );
}

/**
 * Flatten the currently selected prediction groups into member prediction views.
 *
 * @param {object} state - Canonical dashboard state.
 * @returns {Array<object>} Selected prediction views.
 */
export function getSelectedPredictionViews(state) {
  return getSelectedPredictionGroups(state).flatMap((group) => group.predictions);
}

/**
 * Gather evaluations from the currently selected prediction groups.
 *
 * @param {object} state - Canonical dashboard state.
 * @returns {Array<object>} Selected evaluations.
 */
export function gatherSelectedEvaluations(state) {
  if (!state.selectedGroupIds.size) {
    return [];
  }
  return getSelectedEvaluations(getSelectedPredictionGroups(state));
}

/**
 * Group selected evaluations by experiment identifier.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Array<object> | null} [selectedEvaluations=null] - Optional preselected evaluations.
 * @returns {Map<string, Array<object>>} Evaluations keyed by experiment.
 */
export function getEvaluationsByExperiment(state, selectedEvaluations = null) {
  const resolvedEvaluations = selectedEvaluations || gatherSelectedEvaluations(state);
  const byExperiment = new Map();
  for (const evaluation of resolvedEvaluations) {
    const experiment = getEvaluationExperiment(evaluation);
    if (!byExperiment.has(experiment)) {
      byExperiment.set(experiment, []);
    }
    byExperiment.get(experiment).push(evaluation);
  }
  return byExperiment;
}

/**
 * Return the selected evaluations that belong to one evaluation experiment.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {string} experiment - Evaluation experiment identifier.
 * @param {Array<object> | null} [selectedEvaluations=null] - Optional preselected evaluations.
 * @returns {Array<object>} Evaluations for the experiment.
 */
export function getSelectedEvaluationsForExperiment(state, experiment, selectedEvaluations = null) {
  if (!experiment) {
    return [];
  }
  const resolvedEvaluations = selectedEvaluations || gatherSelectedEvaluations(state);
  return resolvedEvaluations.filter((evaluation) => getEvaluationExperiment(evaluation) === experiment);
}

/**
 * Collect all evaluation columns present across the given evaluations.
 *
 * @param {Array<object>} evaluations - Evaluation entries.
 * @returns {string[]} Sorted evaluation columns.
 */
export function getEvaluationColumns(evaluations = []) {
  const evalColumns = new Set();
  for (const evaluation of evaluations) {
    for (const key of Object.keys(evaluation.overrides || {})) {
      evalColumns.add(key);
    }
    for (const key of Object.keys(getFlattenedEvaluationJobReturnValue(evaluation))) {
      evalColumns.add(`${JOB_RETURN_VALUE_PREFIX}${key}`);
    }
  }
  return Array.from(evalColumns).sort();
}

/**
 * Choose default prediction truncate columns based on file/run-like names.
 *
 * @param {string[]} predictionColumns - Prediction column identifiers.
 * @returns {Set<string>} Default truncate-enabled columns.
 */
export function getDefaultTruncateColumns(predictionColumns) {
  const defaults = new Set();
  for (const column of predictionColumns) {
    const name = stripPredictionFieldPrefix(column);
    if (/file|run/i.test(name) || /file|run/i.test(column)) {
      defaults.add(column);
    }
  }
  return defaults;
}

/**
 * Choose default prediction group-by fields from varying non-seed override columns.
 *
 * @param {string[]} predictionColumns - Prediction column identifiers.
 * @param {Array<object>} predictionViews - Prediction views.
 * @returns {string[]} Default prediction group-by fields.
 */
export function getDefaultGroupByFields(predictionColumns, predictionViews = []) {
  const candidateColumns = predictionColumns.filter(
    (column) =>
      column.startsWith(PREDICTION_OVERRIDES_PREFIX) &&
      stripPredictionFieldPrefix(column).toLowerCase() !== "seed"
  );
  return getColumnsWithMultipleValues(
    predictionViews,
    candidateColumns,
    (predictionView, column) => predictionView.predictionFlat?.[column]
  );
}

/**
 * Choose default evaluation group-by fields from varying evaluation columns.
 *
 * @param {string[]} evalColumns - Evaluation column identifiers.
 * @param {Array<object>} evaluations - Evaluation entries.
 * @returns {string[]} Default evaluation group-by fields.
 */
export function getDefaultEvalGroupByFields(evalColumns, evaluations = []) {
  const candidateColumns = evalColumns.filter(
    (column) => getDisplayEvalColumnName(column) !== "dataset.predictions.log"
  );
  return getColumnsWithMultipleValues(
    evaluations,
    candidateColumns,
    (evaluation, column) => getEvaluationColumnRawValue(evaluation, column)
  );
}

/**
 * Build a stable signature from effective prediction values for the provided columns.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Record<string, unknown>} predictionFlat - Flattened prediction row.
 * @param {string[]} predictionColumns - Prediction columns contributing to the signature.
 * @returns {string} Stable JSON signature.
 */
export function getPredictionEffectiveSignature(state, predictionFlat, predictionColumns) {
  return JSON.stringify(
    Object.fromEntries(
      (predictionColumns || [])
        .map((column) => [column, getPredictionEffectiveValue(state, predictionFlat, column)])
        .sort(([keyA], [keyB]) => keyA.localeCompare(keyB))
    )
  );
}

/**
 * Return prediction columns whose views still contain missing values.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Array<object>} predictionViews - Prediction views.
 * @param {string[] | null} [predictionColumns=null] - Optional prediction columns.
 * @returns {string[]} Prediction columns with missing values.
 */
export function getPredictionColumnsWithMissingValues(state, predictionViews, predictionColumns = null) {
  const resolvedColumns = predictionColumns || getPredictionColumns(predictionViews);
  return resolvedColumns.filter((column) =>
    predictionViews.some((predictionView) => isMissingValue(predictionView.predictionFlat?.[column]))
  );
}

/**
 * Collect non-empty suggestion values for a prediction column.
 *
 * @param {Array<object>} predictionViews - Prediction views.
 * @param {string} column - Prediction column identifier.
 * @returns {string[]} Suggested default values.
 */
export function getPredictionDefaultSuggestions(predictionViews, column) {
  return collectSuggestionValues(
    predictionViews.map((predictionView) => predictionView.predictionFlat?.[column])
  );
}

/**
 * Count how many prediction views are missing a value for the given column.
 *
 * @param {Array<object>} predictionViews - Prediction views.
 * @param {string} column - Prediction column identifier.
 * @returns {number} Missing-value count.
 */
export function getPredictionMissingValueCount(predictionViews, column) {
  return predictionViews.filter((predictionView) => isMissingValue(predictionView.predictionFlat?.[column])).length;
}

/**
 * Return evaluation columns whose rows still contain missing values.
 *
 * @param {Array<object>} evaluations - Evaluation entries.
 * @param {string[]} evalColumns - Evaluation column identifiers.
 * @returns {string[]} Evaluation columns with missing values.
 */
export function getEvalColumnsWithMissingValues(evaluations, evalColumns) {
  return evalColumns.filter((column) => evaluations.some((evaluation) => isMissingValue(getEvaluationColumnRawValue(evaluation, column))));
}

/**
 * Collect non-empty suggestion values for one evaluation column.
 *
 * @param {Array<object>} evaluations - Evaluation entries.
 * @param {string} column - Evaluation column identifier.
 * @returns {string[]} Suggested default values.
 */
export function getEvalDefaultSuggestions(evaluations, column) {
  return collectSuggestionValues(evaluations.map((evaluation) => getEvaluationColumnRawValue(evaluation, column)));
}

/**
 * Count how many evaluations are missing a value for the given column.
 *
 * @param {Array<object>} evaluations - Evaluation entries.
 * @param {string} column - Evaluation column identifier.
 * @returns {number} Missing-value count.
 */
export function getEvalMissingValueCount(evaluations, column) {
  return evaluations.filter((evaluation) => isMissingValue(getEvaluationColumnRawValue(evaluation, column))).length;
}

/**
 * Return the evaluation columns for the currently active evaluation experiment.
 *
 * @param {object} state - Canonical dashboard state.
 * @returns {string[]} Active evaluation columns.
 */
export function getActiveEvalColumns(state) {
  if (!state.activeEvalTab) {
    return [];
  }
  return getEvaluationContext(state, state.activeEvalTab)?.evalColumns || [];
}

/**
 * Return the group-level value used when sorting prediction groups.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {object} group - Prediction group.
 * @param {string} column - Sort column.
 * @returns {unknown} Sort value.
 */
export function getPredictionGroupSortValue(state, group, column) {
  if (column === "expand") {
    return state.expandedGroupIds.has(group.groupId) ? 1 : 0;
  }
  if (column === "select") {
    return state.selectedGroupIds.has(group.groupId) ? 1 : 0;
  }
  if (column === "group_size") {
    return group.predictions.length;
  }
  return getGroupValueDisplay(state, group, column);
}

/**
 * Return the member-level value used when sorting prediction rows within a group.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {object} predictionView - Prediction view.
 * @param {string} column - Sort column.
 * @returns {unknown} Sort value.
 */
export function getPredictionMemberSortValue(state, predictionView, column) {
  if (column === "group_size") {
    return predictionView.evaluations.length;
  }
  if (SORTABLE_CONTROL_COLUMNS.has(column)) {
    return "";
  }
  return getPredictionEffectiveValue(state, predictionView.predictionFlat, column);
}

/**
 * Return prediction groups sorted according to the active prediction sort config.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Array<object> | null} [predictionGroups=null] - Optional prediction groups.
 * @returns {Array<object>} Sorted prediction groups.
 */
export function getSortedPredictionGroups(state, predictionGroups = null) {
  const resolvedGroups = predictionGroups || getPredictionGroups(state);
  const validSortColumns = new Set([...SORTABLE_CONTROL_COLUMNS, ...getCurrentPredictionColumns(state)]);
  state.predictionSort = normalizeSortConfig(state.predictionSort, validSortColumns);
  return sortItems(resolvedGroups, state.predictionSort, (group, column) =>
    getPredictionGroupSortValue(state, group, column)
  );
}

/**
 * Return prediction members sorted according to the active prediction sort config.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Array<object>} predictions - Prediction members.
 * @returns {Array<object>} Sorted member rows.
 */
export function getSortedPredictionMembers(state, predictions) {
  return sortItems(predictions, state.predictionSort, (predictionView, column) =>
    getPredictionMemberSortValue(state, predictionView, column)
  );
}

/**
 * Summarize selection state for the currently displayed prediction groups.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Array<object>} displayedGroups - Displayed prediction groups.
 * @returns {{displayedGroupIds: string[], selectedCount: number, allSelected: boolean, someSelected: boolean}} Selection summary.
 */
export function getDisplayedSelectionState(state, displayedGroups = []) {
  const displayedGroupIds = displayedGroups.map((group) => group.groupId);
  const selectedCount = displayedGroupIds.filter((groupId) => state.selectedGroupIds.has(groupId)).length;
  return {
    displayedGroupIds,
    selectedCount,
    allSelected: displayedGroupIds.length > 0 && selectedCount === displayedGroupIds.length,
    someSelected: selectedCount > 0 && selectedCount < displayedGroupIds.length,
  };
}

/**
 * Format mixed group values for prediction groups.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {object} group - Prediction group.
 * @param {string} column - Prediction column identifier.
 * @returns {string} Group display value.
 */
export function getGroupValueDisplay(state, group, column) {
  const values = new Set(
    group.predictions.map((prediction) => getPredictionEffectiveValue(state, prediction.predictionFlat, column))
  );
  return formatDistinctValueDisplay(values);
}

/**
 * Group evaluations by active prediction and evaluation grouping fields.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {Array<object>} evaluations - Evaluation entries.
 * @param {string[]} groupByFields - Evaluation group-by fields.
 * @param {string[] | null} [predictionGroupByFields=null] - Prediction group-by fields.
 * @param {object | null} [evalTabState=null] - Per-experiment evaluation tab state.
 * @returns {Array<object>} Evaluation groups.
 */
export function getEvaluationGroups(
  state,
  evaluations,
  groupByFields,
  predictionGroupByFields = null,
  evalTabState = null
) {
  const resolvedPredictionGroupByFields = predictionGroupByFields || state.groupByFields || [];
  const resolvedEvalTabState = evalTabState || (state.activeEvalTab ? state.evalTabStates[state.activeEvalTab] : null);
  const map = new Map();
  for (const evaluation of evaluations || []) {
    const keyParts = [];
    for (const field of resolvedPredictionGroupByFields) {
      keyParts.push(`prediction.${field}=${getPredictionEffectiveValue(state, getFlattenedPredictionForEvaluation(state, evaluation), field)}`);
    }
    for (const field of groupByFields || []) {
      keyParts.push(`eval.${field}=${getEvaluationEffectiveValue(evaluation, field, resolvedEvalTabState)}`);
    }
    const groupId = keyParts.length ? keyParts.join(" | ") : getEvaluationRunId(evaluation);
    if (!map.has(groupId)) {
      map.set(groupId, {
        groupId,
        evaluations: [],
        values: Object.fromEntries(
          (groupByFields || []).map((field) => [field, getEvaluationEffectiveValue(evaluation, field, resolvedEvalTabState)])
        ),
      });
    }
    map.get(groupId).evaluations.push(evaluation);
  }
  return Array.from(map.values()).sort((a, b) => b.evaluations.length - a.evaluations.length);
}

/**
 * Format a mixed evaluation-group display value.
 *
 * @param {Array<object>} evaluations - Evaluation entries.
 * @param {(evaluation: object) => unknown} getter - Value getter.
 * @returns {string} Group display value.
 */
export function getGroupValueDisplayFromEvaluations(evaluations, getter) {
  const values = new Set((evaluations || []).map((evaluation) => normalizeValue(getter(evaluation))));
  return formatDistinctValueDisplay(values);
}

/**
 * Return the group-level value used when sorting evaluation groups.
 *
 * @param {object} group - Evaluation group.
 * @param {string} column - Sort column.
 * @param {object} evalTabState - Per-experiment evaluation tab state.
 * @returns {unknown} Sort value.
 */
export function getEvaluationGroupSortValue(group, column, evalTabState) {
  if (column === "expand") {
    return evalTabState.expandedGroupIds.has(group.groupId) ? 1 : 0;
  }
  if (column === "select") {
    return evalTabState.selectedGroupIds.has(group.groupId) ? 1 : 0;
  }
  if (column === "group_size") {
    return group.evaluations.length;
  }
  if (column === "eval_run_dir") {
    return getGroupValueDisplayFromEvaluations(group.evaluations, (evaluation) => evaluation.runDir);
  }
  return getGroupValueDisplayFromEvaluations(
    group.evaluations,
    (evaluation) => getEvaluationEffectiveValue(evaluation, column, evalTabState)
  );
}

/**
 * Return the row-level value used when sorting evaluation members.
 *
 * @param {object} evaluation - Evaluation entry.
 * @param {string} column - Sort column.
 * @param {object} evalTabState - Per-experiment evaluation tab state.
 * @returns {unknown} Sort value.
 */
export function getEvaluationRunSortValue(evaluation, column, evalTabState) {
  if (column === "eval_run_dir") {
    return evaluation.runDir;
  }
  if (SORTABLE_CONTROL_COLUMNS.has(column)) {
    return "";
  }
  return getEvaluationEffectiveValue(evaluation, column, evalTabState);
}

/**
 * Return evaluation groups sorted according to one experiment tab's sort config.
 *
 * @param {Array<object>} groups - Evaluation groups.
 * @param {object} evalTabState - Per-experiment evaluation tab state.
 * @returns {Array<object>} Sorted evaluation groups.
 */
export function getSortedEvaluationGroups(groups, evalTabState) {
  return sortItems(groups, evalTabState.sort, (group, column) =>
    getEvaluationGroupSortValue(group, column, evalTabState)
  );
}

/**
 * Return evaluation rows sorted according to one experiment tab's sort config.
 *
 * @param {Array<object>} evaluations - Evaluation entries.
 * @param {object} evalTabState - Per-experiment evaluation tab state.
 * @returns {Array<object>} Sorted evaluation rows.
 */
export function getSortedEvaluations(evaluations, evalTabState) {
  return sortItems(evaluations, evalTabState.sort, (evaluation, column) =>
    getEvaluationRunSortValue(evaluation, column, evalTabState)
  );
}

/**
 * Return the current evaluation context derived from canonical state and UI settings.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {string | null} [activeExperiment=state.activeEvalTab] - Active evaluation experiment.
 * @param {Array<object> | null} [selectedEvaluations=null] - Optional selected evaluations.
 * @returns {object | null} Active evaluation context.
 */
export function getEvaluationContext(
  state,
  activeExperiment = state.activeEvalTab,
  selectedEvaluations = null
) {
  if (!activeExperiment) {
    return null;
  }
  const resolvedSelectedEvaluations = selectedEvaluations || gatherSelectedEvaluations(state);
  const experimentEvaluations = getSelectedEvaluationsForExperiment(
    state,
    activeExperiment,
    resolvedSelectedEvaluations
  );
  const evalColumns = getEvaluationColumns(experimentEvaluations);
  const evalTabState = ensureEvalTabState(state, activeExperiment, evalColumns, {
    evaluations: experimentEvaluations,
    getDefaultEvalGroupByFields,
  });
  const evaluationGroups = getEvaluationGroups(
    state,
    experimentEvaluations,
    evalTabState.groupByFields,
    state.groupByFields,
    evalTabState
  );
  syncEvaluationGroupUiState(evalTabState, evaluationGroups, experimentEvaluations);
  return {
    activeExperiment,
    experimentEvaluations,
    evalColumns,
    evalTabState,
    evaluationGroups,
  };
}

/**
 * Filter evaluation groups down to the selected evaluation group ids.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {object | null} [evaluationContext=null] - Optional evaluation context.
 * @returns {Array<object>} Selected evaluation groups.
 */
export function getSelectedEvaluationGroups(state, evaluationContext = null) {
  const resolvedContext = evaluationContext || getEvaluationContext(state);
  if (!resolvedContext) {
    return [];
  }
  const { evaluationGroups, evalTabState } = resolvedContext;
  return evaluationGroups.filter((group) => evalTabState.selectedGroupIds.has(group.groupId));
}

/**
 * Combine prediction grouping and evaluation grouping into the plot-group shape.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {string} activeExperiment - Active evaluation experiment.
 * @param {Array<object>} selectedEvalGroups - Selected evaluation groups.
 * @param {string[]} evalGroupByFields - Evaluation group-by fields.
 * @param {object} evalTabState - Per-experiment evaluation tab state.
 * @returns {{groups: Array<object>, fields: string[]}} Plot-group descriptor.
 */
export function getPlotGroups(state, activeExperiment, selectedEvalGroups, evalGroupByFields, evalTabState) {
  const allFields = [...new Set([
    ...(state.groupByFields || []),
    ...(evalGroupByFields || []).map((field) => `${EVALUATION_PREFIX}${field}`),
  ])];

  const map = new Map();
  for (const evalGroup of selectedEvalGroups || []) {
    for (const evaluation of evalGroup.evaluations) {
      if (getEvaluationExperiment(evaluation) !== activeExperiment) {
        continue;
      }
      const values = {};
      for (const field of allFields) {
        const evaluationField = stripEvaluationFieldPrefix(field);
        if (evaluationField !== field) {
          values[field] = getEvaluationEffectiveValue(
            evaluation,
            evaluationField,
            evalTabState
          );
        } else {
          values[field] = getPredictionEffectiveValue(
            state,
            getFlattenedPredictionForEvaluation(state, evaluation),
            field
          );
        }
      }
      const groupId = allFields.length
        ? allFields.map((field) => `${field}=${normalizeValue(values[field])}`).join(" | ")
        : getEvaluationRunId(evaluation);
      if (!map.has(groupId)) {
        map.set(groupId, { groupId, values, evaluations: [] });
      }
      map.get(groupId).evaluations.push(evaluation);
    }
  }

  return {
    groups: Array.from(map.values()).sort((a, b) => b.evaluations.length - a.evaluations.length),
    fields: allFields,
  };
}

/**
 * Normalize metric collection types to their plot-facing visualization types.
 *
 * @param {string} metricType - Raw metric type.
 * @returns {string} Visualization metric type.
 */
export function getVisualizationMetricType(metricType) {
  if (metricType === "ConfusionMatrixCollection") {
    return "ConfusionMatrix";
  }
  if (metricType === "TpFpFnCollectorCollection") {
    return "TpFpFnCollector";
  }
  return metricType;
}

/**
 * Derive the active metric type for one evaluation context.
 *
 * @param {object} state - Canonical dashboard state.
 * @param {string} activeExperiment - Active evaluation experiment.
 * @param {object | null} [evaluationContext=null] - Optional evaluation context.
 * @returns {string} Visualization metric type.
 */
export function getMetricTypeForEvaluationContext(state, activeExperiment, evaluationContext = null) {
  const resolvedContext = evaluationContext || getEvaluationContext(state, activeExperiment);
  const metricTypes = new Set(
    (resolvedContext?.experimentEvaluations || [])
      .map((evaluation) => getVisualizationMetricType(normalizeValue(evaluation?.jobReturnValue?.type).trim()))
      .filter(Boolean)
  );
  if (metricTypes.size > 1) {
    throw new Error(
      `Multiple evaluation metric types found for ${JSON.stringify(activeExperiment)}: ${Array.from(metricTypes)
        .sort((a, b) => a.localeCompare(b))
        .join(", ")}`
    );
  }
  return Array.from(metricTypes)[0] || "";
}

/**
 * Build a stable content signature for one normalized prediction payload.
 *
 * @param {object} prediction - Canonical prediction object.
 * @returns {string} Stable prediction content signature.
 */
export function getPredictionContentSignature(prediction) {
  return getStableObjectSignature(getFlattenedPrediction(prediction));
}

/**
 * Format a mixed set of values for display in grouped rows.
 *
 * @param {Set<string>} values - Distinct display values.
 * @returns {string} Display string.
 */
function formatDistinctValueDisplay(values) {
  if (values.size <= 1) {
    return values.values().next().value || "";
  }
  return `(mixed: ${values.size} values)`;
}
