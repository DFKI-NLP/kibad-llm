"""Contract and source-parity tests for the separately distributable Task C scorer."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess  # nosec B404: fixed local interpreter and arguments, without a shell.
import sys

import pytest

from kibad_llm.metrics.f1 import F1MicroMultipleFieldsMetric

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "shared_task/evaluation/evaluate.py"
SPEC = importlib.util.spec_from_file_location("task_c_evaluate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
scoring = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scoring)


def no_model(*args):
    raise AssertionError("This evaluation must not initialize BERTScore")


def write_records(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def test_sets_exact_strings_nested_independence_and_macro():
    refs = {
        "a": {
            "habitat": ["Wald", "Boden", "Wald", None, " "],
            "ecosystem_type": [{"category": "A", "term": "X"}, {"category": "B", "term": "Y"}],
        },
        "b": {"habitat": "Wald"},
    }
    preds = {
        "b": {"habitat": "wald"},
        "a": {
            "habitat": ["Wald", "Wald", " Boden"],
            "ecosystem_type": [{"category": "B", "term": "X"}, {"category": "A", "term": "Y"}],
            "unscored": {"arbitrary": [1, True]},
        },
    }
    result = scoring.evaluate(refs, preds, "c1", pair_scorer=no_model)
    assert result["fields"]["habitat"] == {
        "tp": 1,
        "fp": 2,
        "fn": 2,
        "precision": 1 / 3,
        "recall": 1 / 3,
        "f1": 1 / 3,
        "support": 3,
    }
    assert result["fields"]["ecosystem_type.category"]["f1"] == 1
    assert result["fields"]["ecosystem_type.term"]["f1"] == 1
    assert result["fields"]["taxa.species_group"]["f1"] == 0
    assert result["scores"]["c1_score"] == pytest.approx((1 / 3 + 2) / 5)
    assert result["summaries"]["c1"]["micro"]["f1"] == pytest.approx(5 / 7)


@pytest.mark.parametrize("empty", [None, [], {}, "", " \t", [None, ""]])
def test_empty_values(empty):
    assert scoring.field_values({"habitat": empty}, "habitat") == set()


@pytest.mark.parametrize("bad", [42, True, 1.5, {"value": "Wald"}, ["Wald", 0]])
def test_malformed_scored_values(bad):
    with pytest.raises(ValueError, match="Paper 'a'.*habitat"):
        scoring.evaluate({"a": {}}, {"a": {"habitat": bad}}, "c1")


def test_taxa_names_exact_extra_fields_ignored_and_c1_unaffected():
    refs = {
        "a": {
            "taxa": [
                {
                    "scientific_name": "Fucus spp",
                    "species_group": "Andere Pflanzen",
                    "collective_term": False,
                }
            ]
        }
    }
    preds = {
        "a": {
            "taxa": [
                {
                    "scientific_name": "Fucus spp.",
                    "species_group": "Andere Pflanzen",
                    "collective_term": True,
                }
            ]
        }
    }
    result = scoring.evaluate(refs, preds, "c2b", categorical_only=True, pair_scorer=no_model)
    assert result["fields"]["taxa.scientific_name"]["fp"] == 1
    assert result["fields"]["taxa.scientific_name"]["fn"] == 1
    assert result["scores"]["c1_score"] == 0.2
    assert "biodiversity_variable" not in result["fields"]


def test_macro_and_micro_union_does_not_duplicate_shared_fields():
    result = scoring.evaluate(
        {"a": {"biodiversity_level": "Artenvielfalt"}},
        {"a": {"biodiversity_level": "Artenvielfalt"}},
        categorical_only=True,
    )
    assert result["summaries"]["c1"]["categorical_fields"] == 5
    assert result["summaries"]["c2b"]["categorical_fields"] == 6
    assert result["summaries"]["c2"]["categorical_fields"] == 13
    assert result["summaries"]["all"]["categorical_fields"] == 16
    assert result["summaries"]["all"]["micro"]["tp"] == 1
    assert result["summaries"]["all"]["macro_f1"] == 1 / 16


def test_symmetric_best_match_and_missing_text_penalties():
    matrix = {
        ("p1", "r1"): 0.9,
        ("p1", "r2"): 0.2,
        ("p1", "r3"): 0.1,
        ("p2", "r1"): 0.1,
        ("p2", "r2"): 0.8,
        ("p2", "r3"): 0.7,
    }

    def pairs(predictions, references):
        return [matrix[p, r] for p, r in zip(predictions, references)]

    refs = {
        "a": {"biodiversity_variable": ["r1", "r2", "r3"]},
        "b": {"biodiversity_variable": ["missing"]},
        "c": {},
        "d": {},
    }
    preds = {
        "a": {"biodiversity_variable": ["p1", "p2", "p2"]},
        "b": {},
        "c": {"biodiversity_variable": ["extra"]},
        "d": {},
    }
    result = scoring.evaluate(refs, preds, "c2b", pair_scorer=pairs)
    text = result["fields"]["biodiversity_variable"]
    # Row maxima: .9,.8; column maxima: .9,.8,.7. Two unmatched values add to denominator.
    assert text["best_match_sum"] == pytest.approx(4.1)
    assert text["prediction_values"] == 3
    assert text["reference_values"] == 4
    assert text["bertscore"] == pytest.approx(4.1 / 7)
    assert result["summaries"]["c2b"]["bertscore"] == text["bertscore"]
    assert result["scores"]["c1_score"] == 0


def test_best_matches_are_many_to_one_and_batches_are_bounded():
    sizes = []

    def pairs(preds, refs):
        sizes.append(len(preds))
        return [1.0] * len(preds)

    assert (
        scoring.best_match_sum({f"p{i}" for i in range(7)}, {f"r{i}" for i in range(8)}, pairs)
        == 15
    )
    assert sum(sizes) == 56
    assert max(sizes) <= scoring.BATCH_SIZE
    assert scoring.best_match_sum(set(), {"x"}, no_model) == 0


@pytest.mark.parametrize("driver", ["direct_driver", "indirect_driver"])
def test_driver_details_alias_scores_unmodified_data_and_accepts_both_spellings(driver):
    refs = {"a": {driver: [{"details": "Landnutzung"}]}}
    preds = {"a": {driver: [{"description": "Landnutzung"}]}}
    result = scoring.evaluate(refs, preds, "c2c", pair_scorer=lambda p, r: [1.0] * len(p))
    assert result["fields"][f"{driver}.description"]["bertscore"] == 1
    assert scoring.field_values(
        {driver: [{"details": "x", "description": ["x", "x"]}]}, f"{driver}.description"
    ) == {"x"}
    with pytest.raises(ValueError, match="conflicting description/details"):
        scoring.field_values(
            {driver: [{"details": "x", "description": "y"}]}, f"{driver}.description"
        )


def test_text_group_aggregation_weights_values_and_keeps_descriptions_independent():
    refs = {
        "a": {
            "direct_driver": [{"category": "A", "description": "text"}],
            "indirect_driver": [{"description": "other"}, {"description": "third"}],
        }
    }
    preds = {"a": {"direct_driver": [{"category": "B", "description": "text"}]}}
    result = scoring.evaluate(refs, preds, "c2c", pair_scorer=lambda p, r: [1.0] * len(p))
    assert result["fields"]["direct_driver.category"]["f1"] == 0
    assert result["fields"]["direct_driver.description"]["bertscore"] == 1
    assert result["fields"]["indirect_driver.description"]["bertscore"] == 0
    assert result["summaries"]["c2c"]["bertscore"] == 0.5


@pytest.mark.parametrize("preds", [{}, {"b": {}}, {"a": {}, "b": {}}])
def test_missing_and_unknown_ids(preds):
    with pytest.raises(ValueError, match="Paper IDs differ"):
        scoring.evaluate({"a": {}}, preds)


@pytest.mark.parametrize(
    "content",
    [
        "",
        "[]\n",
        '{"habitat":[]}\n',
        '{"zotitem_ptr_id":12}\n',
        '{"zotitem_ptr_id":" "}\n',
        '{"zotitem_ptr_id":"a", "habitat":NaN}\n',
        '{"zotitem_ptr_id":"a", "zotitem_ptr_id":"b"}\n',
        '{"zotitem_ptr_id":"a", "taxa":[{"species_group":"x","species_group":"y"}]}\n',
        '{"zotitem_ptr_id":"a"}\n{"zotitem_ptr_id":"a"}\n',
        "{invalid\n",
    ],
)
def test_jsonl_rejects_ambiguous_or_invalid_input(tmp_path, content):
    path = tmp_path / "invalid.jsonl"
    path.write_text(content)
    with pytest.raises(ValueError, match=str(path)):
        scoring.load_jsonl(path)


def test_jsonl_supports_blank_lines_nulls_and_non_ascii(tmp_path):
    path = tmp_path / "valid.jsonl"
    path.write_text(
        '\n{"zotitem_ptr_id":"a", "habitat":"Küsten und Küstengewässer"}\n\n', encoding="utf-8"
    )
    assert scoring.load_jsonl(path)["a"]["habitat"] == "Küsten und Küstengewässer"


def test_isolated_cli_and_codabench_share_results(tmp_path):
    script = tmp_path / "evaluate.py"
    shutil.copyfile(SCRIPT, script)
    refs, preds = tmp_path / "input/ref/references.jsonl", tmp_path / "input/res/predictions.jsonl"
    records = [{"zotitem_ptr_id": "a", "habitat": ["Wald"]}]
    write_records(refs, records)
    write_records(preds, records)
    report = tmp_path / "local.json"
    # -I -S excludes site packages, environment PYTHONPATH and repository modules.
    base = [sys.executable, "-I", "-S", str(script)]
    subprocess.run(  # nosec B603: only test-controlled paths and fixed arguments.
        base
        + [
            "score",
            "--references",
            str(refs),
            "--predictions",
            str(preds),
            "--categorical-only",
            "--output",
            str(report),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    output = tmp_path / "out"
    subprocess.run(  # nosec B603: only test-controlled paths and fixed arguments.
        base + ["codabench", str(tmp_path / "input"), str(output), "--categorical-only"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    local = json.loads(report.read_text())
    assert json.loads((output / "detailed_scores.json").read_text()) == local
    assert json.loads((output / "scores.json").read_text()) == local["scores"]
    assert local["scores"]["c1_score"] == 0.2
    assert "all_bertscore" not in local["scores"]


def test_cli_rejects_extra_submission_file_and_missing_paper(tmp_path, capsys):
    refs, preds = tmp_path / "input/ref/references.jsonl", tmp_path / "input/res/predictions.jsonl"
    write_records(refs, [{"zotitem_ptr_id": "a"}])
    write_records(preds, [{"zotitem_ptr_id": "b"}])
    assert (
        scoring.main(
            ["score", "--references", str(refs), "--predictions", str(preds), "--task", "c1"]
        )
        == 1
    )
    assert "Paper IDs differ" in capsys.readouterr().err
    (preds.parent / "extra.txt").write_text("extra")
    assert scoring.main(["codabench", str(tmp_path / "input"), str(tmp_path / "out")]) == 1
    assert "exactly one file" in capsys.readouterr().err
    assert not (tmp_path / "out/scores.json").exists()


@pytest.mark.parametrize("perturb", [False, True])
def test_parity_with_existing_metrics_on_training_data(perturb):
    data = ROOT / "shared_task/example-data/train.jsonl"
    if not data.is_file():
        pytest.skip("Local course training data is not distributed with the repository")
    refs = scoring.load_jsonl(data)
    preds = deepcopy(refs)
    if perturb:
        for i, record in enumerate(preds.values()):
            if i % 3 == 0:
                for field in ("habitat", "taxa", "soil", "direct_driver"):
                    record.pop(field, None)
            if i % 5 == 0:
                record["climate"] = ["wrong", "wrong", " ", None]
                record["ecosystem_type"] = [{"category": "wrong", "term": "wrong"}]
    result = scoring.evaluate(refs, preds, categorical_only=True, pair_scorer=no_model)
    fields = list(result["fields"])
    metric = F1MicroMultipleFieldsMetric(fields=fields, flatten_dicts=True)
    for record_id in refs:
        metric.update(prediction=preds[record_id], reference=refs[record_id], record_id=record_id)
    expected = metric.compute(reset=False)
    for field in fields:
        actual = result["fields"][field]
        assert {k: actual[k] for k in ("precision", "recall", "f1", "support")} == expected[field]
        assert {k: actual[k] for k in ("tp", "fp", "fn")} == metric.metrics[field].state_count
    assert result["summaries"]["all"]["macro_f1"] == pytest.approx(expected["AVG"]["f1"])
    assert result["summaries"]["all"]["micro"]["f1"] == expected["ALL"]["f1"]


def test_unmodified_training_data_has_scored_driver_text():
    data = ROOT / "shared_task/example-data/train.jsonl"
    if not data.is_file():
        pytest.skip("Local course training data is not distributed with the repository")
    records = scoring.load_jsonl(data)
    result = scoring.evaluate(
        records, records, pair_scorer=lambda p, r: [float(a == b) for a, b in zip(p, r)]
    )
    assert len(result["fields"]) == 19
    for field in scoring.TEXT_FIELDS:
        assert result["fields"][field]["reference_values"] > 0
        assert result["fields"][field]["bertscore"] == 1
