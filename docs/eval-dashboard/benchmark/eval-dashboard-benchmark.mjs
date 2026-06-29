#!/usr/bin/env node
/**
 * Browser benchmark for the static eval dashboard.
 *
 * The benchmark is intentionally manual and non-gating. It launches the dashboard
 * with `debugTiming=1`, loads complete local evaluation folders through the
 * browser file-input path, captures the dashboard's console timing tables, runs a
 * small set of representative plot interactions, and writes a JSON report.
 */

import fs from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DASHBOARD_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(DASHBOARD_ROOT, "../..");
const DEFAULT_FOLDERS = [
  "data/results/logs/477_faktencheck_core",
  "data/results/logs/481_faktencheck_core",
];
const DEFAULT_TIMEOUT_MS = 180000;

function printUsage() {
  console.log(`Usage: npm run benchmark -- [options] [folder ...]

Options:
  --output <path>      Write JSON report to this path.
                       Default: /tmp/eval-dashboard-benchmark-<timestamp>.json
  --headed            Run Chrome headed instead of headless.
  --channel <name>    Playwright browser channel. Default: chrome.
  --timeout <ms>      Per-wait timeout in milliseconds. Default: ${DEFAULT_TIMEOUT_MS}.
  --help              Show this help text.

Folder paths are resolved relative to the current working directory first, then relative to the repository root.

Folders default to:
${DEFAULT_FOLDERS.map((folder) => `  - ${folder}`).join("\n")}
`);
}

function parseArgs(argv) {
  const options = {
    output: "",
    headed: false,
    channel: "chrome",
    timeoutMs: DEFAULT_TIMEOUT_MS,
    folders: [],
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help" || arg === "-h") {
      options.help = true;
      continue;
    }
    if (arg === "--output") {
      options.output = argv[++index] || "";
      continue;
    }
    if (arg === "--headed") {
      options.headed = true;
      continue;
    }
    if (arg === "--channel") {
      options.channel = argv[++index] || "";
      continue;
    }
    if (arg === "--timeout") {
      const parsed = Number.parseInt(argv[++index] || "", 10);
      if (!Number.isFinite(parsed) || parsed <= 0) {
        throw new Error("--timeout must be a positive integer.");
      }
      options.timeoutMs = parsed;
      continue;
    }
    if (arg.startsWith("--")) {
      throw new Error(`Unknown option: ${arg}`);
    }
    options.folders.push(arg);
  }

  if (!options.output) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    options.output = `/tmp/eval-dashboard-benchmark-${timestamp}.json`;
  }
  if (!options.channel) {
    options.channel = "chrome";
  }
  if (!options.folders.length) {
    options.folders = [...DEFAULT_FOLDERS];
  }
  return options;
}

async function importPlaywright() {
  try {
    return await import("playwright");
  } catch (error) {
    throw new Error(
      "Playwright is required for eval-dashboard benchmarking. Run `npm install` in docs/eval-dashboard/benchmark, then rerun `npm run benchmark`."
    );
  }
}

async function pathExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function resolveFolderPath(folder) {
  const cwdPath = path.resolve(process.cwd(), folder);
  if (await pathExists(cwdPath)) {
    return cwdPath;
  }
  return path.resolve(REPO_ROOT, folder);
}

async function collectRelevantFileCount(folderPath) {
  let count = 0;
  async function visit(dir) {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      const entryPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        await visit(entryPath);
        continue;
      }
      if (entry.name === "job_return_value.json") {
        count += 1;
        continue;
      }
      if (entry.name === "overrides.yaml" && path.basename(path.dirname(entryPath)) === ".hydra") {
        count += 1;
      }
    }
  }
  await visit(folderPath);
  return count;
}

function startStaticServer() {
  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url || "/", "http://127.0.0.1");
      const pathname = decodeURIComponent(url.pathname === "/" ? "/index.html" : url.pathname);
      const filePath = path.resolve(DASHBOARD_ROOT, `.${pathname}`);
      if (!filePath.startsWith(DASHBOARD_ROOT)) {
        res.writeHead(403);
        res.end("Forbidden");
        return;
      }
      const data = await fs.readFile(filePath);
      const ext = path.extname(filePath);
      const type = ext === ".js" ? "text/javascript" : ext === ".css" ? "text/css" : "text/html";
      res.writeHead(200, { "Content-Type": type });
      res.end(data);
    } catch {
      res.writeHead(404);
      res.end("Not found");
    }
  });

  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", reject);
      resolve({ server, port: server.address().port });
    });
  });
}

