"""Tests for file-backed Codex extraction and native usage reporting."""

import json
from pathlib import Path
import subprocess  # nosec B404  # Used only to simulate TimeoutExpired.

from hydra.utils import instantiate
from llama_index.core.base.llms.types import MessageRole
import pytest

from kibad_llm.extractors.base import extract_from_text, extract_from_text_lenient
from kibad_llm.llms.codex import Codex
from kibad_llm.llms.request import ExtractionPrompt, SimpleChatMessage
from tests.conftest import cfg_global

CODEX_PRESET = "faktencheck_core_fields_schema_with_evidence_codex"


@pytest.mark.parametrize(
    "usage_reports",
    [
        [],
        [{"input_tokens": 12, "cached_input_tokens": 4, "output_tokens": 3}],
        [{"input_tokens": 12}, {"input_tokens": 7, "output_tokens": 2}],
    ],
)
@pytest.mark.parametrize("invalid_json", [False, True])
def test_file_backed_preset_stages_markdown_and_uses_only_template_messages(
    tmp_path, monkeypatch, usage_reports, invalid_json
):
    """Use the shared metadata callback and retain usage when JSON postprocessing fails."""
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
            final.write_text(
                "invalid JSON" if invalid_json else json.dumps(answer), encoding="utf-8"
            )
            for usage in usage_reports:
                kwargs["stdout"].write(
                    json.dumps({"type": "turn.completed", "usage": usage}) + "\n"
                )
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setenv("CODEX_API_KEY", "test")
    monkeypatch.setattr("kibad_llm.llms.codex.shutil.which", lambda _: "/usr/bin/codex")
    monkeypatch.setattr("kibad_llm.llms.codex.subprocess.run", run_cli)

    result = instantiate(cfg.extractor, _convert_="all")(document, "fixture")

    if invalid_json:
        assert len(result.errors) == 1
        assert result.errors[0].startswith("JSONDecodeError:")
    else:
        assert result.errors == []
        assert result.structured["habitat"] == ["Wald"]
    expected_metadata = {"usage": usage_reports} if usage_reports else None
    assert result.backend_metadata == expected_metadata
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


@pytest.mark.parametrize(
    "error",
    [
        subprocess.TimeoutExpired("codex", 30),
        ValueError("Codex did not produce a final response."),
    ],
)
def test_failed_execution_uses_existing_error_result(tmp_path, monkeypatch, error):
    """Record execution failures through the existing extractor and retain CLI diagnostics."""
    backend = Codex("test-model", "high", 30, str(tmp_path))

    def fail(document, prompt, artifact, events):
        """Simulate a failed CLI execution with an incomplete event log."""
        events.write_text('{"type":', encoding="utf-8")
        raise error

    monkeypatch.setattr(backend, "_run", fail)
    result = extract_from_text_lenient(
        text="Source Markdown",
        text_id="fixture",
        prompt_template={"user_message": "Read input.md"},
        llm=backend,
        use_guided_decoding=False,
    )
    assert len(result.errors) == 1
    assert result.errors[0].startswith(type(error).__name__ + ":")
    assert result.backend_metadata is None
    (error_file,) = tmp_path.glob("*/error.txt")
    assert error_file.read_text(encoding="utf-8") == str(error)
    assert error_file.with_name("events.jsonl").is_file()


@pytest.mark.parametrize("event_log", ['{"usage":', '{"usage": "invalid"}'])
def test_metadata_error_does_not_discard_response(tmp_path, monkeypatch, event_log):
    """Use the shared callback error handling when CLI usage cannot be parsed."""
    backend = Codex("test-model", "high", 30, str(tmp_path))

    def run(document, prompt, artifact, events):
        """Return valid extraction content alongside malformed CLI events."""
        events.write_text(event_log, encoding="utf-8")
        return "{}"

    monkeypatch.setattr(backend, "_run", run)
    result = extract_from_text(
        text="Source",
        text_id="fixture",
        prompt_template={"user_message": "Read input.md"},
        llm=backend,
        use_guided_decoding=False,
    )
    assert result.structured == {}
    assert result.backend_metadata is None
    assert len(result.errors) == 1
    assert result.errors[0].startswith(("JSONDecodeError:", "TypeError:"))
