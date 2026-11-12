"""Document extraction through the non-interactive Codex CLI."""

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404  # Required to invoke the Codex CLI.
from tempfile import TemporaryDirectory
from time import monotonic
from typing import Any
from uuid import uuid4

from llama_index.core.base.llms.types import ChatMessage, ChatResponse, MessageRole

from kibad_llm.llms.base import (
    LLM,
    BackendExecutionError,
    MessageFormatter,
    MissingDocumentError,
    SimpleChatMessage,
)
from kibad_llm.utils.log import warn_once


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
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout
        self.artifact_dir = Path(artifact_dir).resolve()
        self.executable = executable

    def prepare_request(
        self,
        document: str,
        format_messages: MessageFormatter,
    ) -> tuple[list[SimpleChatMessage], dict[str, str]]:
        try:
            messages = format_messages(require_document=False)
        except MissingDocumentError as error:
            raise ValueError(
                "Codex reads the document from input.md. Use "
                "experiment/predict=faktencheck_core_fields_schema_with_evidence_codex "
                "or remove the document placeholder from your file-backed template."
            ) from error
        return messages, {"input.md": document}

    def get_reasoning_from_chat_response(self, response: ChatResponse) -> None:
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
        document = (input_artifacts or {})["input.md"]
        artifact = self.artifact_dir / uuid4().hex
        artifact.mkdir(mode=0o700, parents=True)
        events = artifact / "events.jsonl"
        prompt = "\n\n".join(f"{message.role.value}:\n{message.content}" for message in messages)
        (artifact / "prompt.txt").write_text(prompt, encoding="utf-8")
        metadata: dict[str, Any] = {
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "timeout_seconds": self.timeout,
            "markdown_sha256": sha256(document.encode()).hexdigest(),
            "execution_events": str(events.relative_to(self.artifact_dir.parent)),
            "input_tokens": None,
            "cached_input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "attempt_count": 0,
        }
        started = monotonic()
        try:
            answer = self._run(document, prompt, artifact, events, metadata)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            (artifact / "error.txt").write_text(str(error), encoding="utf-8")
            raise BackendExecutionError(str(error), metadata) from error
        finally:
            metadata["backend_elapsed_seconds"] = monotonic() - started
            if events.exists():
                with events.open(encoding="utf-8", errors="replace") as stream:
                    for line in stream:
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        usage: dict[str, int] = event.get("usage") or {}
                        for key in (
                            "input_tokens",
                            "cached_input_tokens",
                            "output_tokens",
                            "reasoning_tokens",
                        ):
                            if usage.get(key) is not None:
                                metadata[key] = (metadata[key] or 0) + usage[key]
            (artifact / "metadata.json").write_text(
                json.dumps(metadata, indent=2), encoding="utf-8"
            )

        return ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=answer),
            additional_kwargs={"backend_metadata": metadata},
        )

    def _run(
        self,
        document: str,
        prompt: str,
        artifact: Path,
        events: Path,
        metadata: dict[str, Any],
    ) -> str:
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
            (workspace / "input.md").write_text(document, encoding="utf-8")
            # The operator controls the Codex executable and PATH. The version flag is fixed.
            metadata["codex_version"] = subprocess.check_output(  # nosec B603
                [executable, "--version"], text=True, timeout=30
            ).strip()
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
                    "test -r input.md; touch probe; "
                    'for path do if test -r "$path"; then echo "Readable: $path" >&2; exit 1; fi; done',
                    "probe",
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
                metadata["attempt_count"] = 1
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
            answer = final.read_text(encoding="utf-8")
            json.loads(answer)
            return answer