function installTimingCaptureScript() {
  return `(() => {
    window.__timingTables = [];
    window.__lastTimingHeading = "";
    window.__originalConsoleDebug ||= console.debug.bind(console);
    window.__originalConsoleTable ||= console.table.bind(console);
    console.debug = (...args) => {
      if (String(args[0] || "").includes("timing")) {
        window.__lastTimingHeading = String(args[0]);
      }
      window.__originalConsoleDebug(...args);
    };
    console.table = (rows) => {
      window.__timingTables.push({
        heading: window.__lastTimingHeading,
        rows: JSON.parse(JSON.stringify(rows)),
      });
      window.__originalConsoleTable(rows);
    };
  })();`;
}

function summarizeRows(rows) {
  return rows.map((row) => ({
    stage: row.stage,
    duration_ms: row.duration_ms,
    plot: row.plot || "",
    field: row.field || "",
    entry_count: row.entry_count || "",
    file_count: row.file_count || "",
  }));
}

function summarizeTables(tables) {
  return tables.map((table, index) => ({
    index,
    heading: table.heading,
    total_ms: Number(
      table.rows.reduce((sum, row) => sum + Number(row.duration_ms || 0), 0).toFixed(2)
    ),
    rows: summarizeRows(table.rows),
  }));
}

function summarizeTablesWithOffset(tables, startIndex = 0) {
  return summarizeTables(tables).map((table, index) => ({
    ...table,
    index: startIndex + index,
  }));
}

function remapInteractionTimingIndexes(interaction, sourceStartIndex, targetStartIndex) {
  const { source_timing_table_start_index: _sourceTimingTableStartIndex, ...publicInteraction } = interaction;
  return {
    ...publicInteraction,
    timing_table_indexes: interaction.timing_table_indexes.map(
      (index) => targetStartIndex + index - sourceStartIndex
    ),
  };
}

async function waitForTimingTable(page, previousCount, timeoutMs) {
  await page.waitForFunction(
    (count) => Array.isArray(window.__timingTables) && window.__timingTables.length > count,
    previousCount,
    { timeout: timeoutMs }
  );
}

async function captureInteractionTiming(page, name, timeoutMs, action) {
  const count = await page.evaluate(() => window.__timingTables.length);
  const start = await page.evaluate(() => performance.now());
  const changed = await action();

  if (!changed) {
    return false;
  }
  await waitForTimingTable(page, count, timeoutMs);
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => resolve()))
  );
  const end = await page.evaluate(() => performance.now());
  const nextCount = await page.evaluate(() => window.__timingTables.length);

  return {
    name,
    wall_ms: Number((end - start).toFixed(2)),
    source_timing_table_start_index: count,
    timing_table_indexes: Array.from(
      { length: Math.max(0, nextCount - count) },
      (_, index) => count + index
    ),
  };
}

async function clickAndCaptureTiming(page, name, selector, timeoutMs) {
  return captureInteractionTiming(page, name, timeoutMs, () => page.evaluate((buttonSelector) => {
    const button = document.querySelector(buttonSelector);
    if (!button || button.disabled || button.offsetParent === null) {
      return false;
    }
    if (button.classList?.contains("active")) {
      return false;
    }
    button.click();
    return true;
  }, selector));
}

async function clickNextPlotTab(page, timeoutMs, name = "switch active plot tab") {
  return captureInteractionTiming(page, name, timeoutMs, () => page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll("#evalPlotTabs button"));
    const next = buttons.find((button) => !button.classList.contains("active"));
    if (!next) {
      return false;
    }
    next.click();
    return true;
  }));
}

async function deselectFirstCheckedTableRow(page, name, tableSelector, timeoutMs) {
  const checkboxSelector = `${tableSelector} tbody tr:not(.member-row) td:nth-child(2) input[type="checkbox"]:checked`;
  return captureInteractionTiming(page, name, timeoutMs, async () => {
    const checkboxes = page.locator(checkboxSelector);
    if (await checkboxes.count() === 0) {
      return false;
    }
    await checkboxes.first().click();
    return true;
  });
}

