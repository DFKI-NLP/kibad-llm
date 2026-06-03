/**
 * Grouped-plot legend model helpers.
 */

export {
  buildGroupedLegendModel,
  getLegendItemsForPoints,
} from "./shared.js";

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
