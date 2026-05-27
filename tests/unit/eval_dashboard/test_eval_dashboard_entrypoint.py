from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_INDEX = REPO_ROOT / "docs" / "index.md"
DASHBOARD_ENTRY = REPO_ROOT / "docs" / "eval-dashboard" / "index.html"
DASHBOARD_COMPAT = REPO_ROOT / "docs" / "eval-dashboard.html"
PROPERDOCS_CONFIG = REPO_ROOT / "properdocs.yml"
BASELINE_MANIFEST = (
    REPO_ROOT / "tests" / "fixtures" / "eval_dashboard" / "baseline" / "baseline-manifest.md"
)
BASELINE_SUMMARY = (
    REPO_ROOT / "tests" / "fixtures" / "eval_dashboard" / "baseline" / "baseline-summary.json"
)


def _load_properdocs() -> dict:
    return yaml.safe_load(PROPERDOCS_CONFIG.read_text(encoding="utf-8"))


def test_dashboard_entrypoint_exists() -> None:
    assert DASHBOARD_ENTRY.is_file()
    assert DASHBOARD_COMPAT.is_file()


def test_phase_zero_baseline_artifacts_exist() -> None:
    assert BASELINE_MANIFEST.is_file()
    assert BASELINE_SUMMARY.is_file()


def test_properdocs_nav_points_to_new_dashboard_entry() -> None:
    config = _load_properdocs()
    assert {"Evaluation dashboard": "eval-dashboard/index.html"} in config["nav"]


def test_docs_index_links_point_to_new_dashboard_entry() -> None:
    text = DOCS_INDEX.read_text(encoding="utf-8")
    assert "(eval-dashboard/index.html)" in text
    assert "(eval-dashboard.html)" not in text


def test_old_dashboard_path_has_redirect_coverage() -> None:

    compat_html = DASHBOARD_COMPAT.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' in compat_html
    assert "eval-dashboard/index.html" in compat_html