async function switchToMetricFieldTab(page, name, targetTabText, timeoutMs) {
  const count = await page.evaluate(() => window.__timingTables.length);
  const start = await page.evaluate(() => performance.now());
  const modeClicked = await page.evaluate(() => {
    const button = document.querySelector("#confusionTabsByMetricFieldButton");
    if (!button || button.disabled || button.offsetParent === null) {
      return false;
    }
    if (!button.classList?.contains("active")) {
      button.click();
    }
    return true;
  });

  if (!modeClicked) {
    return false;
  }
  await waitForTimingTable(page, count, timeoutMs);
  const afterModeCount = await page.evaluate(() => window.__timingTables.length);
  const tabClicked = await page.evaluate((targetText) => {
    const button = Array.from(document.querySelectorAll("#evalPlotTabs button"))
      .find((candidate) => candidate.textContent.includes(targetText));
    if (!button || button.disabled || button.offsetParent === null) {
      return false;
    }
    if (!button.classList?.contains("active")) {
      button.click();
    }
    return true;
  }, targetTabText);

  if (!tabClicked) {
    return false;
  }
  await waitForTimingTable(page, afterModeCount, timeoutMs);
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => resolve()))
  );
  const end = await page.evaluate(() => performance.now());
  const nextCount = await page.evaluate(() => window.__timingTables.length);

  return {
    name,
    wall_ms: Number((end - start).toFixed(2)),
    source_timing_table_start_index: count,
    timing_table_indexes: Array.from(
      { length: Math.max(0, nextCount - count) },
      (_, index) => count + index
    ),
  };
}

async function openLoadedDashboardPage({ browser, dashboardUrl, absoluteFolder, timeoutMs }) {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1200 } });
  const page = await context.newPage();
  await page.addInitScript(installTimingCaptureScript());
  await page.goto(dashboardUrl, { waitUntil: "domcontentloaded", timeout: timeoutMs });
  await page.waitForSelector("#folderInput", { timeout: timeoutMs });

  const beforeLoad = await page.evaluate(() => window.__timingTables.length);
  const loadStart = await page.evaluate(() => performance.now());
  await page.locator("#folderInput").setInputFiles(absoluteFolder);
  await page.waitForFunction(
    (count) => {
      const hasLoadAndRender = Array.isArray(window.__timingTables) && window.__timingTables.length >= count + 3;
      const downloadButton = document.getElementById("downloadFiguresButton");
      return hasLoadAndRender && downloadButton?.textContent?.includes("(");
    },
    beforeLoad,
    { timeout: timeoutMs }
  );
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => resolve()))
  );
  const loadEnd = await page.evaluate(() => performance.now());
  const afterLoad = await page.evaluate(() => window.__timingTables.length);

  return {
    context,
    page,
    loadMeasurement: {
      name: "complete folder load to usable dashboard",
      wall_ms: Number((loadEnd - loadStart).toFixed(2)),
      timing_table_indexes: Array.from(
        { length: Math.max(0, afterLoad - beforeLoad) },
        (_, index) => beforeLoad + index
      ),
    },
  };
}

async function runFreshInteractionScenario({
  browser,
  dashboardUrl,
  absoluteFolder,
  timeoutMs,
  tableStartIndex,
  action,
}) {
  const { context, page } = await openLoadedDashboardPage({
    browser,
    dashboardUrl,
    absoluteFolder,
    timeoutMs,
  });

  try {
    const interaction = await action(page);
    if (!interaction) {
      return {
        interaction: null,
        tables: [],
      };
    }
    const sourceStartIndex = interaction.source_timing_table_start_index;
    const pageTables = await page.evaluate(() => window.__timingTables);
    const interactionTables = summarizeTablesWithOffset(
      pageTables.slice(sourceStartIndex),
      tableStartIndex
    );
    return {
      interaction: remapInteractionTimingIndexes(interaction, sourceStartIndex, tableStartIndex),
      tables: interactionTables,
    };
  } finally {
    await context.close();
  }
}

