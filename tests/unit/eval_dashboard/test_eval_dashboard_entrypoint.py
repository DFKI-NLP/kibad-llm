"""Structural smoke tests for the eval dashboard docs entrypoint."""

import yaml

from kibad_llm.config import PROJ_ROOT
from tests import FIXTURE_DATA_ROOT

DOCS_ROOT = PROJ_ROOT / "docs"
DOCS_INDEX = DOCS_ROOT / "index.md"
DASHBOARD_ENTRY = DOCS_ROOT / "eval-dashboard" / "index.html"
DASHBOARD_DOCS_PAGE = DOCS_ROOT / "eval-dashboard.md"
DASHBOARD_CSS_ROOT = DOCS_ROOT / "eval-dashboard" / "assets" / "css"
DASHBOARD_JS_ROOT = DOCS_ROOT / "eval-dashboard" / "assets" / "js"
DASHBOARD_JS_ENTRY = DASHBOARD_JS_ROOT / "main.js"
DATA_JS_ROOT = DASHBOARD_JS_ROOT / "data"
STATE_JS_ROOT = DASHBOARD_JS_ROOT / "state"
UI_JS_ROOT = DASHBOARD_JS_ROOT / "ui"
UTILS_JS_ROOT = DASHBOARD_JS_ROOT / "utils"
BROWSER_JS_ROOT = DASHBOARD_JS_ROOT / "browser"
PLOTS_JS_ROOT = DASHBOARD_JS_ROOT / "plots"
PROPERDOCS_CONFIG = PROJ_ROOT / "properdocs.yml"
BASELINE_MANIFEST = FIXTURE_DATA_ROOT / "eval_dashboard" / "baseline" / "baseline-manifest.md"
BASELINE_SUMMARY = FIXTURE_DATA_ROOT / "eval_dashboard" / "baseline" / "baseline-summary.json"
EXPECTED_CSS_FILES = (
    "index.css",
    "tokens.css",
    "layout.css",
    "controls.css",
    "tables.css",
    "plots.css",
)
EXPECTED_JS_UTILITY_FILES = (
    "flatten.js",
    "sort.js",
    "text.js",
    "values.js",
)
EXPECTED_JS_STATE_FILES = (
    "selectors.js",
    "store.js",
)
EXPECTED_JS_DATA_FILES = (
    "file-loader.js",
    "git-loader.js",
    "ingest-runs.js",
    "normalize.js",
    "parse-overrides.js",
)
EXPECTED_JS_UI_FILES = (
    "controls.js",
    "dom.js",
    "evaluation-table.js",
    "eval-json-pane.js",
    "prediction-table.js",
    "status.js",
    "table-shared.js",
    "tabs.js",
)
EXPECTED_JS_BROWSER_FILES = ("session.js",)
EXPECTED_JS_PLOTS_FILES = (
    "bars.js",
    "confusion.js",
    "dashboard.js",
    "export.js",
    "legend.js",
    "shared.js",
    "tpfpfn.js",
)


def _load_properdocs() -> dict:
    """Load the ProperDocs configuration for entrypoint assertions."""

    return yaml.safe_load(PROPERDOCS_CONFIG.read_text(encoding="utf-8"))


def test_dashboard_entrypoint_exists() -> None:
    """Ensure the dashboard documentation page and runtime entrypoint exist."""

    assert DASHBOARD_DOCS_PAGE.is_file()
    assert DASHBOARD_ENTRY.is_file()


def test_phase_zero_baseline_artifacts_exist() -> None:
    """Ensure the baseline artifacts established before refactoring are present."""

    assert BASELINE_MANIFEST.is_file()
    assert BASELINE_SUMMARY.is_file()


def test_phase_three_dashboard_css_assets_exist() -> None:
    """Ensure the Phase 3 external stylesheet files exist under the dashboard asset path."""

    for file_name in EXPECTED_CSS_FILES:
        assert (DASHBOARD_CSS_ROOT / file_name).is_file()


def test_phase_four_dashboard_js_entry_exists() -> None:
    """Ensure the Phase 4 external JavaScript module exists under the dashboard asset path."""

    assert DASHBOARD_JS_ENTRY.is_file()


def test_phase_five_dashboard_js_utility_modules_exist() -> None:
    """Ensure the Phase 5 utility modules exist under the dashboard asset path."""

    for file_name in EXPECTED_JS_UTILITY_FILES:
        assert (UTILS_JS_ROOT / file_name).is_file()


def test_phase_six_dashboard_js_state_modules_exist() -> None:
    """Ensure the Phase 6 state modules exist under the dashboard asset path."""

    for file_name in EXPECTED_JS_STATE_FILES:
        assert (STATE_JS_ROOT / file_name).is_file()


def test_phase_seven_and_phase_eight_dashboard_js_data_modules_exist() -> None:
    """Ensure the Phase 7 and Phase 8 data modules exist under the dashboard asset path."""

    for file_name in EXPECTED_JS_DATA_FILES:
        assert (DATA_JS_ROOT / file_name).is_file()


def test_phase_nine_and_phase_ten_dashboard_js_ui_modules_exist() -> None:
    """Ensure the Phase 9, Phase 10A, and Phase 10B UI modules exist under the dashboard asset path."""

    for file_name in EXPECTED_JS_UI_FILES:
        assert (UI_JS_ROOT / file_name).is_file()


def test_phase_nine_dashboard_js_browser_modules_exist() -> None:
    """Ensure the Phase 9 browser-session module exists under the dashboard asset path."""

    for file_name in EXPECTED_JS_BROWSER_FILES:
        assert (BROWSER_JS_ROOT / file_name).is_file()


def test_phase_eleven_dashboard_js_plot_modules_exist() -> None:
    """Ensure the Phase 11 and Phase 12 plot/export modules exist under the dashboard asset path."""

    for file_name in EXPECTED_JS_PLOTS_FILES:
        assert (PLOTS_JS_ROOT / file_name).is_file()


def test_properdocs_nav_points_to_dashboard_docs_page() -> None:
    """Ensure docs navigation points to the dashboard documentation page."""

    config = _load_properdocs()
    assert {"Evaluation dashboard": "eval-dashboard.md"} in config["nav"]


def test_docs_index_links_point_to_dashboard_docs_page() -> None:
    """Ensure docs landing-page links target the dashboard documentation page."""

    text = DOCS_INDEX.read_text(encoding="utf-8")
    assert "(eval-dashboard.md)" in text
    assert "(eval-dashboard.html)" not in text


def test_dashboard_docs_page_links_to_runtime_entrypoint() -> None:
    """Ensure the documentation page keeps a prominent link to the runtime dashboard."""

    text = DASHBOARD_DOCS_PAGE.read_text(encoding="utf-8")
    assert "**Open the dashboard:**" in text
    assert "(eval-dashboard/index.html)" in text
    assert "(eval-dashboard.html)" not in text
