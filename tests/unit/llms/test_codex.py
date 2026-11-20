"""Tests for file-backed Codex extraction and native usage reporting."""

import json
from pathlib import Path
import subprocess  # nosec B404  # Used to run the fixed probe script and simulate CLI results.

from hydra.utils import instantiate
from llama_index.core.base.llms.types import ChatMessage, ChatResponse, MessageRole
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
        {"user_message": user},
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
        {"user_message": "{schema_filename}\n{schema}"},
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
        {"user_message": template},
        document="Source",
        schema=schema,
    )

    assert request.input_artifacts == {}


def test_schema_file_uses_evidence_adjusted_prompt_schema(tmp_path, monkeypatch):
    """Use the evidence-adjusted prompt schema and preserve the original schema."""
    cfg = cfg_global(
        out_dir=tmp_path,
        overrides=[f"experiment/predict={CODEX_PRESET}"],
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
            "system_message": "Use {schema_filename}",
            "user_message": "Read {document_filename}",
        },
        llm=backend,
        schema=schema,
        use_guided_decoding=False,
        include_evidence=True,
        use_wrapped_schema_in_prompt=True,
        return_messages_formatted=True,
    )

    assert result.errors == []
    assert result.structured == {"habitat": "Wald"}
    assert result.messages_formatted == {"system": "Use schema.json", "user": "Read input.md"}
    assert inputs["input.md"] == "Wälder"
    field = json.loads(inputs["schema.json"])["properties"]["habitat"]
    assert "evidence_anchor" in field["properties"]
    assert schema == {"type": "object", "properties": {"habitat": {"type": "string"}}}


@pytest.mark.parametrize("field", ["schema", "schema_description", "schema_filename"])
def test_codex_requires_schema_for_referenced_field(tmp_path, field):
    """Name the field that requested the missing schema before inference."""
    backend = Codex("test-model", "high", 30, str(tmp_path))

    with pytest.raises(ValueError, match=rf"\{{{field}\}}.*requires a schema"):
        backend.prepare_request(
            {"system_message": f"Use {{{field}}}"},
            document="Source",
            schema=None,
        )
    assert not list(tmp_path.iterdir())


def test_extractor_accepts_initial_codex_turn_without_files(tmp_path, monkeypatch):
    """Allow a first-turn prompt to omit both file fields."""
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
def test_file_backed_preset_stages_document_and_schema(
    tmp_path, monkeypatch, usage_reports, invalid_json
):
    """Stage the preset's input files and retain usage when JSON parsing fails."""
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
        """Verify the staged inputs and simulate the CLI's final response and usage."""
        assert (cwd / "input.md").read_bytes() == document.encode()
        schema_text = (cwd / "schema.json").read_text(encoding="utf-8")
        schema = json.loads(schema_text)
        assert "evidence_anchor" in schema["properties"]["habitat"]["items"]["properties"]
        if args[1] == "sandbox":
            (cwd / "probe").touch()
        else:
            assert schema_text not in kwargs["input"]
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
    assert "{schema_filename}" in result.messages["system"]
    assert "{document_filename}" in result.messages["user"]
    system = result.messages_formatted["system"]
    user = result.messages_formatted["user"]
    (prompt_file,) = tmp_path.glob("codex/*/prompt.txt")
    prompt = prompt_file.read_text(encoding="utf-8")
    assert prompt == f"system:\n{system}\n\nuser:\n{user}"
    assert prompt.count("input.md") == 1
    assert prompt.count("schema.json") == 1
    assert quote not in prompt
    assert "evidence_anchor" in system


