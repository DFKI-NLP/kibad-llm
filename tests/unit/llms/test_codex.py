import json
from pathlib import Path
import subprocess

import pytest

from kibad_llm.llms.base import BackendExecutionError, MessageRole, SimpleChatMessage
from kibad_llm.llms.codex import Codex


def test_prepare_request_preserves_markdown(tmp_path):
    backend = Codex("test-model", "medium", 30, str(tmp_path))
    document = "# Fixture\n\nBody"
    messages, artifacts = backend.prepare_request(
        document, lambda text: [SimpleChatMessage(MessageRole.USER, text)]
    )
    assert "input.md" in messages[0].content
    assert document not in messages[0].content
    assert artifacts == {"input.md": document}


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
