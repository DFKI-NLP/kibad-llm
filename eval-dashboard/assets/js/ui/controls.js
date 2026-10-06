/**
 * Shared options-panel and control-list helpers for the eval dashboard.
 */

import { normalizeSortConfig } from "../utils/sort.js";
import { setPanelVisibility } from "./dom.js";
import { formatSortLabel as formatSharedSortLabel } from "./table-shared.js";

/**
 * Normalize collection-style metric names down to the plot-control visualization family.
 *
 * @param {string | null | undefined} metricType - Raw metric type from evaluation context.
 * @returns {string | null | undefined} Visualization-oriented metric family.
 */
function getVisualizationMetricType(metricType) {
  if (metricType === "ConfusionMatrixCollection") {
    return "ConfusionMatrix";
  }
  if (metricType === "TpFpFnCollectorCollection") {
    return "TpFpFnCollector";
  }
  return metricType;
}

/**
 * Build labeled option objects from one ordered column list.
 *
 * @param {Iterable<string>} columns - Columns to expose as options.
 * @param {(column: string) => string} [getLabel] - Display-label formatter.
 * @returns {Array<{value: string, label: string}>} Plain option models.
 */
export function buildColumnOptions(columns, getLabel = (column) => String(column)) {
  return Array.from(columns || []).map((column) => ({ value: column, label: getLabel(column) }));
}

/**
 * Return the available columns that are not currently active.
 *
 * @param {Iterable<string>} availableColumns - All available columns.
 * @param {Iterable<string>} activeColumns - Currently active columns.
 * @returns {string[]} Columns that should become active in a toggle-only action.
 */
export function getToggleOnlyColumns(availableColumns, activeColumns) {
  const activeSet = new Set(activeColumns || []);
  return Array.from(availableColumns || []).filter((column) => !activeSet.has(column));
}

/**
 * Build plain control models for missing-value default inputs.
 *
 * @param {object} options - Default-control callbacks.
 * @param {Iterable<string>} options.columns - Columns that currently need defaults.
 * @param {(column: string) => string} options.getLabel - Label formatter.
 * @param {(column: string) => string} options.getValue - Current configured default lookup.
 * @param {(column: string) => string[]} options.getSuggestions - Suggestion lookup.
 * @param {(column: string) => number} options.getMissingCount - Missing-value count lookup.
 * @returns {Array<{column: string, label: string, value: string, suggestions: string[], missingCount: number}>} Plain control models.
 */
export function buildMissingDefaultControlModels({
  columns,
  getLabel,
  getValue,
  getSuggestions,
  getMissingCount,
}) {
  return Array.from(columns || []).map((column) => ({
    column,
    label: getLabel(column),
    value: getValue(column),
    suggestions: getSuggestions(column),
    missingCount: getMissingCount(column),
  }));
}

/**
 * Build both checkbox options and missing-default control models for one options panel.
 *
 * @param {object} options - Checkbox/default model composition callbacks.
 * @param {Iterable<string>} options.checkboxColumns - Columns exposed as checkbox toggles.
 * @param {(column: string) => string} [options.getCheckboxLabel] - Checkbox label formatter.
 * @param {Iterable<string>} options.defaultColumns - Columns needing missing-value defaults.
 * @param {(column: string) => string} options.getDefaultLabel - Default-control label formatter.
 * @param {(column: string) => string} options.getDefaultValue - Current configured default lookup.
 * @param {(column: string) => string[]} options.getDefaultSuggestions - Suggestion lookup.
 * @param {(column: string) => number} options.getDefaultMissingCount - Missing-value count lookup.
 * @returns {{checkboxOptions: Array<{value: string, label: string}>, defaultControlModels: Array<{column: string, label: string, value: string, suggestions: string[], missingCount: number}>}} Plain options-panel models.
 */
export function buildOptionsPanelModels({
  checkboxColumns,
  getCheckboxLabel = (column) => String(column),
  defaultColumns,
  getDefaultLabel,
  getDefaultValue,
  getDefaultSuggestions,
  getDefaultMissingCount,
}) {
  return {
    checkboxOptions: buildColumnOptions(checkboxColumns, getCheckboxLabel),
    defaultControlModels: buildMissingDefaultControlModels({
      columns: defaultColumns,
      getLabel: getDefaultLabel,
      getValue: getDefaultValue,
      getSuggestions: getDefaultSuggestions,
      getMissingCount: getDefaultMissingCount,
    }),
  };
}

