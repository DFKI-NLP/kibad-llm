/**
 * Debug timing helpers for eval-dashboard instrumentation.
 */

/**
 * Resolve whether dashboard timing logs should be enabled.
 *
 * @param {object} [options] - Browser location dependency.
 * @param {{search?: string} | null} [options.locationLike=globalThis.location] - Location-like object.
 * @param {string} [options.paramName="debugTiming"] - Query parameter name.
 * @returns {boolean} Whether timing output is enabled.
 */
export function isDebugTimingEnabled({
  locationLike = globalThis.location,
  paramName = "debugTiming",
} = {}) {
  const params = new URLSearchParams(locationLike?.search || "");
  const value = params.get(paramName);
  if (value === null) {
    return false;
  }
  const normalized = value.trim().toLowerCase();
  return normalized === "" || normalized === "1" || normalized === "true" || normalized === "yes";
}

/**
 * Return a monotonic timestamp when available.
 *
 * @param {object} [performanceLike=globalThis.performance] - Performance-like object.
 * @returns {number} Current timestamp in milliseconds.
 */
export function getTimingNow(performanceLike = globalThis.performance) {
  if (typeof performanceLike?.now === "function") {
    return performanceLike.now();
  }
  return Date.now();
}

/**
 * Create a lightweight timing collector.
 *
 * @param {object} [options] - Timing dependencies and display options.
 * @param {boolean} [options.enabled=false] - Whether timings should be collected and logged.
 * @param {string} [options.label="eval-dashboard"] - Timing session label.
 * @param {object} [options.performanceLike=globalThis.performance] - Performance-like object.
 * @param {object} [options.consoleLike=globalThis.console] - Console-like object.
 * @returns {object} Timing collector.
 */
export function createTimingCollector({
  enabled = false,
  label = "eval-dashboard",
  performanceLike = globalThis.performance,
  consoleLike = globalThis.console,
} = {}) {
  const records = [];
  const now = () => getTimingNow(performanceLike);

  const add = (stage, durationMs, metadata = {}) => {
    if (!enabled) {
      return;
    }
    records.push({
      stage,
      duration_ms: Number(durationMs.toFixed(2)),
      ...metadata,
    });
  };

  const time = (stage, callback, metadata = {}) => {
    if (!enabled) {
      return callback();
    }
    const start = now();
    try {
      return callback();
    } finally {
      add(stage, now() - start, metadata);
    }
  };

  const timeAsync = async (stage, callback, metadata = {}) => {
    if (!enabled) {
      return callback();
    }
    const start = now();
    try {
      return await callback();
    } finally {
      add(stage, now() - start, metadata);
    }
  };

  const flush = (metadata = {}) => {
    if (!enabled || records.length === 0) {
      return [];
    }
    const rows = records.map((record) => ({ ...metadata, ...record }));
    const heading = `[${label}] timing`;
    if (typeof consoleLike?.table === "function") {
      consoleLike?.debug?.(heading);
      consoleLike.table(rows);
    } else if (typeof consoleLike?.debug === "function") {
      consoleLike.debug(heading, rows);
    } else if (typeof consoleLike?.log === "function") {
      consoleLike.log(heading, rows);
    }
    records.length = 0;
    return rows;
  };

  return {
    enabled,
    records,
    add,
    time,
    timeAsync,
    flush,
  };
}
