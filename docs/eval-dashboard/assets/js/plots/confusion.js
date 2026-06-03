/**
 * Confusion-matrix plot aggregation and tab-map helpers.
 */

import { meanAndStd, normalizeValue } from "../utils/values.js";
import {
  getGroupLabelForFields,
  getPlotDisplayLabel,
} from "./shared.js";

export function getMetricCollectionSourceRunDir(evaluation) {
  return normalizeValue(evaluation?.sourceRunDir ?? evaluation?.runDir).trim();
}

export function expandMetricFieldCollectionEvaluation(
  evaluation,
  { collectionType, singularType, fallbackRunDirPrefix }
) {
  if (!evaluation || typeof evaluation !== "object") {
    return [];
  }

  const metricType = normalizeValue(evaluation?.jobReturnValue?.type).trim();
  const sourceRunDir = getMetricCollectionSourceRunDir(evaluation);
  if (metricType === collectionType) {
    const fieldEntries = evaluation.data;
    if (!fieldEntries || typeof fieldEntries !== "object" || Array.isArray(fieldEntries)) {
      return [];
    }

    const baseOverrides =
      evaluation.overrides && typeof evaluation.overrides === "object" && !Array.isArray(evaluation.overrides)
        ? evaluation.overrides
        : {};

    return Object.entries(fieldEntries)
      .filter(([, fieldEntry]) => fieldEntry && typeof fieldEntry === "object" && !Array.isArray(fieldEntry))
      .map(([field, fieldEntry]) => ({
        ...evaluation,
        runDir: sourceRunDir ? `${sourceRunDir}#${field}` : `${fallbackRunDirPrefix}#${field}`,
        sourceRunDir,
        jobReturnValue: {
          ...(evaluation.jobReturnValue || {}),
          type: singularType,
        },
        overrides: {
          ...baseOverrides,
          "metric.field": field,
        },
        data: fieldEntry,
      }));
  }

  return [
    {
      ...evaluation,
      sourceRunDir,
    },
  ];
}

export function expandConfusionMatrixLikeEvaluation(evaluation) {
  return expandMetricFieldCollectionEvaluation(evaluation, {
    collectionType: "ConfusionMatrixCollection",
    singularType: "ConfusionMatrix",
    fallbackRunDirPrefix: "confusion-field",
  });
}

export function normalizeConfusionMatrixLikeEvaluations(evaluations) {
  return (evaluations || []).flatMap((evaluation) => expandConfusionMatrixLikeEvaluation(evaluation));
}

export function countDistinctConfusionMatrixRuns(evaluations) {
  return new Set(
    (evaluations || [])
      .map((evaluation) => getMetricCollectionSourceRunDir(evaluation))
      .filter(Boolean)
  ).size;
}

export function getConfusionMatrixTitle({
  experimentEvaluations,
  evalTabState,
  getEvaluationEffectiveValue,
  shortenLabels = false,
}) {
  const fieldValues = new Set(
    experimentEvaluations
      .map((evaluation) => getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState))
      .filter((value) => value)
  );
  if (fieldValues.size === 0) {
    return "(missing metric.field)";
  }
  if (fieldValues.size === 1) {
    return getPlotDisplayLabel(Array.from(fieldValues)[0], { shortenLabels });
  }
  return `mixed metric.field: ${Array.from(fieldValues)
    .sort((a, b) => a.localeCompare(b))
    .map((value) => getPlotDisplayLabel(value, { shortenLabels }))
    .join(", ")}`;
}

export function getConfusionMatrixAggregation(experimentEvaluations) {
  const rowLabels = new Set();
  const colLabels = new Set();
  const evaluationCells = [];

  for (const evaluation of experimentEvaluations) {
    const map = new Map();
    const evalData = evaluation.data || {};
    for (const [actualLabel, predictedMap] of Object.entries(evalData)) {
      if (!predictedMap || typeof predictedMap !== "object" || Array.isArray(predictedMap)) {
        continue;
      }
      for (const [predictedLabel, rawValue] of Object.entries(predictedMap)) {
        if (!Number.isFinite(rawValue)) {
          continue;
        }
        const value = Number(rawValue);
        rowLabels.add(actualLabel);
        colLabels.add(predictedLabel);
        map.set(`${actualLabel}|#|${predictedLabel}`, value);
      }
    }
    evaluationCells.push(map);
  }

  const sortWithForcedLast = (values, forcedLast) =>
    Array.from(values).sort((a, b) => {
      if (a === forcedLast && b !== forcedLast) {
        return 1;
      }
      if (b === forcedLast && a !== forcedLast) {
        return -1;
      }
      return a.localeCompare(b);
    });

  const rows = sortWithForcedLast(rowLabels, "UNASSIGNABLE");
  const cols = sortWithForcedLast(colLabels, "UNDETECTED");
  const cells = new Map();
  for (const row of rows) {
    for (const col of cols) {
      const key = `${row}|#|${col}`;
      const values = evaluationCells.map((cellMap) => cellMap.get(key) ?? 0);
      const stats = meanAndStd(values) || { mean: 0, std: 0 };
      cells.set(key, stats);
    }
  }

  return { rows, cols, cells };
}

