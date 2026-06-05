/**
 * Shared sparse-matrix helpers for matrix-like plot data.
 */

import { getGroupLabelForFields, getPlotDisplayLabel } from "./shared.js";

/**
 * Builds the stable sparse-cell key used by matrix aggregation maps.
 *
 * Confusion and TP/FP/FN matrices both store sparse cells as `Map` entries
 * keyed by row and column labels. Keeping the delimiter in one place avoids
 * drifting key formats between preparation, aggregation, rendering, and
 * download serialization.
 *
 * @param {string} row - Matrix row label.
 * @param {string} col - Matrix column label.
 * @returns {string} Stable sparse-cell key.
 */
export function getMatrixCellKey(row, col) {
  return `${row}|#|${col}`;
}

/**
 * Builds the JSON-safe matrix plotting data used by downloads.
 *
 * Confusion and TP/FP/FN rendering both consume aggregation input objects with
 * the same sparse matrix structure. This helper preserves that pre-aggregation
 * plotting shape and only replaces `Map` cells with JSON-safe entry arrays.
 *
 * @param {object} aggregationInput - Matrix aggregation input.
 * @returns {object} JSON-safe matrix plotting data.
 */
export function buildJsonSafeMatrixPlottingData(aggregationInput) {
  return {
    rows: aggregationInput?.rows || [],
    cols: aggregationInput?.cols || [],
    evaluationCells: (aggregationInput?.evaluationCells || []).map((cellMap) => {
      // Matrix plotting data uses sparse Maps; JSON needs stable array entries.
      return Array.from(cellMap.entries());
    }),
  };
}

/**
 * Builds matrix plot tabs grouped by metric field or plot group.
 *
 * Confusion and TP/FP/FN plots expose the same tab shape after their
 * evaluations are wrapped as metric-field collections. Centralizing that shape
 * keeps dashboard rendering and download selection aligned across matrix-like
 * metric families.
 *
 * @param {object} options - Plot groups, tab mode, collection wrapping, and label helpers.
 * @returns {Map<string, object>} Tab map with labels and plot definitions.
 */
export function buildMatrixTabMap({
  plotGroups,
  labelFields,
  evalTabState,
  matrixTabsBy,
  getEvaluationEffectiveValue,
  displayPlotGroupFieldName,
  shortenLabels = false,
  getCollectionViews,
  filterEvaluations = (evaluations) => evaluations,
  compareFieldLabels = (a, b) => a.localeCompare(b),
}) {
  const tabMap = new Map();
  const collectionViewOptions = { evalTabState, getEvaluationEffectiveValue };
  const groupEntries = (plotGroups || [])
    .map((group, index) => ({
      key: `group|#|${group.groupId}`,
      label: getGroupLabelForFields(
        group,
        labelFields,
        `group ${index + 1}`,
        displayPlotGroupFieldName
      ),
      collections: getCollectionViews(
        filterEvaluations(group.evaluations || []),
        collectionViewOptions
      ),
    }))
    .filter((entry) => entry.collections.length > 0);

  if (matrixTabsBy === "metric_field") {
    for (const groupEntry of groupEntries) {
      const byField = new Map();
      for (const collection of groupEntry.collections) {
        for (const fieldLabel of collection.fields.keys()) {
          if (!tabMap.has(fieldLabel)) {
            tabMap.set(fieldLabel, {
              label: getPlotDisplayLabel(fieldLabel, { shortenLabels }),
              plots: [],
            });
          }
          if (!byField.has(fieldLabel)) {
            byField.set(fieldLabel, []);
          }
          byField.get(fieldLabel).push(collection);
        }
      }
      for (const [fieldKey, collectionsForFieldAndGroup] of byField.entries()) {
        const tab = tabMap.get(fieldKey);
        if (!tab || collectionsForFieldAndGroup.length === 0) {
          continue;
        }
        tab.plots.push({
          label: groupEntry.label,
          fieldLabel: fieldKey,
          collections: collectionsForFieldAndGroup,
        });
      }
    }
    return tabMap;
  }

  for (const groupEntry of groupEntries) {
    const byField = new Map();
    for (const collection of groupEntry.collections) {
      for (const fieldLabel of collection.fields.keys()) {
        if (!byField.has(fieldLabel)) {
          byField.set(fieldLabel, []);
        }
        byField.get(fieldLabel).push(collection);
      }
    }
    const plots = Array.from(byField.entries())
      .sort(([a], [b]) => compareFieldLabels(a, b))
      .map(([fieldLabel, collections]) => ({
        label: fieldLabel,
        fieldLabel,
        collections,
      }));
    tabMap.set(groupEntry.key, { label: groupEntry.label, plots });
  }

  return tabMap;
}
