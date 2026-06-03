/**
 * Grouped-plot legend model helpers.
 */

export {
  buildGroupedLegendModel,
  getLegendItemsForPoints,
} from "./shared.js";

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