async function runFolderBenchmark({ browser, dashboardUrl, folder, timeoutMs }) {
  const absoluteFolder = await resolveFolderPath(folder);
  if (!(await pathExists(absoluteFolder))) {
    throw new Error(`Benchmark folder does not exist: ${folder}`);
  }

  const relevantFileCount = await collectRelevantFileCount(absoluteFolder);
  const { context, page, loadMeasurement } = await openLoadedDashboardPage({
    browser,
    dashboardUrl,
    absoluteFolder,
    timeoutMs,
  });

  const interactions = [];
  let tables = [];

  try {
    const pageTables = await page.evaluate(() => window.__timingTables);
    tables = summarizeTablesWithOffset(pageTables);
  } finally {
    await context.close();
  }

  const freshScenarios = [
    {
      action: (scenarioPage) => clickAndCaptureTiming(
        scenarioPage,
        "fresh post-load switch tab grouping to metric field",
        "#confusionTabsByMetricFieldButton",
        timeoutMs
      ),
    },
    {
      action: (scenarioPage) => clickNextPlotTab(
        scenarioPage,
        timeoutMs,
        "fresh post-load switch active plot tab"
      ),
    },
    {
      action: (scenarioPage) => switchToMetricFieldTab(
        scenarioPage,
        "fresh post-load switch to metric-field german_name tab",
        "german_name",
        timeoutMs
      ),
    },
    {
      action: (scenarioPage) => switchToMetricFieldTab(
        scenarioPage,
        "fresh post-load switch to metric-field scientific_name tab",
        "scientific_name",
        timeoutMs
      ),
    },
    {
      action: (scenarioPage) => clickAndCaptureTiming(
        scenarioPage,
        "fresh post-load set evaluation group-by to none",
        "#evalGroupByNoneButton",
        timeoutMs
      ),
    },
    {
      action: (scenarioPage) => deselectFirstCheckedTableRow(
        scenarioPage,
        "fresh post-load deselect evaluation table row",
        "#evaluationsTable",
        timeoutMs
      ),
    },
    {
      action: (scenarioPage) => deselectFirstCheckedTableRow(
        scenarioPage,
        "fresh post-load deselect prediction table row",
        "#predictionsTable",
        timeoutMs
      ),
    },
  ];

  for (const scenario of freshScenarios) {
    const result = await runFreshInteractionScenario({
      browser,
      dashboardUrl,
      absoluteFolder,
      timeoutMs,
      tableStartIndex: tables.length,
      action: scenario.action,
    });
    if (result.interaction) {
      interactions.push(result.interaction);
      tables.push(...result.tables);
    }
  }

  return {
    folder,
    absolute_folder: absoluteFolder,
    relevant_files: relevantFileCount,
    initial_load: loadMeasurement,
    interactions,
    tables,
  };
}

function printSummary(report) {
  for (const result of report.results) {
    console.log(`\n${result.folder}`);
    console.log(`  relevant files: ${result.relevant_files}`);
    console.log(`  initial load: ${result.initial_load.wall_ms} ms`);
    console.log(
      `  interactions: ${
        result.interactions.map((interaction) => `${interaction.name} (${interaction.wall_ms} ms)`).join(", ") ||
        "(none)"
      }`
    );
    for (const table of result.tables) {
      const slowest = [...table.rows]
        .sort((left, right) => Number(right.duration_ms) - Number(left.duration_ms))
        .slice(0, 3)
        .map((row) => `${row.stage}${row.field ? ` (${row.field})` : ""}: ${row.duration_ms} ms`)
        .join("; ");
      console.log(`  [${table.index}] ${table.heading}: ${table.total_ms} ms`);
      if (slowest) {
        console.log(`      slowest: ${slowest}`);
      }
    }
  }
  console.log(`\nWrote benchmark report: ${report.output}`);
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printUsage();
    return;
  }

  const { chromium } = await importPlaywright();
  const { server, port } = await startStaticServer();
  const dashboardUrl = `http://127.0.0.1:${port}/index.html?debugTiming=1`;
  let browser = null;

  try {
    browser = await chromium.launch({
      channel: options.channel,
      headless: !options.headed,
    });
    const results = [];
    for (const folder of options.folders) {
      results.push(await runFolderBenchmark({
        browser,
        dashboardUrl,
        folder,
        timeoutMs: options.timeoutMs,
      }));
    }

    const report = {
      benchmarked_at: new Date().toISOString(),
      dashboard_url: dashboardUrl,
      browser_channel: options.channel,
      browser_version: await browser.version(),
      headless: !options.headed,
      output: path.resolve(options.output),
      results,
    };
    await fs.mkdir(path.dirname(report.output), { recursive: true });
    await fs.writeFile(report.output, `${JSON.stringify(report, null, 2)}\n`);
    printSummary(report);
  } finally {
    if (browser) {
      await browser.close();
    }
    await new Promise((resolve) => server.close(resolve));
  }
}

main().catch((error) => {
  console.error(error.message || error);
  process.exitCode = 1;
});
