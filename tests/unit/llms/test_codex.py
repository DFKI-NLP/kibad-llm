"""Tests for file-backed Codex extraction and native usage reporting."""

import json
from pathlib import Path
import subprocess  # nosec B404  # Used to run the fixed probe script and simulate CLI results.

from hydra.utils import instantiate
from llama_index.core.base.llms.types import MessageRole
import pytest

from kibad_llm.extractors.base import extract_from_text, extract_from_text_lenient
from kibad_llm.llms.codex import Codex
from kibad_llm.llms.request import MissingBindingError, SimpleChatMessage
from tests.conftest import cfg_global

CODEX_PRESET = "faktencheck_core_fields_schema_with_evidence_codex"


@pytest.mark.parametrize("include_document", [False, True])
@pytest.mark.parametrize("include_schema_file", [False, True])
def test_codex_stages_only_files_referenced_by_filename_placeholders(
    tmp_path, monkeypatch, include_document, include_schema_file
):
    """Stage and probe exactly the files referenced on a first turn, including no files."""
    backend = Codex("test-model", "high", 30, str(tmp_path))
    schema = {"type": "object", "properties": {"habitat": {"const": "Wälder"}}}
    document = "# Original Markdown\nWälder\n"
    user = "Read {document_filename}." if include_document else "Return the fields."
    user += "\n{schema_filename}" if include_schema_file else "\n{schema}"
    request = backend.prepare_request(
        {
            "user_message": user,
            "document_filename_placeholder": "document_filename",
            "schema_filename_placeholder": "schema_filename",
            "schema_placeholder": "schema",
        },
        document=document,
        schema=schema,
    )
    expected = {}
    if include_document:
        expected["input.md"] = document
    if include_schema_file:
        expected["schema.json"] = json.dumps(schema, ensure_ascii=False)
    assert request.input_artifacts == expected
    run_shell = subprocess.run

    def run_cli(args, *, cwd, **kwargs):
        """Check staged file contents and probe arguments, then simulate inference."""
        assert {path.name: path.read_text(encoding="utf-8") for path in cwd.iterdir()} == expected
        if args[1] == "sandbox":
            filenames = args[args.index("probe") + 1 : args.index("--")]
            assert set(filenames) == set(expected)
            protected = str(tmp_path / "unavailable-private-file")
            probe = run_shell(
                ["/bin/sh", "-ec", args[4], "probe", *filenames, "--", protected],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert probe.returncode == 0, probe.stderr
            if not expected:
                missing_input = run_shell(
                    ["/bin/sh", "-ec", args[4], "probe", "missing.md", "--", protected],
                    cwd=cwd,
                    capture_output=True,
                    timeout=5,
                )
                assert missing_input.returncode != 0
        else:
            Path(args[args.index("--output-last-message") + 1]).write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setenv("CODEX_API_KEY", "test")
    monkeypatch.setattr("kibad_llm.llms.codex.shutil.which", lambda _: "/usr/bin/codex")
    monkeypatch.setattr("kibad_llm.llms.codex.subprocess.run", run_cli)
    kwargs = {"input_artifacts": request.input_artifacts} if request.input_artifacts else {}

    response = backend.call_llm_chat_with_guided_decoding(request.messages, **kwargs)

    assert response.message.content == "{}"


def test_codex_can_supply_the_same_schema_inline_and_as_a_file(tmp_path):
    """Create the schema file when requested alongside its inline representation."""
    backend = Codex("test-model", "high", 30, str(tmp_path))
    request = backend.prepare_request(
        {
            "user_message": "{schema_filename}\n{schema}",
            "schema_filename_placeholder": "schema_filename",
            "schema_placeholder": "schema",
        },
        document="Source",
        schema={"type": "string", "const": "Wälder"},
    )

    schema_file, inline_schema = request.current_messages[0].content.split("\n", maxsplit=1)
    assert request.input_artifacts == {schema_file: inline_schema}


@pytest.mark.parametrize(
    "template",
    [
        "Read input.md and schema.json; {schema}",
        "{{document_filename}} {{schema_filename}}; {schema}",
    ],
)
def test_codex_does_not_attach_files_for_literals_or_rendered_values(tmp_path, template):
    """Literal filenames and placeholder text inside a schema do not request files."""
    backend = Codex("test-model", "high", 30, str(tmp_path))
    schema = {"description": "Literal {document_filename} and {schema_filename}"}

    request = backend.prepare_request(
        {
            "user_message": template,
            "document_filename_placeholder": "document_filename",
            "schema_filename_placeholder": "schema_filename",
            "schema_placeholder": "schema",
        },
        document="Source",
        schema=schema,
    )

    assert request.input_artifacts == {}


def test_schema_file_uses_prompt_schema_and_custom_filename_placeholders(tmp_path, monkeypatch):
    """Use the evidence-adjusted prompt schema and preserve the original schema."""
    cfg = cfg_global(
        out_dir=tmp_path,
        overrides=[
            f"experiment/predict={CODEX_PRESET}",
            "extractor.prompt_template.document_filename_placeholder=source_file",
            "extractor.prompt_template.schema_filename_placeholder=output_file",
        ],
    )
    backend = instantiate(cfg.extractor.llm)
    schema = {"type": "object", "properties": {"habitat": {"type": "string"}}}
    inputs = {}

    def run(input_artifacts, prompt, artifact, events):
        """Capture prepared inputs and return evidence-wrapped extraction content."""
        inputs.update(input_artifacts)
        events.write_text("", encoding="utf-8")
        return json.dumps({"habitat": {"content": "Wald", "evidence_anchor": "Wälder"}})

    monkeypatch.setattr(backend, "_run", run)
    result = extract_from_text(
        text="Wälder",
        text_id="fixture",
        prompt_template={
            **cfg.extractor.prompt_template,
            "system_message": "Use {output_file}",
            "user_message": "Read {source_file}",
        },
        llm=backend,
        schema=schema,
        use_guided_decoding=False,
        adjust_schema_for_evidence_detection=True,
        adjust_schema_description_for_evidence_detection=True,
        return_messages_formatted=True,
    )

    assert result.errors == []
    assert result.structured == {"habitat": "Wald"}
    assert result.messages_formatted == {"system": "Use schema.json", "user": "Read input.md"}
    assert inputs["input.md"] == "Wälder"
    field = json.loads(inputs["schema.json"])["properties"]["habitat"]
    assert "evidence_anchor" in field["properties"]
    assert schema == {"type": "object", "properties": {"habitat": {"type": "string"}}}


def test_codex_requires_schema_when_its_filename_is_referenced(tmp_path):
    """Fail before inference if the requested schema file has no schema value."""
    backend = Codex("test-model", "high", 30, str(tmp_path))

    with pytest.raises(MissingBindingError) as raised:
        backend.prepare_request(
            {
                "system_message": "Use {schema_filename}",
                "user_message": "Read {document_filename}",
                "schema_filename_placeholder": "schema_filename",
                "document_filename_placeholder": "document_filename",
            },
            document="Source",
            schema=None,
        )
    assert raised.value.placeholder == "schema_filename"
    assert raised.value.role == MessageRole.SYSTEM
    assert not list(tmp_path.iterdir())


def test_extractor_accepts_initial_codex_turn_without_files(tmp_path, monkeypatch):
    """Pass a first-turn prompt with no filename fields through to Codex."""
    backend = Codex("test-model", "high", 30, str(tmp_path))

    def run(input_artifacts, prompt, artifact, events):
        """Return a model response for the fileless prompt."""
        assert input_artifacts == {}
        assert "Return an empty object." in prompt
        events.write_text("", encoding="utf-8")
        return "{}"

    monkeypatch.setattr(backend, "_run", run)
    result = extract_from_text(
        text="Source",
        text_id="fixture",
        prompt_template={"user_message": "Return an empty object."},
        use_guided_decoding=False,
        llm=backend,
    )
    assert result.errors == []
    assert result.structured == {}


@pytest.mark.parametrize("filename", ["notes.txt", "../outside.md"])
def test_codex_rejects_unsupported_input_filenames_before_creating_artifacts(tmp_path, filename):
    """Restrict staged inputs to the backend's document and schema filenames."""
    artifact_dir = tmp_path / "codex"
    backend = Codex("test-model", "high", 30, str(artifact_dir))

    with pytest.raises(ValueError, match="Unsupported Codex input filenames"):
        backend.call_llm_chat_with_guided_decoding([], input_artifacts={filename: "Source"})
    assert not artifact_dir.exists()


@pytest.mark.parametrize(
    "options, message",
    [
        ({"json_schema": {}}, "does not support guided decoding"),
        ({"json_schema": {"type": "object"}}, "does not support guided decoding"),
        ({"temperature": 0.0}, "additional request parameters: temperature"),
        ({"temperature": 0.0, "seed": None}, "additional request parameters: seed, temperature"),
    ],
)
def test_codex_rejects_unsupported_options_before_creating_artifacts(
    tmp_path, monkeypatch, options, message
):
    """Reject unsupported options without starting the CLI or creating run artifacts."""
    artifact_dir = tmp_path / "codex"
    backend = Codex("test-model", "high", 30, str(artifact_dir))

    def run(*args):
        """Fail if an unsupported request reaches CLI execution."""
        pytest.fail("Unsupported request reached CLI execution")

    monkeypatch.setattr(backend, "_run", run)
    with pytest.raises(ValueError, match=message):
        backend.call_llm_chat_with_guided_decoding(
            [SimpleChatMessage(role=MessageRole.USER, content="Read input.md")],
            input_artifacts={"input.md": "Source Markdown"},
            **options,
        )
    assert not artifact_dir.exists()


@pytest.mark.parametrize(
    "override, message",
    [
        ("++extractor.use_guided_decoding=true", "does not support guided decoding"),
        (
            "+extractor.request_parameters.temperature=0.0",
            "additional request parameters: temperature",
        ),
    ],
)
def test_unsupported_preset_options_use_existing_error_result(
    tmp_path, monkeypatch, override, message
):
    """Record invalid configuration through the extractor without starting inference."""
    cfg = cfg_global(
        out_dir=tmp_path,
        overrides=[f"experiment/predict={CODEX_PRESET}", override],
    )

    def run(*args):
        """Fail if an invalid preset reaches CLI execution."""
        pytest.fail("Invalid preset reached CLI execution")

    monkeypatch.setattr(Codex, "_run", run)
    result = instantiate(cfg.extractor, _convert_="all")("Source Markdown", "fixture")

    assert len(result.errors) == 1
    assert result.errors[0].startswith("ValueError:")
    assert message in result.errors[0]
    assert not (tmp_path / "codex").exists()


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
        """Verify the staged document and simulate the CLI's final response and usage."""
        assert (cwd / "input.md").read_bytes() == document.encode()
        assert not (cwd / "schema.json").exists()
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
    assert "{document_filename}" in result.messages["user"]
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
        ({"user_message": "{schema:{document}}", "schema_placeholder": "schema"}, "document"),
    ],
)
def test_codex_rejects_inline_template_before_inference(tmp_path, template, placeholder):
    """Reject inline document bindings in either role, including custom field names."""
    backend = Codex("test-model", "medium", 30, str(tmp_path))

    with pytest.raises(MissingBindingError) as raised:
        extract_from_text(
            text="# Fixture",
            text_id="fixture",
            prompt_template={**template, "document_placeholder": placeholder},
            llm=backend,
            schema={},
            use_guided_decoding=False,
        )
    assert raised.value.placeholder == placeholder
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "field", ["missing", "schema", "schema_description", "document_filename", "schema_filename"]
)
def test_codex_reports_undeclared_fields(tmp_path, field):
    """Document and schema inputs only bind fields declared by the template."""
    backend = Codex("test-model", "high", 600, str(tmp_path))
    with pytest.raises(MissingBindingError) as raised:
        backend.prepare_request(
            {"user_message": f"Read {{{field}}}"}, document="Source", schema={}
        )
    assert raised.value.placeholder == field
    assert raised.value.role == MessageRole.USER