@pytest.mark.parametrize(
    "template, role",
    [
        ({"user_message": "Read {document}"}, MessageRole.USER),
        ({"system_message": "Read {document!s}"}, MessageRole.SYSTEM),
        ({"user_message": "Read {document[0]}"}, MessageRole.USER),
        ({"user_message": "{schema:{document}}"}, MessageRole.USER),
    ],
)
def test_codex_rejects_inline_template_before_inference(tmp_path, template, role):
    """Report the message that references the unsupported inline document field."""
    backend = Codex("test-model", "medium", 30, str(tmp_path))

    with pytest.raises(MissingBindingError) as raised:
        extract_from_text(
            text="# Fixture",
            text_id="fixture",
            prompt_template=template,
            llm=backend,
            schema={},
            use_guided_decoding=False,
        )
    assert raised.value.placeholder == "document"
    assert raised.value.role == role
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "codex_key, expected", [(None, "project-key"), ("override-key", "override-key")]
)
def test_codex_prefers_api_keys_over_saved_login(tmp_path, monkeypatch, codex_key, expected):
    """Keep the project API key ahead of the saved login and allow an explicit override."""
    login_home = tmp_path / "login"
    login_home.mkdir()
    auth = login_home / "auth.json"
    auth.write_text('{"auth_mode": "chatgpt"}', encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(login_home))
    monkeypatch.setenv("OPENAI_API_KEY", "project-key")
    if codex_key is None:
        monkeypatch.delenv("CODEX_API_KEY", raising=False)
    else:
        monkeypatch.setenv("CODEX_API_KEY", codex_key)

    def run_cli(args, *, cwd, env, **kwargs):
        """Check which credential reaches the CLI and simulate a successful call."""
        assert env["CODEX_API_KEY"] == expected
        assert not (Path(env["CODEX_HOME"]) / "auth.json").exists()
        if args[1] == "sandbox":
            (cwd / "probe").touch()
        else:
            Path(args[args.index("--output-last-message") + 1]).write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr("kibad_llm.llms.codex.shutil.which", lambda _: "/usr/bin/codex")
    monkeypatch.setattr("kibad_llm.llms.codex.subprocess.run", run_cli)
    backend = Codex("test-model", "high", 30, str(tmp_path / "artifacts"))

    assert backend.call_llm_chat_with_guided_decoding([]).message.content == "{}"
    assert list(login_home.iterdir()) == [auth]


