/**
 * Generic bar/error plot entry and tab-map helpers.
 */

import { meanAndStd, normalizeValue } from "../utils/values.js";
import {
  buildGroupedLegendModel,
  getGroupLabelForFields,
  getBarColor,
  getLegendItemsForPoints,
  getMetricPreparedDataContainer,
  getPlotDisplayLabel,
  scheduleAdaptiveSvgFit,
  styleErrorBarSegment,
} from "./shared.js";
import { createPlotLegendElement } from "./legend.js";

/**
 * Resolves the display title for a metric plot entry.
 *
 * @param {object} plotEntry - Plot entry created by buildPlotEntries.
 * @param {string} metricType - Metric type for special title handling.
 * @param {object} [options] - Label and tab display options.
 * @returns {string} Display title label.
 */
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

/**
 * Recursively collects numeric leaf paths from a metric data object.
 *
 * @param {*} value - Metric data value to inspect.
 * @param {Array<string>} [parts] - Current path parts during recursion.
 * @param {Map<string, Array<string>>} [out] - Accumulator keyed by encoded paths.
 * @returns {Map<string, Array<string>>} Numeric metric leaf paths.
 */
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

/**
 * Encodes metric path parts into the stable key used by prepared numeric data.
 *
 * @param {Array<string>} parts - Metric path parts.
 * @returns {string} Encoded metric path key.
 */
export function getNumericMetricPathKey(parts) {
  return (parts || []).join("|#|");
}

/**
 * Recursively collects numeric metric paths and values for one evaluation.
 *
 * @param {*} value - Metric data value to inspect.
 * @param {Array<string>} [parts] - Current path parts during recursion.
 * @param {Map<string, object>} [metricPaths] - Path accumulator keyed by encoded path.
 * @param {Map<string, number>} [values] - Numeric value accumulator keyed by encoded path.
 * @returns {{metricPaths: Map<string, object>, values: Map<string, number>}} Prepared numeric data.
 */
function collectNumericMetricLeafData(value, parts = [], metricPaths = new Map(), values = new Map()) {
  if (!value || typeof value !== "object") {
    return { metricPaths, values };
  }
  for (const [key, child] of Object.entries(value)) {
    const pathParts = [...parts, key];
    if (typeof child === "number" && Number.isFinite(child)) {
      const pathKey = getNumericMetricPathKey(pathParts);
      metricPaths.set(pathKey, { key: pathKey, parts: pathParts, label: pathParts.join(".") });
      values.set(pathKey, child);
      continue;
    }
    if (child && typeof child === "object" && !Array.isArray(child)) {
      collectNumericMetricLeafData(child, pathParts, metricPaths, values);
    }
  }
  return { metricPaths, values };
}

/**
 * Lazily prepares one evaluation's numeric metric data for bar/error plots.
 *
 * The prepared shape stores metric path metadata and flat per-path numeric
 * values. `buildPlotEntries()` uses the same prepared values for aggregation
 * and exposes them as point samples for future `Download data` support.
 *
 * @param {object} evaluation - Raw evaluation record with metric data.
 * @returns {{metricPaths: Map<string, object>, values: Map<string, number>}} Prepared per-evaluation numeric data.
 */
export function prepareNumericMetricEvaluationData(evaluation) {
  const cache = getMetricPreparedDataContainer(evaluation);
  if (cache?.numericMetrics) {
    return cache.numericMetrics;
  }

  const prepared = collectNumericMetricLeafData(evaluation?.data);
  if (cache) {
    cache.numericMetrics = prepared;
  }
  return prepared;
}

/**
 * Collects the union of numeric metric paths from prepared evaluation data.
 *
 * @param {Array<object>} evaluations - Evaluation records.
 * @returns {Array<object>} Sorted metric path records.
 */
export function collectPreparedNumericMetricPaths(evaluations) {
  const metricPaths = new Map();
  for (const evaluation of evaluations || []) {
    for (const [key, metricPath] of prepareNumericMetricEvaluationData(evaluation).metricPaths) {
      metricPaths.set(key, metricPath);
    }
  }
  return Array.from(metricPaths.values()).sort((a, b) => a.label.localeCompare(b.label));
}

/**
 * Splits a metric label into prefix and suffix at the final dot.
 *
 * @param {string} label - Metric label.
 * @returns {{prefix: string, suffix: string}} Split label components.
 */
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

