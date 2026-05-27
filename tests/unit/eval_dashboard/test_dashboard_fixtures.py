"""Fixture integrity tests for curated eval dashboard inputs."""

import json
from pathlib import Path

from tests import FIXTURE_DATA_ROOT

FIXTURE_ROOT = FIXTURE_DATA_ROOT / "eval_dashboard"
FIXTURE_README = FIXTURE_ROOT / "README.md"

VALID_FIXTURE_DIRS = {
    "bars": 0,
    "errors": 0,
    "run_v0": 0,
    "run_v1": 1,
    "run_v2": 2,
    "confusion_matrix": 2,
    "tpfpfn": 2,
}
INVALID_FIXTURE_DIRS = {
    "malformed",
    "unsupported_version",
    "conflicting_prediction_ids",
}


def _read_json(path: Path) -> dict:
    """Load a JSON fixture file into a Python object."""

    return json.loads(path.read_text(encoding="utf-8"))


def _job_return_value_path(fixture_name: str) -> Path:
    """Return the `job_return_value.json` path for a named fixture."""

    return FIXTURE_ROOT / fixture_name / "job_return_value.json"


def _overrides_path(fixture_name: str) -> Path:
    """Return the `.hydra/overrides.yaml` path for a named fixture."""

    return FIXTURE_ROOT / fixture_name / ".hydra" / "overrides.yaml"


def test_fixture_readme_documents_all_fixture_directories() -> None:
    """Ensure the fixture README mentions every curated fixture directory."""

    assert FIXTURE_README.is_file()
    readme_text = FIXTURE_README.read_text(encoding="utf-8")

    for fixture_name in [*VALID_FIXTURE_DIRS, *sorted(INVALID_FIXTURE_DIRS)]:
        assert f"`{fixture_name}`" in readme_text


def test_valid_fixtures_have_required_files() -> None:
    """Ensure each valid fixture provides the expected dashboard input files."""

    for fixture_name in VALID_FIXTURE_DIRS:
        assert _job_return_value_path(fixture_name).is_file()
        assert _overrides_path(fixture_name).is_file()


def test_valid_fixture_versions_cover_supported_dashboard_versions() -> None:
    """Verify curated valid fixtures cover dashboard input versions 0, 1, and 2."""

    versions = {}

    for fixture_name, expected_version in VALID_FIXTURE_DIRS.items():
        payload = _read_json(_job_return_value_path(fixture_name))
        versions[fixture_name] = payload.get("version", 0)
        assert versions[fixture_name] == expected_version
        assert payload["prediction"]["job_return_value"]["output_file"]

    assert {versions["run_v0"], versions["run_v1"], versions["run_v2"]} == {0, 1, 2}


def test_metric_specific_fixtures_have_expected_version_two_types() -> None:
    """Verify plot-family fixtures expose the expected metric-specific payload shapes."""

    bars_payload = _read_json(_job_return_value_path("bars"))
    errors_payload = _read_json(_job_return_value_path("errors"))
    confusion_payload = _read_json(_job_return_value_path("confusion_matrix"))
    tpfpfn_payload = _read_json(_job_return_value_path("tpfpfn"))

    assert "with_error" in errors_payload
    assert "no_error" in errors_payload
    assert any(key.endswith(".f1") or key == "ALL" for key in bars_payload)
    assert confusion_payload["type"] == "ConfusionMatrixCollection"
    assert tpfpfn_payload["type"] == "TpFpFnCollectorCollection"


def test_explicit_plot_family_fixtures_cover_all_live_dashboard_plot_modes() -> None:
    """Ensure every currently supported plot family has an explicit curated fixture."""

    readme_text = FIXTURE_README.read_text(encoding="utf-8")

    for fixture_name in ("bars", "errors", "confusion_matrix", "tpfpfn"):
        assert _job_return_value_path(fixture_name).is_file()
        assert _overrides_path(fixture_name).is_file()
        assert f"`{fixture_name}`" in readme_text


def test_invalid_fixture_directories_have_expected_files() -> None:
    """Ensure intentionally invalid fixtures still provide the files needed for smoke tests."""

    for fixture_name in {"malformed", "unsupported_version"}:
        assert _job_return_value_path(fixture_name).is_file()
        assert _overrides_path(fixture_name).is_file()

    conflict_root = FIXTURE_ROOT / "conflicting_prediction_ids"
    for run_name in ("run_a", "run_b"):
        assert (conflict_root / run_name / "job_return_value.json").is_file()
        assert (conflict_root / run_name / ".hydra" / "overrides.yaml").is_file()


def test_malformed_fixture_contains_invalid_json() -> None:
    """Verify the malformed fixture remains malformed JSON by design."""

    malformed_text = _job_return_value_path("malformed").read_text(encoding="utf-8")

    try:
        json.loads(malformed_text)
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError("Malformed fixture unexpectedly contains valid JSON.")


def test_unsupported_version_fixture_uses_unknown_version() -> None:
    """Verify the unsupported-version fixture uses a version outside the supported set."""

    payload = _read_json(_job_return_value_path("unsupported_version"))
    assert payload["version"] not in {0, 1, 2}


def test_conflicting_prediction_id_fixture_contains_two_different_prediction_payloads() -> None:
    """Verify the conflicting fixture reuses a prediction id with differing payload metadata."""

    conflict_root = FIXTURE_ROOT / "conflicting_prediction_ids"
    payload_a = _read_json(conflict_root / "run_a" / "job_return_value.json")
    payload_b = _read_json(conflict_root / "run_b" / "job_return_value.json")

    prediction_a = payload_a["prediction"]
    prediction_b = payload_b["prediction"]

    assert (
        prediction_a["job_return_value"]["output_file"]
        == prediction_b["job_return_value"]["output_file"]
    )
    assert prediction_a != prediction_b