@pytest.mark.parametrize("first_exit_code", [0, 1])
def test_codex_keeps_refreshed_login_between_documents(tmp_path, monkeypatch, first_exit_code):
    """Pass the refreshed login to the next document even if the first extraction fails."""
    login_home = tmp_path / "login"
    login_home.mkdir()
    auth = login_home / "auth.json"
    original = {"auth_mode": "chatgpt", "tokens": {"refresh_token": "original-token"}}
    refreshed = {"auth_mode": "chatgpt", "tokens": {"refresh_token": "replacement-token"}}
    auth.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(login_home))
    monkeypatch.delenv("CODEX_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    used_credentials = []

    def run_cli(args, *, cwd, env, **kwargs):
        """Simulate the CLI rotating the login token in its temporary state."""
        staged = Path(env["CODEX_HOME"]) / "auth.json"
        assert staged != auth
        assert (staged.stat().st_mode & 0o777) == 0o600
        if args[1] == "sandbox":
            (cwd / "probe").touch()
            return subprocess.CompletedProcess(args, 0)
        used_credentials.append(json.loads(staged.read_text(encoding="utf-8")))
        if len(used_credentials) == 1:
            staged.write_text(json.dumps(refreshed), encoding="utf-8")
            if first_exit_code:
                return subprocess.CompletedProcess(args, first_exit_code)
        Path(args[args.index("--output-last-message") + 1]).write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr("kibad_llm.llms.codex.shutil.which", lambda _: "/usr/bin/codex")
    monkeypatch.setattr("kibad_llm.llms.codex.subprocess.run", run_cli)
    backend = Codex("test-model", "high", 30, str(tmp_path / "artifacts"))

    if first_exit_code:
        with pytest.raises(ValueError, match="Codex exited with status 1"):
            backend.call_llm_chat_with_guided_decoding([])
    else:
        assert backend.call_llm_chat_with_guided_decoding([]).message.content == "{}"
    assert json.loads(auth.read_text(encoding="utf-8")) == refreshed
    assert (auth.stat().st_mode & 0o777) == 0o600
    assert backend.call_llm_chat_with_guided_decoding([]).message.content == "{}"
    assert used_credentials == [original, refreshed]


def test_codex_rejects_placeholder_alias_settings(tmp_path):
    """Report unsupported settings even when the messages already use fixed field names."""
    backend = Codex("test-model", "high", 30, str(tmp_path))
    with pytest.raises(
        TypeError, match="Codex prompt_template contains unrecognized settings"
    ) as raised:
        backend.prepare_request(
            {
                "user_message": "Read {document_filename}. Use {schema}.",
                "document_filename_placeholder": "source_file",
                "schema_placeholder": "output_schema",
            },
            document="Text",
            schema={},
        )
    assert "'document_filename_placeholder', 'schema_placeholder'" in str(raised.value)


def test_prepare_request_stages_files_for_the_current_turn_only(tmp_path):
    """Prepend rendered history and select staged files from the current messages."""
    backend = Codex("test-model", "high", 600, str(tmp_path))
    history = [SimpleChatMessage(role=MessageRole.USER, content="Previous turn")]
    schema = {
        "type": "object",
        "properties": {"habitat": {"type": "string", "description": "Study habitat"}},
    }
    document = "# Original Markdown\n"
    request = backend.prepare_request(
        {
            "system_message": "{schema_description}",
            "user_message": "Read {document_filename}.\n{schema}",
            "schema_description_kwargs": {"include_field_descriptions": False},
        },
        document=document,
        schema=schema,
        history=history,
    )

    system, user = request.current_messages
    assert "habitat" in system.content
    assert "Study habitat" not in system.content
    assert user.content.startswith("Read input.md.")
    assert json.loads(user.content.split("\n", maxsplit=1)[1]) == schema
    assert request.messages == [*history, system, user]
    assert history == [SimpleChatMessage(role=MessageRole.USER, content="Previous turn")]
    assert request.input_artifacts == {"input.md": document}
    assert all(document not in message.content for message in request.messages)

    followup = backend.prepare_request(
        {"user_message": "Use {schema_filename}."},
        document=document,
        schema=schema,
        history=request.messages,
    )

    assert followup.messages == [*request.messages, *followup.current_messages]
    assert followup.current_messages[0].content == "Use schema.json."
    assert followup.input_artifacts == {"schema.json": json.dumps(schema, ensure_ascii=False)}


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
        prompt_template={"user_message": "Read {document_filename}"},
        llm=backend,
        use_guided_decoding=False,
    )
    assert len(result.errors) == 1
    assert result.errors[0].startswith(type(error).__name__ + ":")
    assert result.backend_metadata is None
    (error_file,) = tmp_path.glob("*/error.txt")
    assert error_file.read_text(encoding="utf-8") == str(error)
    assert error_file.with_name("events.jsonl").is_file()


def test_codex_keeps_usage_after_event_with_unicode_separator(tmp_path):
    """Preserve a Unicode line separator inside a valid JSONL record."""
    backend = Codex("test-model", "high", 30, str(tmp_path))
    usage = {"input_tokens": 10, "output_tokens": 2}
    events = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": "A\u2028B"}},
        {"type": "turn.completed", "usage": usage},
    ]
    raw = "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events)
    response = ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content="{}"), raw=raw)

    assert backend.get_backend_metadata_from_chat_response(response) == {"usage": [usage]}


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
        prompt_template={"user_message": "Read {document_filename}"},
        llm=backend,
        use_guided_decoding=False,
    )
    assert result.structured == {}
    assert result.backend_metadata is None
    assert len(result.errors) == 1
    assert result.errors[0].startswith(("JSONDecodeError:", "TypeError:"))