/**
 * Converts metric paths and evaluation groups into plottable bar entries.
 *
 * @param {object} options - Plot entry construction inputs.
 * @returns {Array<object>} Plot entries with mean/std point data.
 */
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
    const metricPathKey = metricPath.key || getNumericMetricPathKey(metricPath.parts);
    const points = [];
    plotGroups.forEach((group, index) => {
      const samples = group.evaluations
        .map((evaluation) => {
          const value = prepareNumericMetricEvaluationData(evaluation).values.get(metricPathKey);
          if (!Number.isFinite(value)) {
            return null;
          }
          return {
            runDir: normalizeValue(evaluation?.runDir),
            metricLabel: metricPath.label,
            metricPath: metricPath.parts,
            value,
          };
        })
        .filter(Boolean);
      const values = samples.map((sample) => sample.value);
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
        samples,
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

/**
 * Groups metric plot entries into bar plot tabs.
 *
 * @param {Array<object>} plotEntries - Entries produced by buildPlotEntries.
 * @param {object} [options] - Tab grouping options.
 * @returns {Map<string, Array<object>>} Tab map keyed by prefix or suffix.
 */
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

/**
 * Splits error metric entries into total and details tabs.
 *
 * @param {Array<object>} plotEntries - Error metric plot entries.
 * @returns {Map<string, Array<object>>} Tab map for available error sections.
 */
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

/**
 * Creates an SVG bar plot with mean bars and standard-deviation error bars.
 *
 * @param {object} options - Rendering dependencies, points, and tooltip handlers.
 * @returns {SVGSVGElement} Rendered bar plot SVG.
 */
export function createBarPlotSvg({
  documentLike = globalThis.document,
  requestAnimationFrameLike = globalThis.requestAnimationFrame,
  points,
  showTooltip,
  moveTooltip,
  hideTooltip,
}) {
  const width = Math.max(720, points.length * 150);
  const height = 320;
  const margin = { top: 18, right: 20, bottom: 95, left: 60 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;
  const yMax = Math.max(
    0.05,
    ...points.map((point) => point.mean + point.std)
  );
  const step = chartWidth / Math.max(points.length, 1);
  const barWidth = Math.max(20, Math.min(60, step * 0.55));

  const svg = documentLike.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const contentGroup = documentLike.createElementNS("http://www.w3.org/2000/svg", "g");
  svg.appendChild(contentGroup);

  const yTicks = 5;
  for (let tick = 0; tick <= yTicks; tick += 1) {
    const value = (yMax * tick) / yTicks;
    const y = margin.top + chartHeight - (value / yMax) * chartHeight;
    const grid = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
    grid.setAttribute("x1", String(margin.left));
    grid.setAttribute("x2", String(width - margin.right));
    grid.setAttribute("y1", String(y));
    grid.setAttribute("y2", String(y));
    grid.setAttribute("stroke", "#64748b66");
    grid.setAttribute("stroke-width", "1");
    contentGroup.appendChild(grid);

    const label = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(margin.left - 8));
    label.setAttribute("y", String(y + 4));
    label.setAttribute("text-anchor", "end");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = value.toFixed(2);
    contentGroup.appendChild(label);
  }

  for (const [index, point] of points.entries()) {
    const centerX = margin.left + step * index + step / 2;
    const barHeight = (point.mean / yMax) * chartHeight;
    const barY = margin.top + chartHeight - barHeight;
    const barX = centerX - barWidth / 2;

    const rect = documentLike.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", String(barX));
    rect.setAttribute("y", String(barY));
    rect.setAttribute("width", String(barWidth));
    rect.setAttribute("height", String(Math.max(0, barHeight)));
    rect.setAttribute("fill", "#60a5fa");
    rect.style.cursor = "crosshair";
    rect.addEventListener("mouseover", (event) => {
      showTooltip(event, [
        point.label,
        `mean: ${Number(point.mean).toFixed(4)}`,
        `std:  ${Number(point.std).toFixed(4)}`,
      ]);
    });
    rect.addEventListener("mousemove", moveTooltip);
    rect.addEventListener("mouseout", hideTooltip);
    contentGroup.appendChild(rect);

    const errTop = margin.top + chartHeight - ((point.mean + point.std) / yMax) * chartHeight;
    const errBottom = margin.top + chartHeight - ((point.mean - point.std) / yMax) * chartHeight;
    const errorLine = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
    errorLine.setAttribute("x1", String(centerX));
    errorLine.setAttribute("x2", String(centerX));
    errorLine.setAttribute("y1", String(errTop));
    errorLine.setAttribute("y2", String(errBottom));
    styleErrorBarSegment(errorLine);
    errorLine.setAttribute("stroke-width", "2");
    contentGroup.appendChild(errorLine);

    const capTop = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
    capTop.setAttribute("x1", String(centerX - 6));
    capTop.setAttribute("x2", String(centerX + 6));
    capTop.setAttribute("y1", String(errTop));
    capTop.setAttribute("y2", String(errTop));
    styleErrorBarSegment(capTop);
    capTop.setAttribute("stroke-width", "2");
    contentGroup.appendChild(capTop);

    const capBottom = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
    capBottom.setAttribute("x1", String(centerX - 6));
    capBottom.setAttribute("x2", String(centerX + 6));
    capBottom.setAttribute("y1", String(errBottom));
    capBottom.setAttribute("y2", String(errBottom));
    styleErrorBarSegment(capBottom);
    capBottom.setAttribute("stroke-width", "2");
    contentGroup.appendChild(capBottom);

    const xLabel = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    xLabel.setAttribute("x", String(centerX));
    xLabel.setAttribute("y", String(height - margin.bottom + 16));
    xLabel.setAttribute("transform", `rotate(-28 ${centerX} ${height - margin.bottom + 16})`);
    xLabel.setAttribute("text-anchor", "end");
    xLabel.setAttribute("fill", "currentColor");
    xLabel.setAttribute("font-size", "11");
    xLabel.textContent = point.displayLabel;
    contentGroup.appendChild(xLabel);
  }

  scheduleAdaptiveSvgFit({ documentLike, requestAnimationFrameLike, svg, contentGroup, minWidth: width, minHeight: height });
  return svg;
}

/**
 * Creates an SVG grouped bar plot with one bar per category/series pair.
 *
 * @param {object} options - Rendering dependencies, points, legend model, and tooltip handlers.
 * @returns {SVGSVGElement} Rendered grouped bar plot SVG.
 */
export function createGroupedBarPlotSvg({
  documentLike = globalThis.document,
  requestAnimationFrameLike = globalThis.requestAnimationFrame,
  points,
  legendModel = null,
  showTooltip,
  moveTooltip,
  hideTooltip,
}) {
  const categoryOrder = [];
  const categorySet = new Set();
  const categoryDisplayMap = new Map();
  const valueMap = new Map();

  for (const point of points) {
    if (!categorySet.has(point.category)) {
      categorySet.add(point.category);
      categoryOrder.push(point.category);
    }
    if (!categoryDisplayMap.has(point.category)) {
      categoryDisplayMap.set(point.category, point.displayCategory);
    }
    valueMap.set(`${point.category}|#|${point.series}`, point);
  }

  const localSeriesOrder = [];
  const localSeriesSet = new Set();
  for (const point of points) {
    if (!localSeriesSet.has(point.series)) {
      localSeriesSet.add(point.series);
      localSeriesOrder.push(point.series);
    }
  }

  const seriesOrder = legendModel?.seriesOrder?.length ? legendModel.seriesOrder : localSeriesOrder;

  const seriesCount = Math.max(1, seriesOrder.length);
  const width = Math.max(760, categoryOrder.length * (120 + seriesCount * 26));
  const height = 340;
  const margin = { top: 18, right: 20, bottom: 95, left: 60 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;
  const yMax = Math.max(
    0.05,
    ...points.map((point) => point.mean + point.std)
  );
  const categoryStep = chartWidth / Math.max(categoryOrder.length, 1);
  const categoryWidth = categoryStep * 0.82;
  const barGap = 4;
  const barWidth = Math.max(
    10,
    Math.min(26, (categoryWidth - barGap * Math.max(0, seriesCount - 1)) / seriesCount)
  );
  const groupPixelWidth = barWidth * seriesCount + barGap * Math.max(0, seriesCount - 1);

  const svg = documentLike.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const contentGroup = documentLike.createElementNS("http://www.w3.org/2000/svg", "g");
  svg.appendChild(contentGroup);

  const yTicks = 5;
  for (let tick = 0; tick <= yTicks; tick += 1) {
    const value = (yMax * tick) / yTicks;
    const y = margin.top + chartHeight - (value / yMax) * chartHeight;
    const grid = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
    grid.setAttribute("x1", String(margin.left));
    grid.setAttribute("x2", String(width - margin.right));
    grid.setAttribute("y1", String(y));
    grid.setAttribute("y2", String(y));
    grid.setAttribute("stroke", "#64748b66");
    grid.setAttribute("stroke-width", "1");
    contentGroup.appendChild(grid);

    const label = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(margin.left - 8));
    label.setAttribute("y", String(y + 4));
    label.setAttribute("text-anchor", "end");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = value.toFixed(2);
    contentGroup.appendChild(label);
  }

  for (const [categoryIndex, category] of categoryOrder.entries()) {
    const centerX = margin.left + categoryStep * categoryIndex + categoryStep / 2;
    const groupStartX = centerX - groupPixelWidth / 2;

    for (const [seriesIndex, series] of seriesOrder.entries()) {
      const point = valueMap.get(`${category}|#|${series}`);
      if (!point) {
        continue;
      }
      const barHeight = (point.mean / yMax) * chartHeight;
      const barY = margin.top + chartHeight - barHeight;
      const barX = groupStartX + seriesIndex * (barWidth + barGap);
      const color = legendModel?.colorBySeries?.get(series) || getBarColor(seriesIndex);

      const rect = documentLike.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", String(barX));
      rect.setAttribute("y", String(barY));
      rect.setAttribute("width", String(barWidth));
      rect.setAttribute("height", String(Math.max(0, barHeight)));
      rect.setAttribute("fill", color);
      rect.style.cursor = "crosshair";
      rect.addEventListener("mouseover", (event) => {
        const tooltipLines = [category];
        if (seriesOrder.length > 1) {
          tooltipLines.push(`series: ${point.displaySeries || legendModel?.displayBySeries?.get(series) || series}`);
        }
        tooltipLines.push(
          `mean: ${Number(point.mean).toFixed(4)}`,
          `std:  ${Number(point.std).toFixed(4)}`
        );
        showTooltip(event, tooltipLines);
      });
      rect.addEventListener("mousemove", moveTooltip);
      rect.addEventListener("mouseout", hideTooltip);
      contentGroup.appendChild(rect);

      const errTop = margin.top + chartHeight - ((point.mean + point.std) / yMax) * chartHeight;
      const errBottom = margin.top + chartHeight - ((point.mean - point.std) / yMax) * chartHeight;
      const centerBarX = barX + barWidth / 2;

      const errorLine = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
      errorLine.setAttribute("x1", String(centerBarX));
      errorLine.setAttribute("x2", String(centerBarX));
      errorLine.setAttribute("y1", String(errTop));
      errorLine.setAttribute("y2", String(errBottom));
      styleErrorBarSegment(errorLine);
      errorLine.setAttribute("stroke-width", "2");
      contentGroup.appendChild(errorLine);

      const capTop = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
      capTop.setAttribute("x1", String(centerBarX - 5));
      capTop.setAttribute("x2", String(centerBarX + 5));
      capTop.setAttribute("y1", String(errTop));
      capTop.setAttribute("y2", String(errTop));
      styleErrorBarSegment(capTop);
      capTop.setAttribute("stroke-width", "2");
      contentGroup.appendChild(capTop);

      const capBottom = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
      capBottom.setAttribute("x1", String(centerBarX - 5));
      capBottom.setAttribute("x2", String(centerBarX + 5));
      capBottom.setAttribute("y1", String(errBottom));
      capBottom.setAttribute("y2", String(errBottom));
      styleErrorBarSegment(capBottom);
      capBottom.setAttribute("stroke-width", "2");
      contentGroup.appendChild(capBottom);
    }

    const xLabel = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    xLabel.setAttribute("x", String(centerX));
    xLabel.setAttribute("y", String(height - margin.bottom + 16));
    xLabel.setAttribute("transform", `rotate(-28 ${centerX} ${height - margin.bottom + 16})`);
    xLabel.setAttribute("text-anchor", "end");
    xLabel.setAttribute("fill", "currentColor");
    xLabel.setAttribute("font-size", "11");
    xLabel.textContent = categoryDisplayMap.get(category) || category;
    contentGroup.appendChild(xLabel);
  }

  scheduleAdaptiveSvgFit({ documentLike, requestAnimationFrameLike, svg, contentGroup, minWidth: width, minHeight: height });
  return svg;
}

/**
 * Renders plot tab buttons, optional legends, and the active plot grid.
 *
 * @param {object} options - Current tab state, plot data, DOM nodes, and renderer callbacks.
 * @returns {{activeEvalPlotTab: string, activePlotLegendItems: Array<object>}} Updated active tab and shared legend items.
 */
export function renderPlotTabsAndGrid({
  documentLike = globalThis.document,
  tabMap,
  activeExperiment,
  groupBarFields,
  metricType,
  activeEvalPlotTab,
  plotShowLegendOnce,
  plotShowLegendOnceRow,
  evalPlotTabs,
  evalPlotContent,
  buildCountTabButtonModels,
  renderTabButtons,
  resolveActiveTabValue,
  getPlotTitleLabel,
  displayPlotGroupFieldName,
  createBarSvg = (points) => createBarPlotSvg({ documentLike, points }),
  createGroupedBarSvg = (points, legendModel) => createGroupedBarPlotSvg({ documentLike, points, legendModel }),
  createLegendElement = createPlotLegendElement,
  onActiveTabChange,
}) {
  const tabPriority = ["total", "details"];
  const sortedTabKeys = Array.from(tabMap.keys()).sort((a, b) => {
    const pa = tabPriority.indexOf(a);
    const pb = tabPriority.indexOf(b);
    if (pa !== -1 && pb !== -1) return pa - pb;
    if (pa !== -1) return -1;
    if (pb !== -1) return 1;
    return a.localeCompare(b);
  });
  const nextActiveTab = resolveActiveTabValue(activeEvalPlotTab, sortedTabKeys);
  renderTabButtons({
    documentLike,
    containerElement: evalPlotTabs,
    tabModels: buildCountTabButtonModels(sortedTabKeys, {
      activeValue: nextActiveTab,
      getLabelText: (key) => key,
      getCount: (key) => tabMap.get(key).length,
      getTitle: (key) => key,
    }),
    onSelect: (key) => onActiveTabChange(key),
  });

  const activeEntries = tabMap.get(nextActiveTab) || [];
  const groupedLegendModel = groupBarFields.length
    ? buildGroupedLegendModel(activeEntries)
    : null;
  evalPlotContent.innerHTML = "";

  if (plotShowLegendOnceRow) {
    plotShowLegendOnceRow.style.display = groupedLegendModel?.items.length > 1 ? "" : "none";
  }
  const hasSharedLegend = Boolean(groupedLegendModel && groupedLegendModel.items.length > 1);
  if (hasSharedLegend && plotShowLegendOnce) {
    evalPlotContent.appendChild(createLegendElement({
      documentLike,
      legendItems: groupedLegendModel.items,
    }));
  }

  const grid = documentLike.createElement("div");
  grid.className = "plot-grid";
  for (const entry of activeEntries) {
    const card = documentLike.createElement("section");
    card.className = "plot-card";
    const title = documentLike.createElement("p");
    title.className = "plot-title";
    const groupedByText = groupBarFields.length
      ? ` | grouped by: ${groupBarFields.map((field) => displayPlotGroupFieldName(field)).join(", ")}`
      : "";
    title.textContent = `${getPlotTitleLabel(entry, metricType)} (mean ± std)${groupedByText}`;
    card.appendChild(title);
    if (groupBarFields.length) {
      const plotLegendItems = getLegendItemsForPoints(entry.points, groupedLegendModel);
      if (plotLegendItems.length > 1 && !plotShowLegendOnce) {
        card.appendChild(createLegendElement({
          documentLike,
          legendItems: plotLegendItems,
        }));
      }
      card.appendChild(createGroupedBarSvg(entry.points, groupedLegendModel));
    } else {
      card.appendChild(createBarSvg(entry.points));
    }
    grid.appendChild(card);
  }

  if (!grid.childElementCount) {
    const msg = documentLike.createElement("p");
    msg.className = "plot-empty";
    msg.textContent = "No plottable metric values found for the active tab.";
    evalPlotContent.appendChild(msg);
  } else {
    evalPlotContent.appendChild(grid);
  }

  return {
    activeEvalPlotTab: nextActiveTab,
    activePlotLegendItems: hasSharedLegend ? groupedLegendModel.items : [],
  };
}
