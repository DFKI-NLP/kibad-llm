from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

DEFAULT_TARGETS = [
    "tests/integration/test_predict.py",
    "tests/integration/test_extractors.py",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _collect_node_ids(repo_root: Path, targets: list[str]) -> list[str]:
    command = ["uv", "run", "pytest", "--collect-only", "-q", *targets]
    result = subprocess.run(
        command,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        line.strip()
        for line in result.stdout.splitlines()
        if "::" in line and not line.startswith("=")
    ]


def _build_sitecustomize(temp_dir: Path) -> Path:
    sitecustomize = temp_dir / "sitecustomize.py"
    sitecustomize.write_text(
        """
from __future__ import annotations

import builtins
import io
import os
from pathlib import Path

LOG_PATH = os.environ.get("LLM_CHAT_OPEN_LOG")
FIXTURE_DIR = os.environ.get("LLM_CHAT_FIXTURE_DIR")
_REAL_OPEN = builtins.open


def _record_path(file: object) -> None:
    if not LOG_PATH or not FIXTURE_DIR:
        return
    try:
        path_str = os.fspath(file)
    except TypeError:
        return

    try:
        resolved = str(Path(path_str).resolve())
    except OSError:
        resolved = os.path.abspath(path_str)

    if not resolved.endswith(".json") or FIXTURE_DIR not in resolved:
        return

    with _REAL_OPEN(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(resolved + "\\n")


def _wrapped_open(file, *args, **kwargs):
    _record_path(file)
    return _REAL_OPEN(file, *args, **kwargs)


builtins.open = _wrapped_open
io.open = _wrapped_open
""".lstrip(),
        encoding="utf-8",
    )
    return sitecustomize


def _run_test_and_capture_fixture_usage(
    repo_root: Path,
    fixture_dir: Path,
    node_id: str,
) -> tuple[int, list[str], str]:
    with tempfile.TemporaryDirectory(prefix="llm-chat-usage-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        _build_sitecustomize(temp_dir)
        log_path = temp_dir / "opened-fixtures.log"

        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"{temp_dir}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(temp_dir)
        )
        env["LLM_CHAT_OPEN_LOG"] = str(log_path)
        env["LLM_CHAT_FIXTURE_DIR"] = str(fixture_dir.resolve())

        result = subprocess.run(
            ["uv", "run", "pytest", "-q", node_id],
            cwd=repo_root,
            capture_output=True,
            text=True,
            env=env,
        )

        used_files: list[str] = []
        if log_path.exists():
            used_files = sorted(
                {
                    str(Path(line.strip()).resolve().relative_to(repo_root))
                    for line in log_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                }
            )

        return result.returncode, used_files, result.stdout + result.stderr


def _make_report(
    node_ids: list[str],
    usage_by_node: dict[str, list[str]],
    fixture_dir: Path,
) -> dict[str, Any]:
    reverse_usage: dict[str, list[str]] = defaultdict(list)
    for node_id in node_ids:
        for fixture_file in usage_by_node[node_id]:
            reverse_usage[fixture_file].append(node_id)

    all_fixture_files = sorted(
        str(path.relative_to(_repo_root())) for path in fixture_dir.glob("*.json") if path.is_file()
    )
    unused_fixture_files = [
        fixture_file for fixture_file in all_fixture_files if fixture_file not in reverse_usage
    ]

    return {
        "tests": [{"node_id": node_id, "fixtures": usage_by_node[node_id]} for node_id in node_ids],
        "fixtures": [
            {"fixture": fixture_file, "tests": sorted(reverse_usage[fixture_file])}
            for fixture_file in sorted(reverse_usage)
        ],
        "unused_fixture_files": unused_fixture_files,
    }


def _print_report(report: dict[str, Any]) -> None:
    print("Tests -> llm_chat fixtures")
    for test_entry in report["tests"]:
        print(f"- {test_entry['node_id']}")
        fixtures: list[str] = test_entry["fixtures"]
        if fixtures:
            for fixture in fixtures:
                print(f"    - {fixture}")
        else:
            print("    - <none>")

    print("\nFixtures -> tests")
    for fixture_entry in report["fixtures"]:
        print(f"- {fixture_entry['fixture']}")
        for node_id in fixture_entry["tests"]:
            print(f"    - {node_id}")

    print("\nUnused fixture files")
    unused_fixture_files: list[str] = report["unused_fixture_files"]
    if unused_fixture_files:
        for fixture_file in unused_fixture_files:
            print(f"- {fixture_file}")
    else:
        print("- <none>")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Show which tests use which files under tests/fixtures/llm_chat by running each "
            "pytest node in isolation and logging opened fixture files."
        )
    )
    parser.add_argument(
        "targets",
        nargs="*",
        default=DEFAULT_TARGETS,
        help=(
            "Pytest targets to inspect. Pass test files to auto-collect node ids, or pass explicit "
            "pytest node ids containing '::'. Defaults to the integration tests that use llm_chat_replay."
        ),
    )
    parser.add_argument(
        "--fixture-dir",
        default="tests/fixtures/llm_chat",
        help="Path to the llm_chat fixture directory, relative to the repository root.",
    )
    parser.add_argument(
        "--json-output",
        help="Optional path to write the full report as JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = _repo_root()
    fixture_dir = (repo_root / args.fixture_dir).resolve()

    if not fixture_dir.is_dir():
        print(f"Fixture directory does not exist: {fixture_dir}", file=sys.stderr)
        return 2

    if any("::" in target for target in args.targets):
        node_ids = args.targets
    else:
        node_ids = _collect_node_ids(repo_root, args.targets)

    if not node_ids:
        print("No pytest node ids found.", file=sys.stderr)
        return 2

    usage_by_node: dict[str, list[str]] = {}
    failed_nodes: dict[str, str] = {}
    for node_id in node_ids:
        returncode, used_files, output = _run_test_and_capture_fixture_usage(
            repo_root=repo_root,
            fixture_dir=fixture_dir,
            node_id=node_id,
        )
        usage_by_node[node_id] = used_files
        if returncode != 0:
            failed_nodes[node_id] = output

    report = _make_report(node_ids=node_ids, usage_by_node=usage_by_node, fixture_dir=fixture_dir)
    _print_report(report)

    if args.json_output:
        json_output_path = Path(args.json_output)
        if not json_output_path.is_absolute():
            json_output_path = repo_root / json_output_path
        json_output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if failed_nodes:
        print("\nSome tests failed while collecting usage:", file=sys.stderr)
        for node_id, output in failed_nodes.items():
            print(f"\n--- {node_id} ---\n{output}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

