import json
from pathlib import Path
import subprocess  # nosec B404  # Used only to simulate TimeoutExpired.

from hydra.utils import instantiate
from llama_index.core.base.llms.types import MessageRole
import pytest

from kibad_llm.extractors.base import extract_from_text
from kibad_llm.llms.base import BackendExecutionError
from kibad_llm.llms.codex import Codex
from kibad_llm.llms.request import ExtractionPrompt, SimpleChatMessage
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


@pytest.mark.parametrize(
    "template, placeholder",
    [
        ({"user_message": "Read {document}"}, "document"),
        ({"system_message": "Read {markdown!s}"}, "markdown"),
        ({"user_message": "Read {document[0]}"}, "document"),
        ({"user_message": "{schema:{document}}"}, "document"),
    ],
)
def test_codex_rejects_inline_template_before_inference(tmp_path, template, placeholder):
    """Reject inline document bindings in either role, including custom field names."""
    backend = Codex("test-model", "medium", 30, str(tmp_path))

    with pytest.raises(ValueError, match=CODEX_PRESET):
        extract_from_text(
            text="# Fixture",
            text_id="fixture",
            prompt_template={**template, "document_placeholder": placeholder},
            llm=backend,
            schema={},
            use_guided_decoding=False,
        )
    assert not list(tmp_path.iterdir())


def test_codex_reports_unrelated_missing_bindings(tmp_path):
    """Preserve the shared renderer's error for an unrelated missing field."""
    backend = Codex("test-model", "high", 600, str(tmp_path))
    with pytest.raises(ValueError, match="No value for placeholder 'missing' in USER message"):
        backend.prepare_request(
            ExtractionPrompt(document="Source", schema=None, user_message="Read {missing}")
        )


def test_prepare_request_preserves_history_and_custom_schema_placeholders(tmp_path):
    """Render custom schema bindings while leaving escaped document fields literal."""
    backend = Codex("test-model", "high", 600, str(tmp_path))
    history = [SimpleChatMessage(role=MessageRole.USER, content="Previous turn")]
    schema = {"type": "object", "properties": {"habitat": {"type": "string"}}}
    prompt = ExtractionPrompt(
        document="# Original Markdown\n",
        schema=schema,
        system_message="{description}",
        user_message="Read input.md; {{markdown}} is literal.\n{output_schema}",
        history=history,
        document_placeholder="markdown",
        schema_placeholder="output_schema",
        schema_description_placeholder="description",
    )

    request = backend.prepare_request(prompt)

    system, user = request.current_messages
    assert "habitat" in system.content
    assert user.content.startswith("Read input.md; {markdown} is literal.")
    assert json.loads(user.content.split("\n", maxsplit=1)[1]) == schema
    assert request.messages == [*history, system, user]
    assert history == [SimpleChatMessage(role=MessageRole.USER, content="Previous turn")]
    assert request.input_artifacts == {"input.md": prompt.document}
    assert all(prompt.document not in message.content for message in request.messages)


def test_failed_execution_keeps_metadata_and_current_prompt_snapshot(tmp_path, monkeypatch):
    """Keep partial execution metadata and truncate only the recorded current turn."""
    backend = Codex("test-model", "high", 600, str(tmp_path))
    document = "# Source Markdown"
    history = [SimpleChatMessage(role=MessageRole.USER, content="Previous turn")]
    user_message = "Read input.md and extract the fields."
    metadata = {"input_tokens": 9, "attempt_count": 1}

    def fail(messages, *, json_schema, input_artifacts):
        """Verify the complete request before simulating a backend failure."""
        assert messages == [
            *history,
            SimpleChatMessage(role=MessageRole.USER, content=user_message),
        ]
        assert json_schema is None
        assert input_artifacts == {"input.md": document}
        raise BackendExecutionError("Timed out", metadata)

    monkeypatch.setattr(backend, "call_llm_chat_with_guided_decoding", fail)
    result = extract_from_text(
        text=document,
        text_id="fixture",
        prompt_template={"user_message": user_message},
        llm=backend,
        use_guided_decoding=False,
        history=history,
        return_messages=True,
        return_messages_formatted=True,
        truncate_user_message_formatted=5,
    )

    assert result.errors == ["BackendExecutionError: Timed out"]
    assert result.backend_metadata == metadata
    assert result.messages == {"system": None, "user": user_message}
    assert result.messages_formatted == {"user": "Read ... (truncated @ 5 chars)"}


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