/**
 * Render the enabled/disabled state of the three group-by action buttons.
 *
 * @param {{allButton: HTMLButtonElement | null, toggleButton: HTMLButtonElement | null, noneButton: HTMLButtonElement | null}} buttonRefs - Group-by buttons.
 * @param {Iterable<string>} availableColumns - Columns currently available for grouping.
 * @returns {void}
 */
export function renderGroupByButtonState(buttonRefs, availableColumns) {
  const disabled = Array.from(availableColumns || []).length === 0;
  buttonRefs.allButton.disabled = disabled;
  buttonRefs.toggleButton.disabled = disabled;
  buttonRefs.noneButton.disabled = disabled;
}

/**
 * Create the shared per-column group-by toggle control used in table headers.
 *
 * @param {object} options - Group-by toggle render inputs.
 * @param {Document} [options.documentLike=globalThis.document] - Document-like element factory.
 * @param {boolean} [options.checked=false] - Whether the toggle starts checked.
 * @param {string} [options.title="Use this column for grouping"] - Tooltip for the wrapper.
 * @param {string | null} [options.ariaLabel=null] - Optional aria-label for the checkbox.
 * @param {(checked: boolean, event: Event) => void} options.onToggle - Change callback.
 * @returns {HTMLLabelElement} The configured group-by toggle wrapper.
 */
export function createGroupByToggleControl({
  documentLike = globalThis.document,
  checked = false,
  title = "Use this column for grouping",
  ariaLabel = null,
  onToggle,
}) {
  const toggle = documentLike.createElement("label");
  toggle.className = "group-toggle";
  toggle.title = title;
  const checkbox = documentLike.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = checked;
  if (ariaLabel) {
    checkbox.setAttribute("aria-label", ariaLabel);
  }
  checkbox.addEventListener("change", (event) => onToggle(checkbox.checked, event));
  toggle.appendChild(checkbox);
  return toggle;
}

/**
 * Normalize one sort config and render the current sort status UI.
 *
 * @param {object} options - Sort-status render inputs.
 * @param {HTMLElement | null} options.labelElement - Element receiving the formatted sort label.
 * @param {HTMLButtonElement | null} options.resetButton - Reset-sort button to enable or disable.
 * @param {Array<{column: string, direction: string}> | object | null} options.sortConfig - Current sort configuration.
 * @param {Iterable<string>} options.validColumns - Currently valid sort columns.
 * @param {(column: string) => string} options.displayColumnName - Formatter for data-column labels.
 * @returns {Array<{column: string, direction: string}>} The normalized sort config that was rendered.
 */
export function renderSortStatus({
  labelElement,
  resetButton,
  sortConfig,
  validColumns,
  displayColumnName,
}) {
  const normalizedSort = normalizeSortConfig(sortConfig, new Set(validColumns || []));
  if (labelElement) {
    labelElement.textContent = formatSharedSortLabel(normalizedSort, displayColumnName);
  }
  if (resetButton) {
    resetButton.disabled = normalizedSort.length === 0;
  }
  return normalizedSort;
}

