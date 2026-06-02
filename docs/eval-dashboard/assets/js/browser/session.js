/**
 * Browser-session helpers for eval-dashboard localStorage and query-parameter behavior.
 */

export const DEFAULT_GITHUB_TOKEN_STORAGE_KEY = "evalDashboard.githubToken";
const GIT_URL_QUERY_PARAM = "git_url";

/**
 * Normalize one persisted session value to the dashboard's trimmed-string contract.
 *
 * @param {unknown} value - The raw session value.
 * @returns {string} A trimmed string value.
 */
export function normalizeSessionValue(value) {
  return String(value || "").trim();
}

/**
 * Read the persisted GitHub token from storage, tolerating storage access failures.
 *
 * @param {{storageLike?: Storage | null, storageKey?: string}} [options={}] - Storage adapters and override key.
 * @returns {string} The stored token or an empty string.
 */
export function getStoredGitHubToken({
  storageLike = globalThis.localStorage,
  storageKey = DEFAULT_GITHUB_TOKEN_STORAGE_KEY,
} = {}) {
  try {
    return storageLike?.getItem(storageKey) || "";
  } catch {
    return "";
  }
}

/**
 * Hydrate one input-like element from the persisted GitHub token.
 *
 * @param {{value?: string} | null} inputElement - Input-like element receiving the stored token.
 * @param {{storageLike?: Storage | null, storageKey?: string}} [options={}] - Storage adapters and override key.
 * @returns {string} The stored token value that was applied.
 */
export function initializeGitHubTokenInput(inputElement, options = {}) {
  const token = getStoredGitHubToken(options);
  if (inputElement) {
    inputElement.value = token;
  }
  return token;
}

/**
 * Persist or clear the GitHub token in storage, tolerating storage access failures.
 *
 * @param {unknown} token - The token value to persist.
 * @param {{storageLike?: Storage | null, storageKey?: string}} [options={}] - Storage adapters and override key.
 * @returns {void}
 */
export function persistGitHubToken(
  token,
  { storageLike = globalThis.localStorage, storageKey = DEFAULT_GITHUB_TOKEN_STORAGE_KEY } = {}
) {
  const normalized = normalizeSessionValue(token);
  try {
    if (normalized) {
      storageLike?.setItem(storageKey, normalized);
    } else {
      storageLike?.removeItem(storageKey);
    }
  } catch {
    // Ignore storage write failures and continue without persistence.
  }
}

/**
 * Persist the current value of one input-like GitHub-token element.
 *
 * @param {{value?: unknown} | null} inputElement - Input-like element carrying the token value.
 * @param {{storageLike?: Storage | null, storageKey?: string}} [options={}] - Storage adapters and override key.
 * @returns {string} The normalized token value that was persisted.
 */
export function persistGitHubTokenInputValue(inputElement, options = {}) {
  const token = inputElement?.value;
  const normalized = normalizeSessionValue(token);
  persistGitHubToken(token, options);
  return normalized;
}

/**
 * Read the current `git_url` query parameter from a location-like adapter.
 *
 * @param {{locationLike?: {search?: string} | null}} [options={}] - Optional location adapter.
 * @returns {string} The trimmed `git_url` value, or an empty string.
 */
export function readGitUrlQueryParam({ locationLike = globalThis.location } = {}) {
  const params = new URLSearchParams(locationLike?.search || "");
  return normalizeSessionValue(params.get(GIT_URL_QUERY_PARAM));
}

/**
 * Hydrate one input-like element from the current `git_url` query parameter.
 *
 * @param {{value?: string} | null} inputElement - Input-like element receiving the query-param value.
 * @param {{locationLike?: {search?: string} | null}} [options={}] - Optional location adapter.
 * @returns {string} The trimmed `git_url` value that was applied.
 */
export function initializeGitUrlInputFromQueryParam(inputElement, options = {}) {
  const gitUrl = readGitUrlQueryParam(options);
  if (inputElement) {
    inputElement.value = gitUrl;
  }
  return gitUrl;
}

/**
 * Build the next URL string after updating the dashboard's `git_url` query parameter.
 *
 * @param {string} currentHref - The current absolute page URL.
 * @param {unknown} value - The next `git_url` value.
 * @returns {string} The updated absolute URL string.
 */
export function buildGitUrlQueryParamUrl(currentHref, value) {
  const currentUrl = new URL(currentHref);
  const normalized = normalizeSessionValue(value);
  if (normalized) {
    currentUrl.searchParams.set(GIT_URL_QUERY_PARAM, normalized);
  } else {
    currentUrl.searchParams.delete(GIT_URL_QUERY_PARAM);
  }
  return currentUrl.toString();
}

/**
 * Update the dashboard's `git_url` query parameter through injected location/history adapters.
 *
 * @param {unknown} value - The next `git_url` value.
 * @param {{locationLike?: {href?: string} | null, historyLike?: {replaceState: Function} | null}} [options={}] - Browser adapters.
 * @returns {void}
 */
export function setGitUrlQueryParam(
  value,
  { locationLike = globalThis.location, historyLike = globalThis.history } = {}
) {
  const nextUrl = buildGitUrlQueryParamUrl(locationLike?.href || "", value);
  historyLike?.replaceState(null, "", nextUrl);
}

/**
 * Clear the dashboard's `git_url` query parameter through injected browser adapters.
 *
 * @param {{locationLike?: {href?: string} | null, historyLike?: {replaceState: Function} | null}} [options={}] - Browser adapters.
 * @returns {void}
 */
export function clearGitUrlQueryParam(options = {}) {
  setGitUrlQueryParam("", options);
}

/**
 * Populate one input-like element from `git_url` and optionally trigger the initial load callback.
 *
 * @param {object} options - Bootstrap options.
 * @param {{value?: string} | null} [options.inputElement=null] - Input-like element receiving the query value.
 * @param {(gitUrl: string) => Promise<unknown> | unknown} [options.onLoadRequested] - Callback invoked when a non-empty `git_url` exists.
 * @param {{search?: string} | null} [options.locationLike=globalThis.location] - Optional location adapter.
 * @returns {Promise<boolean>} Whether a bootstrap load request was triggered.
 */
export async function runGitUrlQueryParamBootstrap({
  inputElement = null,
  onLoadRequested,
  locationLike = globalThis.location,
} = {}) {
  const gitUrl = initializeGitUrlInputFromQueryParam(inputElement, { locationLike });
  if (!gitUrl) {
    return false;
  }
  await onLoadRequested?.(gitUrl);
  return true;
}

/**
 * Handle one local-file selection by clearing `git_url`, then delegating to the current load and render callbacks.
 *
 * @param {object} options - Local-load orchestration callbacks.
 * @param {Array<unknown>} [options.files=[]] - Selected file list.
 * @param {() => void} [options.clearGitUrl=clearGitUrlQueryParam] - Query-param clear callback.
 * @param {(files: Array<unknown>) => Promise<unknown> | unknown} [options.loadEvaluationsFromFiles] - Local load callback.
 * @param {() => void} [options.renderPredictions] - Prediction rerender callback.
 * @param {() => void} [options.renderEvaluations] - Evaluation rerender callback.
 * @returns {Promise<void>}
 */
export async function handleLocalEvaluationFileSelection({
  files = [],
  clearGitUrl = () => clearGitUrlQueryParam(),
  loadEvaluationsFromFiles,
  renderPredictions,
  renderEvaluations,
} = {}) {
  clearGitUrl();
  await loadEvaluationsFromFiles?.(files);
  renderPredictions?.();
  renderEvaluations?.();
}
