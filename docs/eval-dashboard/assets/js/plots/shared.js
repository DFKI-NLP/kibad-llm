/**
 * Shared DOM-free plot helpers for the eval dashboard.
 */

import { getValueAtPath } from "../utils/flatten.js";
import { splitLabelByLastDot } from "../utils/text.js";
import { meanAndStd, normalizeValue } from "../utils/values.js";

export const TP_FP_FN_KEYS = ["tp", "fp", "fn"];
export const plotSortCollator = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
});

export function getPlotDisplayLabel(label, { shortenLabels = false } = {}) {
  const text = normalizeValue(label);
  return shortenLabels ? splitLabelByLastDot(text) : text;
}

export function getPlotTitleLabel(plotEntry, metricType, { shortenLabels = false, plotTabsBy = "prefix" } = {}) {
  if (
    metricType === "F1MicroMultipleFieldsMetric" &&
    shortenLabels &&
    plotTabsBy === "suffix"
  ) {
    return plotEntry.prefix === "(root)" ? plotEntry.metricLabel : plotEntry.prefix;
  }
  return getPlotDisplayLabel(plotEntry.metricLabel, { shortenLabels });
}

export function getBarColor(index) {
  const palette = [
    "#60a5fa",
    "#f97316",
    "#22c55e",
    "#a78bfa",
    "#f43f5e",
    "#14b8a6",
    "#eab308",
    "#8b5cf6",
    "#06b6d4",
    "#ef4444",
  ];
  return palette[index % palette.length];
}

export function buildGroupedLegendModel(entries) {
  const seriesOrder = [];
  const seenSeries = new Set();
  const displayBySeries = new Map();

  for (const entry of entries) {
    for (const point of entry.points || []) {
      if (!seenSeries.has(point.series)) {
        seenSeries.add(point.series);
        seriesOrder.push(point.series);
      }
      if (!displayBySeries.has(point.series)) {
        displayBySeries.set(point.series, point.displaySeries || point.series);
      }
    }
  }

  const colorBySeries = new Map();
  const items = seriesOrder.map((series, index) => {
    const color = getBarColor(index);
    const label = displayBySeries.get(series) || series;
    colorBySeries.set(series, color);
    return { series, label, color };
  });

  return { seriesOrder, displayBySeries, colorBySeries, items };
}

export function getLegendItemsForPoints(points, legendModel) {
  if (!legendModel) {
    return [];
  }
  const seriesInPoints = new Set(points.map((point) => point.series));
  return legendModel.items.filter((item) => seriesInPoints.has(item.series));
}

export function getVaryingFields(groups, fields) {
  if (!fields.length || groups.length <= 1) {
    return [];
  }
  return fields.filter((field) => {
    const values = new Set(groups.map((group) => normalizeValue(group.values?.[field])));
    return values.size > 1;
  });
}

export function getGroupLabelForFields(
  group,
  labelFields,
  fallback,
  fieldNameFormatter = (field) => field
) {
  if (labelFields.length === 0) {
    return fallback;
  }
  return labelFields
    .map((field) => `${fieldNameFormatter(field)}=${normalizeValue(group.values[field])}`)
    .join(" | ");
}

export function collectNumericMetricLeafPaths(value, parts = [], out = new Map()) {
  if (!value || typeof value !== "object") {
    return out;
  }
  for (const [key, child] of Object.entries(value)) {
    const pathParts = [...parts, key];
    if (typeof child === "number" && Number.isFinite(child)) {
      out.set(pathParts.join("|#|"), pathParts);
      continue;
    }
    if (child && typeof child === "object" && !Array.isArray(child)) {
      collectNumericMetricLeafPaths(child, pathParts, out);
    }
  }
  return out;
}

export function splitMetricLabelAtLastDot(label) {
  const lastDotIndex = label.lastIndexOf(".");
  if (lastDotIndex === -1) {
    return { prefix: "(root)", suffix: label };
  }
  return {
    prefix: label.slice(0, lastDotIndex),
    suffix: label.slice(lastDotIndex + 1),
  };
}

export function buildPlotEntries({
  metricPaths,
  plotGroups,
  groupBarFields,
  categoryFields,
  getGroupLabel = getGroupLabelForFields,
  displayGroupFieldName = (field) => field,
}) {
  const entries = [];
  for (const metricPath of metricPaths) {
    const points = [];
    plotGroups.forEach((group, index) => {
      const values = group.evaluations
        .map((evaluation) => Number(getValueAtPath(evaluation.data, metricPath.parts)))
        .filter((value) => Number.isFinite(value));
      const stats = meanAndStd(values);
      if (!stats) {
        return;
      }
      const categoryLabel = groupBarFields.length
        ? getGroupLabel(group, categoryFields, "all")
        : getGroupLabel(group, categoryFields, `group ${index + 1}`);
      const displayCategoryLabel = groupBarFields.length
        ? getGroupLabel(group, categoryFields, "all", displayGroupFieldName)
        : getGroupLabel(group, categoryFields, `group ${index + 1}`, displayGroupFieldName);
      const seriesLabel = groupBarFields.length
        ? getGroupLabel(group, groupBarFields, "series")
        : "__single__";
      const displaySeriesLabel = groupBarFields.length
        ? getGroupLabel(group, groupBarFields, "series", displayGroupFieldName)
        : "__single__";
      points.push({
        label: categoryLabel,
        displayLabel: displayCategoryLabel,
        category: categoryLabel,
        displayCategory: displayCategoryLabel,
        series: seriesLabel,
        displaySeries: displaySeriesLabel,
        mean: stats.mean,
        std: stats.std,
      });
    });
    if (!points.length) {
      continue;
    }
    const split = splitMetricLabelAtLastDot(metricPath.label);
    entries.push({ metricLabel: metricPath.label, parts: metricPath.parts, points, ...split });
  }
  return entries;
}

export function buildBarsTabMap(plotEntries, { plotTabsBy = "prefix" } = {}) {
  const tabMap = new Map();
  for (const entry of plotEntries) {
    const tabKey = plotTabsBy === "suffix" ? entry.suffix : entry.prefix;
    if (!tabMap.has(tabKey)) {
      tabMap.set(tabKey, []);
    }
    tabMap.get(tabKey).push(entry);
  }
  return tabMap;
}

export function buildErrorsTabMap(plotEntries) {
  const totalKeys = new Set(["with_error", "no_error"]);
  const total = plotEntries.filter((entry) => totalKeys.has(entry.parts[0]));
  const details = plotEntries.filter((entry) => !totalKeys.has(entry.parts[0]));
  const tabMap = new Map();
  if (total.length) {
    tabMap.set("total", total);
  }
  if (details.length) {
    tabMap.set("details", details);
  }
  return tabMap;
}