/**
 * Render the dashboard's thin plot-control state without pulling plot aggregation into this module.
 *
 * @param {object} options - Plot-control refs plus the current control values.
 * @param {string | null | undefined} options.metricType - Active evaluation metric type.
 * @param {"prefix" | "suffix"} options.plotTabsBy - Current plot-tab grouping mode.
 * @param {"metric_field" | "prediction_group"} options.confusionTabsBy - Current confusion-tab grouping mode.
 * @param {boolean} options.plotShortenLabels - Whether plot labels are shortened.
 * @param {number} options.plotRoundingPrecision - Current rounding precision.
 * @param {number} options.plotConfusionMinLabelTotal - Current confusion label threshold.
 * @param {number} options.plotTpFpFnMinLabelTotal - Current TP/FP/FN label threshold.
 * @param {number} options.plotTpFpFnMinDocumentTotal - Current TP/FP/FN document threshold.
 * @param {boolean} options.plotShowLegendOnce - Whether legend de-duplication is enabled.
 * @param {boolean} options.exportOpaqueBackground - Whether exports should use an opaque background.
 * @param {HTMLElement | null} options.plotTabsByPrefixButton - Prefix-tab mode button.
 * @param {HTMLElement | null} options.plotTabsBySuffixButton - Suffix-tab mode button.
 * @param {HTMLElement | null} options.confusionTabsByMetricFieldButton - Metric-field confusion-tab mode button.
 * @param {HTMLElement | null} options.confusionTabsByPredictionGroupButton - Prediction-group confusion-tab mode button.
 * @param {HTMLInputElement | null} options.plotShortenLabelsInput - Shorten-labels checkbox.
 * @param {HTMLInputElement | null} options.plotRoundingPrecisionInput - Rounding-precision input.
 * @param {HTMLElement | null} options.plotConfusionMinLabelTotalRow - Confusion threshold row.
 * @param {HTMLInputElement | null} options.plotConfusionMinLabelTotalInput - Confusion threshold input.
 * @param {HTMLElement | null} options.plotTpFpFnMinLabelTotalRow - TP/FP/FN label-threshold row.
 * @param {HTMLInputElement | null} options.plotTpFpFnMinLabelTotalInput - TP/FP/FN label-threshold input.
 * @param {HTMLElement | null} options.plotTpFpFnMinDocumentTotalRow - TP/FP/FN document-threshold row.
 * @param {HTMLInputElement | null} options.plotTpFpFnMinDocumentTotalInput - TP/FP/FN document-threshold input.
 * @param {HTMLElement | null} options.plotTabsByRow - Prefix/suffix toggle row.
 * @param {HTMLElement | null} options.plotConfusionTabsByRow - Confusion-tab mode row.
 * @param {HTMLElement | null} options.plotGroupBarsRow - Grouped-bars options row.
 * @param {HTMLElement | null} options.plotShowLegendOnceRow - Legend-once row.
 * @param {HTMLInputElement | null} options.plotShowLegendOnceInput - Legend-once checkbox.
 * @param {HTMLInputElement | null} options.exportOpaqueBackgroundInput - Export-background checkbox.
 * @returns {void}
 */
export function renderPlotControls({
  metricType,
  plotTabsBy,
  confusionTabsBy,
  plotShortenLabels,
  plotRoundingPrecision,
  plotConfusionMinLabelTotal,
  plotTpFpFnMinLabelTotal,
  plotTpFpFnMinDocumentTotal,
  plotShowLegendOnce,
  exportOpaqueBackground,
  plotTabsByPrefixButton,
  plotTabsBySuffixButton,
  confusionTabsByMetricFieldButton,
  confusionTabsByPredictionGroupButton,
  plotShortenLabelsInput,
  plotRoundingPrecisionInput,
  plotConfusionMinLabelTotalRow,
  plotConfusionMinLabelTotalInput,
  plotTpFpFnMinLabelTotalRow,
  plotTpFpFnMinLabelTotalInput,
  plotTpFpFnMinDocumentTotalRow,
  plotTpFpFnMinDocumentTotalInput,
  plotTabsByRow,
  plotConfusionTabsByRow,
  plotGroupBarsRow,
  plotShowLegendOnceRow,
  plotShowLegendOnceInput,
  exportOpaqueBackgroundInput,
}) {
  const visualizationMetricType = getVisualizationMetricType(metricType);
  const isConfusionMatrixLike = visualizationMetricType === "ConfusionMatrix";
  const supportsConfusionStyleTabs =
    isConfusionMatrixLike || metricType === "TpFpFnCollector";
  const isTpFpFnCollector = metricType === "TpFpFnCollector";
  const isF1MicroMultipleFieldsMetric = metricType === "F1MicroMultipleFieldsMetric";
  const supportsGroupedBars =
    metricType === "ErrorCollector" || isF1MicroMultipleFieldsMetric;

  plotTabsByPrefixButton?.classList?.toggle?.("active", plotTabsBy === "prefix");
  plotTabsBySuffixButton?.classList?.toggle?.("active", plotTabsBy === "suffix");
  confusionTabsByMetricFieldButton?.classList?.toggle?.(
    "active",
    confusionTabsBy === "metric_field"
  );
  confusionTabsByPredictionGroupButton?.classList?.toggle?.(
    "active",
    confusionTabsBy === "prediction_group"
  );
  if (plotShortenLabelsInput) {
    plotShortenLabelsInput.checked = plotShortenLabels;
  }
  if (plotRoundingPrecisionInput) {
    plotRoundingPrecisionInput.value = String(plotRoundingPrecision);
  }
  if (plotConfusionMinLabelTotalInput) {
    plotConfusionMinLabelTotalInput.value = String(plotConfusionMinLabelTotal);
  }
  if (plotTpFpFnMinLabelTotalInput) {
    plotTpFpFnMinLabelTotalInput.value = String(plotTpFpFnMinLabelTotal);
  }
  if (plotTpFpFnMinDocumentTotalInput) {
    plotTpFpFnMinDocumentTotalInput.value = String(plotTpFpFnMinDocumentTotal);
  }
  if (plotShowLegendOnceInput) {
    plotShowLegendOnceInput.checked = plotShowLegendOnce;
  }
  if (exportOpaqueBackgroundInput) {
    exportOpaqueBackgroundInput.checked = exportOpaqueBackground;
  }

  setPanelVisibility(plotTabsByRow, isF1MicroMultipleFieldsMetric);
  setPanelVisibility(plotConfusionMinLabelTotalRow, isConfusionMatrixLike);
  setPanelVisibility(plotTpFpFnMinLabelTotalRow, isTpFpFnCollector);
  setPanelVisibility(plotTpFpFnMinDocumentTotalRow, isTpFpFnCollector);
  setPanelVisibility(plotConfusionTabsByRow, supportsConfusionStyleTabs);
  setPanelVisibility(plotGroupBarsRow, supportsGroupedBars);
  setPanelVisibility(plotShowLegendOnceRow, false);
}