export function filterConfusionMatrixAggregationByLabelTotal(aggregation, minLabelTotal) {
  const threshold = Number.isFinite(minLabelTotal) ? Math.max(0, Number(minLabelTotal)) : 0;
  if (!aggregation || threshold <= 0) {
    return aggregation;
  }

  const { rows = [], cols = [], cells = new Map() } = aggregation;
  let filteredRows = [...rows];
  let filteredCols = [...cols];
  let rowTotals = new Map();
  let colTotals = new Map();

  while (true) {
    rowTotals = new Map(
      filteredRows.map((row) => [
        row,
        filteredCols.reduce((sum, col) => sum + (cells.get(`${row}|#|${col}`)?.mean ?? 0), 0),
      ])
    );
    colTotals = new Map(
      filteredCols.map((col) => [
        col,
        filteredRows.reduce((sum, row) => sum + (cells.get(`${row}|#|${col}`)?.mean ?? 0), 0),
      ])
    );

    const nextRows = filteredRows.filter((row) => (rowTotals.get(row) ?? 0) >= threshold);
    const nextCols = filteredCols.filter((col) => (colTotals.get(col) ?? 0) >= threshold);
    if (nextRows.length === filteredRows.length && nextCols.length === filteredCols.length) {
      filteredRows = nextRows;
      filteredCols = nextCols;
      break;
    }
    filteredRows = nextRows;
    filteredCols = nextCols;
    if (!filteredRows.length || !filteredCols.length) {
      break;
    }
  }

  rowTotals = new Map(
    filteredRows.map((row) => [
      row,
      filteredCols.reduce((sum, col) => sum + (cells.get(`${row}|#|${col}`)?.mean ?? 0), 0),
    ])
  );
  colTotals = new Map(
    filteredCols.map((col) => [
      col,
      filteredRows.reduce((sum, row) => sum + (cells.get(`${row}|#|${col}`)?.mean ?? 0), 0),
    ])
  );

  const filteredCells = new Map();
  for (const row of filteredRows) {
    for (const col of filteredCols) {
      const key = `${row}|#|${col}`;
      filteredCells.set(key, cells.get(key) || { mean: 0, std: 0 });
    }
  }
  return {
    rows: filteredRows,
    cols: filteredCols,
    cells: filteredCells,
    rowTotals,
    colTotals,
  };
}

export function buildConfusionTabMap({
  activeExperiment,
  plotGroups,
  experimentEvaluations,
  labelFields,
  evalTabState,
  confusionTabsBy,
  getEvaluationEffectiveValue,
  getEvaluationExperiment,
  displayPlotGroupFieldName,
  shortenLabels = false,
}) {
  const tabMap = new Map();
  const normalizedExperimentEvaluations = normalizeConfusionMatrixLikeEvaluations(experimentEvaluations);
  const groupEntries = plotGroups
    .map((group, index) => ({
      key: `group|#|${group.groupId}`,
      label: getGroupLabelForFields(
        group,
        labelFields,
        `group ${index + 1}`,
        displayPlotGroupFieldName
      ),
      evaluations: normalizeConfusionMatrixLikeEvaluations(
        group.evaluations.filter((evaluation) => getEvaluationExperiment(evaluation) === activeExperiment)
      ),
    }))
    .filter((entry) => entry.evaluations.length > 0);

  if (confusionTabsBy === "metric_field") {
    for (const evaluation of normalizedExperimentEvaluations) {
      const rawField = getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState);
      const fieldLabel = rawField || "(missing metric.field)";
      if (!tabMap.has(fieldLabel)) {
        tabMap.set(fieldLabel, {
          label: getPlotDisplayLabel(fieldLabel, { shortenLabels }),
          plots: [],
        });
      }
    }

    for (const [fieldKey, tab] of tabMap.entries()) {
      for (const groupEntry of groupEntries) {
        const evaluationsForFieldAndGroup = groupEntry.evaluations.filter((evaluation) => {
          const rawField = getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState);
          const fieldLabel = rawField || "(missing metric.field)";
          return fieldLabel === fieldKey;
        });
        if (evaluationsForFieldAndGroup.length === 0) {
          continue;
        }
        tab.plots.push({ label: groupEntry.label, evaluations: evaluationsForFieldAndGroup });
      }
    }
    return tabMap;
  }

  for (const groupEntry of groupEntries) {
    const byField = new Map();
    for (const evaluation of groupEntry.evaluations) {
      const rawField = getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState);
      const fieldLabel = rawField || "(missing metric.field)";
      if (!byField.has(fieldLabel)) {
        byField.set(fieldLabel, []);
      }
      byField.get(fieldLabel).push(evaluation);
    }
    const plots = Array.from(byField.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([fieldLabel, evaluations]) => ({
        label: fieldLabel,
        evaluations,
      }));
    tabMap.set(groupEntry.key, { label: groupEntry.label, plots });
  }

  return tabMap;
}
