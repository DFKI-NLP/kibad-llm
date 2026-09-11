/**
 * Legend helpers for numeric and matrix plots.
 *
 * Grouped numeric plots need stable series models for shared/per-card legends,
 * while TP/FP/FN plots reuse the same DOM renderer with fixed legend items.
 */

/**
 * Selects a deterministic bar color from the dashboard palette.
 *
 * Grouped bar plots assign colors by stable series order. Keeping the palette
 * with legend modeling keeps rendered bars, per-card legends, and shared
 * legends visually aligned.
 *
 * @param {number} index - Zero-based series index.
 * @returns {string} Hex color value.
 */
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

/**
 * Builds a shared legend model for grouped bar plot entries.
 *
 * Grouped plots may render one legend for the whole tab or one legend per card.
 * This model captures stable series order, labels, and colors once so both
 * render paths agree.
 *
 * @param {Array<object>} entries - Plot entries containing grouped points.
 * @returns {object} Series order, display labels, colors, and legend items.
 */
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

/**
 * Filters a legend model down to the series present in a point collection.
 *
 * Per-card legends should not show series that are absent from that specific
 * card, even when a shared tab-level legend contains more series.
 *
 * @param {Array<object>} points - Points rendered in a plot.
 * @param {?object} legendModel - Shared legend model.
 * @returns {Array<object>} Legend items used by the points.
 */
export function getLegendItemsForPoints(points, legendModel) {
  if (!legendModel) {
    return [];
  }
  const seriesInPoints = new Set(points.map((point) => point.series));
  return legendModel.items.filter((item) => seriesInPoints.has(item.series));
}

/**
 * Builds the DOM element used to display plot series legend items.
 *
 * @param {object} options - Legend rendering options.
 * @returns {HTMLElement} A legend container with swatches and labels.
 */
export function createPlotLegendElement({ documentLike = globalThis.document, legendItems }) {
  const legend = documentLike.createElement("div");
  legend.className = "plot-legend";
  legendItems.forEach((item) => {
    const legendItem = documentLike.createElement("span");
    legendItem.className = "plot-legend-item";
    const swatch = documentLike.createElement("span");
    swatch.className = "plot-legend-swatch";
    swatch.style.backgroundColor = item.color;
    const text = documentLike.createElement("span");
    text.textContent = item.label;
    legendItem.appendChild(swatch);
    legendItem.appendChild(text);
    legend.appendChild(legendItem);
  });
  return legend;
}