def test_codex_reads_filename_fields_per_template(tmp_path):
    """Resolve both file bindings from the template on each call to the same backend."""
    backend = Codex("test-model", "high", 30, str(tmp_path))
    for source, spec in [("article", "format"), ("paper", "output_schema")]:
        request = backend.prepare_request(
            {
                "user_message": f"Read {{{source}}} using {{{spec}}}.",
                "document_filename_placeholder": source,
                "schema_filename_placeholder": spec,
            },
            document="Text",
            schema={},
        )
        assert request.current_messages[0].content == "Read input.md using schema.json."
        assert request.input_artifacts == {"input.md": "Text", "schema.json": "{}"}


def test_prepare_request_preserves_history_and_custom_schema_placeholders(tmp_path):
    """Render custom schema bindings while leaving escaped document fields literal."""
    backend = Codex("test-model", "high", 600, str(tmp_path))
    history = [SimpleChatMessage(role=MessageRole.USER, content="Previous turn")]
    schema = {"type": "object", "properties": {"habitat": {"type": "string"}}}
    document = "# Original Markdown\n"
    request = backend.prepare_request(
        {
            "system_message": "{description}",
            "user_message": "Read {source_file}; {{markdown}} is literal.\n{output_schema}",
            "document_filename_placeholder": "source_file",
            "document_placeholder": "markdown",
            "schema_placeholder": "output_schema",
            "schema_description_placeholder": "description",
        },
        document=document,
        schema=schema,
        history=history,
    )

    system, user = request.current_messages
    assert "habitat" in system.content
    assert user.content.startswith("Read input.md; {markdown} is literal.")
    assert json.loads(user.content.split("\n", maxsplit=1)[1]) == schema
    assert request.messages == [*history, system, user]
    assert history == [SimpleChatMessage(role=MessageRole.USER, content="Previous turn")]
    assert request.input_artifacts == {"input.md": document}
    assert all(document not in message.content for message in request.messages)


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

    def fail(input_artifacts, prompt, artifact, events):
        """Simulate a failed CLI execution with an incomplete event log."""
        events.write_text('{"type":', encoding="utf-8")
        raise error

    monkeypatch.setattr(backend, "_run", fail)
    result = extract_from_text_lenient(
        text="Source Markdown",
        text_id="fixture",
        prompt_template={
            "user_message": "Read {document_filename}",
            "document_filename_placeholder": "document_filename",
        },
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

    def run(input_artifacts, prompt, artifact, events):
        """Return valid extraction content alongside malformed CLI events."""
        events.write_text(event_log, encoding="utf-8")
        return "{}"

    monkeypatch.setattr(backend, "_run", run)
    result = extract_from_text(
        text="Source",
        text_id="fixture",
        prompt_template={
            "user_message": "Read {document_filename}",
            "document_filename_placeholder": "document_filename",
        },
        llm=backend,
        use_guided_decoding=False,
    )
    assert result.structured == {}
    assert result.backend_metadata is None
    assert len(result.errors) == 1
    assert result.errors[0].startswith(("JSONDecodeError:", "TypeError:"))