/**
 * Render grouped-bar field toggle chips for the plot-control surface.
 *
 * @param {object} options - Plot group-bar chip render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {HTMLElement | null} options.listElement - Container receiving the chips.
 * @param {Iterable<string>} options.availableFields - Group-by fields that can be toggled.
 * @param {Iterable<string>} [options.checkedValues=[]] - Currently active grouped-bar fields.
 * @param {(field: string) => string} [options.getLabel] - Field-label formatter.
 * @param {(field: string, checked: boolean) => void} options.onToggle - Toggle callback.
 * @returns {void}
 */
export function renderPlotGroupBarChips({
  documentLike,
  listElement,
  availableFields,
  checkedValues = [],
  getLabel = (field) => String(field),
  onToggle,
}) {
  if (!listElement) {
    return;
  }
  listElement.innerHTML = "";
  const resolvedFields = Array.from(availableFields || []);
  if (!resolvedFields.length) {
    const noOptions = documentLike.createElement("span");
    noOptions.className = "hint";
    noOptions.textContent = "No varying group-by columns available.";
    listElement.appendChild(noOptions);
    return;
  }
  renderCheckboxOptionList({
    documentLike,
    listElement,
    options: buildColumnOptions(resolvedFields, getLabel),
    checkedValues,
    onToggle,
  });
}

/**
 * Render a checkbox list for truncate/group-like option controls.
 *
 * @param {object} options - Checkbox-list render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {HTMLElement | null} options.listElement - Container receiving option labels.
 * @param {Array<{value: string, label: string}>} options.options - Option models.
 * @param {Iterable<string>} [options.checkedValues=[]] - Currently checked values.
 * @param {(value: string, checked: boolean) => void} options.onToggle - Toggle callback.
 * @param {(option: {value: string, label: string}) => string | null} [options.getAriaLabel] - Optional checkbox aria-label formatter.
 * @returns {void}
 */
export function renderCheckboxOptionList(options) {
  const {
    documentLike: resolvedDocumentLike,
    listElement: resolvedListElement,
    options: resolvedOptions,
    checkedValues: resolvedCheckedValues = [],
    onToggle: resolvedOnToggle,
    getAriaLabel: resolvedGetAriaLabel = null,
  } = options;
  if (!resolvedListElement) {
    return;
  }
  resolvedListElement.innerHTML = "";
  const checkedSet =
    resolvedCheckedValues instanceof Set
      ? resolvedCheckedValues
      : new Set(resolvedCheckedValues || []);
  for (const option of resolvedOptions || []) {
    const wrapper = resolvedDocumentLike.createElement("label");
    wrapper.className = "truncate-item";
    const checkbox = resolvedDocumentLike.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = checkedSet.has(option.value);
    if (resolvedGetAriaLabel) {
      checkbox.setAttribute("aria-label", resolvedGetAriaLabel(option));
    }
    checkbox.addEventListener("change", () => resolvedOnToggle(option.value, checkbox.checked));
    const text = resolvedDocumentLike.createElement("span");
    text.textContent = option.label;
    wrapper.appendChild(checkbox);
    wrapper.appendChild(text);
    resolvedListElement.appendChild(wrapper);
  }
}

