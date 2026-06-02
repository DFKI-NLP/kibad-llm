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

