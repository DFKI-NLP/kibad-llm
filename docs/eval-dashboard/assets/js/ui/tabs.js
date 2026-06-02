/**
 * Shared tab-state helpers and tab-button renderers for the eval dashboard.
 */

import { syncTabButtonsAndPanels } from "./dom.js";

/**
 * Resolve one active tab id against the currently available values.
 *
 * @param {string | null} activeValue - Requested active tab id.
 * @param {Iterable<string>} availableValues - Available tab ids.
 * @returns {string | null} The preserved active value, the first available tab, or null.
 */
export function resolveActiveTabValue(activeValue, availableValues) {
  const values = Array.from(availableValues || []);
  if (!values.length) {
    return null;
  }
  return values.includes(activeValue) ? activeValue : values[0];
}

/**
 * Build plain tab-button view models from tab ids.
 *
 * @param {Iterable<string>} values - Tab ids to render.
 * @param {object} [options={}] - Label and title callbacks.
 * @param {string | null} [options.activeValue=null] - Active tab id.
 * @param {(value: string) => string} [options.getLabel] - Label formatter.
 * @param {(value: string) => string} [options.getTitle] - Optional title formatter.
 * @returns {Array<{value: string, label: string, title: string, isActive: boolean}>} Plain tab models.
 */
export function buildTabButtonModels(
  values,
  {
    activeValue = null,
    getLabel = (value) => String(value),
    getTitle = () => "",
  } = {}
) {
  return Array.from(values || []).map((value) => ({
    value,
    label: getLabel(value),
    title: getTitle(value),
    isActive: value === activeValue,
  }));
}

/**
 * Render one list of tab buttons from plain tab models.
 *
 * @param {object} options - Render inputs.
 * @param {Document} options.documentLike - Document-like element factory.
 * @param {HTMLElement | null} options.containerElement - Container that receives the buttons.
 * @param {Array<{value: string, label: string, title?: string, isActive?: boolean}>} options.tabModels - Button models.
 * @param {(value: string, event: Event) => void} [options.onSelect] - Click callback per tab.
 * @param {string} [options.buttonClassName="tab-button"] - Base button class name.
 * @param {string} [options.buttonValueAttribute="data-tab-value"] - Attribute storing the tab id.
 * @returns {void}
 */
export function renderTabButtons({
  documentLike,
  containerElement,
  tabModels,
  onSelect = () => {},
  buttonClassName = "tab-button",
  buttonValueAttribute = "data-tab-value",
}) {
  if (!containerElement) {
    return;
  }
  containerElement.innerHTML = "";
  for (const tab of tabModels || []) {
    const button = documentLike.createElement("button");
    button.type = "button";
    button.className = buttonClassName + (tab.isActive ? " active" : "");
    button.textContent = tab.label;
    button.setAttribute(buttonValueAttribute, tab.value);
    if (tab.title) {
      button.title = tab.title;
    }
    button.addEventListener("click", (event) => onSelect(tab.value, event));
    containerElement.appendChild(button);
  }
}

/**
 * Bind delegated click handling for one existing tab-button container.
 *
 * @param {object} options - Delegated tab-selection inputs.
 * @param {HTMLElement | null} options.containerElement - Container that receives click events.
 * @param {() => string | null} [options.getActiveValue] - Current active-tab lookup.
 * @param {(value: string, event: Event) => void} options.onSelect - Selection callback.
 * @param {string} [options.buttonSelector=".options-tab-button"] - Selector used with `closest(...)`.
 * @param {string} [options.valueAttribute="data-tab"] - Attribute storing the tab id.
 * @returns {void}
 */
export function bindDelegatedTabSelection({
  containerElement,
  getActiveValue = () => null,
  onSelect,
  buttonSelector = ".options-tab-button",
  valueAttribute = "data-tab",
}) {
  containerElement?.addEventListener?.("click", (event) => {
    const button = event.target?.closest?.(buttonSelector);
    if (!button) {
      return;
    }
    const value = button.getAttribute?.(valueAttribute);
    if (!value || value === getActiveValue()) {
      return;
    }
    onSelect(value, event);
  });
}

/**
 * Synchronize already-existing tab buttons and panels against one active value.
 *
 * @param {object} options - Cached tab DOM collections and attribute names.
 * @returns {void}
 */
export function renderStaticTabState(options) {
  syncTabButtonsAndPanels(options);
}
