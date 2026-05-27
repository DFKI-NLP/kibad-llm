"""Fixture integrity tests for curated eval dashboard inputs."""

import json
from pathlib import Path

import yaml

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


def _read_yaml(path: Path) -> list[str]:
    """Load a YAML overrides file into a list of override strings."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert payload
    assert all(isinstance(item, str) and item for item in payload)
    return payload


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


def test_valid_fixture_job_return_values_parse_as_json_objects() -> None:
    """Ensure every valid fixture contains a parseable JSON object payload."""

    for fixture_name in VALID_FIXTURE_DIRS:
        payload = _read_json(_job_return_value_path(fixture_name))
        assert isinstance(payload, dict)


def test_valid_fixture_overrides_yaml_parse_as_non_empty_lists() -> None:
    """Ensure every valid fixture contains a parseable YAML list of overrides."""

    for fixture_name in VALID_FIXTURE_DIRS:
        _read_yaml(_overrides_path(fixture_name))


def test_invalid_fixture_overrides_yaml_parse_as_expected() -> None:
    """Ensure invalid fixtures stay invalid only in their intended dimensions."""

    for fixture_name in {"malformed", "unsupported_version"}:
        _read_yaml(_overrides_path(fixture_name))

    conflict_root = FIXTURE_ROOT / "conflicting_prediction_ids"
    for run_name in ("run_a", "run_b"):
        _read_yaml(conflict_root / run_name / ".hydra" / "overrides.yaml")


def test_valid_fixture_prediction_metadata_contract_is_present() -> None:
    """Ensure each valid fixture keeps the minimum prediction metadata shape used by the dashboard."""

    for fixture_name in VALID_FIXTURE_DIRS:
        payload = _read_json(_job_return_value_path(fixture_name))
        prediction = payload["prediction"]
        job_return_value = prediction["job_return_value"]

        assert job_return_value["output_file"]
        assert isinstance(prediction["overrides"], dict)
        assert prediction["overrides"]


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


def test_plot_family_fixtures_have_non_empty_family_specific_payloads() -> None:
    """Ensure explicit plot-family fixtures retain non-empty, family-specific payload shapes."""

    bars_payload = _read_json(_job_return_value_path("bars"))
    errors_payload = _read_json(_job_return_value_path("errors"))
    confusion_payload = _read_json(_job_return_value_path("confusion_matrix"))
    tpfpfn_payload = _read_json(_job_return_value_path("tpfpfn"))

    assert any(not key.startswith("prediction") for key in bars_payload)
    assert errors_payload["with_error"] > 0
    assert errors_payload["no_error"] > 0
    assert confusion_payload["data"]
    assert tpfpfn_payload["data"]


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


def test_valid_fixture_readme_sections_document_purpose_source_basis_and_notes() -> None:
    """Ensure valid fixtures keep provenance and rationale documented in the fixture README."""

    readme_text = FIXTURE_README.read_text(encoding="utf-8")

    for fixture_name in VALID_FIXTURE_DIRS:
        section = readme_text.split(f"### `{fixture_name}`", maxsplit=1)[1]
        next_heading = section.find("\n### `")
        if next_heading != -1:
            section = section[:next_heading]

        assert "- purpose:" in section
        assert "- source basis:" in section
        assert "- notes:" in section


def test_invalid_fixture_readme_sections_document_intended_failure_mode() -> None:
    """Ensure invalid fixtures remain explicitly documented as intentionally invalid."""

    readme_text = FIXTURE_README.read_text(encoding="utf-8")

    expected_snippets = {
        "malformed": (
            "- purpose:",
            "- source basis:",
            "- notes:",
            "malformed JSON",
        ),
        "unsupported_version": (
            "- purpose:",
            "- source basis:",
            "- notes:",
            '"version": 99',
        ),
        "conflicting_prediction_ids": (
            "- purpose:",
            "- source basis:",
            "- notes:",
            "share the same prediction id",
        ),
    }

    for fixture_name, snippets in expected_snippets.items():
        section = readme_text.split(f"### `{fixture_name}`", maxsplit=1)[1]
        next_heading = section.find("\n### `")
        if next_heading != -1:
            section = section[:next_heading]

        for snippet in snippets:
            assert snippet in section
