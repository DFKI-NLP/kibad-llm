/**
 * Generic bar/error plot entry and tab-map helpers.
 */

import {
  buildGroupedLegendModel,
  getBarColor,
  getLegendItemsForPoints,
  scheduleAdaptiveSvgFit,
  styleErrorBarSegment,
} from "./shared.js";
import { createPlotLegendElement } from "./legend.js";

export {
  buildBarsTabMap,
  buildErrorsTabMap,
  buildPlotEntries,
} from "./shared.js";

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
