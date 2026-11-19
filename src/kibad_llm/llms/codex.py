"""Document extraction through the non-interactive Codex CLI."""

from collections.abc import Mapping, Sequence
import json
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404  # Required to invoke the Codex CLI.
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

from llama_index.core.base.llms.types import ChatMessage, ChatResponse, MessageRole

from kibad_llm.llms.base import LLM
from kibad_llm.llms.request import (
    PreparedRequest,
    SimpleChatMessage,
    get_message_templates,
    get_template_placeholders,
    prepare_template_request,
)
from kibad_llm.schema.description import build_schema_description
from kibad_llm.utils.log import warn_once

_DOCUMENT_FILENAME = "input.md"
_SCHEMA_FILENAME = "schema.json"

CODEX_CONFIG_TEMPLATE = """
default_permissions = "document"
approval_policy = "never"
web_search = "disabled"
model_reasoning_effort = {reasoning_effort}
[shell_environment_policy]
inherit = "none"
[features]
apps = false
[plugins._default]
enabled = false
[permissions.document.filesystem]
":minimal" = "read"
{executable} = "read"
[permissions.document.filesystem.":workspace_roots"]
"." = "write"
[permissions.document.network]
enabled = false
"""


class Codex(LLM):
    """Run one isolated Codex conversation per document."""

    def __init__(
        self,
        model: str,
        reasoning_effort: str,
        timeout: float,
        artifact_dir: str,
        executable: str = "codex",
    ):
        """Configure the Codex CLI.

        Args:
            model: Model name passed to the CLI.
            reasoning_effort: Reasoning effort passed to the CLI.
            timeout: Time limit for inference in seconds.
            artifact_dir: Directory for run diagnostics and temporary workspaces.
            executable: Codex CLI executable name or path.
        """
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout
        self.artifact_dir = Path(artifact_dir).resolve()
        self.executable = executable

    def prepare_request(
        self,
        prompt_template: Mapping[str, Any],
        *,
        document: str,
        schema: dict[str, Any] | None,
        history: Sequence[SimpleChatMessage] = (),
    ) -> PreparedRequest:
        """Render templates and attach only the document and schema files they reference.

        The document and schema filename fields are both optional on every turn.
        Referencing either field stages its file in the current call's fresh workspace.
        The schema can also be included inline. History carries rendered messages,
        so a follow-up that needs a file must reference its filename field again.

        Args:
            prompt_template: Current messages and their field declarations. Use
                `document_filename_placeholder` to name the field for `input.md` and
                `schema_filename_placeholder` to name the field for `schema.json`. To include schema
                text in the message, declare `schema_placeholder` for JSON or
                `schema_description_placeholder` for a readable description.
            document: Source Markdown to stage when the template requests the document file.
            schema: Selected prompt schema, or None when none is available.
            history: Previously rendered messages to prepend.

        Returns:
            Rendered current messages, the full conversation, and the requested input artifacts.

        Raises:
            MissingBindingError: A template references an unavailable binding.
            ValueError: The templates cannot be rendered.
            TypeError: Schema serialization or schema description options are invalid.
        """
        templates = get_message_templates(prompt_template)
        placeholders = get_template_placeholders(templates)
        bindings: dict[str, str] = {}
        input_artifacts = {}
        document_file_field = prompt_template.get("document_filename_placeholder")
        if document_file_field in placeholders:
            bindings[document_file_field] = _DOCUMENT_FILENAME
            input_artifacts[_DOCUMENT_FILENAME] = document

        if schema is not None:
            schema_field = prompt_template.get("schema_placeholder")
            if schema_field in placeholders:
                bindings[schema_field] = json.dumps(schema, ensure_ascii=False)
            description_field = prompt_template.get("schema_description_placeholder")
            if description_field in placeholders:
                bindings[description_field] = build_schema_description(
                    schema=schema, **(prompt_template.get("schema_description_kwargs") or {})
                )
            schema_file_field = prompt_template.get("schema_filename_placeholder")
            if schema_file_field in placeholders:
                bindings[schema_file_field] = _SCHEMA_FILENAME
                input_artifacts[_SCHEMA_FILENAME] = json.dumps(schema, ensure_ascii=False)

        request = prepare_template_request(templates, bindings=bindings, history=history)
        request.input_artifacts = input_artifacts
        return request

    def get_reasoning_from_chat_response(self, response: ChatResponse) -> None:
        """Return unavailable reasoning and warn once without raising an extraction error."""
        warn_once("Codex does not return reasoning content.")
        return None

    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[SimpleChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        input_artifacts: dict[str, str] | None = None,
        **request_kwargs,
    ) -> ChatResponse:
        """Execute a file-backed request and return the final text and raw CLI events.

        Schema instructions come from the configured messages; the shared extractor
        performs JSON parsing and schema validation. Guided decoding and additional
        request parameters are rejected before creating artifacts or starting the CLI.

        Args:
            messages: Prepared extraction messages, including conversation history.
            json_schema: Must be None; configure `extractor.use_guided_decoding=false`.
            input_artifacts: Requested source Markdown as `input.md` and JSON Schema as
                `schema.json`. Omit files whose filename fields were not referenced.

        Returns:
            The final response text and raw CLI events for shared postprocessing.

        Keyword Args:
            **request_kwargs: Additional request parameters are unsupported and must be omitted.

        Raises:
            ValueError: Guided decoding, additional request parameters, or unsupported
                input filenames were supplied, or CLI execution failed.
        """
        if json_schema is not None:
            raise ValueError(
                "Codex does not support guided decoding. Set extractor.use_guided_decoding=false; "
                "supply schema instructions through the prompt template."
            )
        if request_kwargs:
            raise ValueError(
                "Codex does not support additional request parameters: "
                f"{', '.join(sorted(request_kwargs))}. "
                "Remove them from extractor.request_parameters."
            )
        inputs = input_artifacts or {}
        unsupported_inputs = inputs.keys() - {_DOCUMENT_FILENAME, _SCHEMA_FILENAME}
        if unsupported_inputs:
            raise ValueError(f"Unsupported Codex input filenames: {sorted(unsupported_inputs)}.")
        artifact = self.artifact_dir / uuid4().hex
        artifact.mkdir(mode=0o700, parents=True)
        events = artifact / "events.jsonl"
        prompt = "\n\n".join(f"{message.role.value}:\n{message.content}" for message in messages)
        (artifact / "prompt.txt").write_text(prompt, encoding="utf-8")
        try:
            answer = self._run(inputs, prompt, artifact, events)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            (artifact / "error.txt").write_text(str(error), encoding="utf-8")
            raise

        return ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=answer),
            raw=events.read_text(encoding="utf-8"),
        )

    def get_backend_metadata_from_chat_response(
        self, response: ChatResponse
    ) -> dict[str, Any] | None:
        """Expose individual CLI usage reports through the shared metadata callback.

        Args:
            response: Codex response whose raw value contains the CLI's JSONL event stream.

        Returns:
            A copy of the usage reports in event order, preserving native fields without
            summing counters, or None when the CLI reported no usage.

        Raises:
            ValueError: A CLI event is not valid JSON.
            TypeError: Reported usage is not a JSON object.
        """
        raw = response.raw
        if raw is None:
            return None
        usage_reports = []
        for line in raw.splitlines():
            event = json.loads(line)
            usage = event.get("usage")
            if usage is not None:
                if not isinstance(usage, dict):
                    raise TypeError(f"Unsupported Codex usage type: {type(usage).__name__}")
                usage_reports.append(usage)
        return {"usage": usage_reports} if usage_reports else None

    def _run(
        self,
        input_artifacts: dict[str, str],
        prompt: str,
        artifact: Path,
        events: Path,
    ) -> str:
        """Stage private runtime state, verify isolation, and execute Codex for one document."""
        executable_path = shutil.which(self.executable)
        if executable_path is None:
            raise FileNotFoundError(f"Codex executable unavailable: {self.executable}")
        executable = Path(executable_path).resolve()
        auth_source = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "auth.json"
        with TemporaryDirectory(prefix="codex-", dir=self.artifact_dir) as temporary:
            root = Path(temporary)
            workspace = root / "document"
            state = root / "state"
            workspace.mkdir()
            state.mkdir(mode=0o700)
            for filename, content in input_artifacts.items():
                (workspace / filename).write_text(content, encoding="utf-8")
            env = {"PATH": "/usr/bin:/bin", "HOME": str(state), "CODEX_HOME": str(state)}
            api_key = os.environ.get("CODEX_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if api_key:
                env["CODEX_API_KEY"] = api_key
            elif auth_source.is_file():
                shutil.copyfile(auth_source, state / "auth.json")
                (state / "auth.json").chmod(0o600)
            else:
                raise ValueError("Set CODEX_API_KEY or provide a Codex auth.json file.")

            (state / "config.toml").write_text(
                CODEX_CONFIG_TEMPLATE.format(
                    reasoning_effort=json.dumps(self.reasoning_effort),
                    executable=json.dumps(str(executable)),
                ),
                encoding="utf-8",
            )
            canary = state / "private"
            canary.touch()
            protected = [
                canary,
                state / "auth.json",
                Path.cwd() / "pyproject.toml",
                artifact / "prompt.txt",
                auth_source,
                Path.home() / ".bash_history",
            ]
            # The probe script is fixed and receives paths as positional arguments.
            probe = subprocess.run(  # nosec B603
                [
                    executable,
                    "sandbox",
                    "/bin/sh",
                    "-ec",
                    'while test "$1" != --; do test -r "$1"; shift; done; '
                    "shift; touch probe; "
                    'for path do if test -r "$path"; then echo "Readable: $path" >&2; exit 1; fi; done',
                    "probe",
                    *input_artifacts,
                    "--",
                    *map(str, protected),
                ],
                cwd=workspace,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if probe.returncode:
                raise ValueError(f"Codex isolation probe failed: {probe.stderr.strip()}")
            (workspace / "probe").unlink()
            final = artifact / "final.json"
            with (
                events.open("w", encoding="utf-8") as stdout,
                (artifact / "stderr.log").open("w", encoding="utf-8") as stderr,
            ):
                # Pass options as arguments and the extraction prompt through stdin.
                result = subprocess.run(  # nosec B603
                    [
                        executable,
                        "exec",
                        "--strict-config",
                        "--ephemeral",
                        "--skip-git-repo-check",
                        "--ignore-rules",
                        "--json",
                        "--model",
                        self.model,
                        "--output-last-message",
                        str(final),
                        "-",
                    ],
                    cwd=workspace,
                    env=env,
                    input=prompt,
                    text=True,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=self.timeout,
                )
            if result.returncode:
                raise ValueError(
                    f"Codex exited with status {result.returncode}. See stderr.log and events.jsonl."
                )
            if not final.is_file():
                raise ValueError("Codex did not produce a final response.")
            return final.read_text(encoding="utf-8")
