import json
import os
from types import SimpleNamespace
from typing import Any

from datasets import Dataset
from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from hydra.utils import instantiate
from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from omegaconf import DictConfig
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.llms.base import LLM
from tests.conftest import WRITE_FIXTURE_DATA, cfg_global

pytestmark = pytest.mark.usefixtures("llm_chat_replay")

# strip extension to have nicer logging output, e.g. tests/test_extractors.py::test_extractor[simple]
# and exclude folders (without extension) and helper configs starting with "_"
AVAILABLE_EXTRACTORS = [
    os.path.splitext(extractor_yaml)[0]
    for extractor_yaml in os.listdir(PROJ_ROOT / "configs" / "extractor")
    if os.path.splitext(extractor_yaml)[1] != "" and not extractor_yaml.startswith("_")
]


@pytest.fixture(scope="function", params=AVAILABLE_EXTRACTORS)
def extractor_name(request) -> str:
    return request.param


@pytest.fixture(scope="function")
def cfg_predict_extractor(tmp_path, extractor_name) -> DictConfig:  # type: ignore
    overrides = [f"extractor={extractor_name}"]

    # use the gpt_oss_20b llm for testing since we monkeypatch its self.model.chat method
    overrides.append("extractor/llm=gpt_oss_20b")

    if extractor_name in ["union", "multi_pass", "conditional_union"]:
        # For union extractors, we need to define extractor overrides. Use two simple
        # setups (setup_a and setup_b) with different schemas.
        overrides.append("+extractor/schema@extractor.overrides.setup_a.schema=faktencheck_simple")
        overrides.append(
            "+extractor/schema@extractor.overrides.setup_b.schema=faktencheck_compounds_simple"
        )

    cfg = cfg_global(
        out_dir=tmp_path,
        overrides=overrides,
        config_name="predict.yaml",
    )

    yield cfg

    GlobalHydra.instance().clear()


