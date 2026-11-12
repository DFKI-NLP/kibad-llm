import json
from pathlib import Path
import subprocess  # nosec B404  # Used only to simulate TimeoutExpired.

from hydra.utils import instantiate
import pytest

from kibad_llm.extractors.base import extract_from_text
from kibad_llm.llms.base import BackendExecutionError
from kibad_llm.llms.codex import Codex
from tests.conftest import cfg_global

CODEX_PRESET = "faktencheck_core_fields_schema_with_evidence_codex"


def test_file_backed_preset_stages_markdown_and_uses_only_template_messages(tmp_path, monkeypatch):
    cfg = cfg_global(
        out_dir=tmp_path,
        overrides=[
            f"experiment/predict={CODEX_PRESET}",
            "extractor.return_messages=true",
            "extractor.return_messages_formatted=true",
            "+extractor.truncate_user_message_formatted=null",
        ],
    )
    assert cfg.extractor.llm.reasoning_effort == "high"
    assert cfg.extractor.llm.timeout == 600

    quote = "Untersucht wurden Wälder."
    document = f"# Ergebnis\n\n{quote}\n"
    answer = {
        "habitat": [{"content": "Wald", "evidence_anchor": quote}],
        "taxa": [],
        "biodiversity_level": [],
        "ecosystem_type": [],
    }

    def run_cli(args, *, cwd, **kwargs):
        assert (cwd / "input.md").read_bytes() == document.encode()
        if args[1] == "sandbox":
            (cwd / "probe").touch()
        else:
            final = Path(args[args.index("--output-last-message") + 1])
            final.write_text(json.dumps(answer), encoding="utf-8")
            kwargs["stdout"].write(json.dumps({"usage": {"input_tokens": 12}}) + "\n")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setenv("CODEX_API_KEY", "test")
    monkeypatch.setattr("kibad_llm.llms.codex.shutil.which", lambda _: "/usr/bin/codex")
    monkeypatch.setattr(
        "kibad_llm.llms.codex.subprocess.check_output", lambda *a, **kw: "codex test"
    )
    monkeypatch.setattr("kibad_llm.llms.codex.subprocess.run", run_cli)

    result = instantiate(cfg.extractor, _convert_="all")(document, "fixture")

    assert result.errors == []
    assert result.structured["habitat"] == ["Wald"]
    assert result.backend_metadata["input_tokens"] == 12
    assert result.messages["user"].endswith("{schema}\n")
    system = result.messages_formatted["system"]
    user = result.messages_formatted["user"]
    (prompt_file,) = tmp_path.glob("codex/*/prompt.txt")
    prompt = prompt_file.read_text(encoding="utf-8")
    assert prompt == f"system:\n{system}\n\nuser:\n{user}"
    assert prompt.count("input.md") == 1
    assert quote not in prompt
    assert "evidence_anchor" in system
    schema = json.loads(user.split("\n\n", maxsplit=1)[1])
    assert "evidence_anchor" in schema["properties"]["habitat"]["items"]["properties"]


def test_codex_rejects_inline_template_before_inference(tmp_path):
    backend = Codex("test-model", "medium", 30, str(tmp_path))

    with pytest.raises(ValueError, match=CODEX_PRESET):
        extract_from_text(
            text="# Fixture",
            text_id="fixture",
            prompt_template={"user_message": "Read {document}"},
            llm=backend,
            use_guided_decoding=False,
        )
    assert not list(tmp_path.iterdir())


def test_timeout_keeps_partial_usage(tmp_path, monkeypatch):
    backend = Codex("test-model", "medium", 30, str(tmp_path))

    def timeout(document, prompt, artifact, events, metadata):
        metadata["attempt_count"] = 1
        event = {"type": "turn.completed", "usage": {"input_tokens": 9, "cached_input_tokens": 4}}
        events.write_text(json.dumps(event) + "\n" + '{"type":', encoding="utf-8")
        raise subprocess.TimeoutExpired("codex", 30)

    monkeypatch.setattr(backend, "_run", timeout)
    with pytest.raises(BackendExecutionError) as raised:
        backend.call_llm_chat_with_guided_decoding([], input_artifacts={"input.md": "fixture"})

    metadata = raised.value.metadata
    assert metadata["input_tokens"] == 9
    assert metadata["cached_input_tokens"] == 4
    assert metadata["output_tokens"] is None
    assert metadata["attempt_count"] == 1
    assert metadata["backend_elapsed_seconds"] >= 0
    assert (tmp_path.parent / Path(metadata["execution_events"])).is_file()