/**
 * Render missing-default controls and synchronize the panel visibility around them.
 *
 * @param {object} options - Default-control render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {HTMLElement | null} options.listElement - Container receiving the controls.
 * @param {HTMLElement | null} options.panelElement - Surrounding panel to show or hide.
 * @param {Array<{column: string, label: string, value: string, suggestions: string[], missingCount: number}>} options.controlModels - Plain control models.
 * @param {(column: string, nextValue: string) => void} options.onCommit - Commit callback.
 * @param {string} options.inputIdPrefix - Prefix for generated datalist ids.
 * @returns {void}
 */
export function renderMissingDefaultControls({
  documentLike,
  listElement,
  panelElement,
  controlModels,
  onCommit,
  inputIdPrefix,
}) {
  if (!listElement) {
    return;
  }
  listElement.innerHTML = "";
  setPanelVisibility(panelElement, (controlModels || []).length > 0);
  for (const controlModel of controlModels || []) {
    renderMissingDefaultControl({
      documentLike,
      listElement,
      controlModel,
      onCommit,
      inputIdPrefix,
    });
  }
}

/**
 * Render one options-panel surface consisting of checkbox toggles plus
 * missing-default controls.
 *
 * @param {object} options - Options-panel render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {HTMLElement | null} options.checkboxListElement - Container receiving checkbox options.
 * @param {Array<{value: string, label: string}>} options.checkboxOptions - Checkbox option models.
 * @param {Iterable<string>} [options.checkedValues=[]] - Currently checked checkbox values.
 * @param {(value: string, checked: boolean) => void} options.onCheckboxToggle - Checkbox toggle callback.
 * @param {(option: {value: string, label: string}) => string | null} [options.getCheckboxAriaLabel] - Optional checkbox aria-label formatter.
 * @param {HTMLElement | null} options.defaultsListElement - Container receiving missing-default controls.
 * @param {HTMLElement | null} options.defaultsPanelElement - Surrounding panel to show or hide.
 * @param {Array<{column: string, label: string, value: string, suggestions: string[], missingCount: number}>} options.defaultControlModels - Plain missing-default control models.
 * @param {(column: string, nextValue: string) => void} options.onDefaultCommit - Missing-default commit callback.
 * @param {string} options.inputIdPrefix - Prefix for generated missing-default datalist ids.
 * @returns {void}
 */
export function renderOptionsPanelControls({
  documentLike,
  checkboxListElement,
  checkboxOptions,
  checkedValues = [],
  onCheckboxToggle,
  getCheckboxAriaLabel = null,
  defaultsListElement,
  defaultsPanelElement,
  defaultControlModels,
  onDefaultCommit,
  inputIdPrefix,
}) {
  renderCheckboxOptionList({
    documentLike,
    listElement: checkboxListElement,
    options: checkboxOptions,
    checkedValues,
    onToggle: onCheckboxToggle,
    getAriaLabel: getCheckboxAriaLabel,
  });
  renderMissingDefaultControls({
    documentLike,
    listElement: defaultsListElement,
    panelElement: defaultsPanelElement,
    controlModels: defaultControlModels,
    onCommit: onDefaultCommit,
    inputIdPrefix,
  });
}