def test_extractor(tmp_path, cfg_predict_extractor, extractor_name):

    HydraConfig().set_config(cfg_predict_extractor)

    file_name = "25ABQZIH.pdf"

    # read markdown from fixture
    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    text = markdown_data["text"]

    extractor = instantiate(cfg_predict_extractor.extractor, _convert_="all")
    result = extractor(text_id=file_name, text=text)

    expected_result_path = (
        PROJ_ROOT / "tests" / "fixtures" / "extractor" / f"{extractor_name}.{file_name}.json"
    )
    if WRITE_FIXTURE_DATA:
        # create directory if it does not exist
        expected_result_path.parent.mkdir(parents=True, exist_ok=True)
        # write fixture data
        with open(expected_result_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    with open(expected_result_path) as f:
        expected_result = json.load(f)

    # ensure that there are no errors
    if extractor_name == "simple":
        assert result["errors"] == []
    else:
        errors_list = result["errors_list"]
        assert errors_list == [[]] * len(errors_list)

    # check top-level keys
    assert set(result) == set(expected_result)

    # just check keys since the actual values are not deterministic
    assert set(result["structured"]) == set(expected_result["structured"])


def test_extractor_preserves_backend_metadata_in_jsonl(
    tmp_path, cfg_predict_extractor, extractor_name
) -> None:
    """Keep each call's usage through the configured workflow and prediction serialization."""

    class TestLLM(LLM):
        """Return different usage for each call to detect dropped or combined records."""

        def __init__(self) -> None:
            """Collect expected metadata in the order of backend calls."""
            self.metadata: list[dict[str, Any]] = []

        def call_llm_chat_with_guided_decoding(self, messages, **kwargs) -> ChatResponse:
            """Return valid empty content and monotonically increasing usage counts."""
            count = len(self.metadata) + 1
            usage = {"prompt_tokens": count, "completion_tokens": 1, "total_tokens": count + 1}
            self.metadata.append({"usage": usage})
            return ChatResponse(
                message=ChatMessage(content="{}"), raw=SimpleNamespace(usage=usage)
            )

    if "max_char_buffer" in cfg_predict_extractor.extractor:
        cfg_predict_extractor.extractor.max_char_buffer = 16
    HydraConfig().set_config(cfg_predict_extractor)
    extractor = instantiate(cfg_predict_extractor.extractor, _convert_="all")
    backend = TestLLM()
    result = extractor(
        text_id="test",
        text="First sentence. Second sentence.",
        llm=backend,
        use_guided_decoding=False,
        validate_with_schema=False,
        return_reasoning=False,
        adjust_schema_for_evidence_detection=False,
        response_has_metadata=False,
    )

    output_file = tmp_path / "predictions.jsonl"
    Dataset.from_list([dict(result)]).to_json(output_file)
    saved_result = json.loads(output_file.read_text())
    assert backend.metadata
    if extractor_name == "simple":
        assert saved_result["backend_metadata"] == backend.metadata[0]
        assert saved_result["errors"] == []
    else:
        assert len(backend.metadata) > 1
        assert saved_result["backend_metadata_list"] == backend.metadata
        assert saved_result["errors_list"] == [[]] * len(backend.metadata)


@pytest.mark.parametrize(
    ("extractor_name", "include_evidence"), [("simple", False), ("chunking", True)]
)
def test_extractor_preserves_confidence_in_jsonl(
    tmp_path, extractor_name, include_evidence
) -> None:
    """Keep per-call trend scores beside the extracted values in prediction JSONL."""
    sentence = "Forest birds declined."
    trend = {
        "Hauptgruppe_RoteListen": "Wirbeltiere",
        "Untergruppe_RoteListen": None,
        "Lebensraum": "Wald",
        "Antwortvariable": "Artenzahl",
        "Trend": "negative",
    }
    evidence = {"evidence_anchor": sentence} if include_evidence else {}
    scores = iter((0.25, 1))

    class TestLLM(LLM):
        """Return a trend with a different confidence for each call."""

        def call_llm_chat_with_guided_decoding(
            self, messages, *, json_schema=None, **kwargs
        ) -> ChatResponse:
            """Return a mock trend and verify the wrapped schema reaches the backend."""
            assert json_schema is not None
            trend_properties = json_schema["$defs"]["OrganismBiodiversityTrend"]["properties"]
            assert set(trend_properties["Trend"]["properties"]) == {
                "content",
                "confidence",
                *evidence,
            }
            score = next(scores)
            wrapped = {
                field: (
                    {"content": value, "confidence": score, **evidence}
                    if value is not None
                    else None
                )
                for field, value in trend.items()
            }
            return ChatResponse(
                message=ChatMessage(content=json.dumps({"organism_trends": [wrapped]}))
            )

    overrides = [
        f"extractor={extractor_name}",
        "extractor/schema=organism_trends",
        "extractor/llm=dry-run",
        "extractor.include_confidence=true",
        f"extractor.adjust_schema_for_evidence_detection={str(include_evidence).lower()}",
        "extractor.return_reasoning=false",
    ]
    if extractor_name == "chunking":
        overrides.append(f"extractor.max_char_buffer={len(sentence) + 1}")
    cfg = cfg_global(out_dir=tmp_path, overrides=overrides)
    extractor = instantiate(cfg.extractor, _convert_="all")
    backend = TestLLM()
    result = extractor(text_id="test", text=f"{sentence} {sentence}", llm=backend)

    output_file = tmp_path / "predictions.jsonl"
    Dataset.from_list([dict(result)]).to_json(output_file)
    saved = json.loads(output_file.read_text())
    assert saved["structured"] == {"organism_trends": [trend]}
    if extractor_name == "simple":
        assert saved["errors"] == []
        wrapped = saved["structured_with_metadata"]["organism_trends"][0]
        assert wrapped["Trend"] == {"content": "negative", "confidence": 0.25}
        assert wrapped["Untergruppe_RoteListen"] is None
    else:
        assert saved["errors_list"] == [[], []]
        entries = [
            item["organism_trends"][0]["Trend"] for item in saved["structured_with_metadata_list"]
        ]
        assert [entry["confidence"] for entry in entries] == [0.25, 1]
        assert [entry["evidence_anchor"] for entry in entries] == [sentence, sentence]
