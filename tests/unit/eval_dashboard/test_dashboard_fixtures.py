import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "eval_dashboard"
FIXTURE_README = FIXTURE_ROOT / "README.md"

VALID_FIXTURE_DIRS = {
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
    return json.loads(path.read_text(encoding="utf-8"))


def _job_return_value_path(fixture_name: str) -> Path:
    return FIXTURE_ROOT / fixture_name / "job_return_value.json"


def _overrides_path(fixture_name: str) -> Path:
    return FIXTURE_ROOT / fixture_name / ".hydra" / "overrides.yaml"


def test_fixture_readme_documents_all_fixture_directories() -> None:
    assert FIXTURE_README.is_file()
    readme_text = FIXTURE_README.read_text(encoding="utf-8")

    for fixture_name in [*VALID_FIXTURE_DIRS, *sorted(INVALID_FIXTURE_DIRS)]:
        assert f"`{fixture_name}`" in readme_text


def test_valid_fixtures_have_required_files() -> None:
    for fixture_name in VALID_FIXTURE_DIRS:
        assert _job_return_value_path(fixture_name).is_file()
        assert _overrides_path(fixture_name).is_file()


def test_valid_fixture_versions_cover_supported_dashboard_versions() -> None:
    versions = {}

    for fixture_name, expected_version in VALID_FIXTURE_DIRS.items():
        payload = _read_json(_job_return_value_path(fixture_name))
        versions[fixture_name] = payload.get("version", 0)
        assert versions[fixture_name] == expected_version
        assert payload["prediction"]["job_return_value"]["output_file"]

    assert {versions["run_v0"], versions["run_v1"], versions["run_v2"]} == {0, 1, 2}


def test_metric_specific_fixtures_have_expected_version_two_types() -> None:
    confusion_payload = _read_json(_job_return_value_path("confusion_matrix"))
    tpfpfn_payload = _read_json(_job_return_value_path("tpfpfn"))

    assert confusion_payload["type"] == "ConfusionMatrixCollection"
    assert tpfpfn_payload["type"] == "TpFpFnCollectorCollection"


def test_invalid_fixture_directories_have_expected_files() -> None:
    for fixture_name in {"malformed", "unsupported_version"}:
        assert _job_return_value_path(fixture_name).is_file()
        assert _overrides_path(fixture_name).is_file()

    conflict_root = FIXTURE_ROOT / "conflicting_prediction_ids"
    for run_name in ("run_a", "run_b"):
        assert (conflict_root / run_name / "job_return_value.json").is_file()
        assert (conflict_root / run_name / ".hydra" / "overrides.yaml").is_file()


def test_malformed_fixture_contains_invalid_json() -> None:
    malformed_text = _job_return_value_path("malformed").read_text(encoding="utf-8")

    try:
        json.loads(malformed_text)
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError("Malformed fixture unexpectedly contains valid JSON.")


def test_unsupported_version_fixture_uses_unknown_version() -> None:
    payload = _read_json(_job_return_value_path("unsupported_version"))
    assert payload["version"] not in {0, 1, 2}


def test_conflicting_prediction_id_fixture_contains_two_different_prediction_payloads() -> None:
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
