import json

from llama_index.core.base.llms.types import ChatResponse, MessageRole
from llama_index.core.llms import ChatMessage
import pytest

from kibad_llm.llms.base import LLM, SimpleChatMessage
from kibad_llm.llms.mock import MockLLM


class _StubLLM(LLM):
    def __init__(self, response: ChatResponse | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls = 0

    def call_llm_chat_with_guided_decoding(self, messages, *, json_schema=None, **request_kwargs):
        self.calls += 1
        if self.error is not None:
            raise self.error
        if self.response is None:
            raise AssertionError("Stub backend requires a response or error.")
        return self.response

    def get_reasoning_from_chat_response(self, response: ChatResponse) -> str | None:
        return getattr(response.raw.choices[0].message, "reasoning", None)


def _make_response(content: str | None = '{"value": 1}', reasoning: str = "stub_reasoning") -> ChatResponse:
    raw_message = type("RawMessage", (), {"reasoning": reasoning, "reasoning_content": reasoning})()
    raw_choice = type("RawChoice", (), {"message": raw_message})()
    raw = type("RawResponse", (), {"choices": [raw_choice]})()
    return ChatResponse(
        message=ChatMessage(role=MessageRole.ASSISTANT, content=content),
        raw=raw,
    )


def test_mock_llm_writes_and_replays_fixture(tmp_path) -> None:
    backend = _StubLLM(response=_make_response())
    llm = MockLLM(
        backend=backend,
        backend_name="stub",
        fixture_dir=str(tmp_path),
        write_fixture_data=True,
    )
    messages = [SimpleChatMessage(role=MessageRole.USER, content="Hello")]
    json_schema = {"type": "object", "properties": {"value": {"type": "integer"}}}

    response = llm.call_llm_chat_with_guided_decoding(messages, json_schema=json_schema, temperature=0.0)

    assert backend.calls == 1
    assert response.message.content == '{"value": 1}'
    fixture_files = list(tmp_path.glob("*.json"))
    assert len(fixture_files) == 1

    with open(fixture_files[0]) as f:
        fixture_data = json.load(f)
    assert fixture_data["request"]["messages"] == [{"role": "user", "content": "Hello"}]
    assert fixture_data["response"]["message"]["content"] == '{"value": 1}'

    replay_backend = _StubLLM(response=_make_response(content='{"value": 999}'))
    replay_llm = MockLLM(
        backend=replay_backend,
        backend_name="stub",
        fixture_dir=str(tmp_path),
        write_fixture_data=False,
    )
    replayed = replay_llm.call_llm_chat_with_guided_decoding(
        messages,
        json_schema=json_schema,
        temperature=0.0,
    )

    assert replay_backend.calls == 0
    assert replayed.message.content == '{"value": 1}'
    assert replay_llm.get_reasoning_from_chat_response(replayed) == "stub_reasoning"


def test_mock_llm_replays_serialized_error(tmp_path) -> None:
    backend = _StubLLM(error=ValueError("boom"))
    llm = MockLLM(
        backend=backend,
        backend_name="stub",
        fixture_dir=str(tmp_path),
        write_fixture_data=True,
    )
    messages = [SimpleChatMessage(role=MessageRole.USER, content="Hello")]

    with pytest.raises(ValueError, match="boom"):
        llm.call_llm_chat_with_guided_decoding(messages, json_schema=None)

    replay_backend = _StubLLM(response=_make_response())
    replay_llm = MockLLM(
        backend=replay_backend,
        backend_name="stub",
        fixture_dir=str(tmp_path),
        write_fixture_data=False,
    )

    with pytest.raises(ValueError, match="boom"):
        replay_llm.call_llm_chat_with_guided_decoding(messages, json_schema=None)

    assert replay_backend.calls == 0


def test_mock_llm_raises_helpful_error_when_fixture_is_missing(tmp_path) -> None:
    llm = MockLLM(
        backend=_StubLLM(response=_make_response()),
        backend_name="stub",
        fixture_dir=str(tmp_path),
        write_fixture_data=False,
    )

    with pytest.raises(FileNotFoundError, match="Missing MockLLM fixture"):
        llm.call_llm_chat_with_guided_decoding(
            [SimpleChatMessage(role=MessageRole.USER, content="Hello")],
            json_schema=None,
        )