/**
 * Build and render one full options panel from column-level callbacks.
 *
 * @param {object} options - Options-panel composition and render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {HTMLElement | null} options.checkboxListElement - Container receiving checkbox options.
 * @param {Iterable<string>} options.checkboxColumns - Columns exposed as checkbox toggles.
 * @param {Iterable<string>} [options.checkedValues=[]] - Currently checked checkbox values.
 * @param {(value: string, checked: boolean) => void} options.onCheckboxToggle - Checkbox toggle callback.
 * @param {(column: string) => string} [options.getCheckboxLabel] - Checkbox label formatter.
 * @param {(option: {value: string, label: string}) => string | null} [options.getCheckboxAriaLabel] - Optional checkbox aria-label formatter.
 * @param {HTMLElement | null} options.defaultsListElement - Container receiving missing-default controls.
 * @param {HTMLElement | null} options.defaultsPanelElement - Surrounding panel to show or hide.
 * @param {Iterable<string>} options.defaultColumns - Columns needing missing-value defaults.
 * @param {(column: string) => string} options.getDefaultLabel - Missing-default label formatter.
 * @param {(column: string) => string} options.getDefaultValue - Current configured default lookup.
 * @param {(column: string) => string[]} options.getDefaultSuggestions - Suggestion lookup.
 * @param {(column: string) => number} options.getDefaultMissingCount - Missing-value count lookup.
 * @param {(column: string, nextValue: string) => void} options.onDefaultCommit - Missing-default commit callback.
 * @param {string} options.inputIdPrefix - Prefix for generated missing-default datalist ids.
 * @returns {{checkboxOptions: Array<{value: string, label: string}>, defaultControlModels: Array<{column: string, label: string, value: string, suggestions: string[], missingCount: number}>}} The rendered plain option models.
 */
export function renderOptionsPanel({
  documentLike,
  checkboxListElement,
  checkboxColumns,
  checkedValues = [],
  onCheckboxToggle,
  getCheckboxLabel = (column) => String(column),
  getCheckboxAriaLabel = null,
  defaultsListElement,
  defaultsPanelElement,
  defaultColumns,
  getDefaultLabel,
  getDefaultValue,
  getDefaultSuggestions,
  getDefaultMissingCount,
  onDefaultCommit,
  inputIdPrefix,
}) {
  const panelModels = buildOptionsPanelModels({
    checkboxColumns,
    getCheckboxLabel,
    defaultColumns,
    getDefaultLabel,
    getDefaultValue,
    getDefaultSuggestions,
    getDefaultMissingCount,
  });
  renderOptionsPanelControls({
    documentLike,
    checkboxListElement,
    checkboxOptions: panelModels.checkboxOptions,
    checkedValues,
    onCheckboxToggle,
    getCheckboxAriaLabel,
    defaultsListElement,
    defaultsPanelElement,
    defaultControlModels: panelModels.defaultControlModels,
    onDefaultCommit,
    inputIdPrefix,
  });
  return panelModels;
}

/**
 * Render one missing-default input row.
 *
 * @param {object} options - One control model and DOM targets.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {HTMLElement} options.listElement - Parent list element.
 * @param {{column: string, label: string, value: string, suggestions: string[], missingCount: number}} options.controlModel - Plain control model.
 * @param {(column: string, nextValue: string) => void} options.onCommit - Commit callback.
 * @param {string} options.inputIdPrefix - Prefix for generated datalist ids.
 * @returns {void}
 */
function renderMissingDefaultControl({
  documentLike,
  listElement,
  controlModel,
  onCommit,
  inputIdPrefix,
}) {
  const wrapper = documentLike.createElement("div");
  wrapper.className = "missing-default-item";

  const labelWrap = documentLike.createElement("label");
  labelWrap.className = "missing-default-label";
  const labelText = documentLike.createElement("strong");
  labelText.textContent = controlModel.label;
  const meta = documentLike.createElement("span");
  meta.className = "missing-default-meta";
  meta.textContent = `${controlModel.missingCount} missing value${controlModel.missingCount === 1 ? "" : "s"}`;
  labelWrap.appendChild(labelText);
  labelWrap.appendChild(meta);

  const input = documentLike.createElement("input");
  input.type = "text";
  input.className = "missing-default-input";
  input.placeholder = "Leave empty to keep blanks";
  input.value = controlModel.value;
  const datalistId = `${inputIdPrefix}-${controlModel.column.replace(/[^a-zA-Z0-9_-]+/g, "-")}`;
  input.setAttribute("list", datalistId);
  input.setAttribute(
    "aria-label",
    `Default value for missing entries in ${controlModel.label}`
  );
  input.addEventListener("change", () => onCommit(controlModel.column, input.value));
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      input.blur();
    }
  });

  const datalist = documentLike.createElement("datalist");
  datalist.id = datalistId;
  for (const suggestion of controlModel.suggestions) {
    const option = documentLike.createElement("option");
    option.value = suggestion;
    datalist.appendChild(option);
  }

  wrapper.appendChild(labelWrap);
  wrapper.appendChild(input);
  wrapper.appendChild(datalist);
  listElement.appendChild(wrapper);
}
