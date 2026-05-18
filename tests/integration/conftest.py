from __future__ import annotations

from collections.abc import Generator, Mapping
from enum import Enum
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from llama_index.core.base.llms.types import ChatResponse, MessageRole
from llama_index.core.llms import ChatMessage as LlamaIndexChatMessage
from llama_index.llms.openai_like import OpenAILike
import pytest

from kibad_llm.config import PROJ_ROOT
from tests.conftest import _env_flag

# dedicated flag to just generate the LLM chat fixture data
WRITE_LLM_CHAT_FIXTURE_DATA = _env_flag(
    "WRITE_LLM_CHAT_FIXTURE_DATA"
)  # set to True to create or update LLM chat fixture data

FIXTURE_DIR = PROJ_ROOT / "tests" / "fixtures" / "llm_chat"
FIXTURE_FORMAT_VERSION = 1

_BACKEND_CONFIG_EXCLUDED_KEYS = {
    "api_key",
    "timeout",
    "max_retries",
    "reuse_client",
    "default_headers",
    "http_client",
    "async_http_client",
    "openai_client",
    "async_openai_client",
    "callback_manager",
    "messages_to_prompt",
    "completion_to_prompt",
    "output_parser",
    "tokenizer",
    "class_name",
}


def _normalize_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _normalize_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_jsonable(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    return value


def _get_backend_config(model: OpenAILike) -> dict[str, Any]:
    model_dump = getattr(model, "model_dump", None)
    if not callable(model_dump):
        raise ValueError(
            "Model does not have a callable model_dump method for extracting backend config."
        )

    backend_config = model_dump(mode="python", exclude_none=False)
    if not isinstance(backend_config, Mapping):
        raise ValueError("Model's model_dump method did not return a mapping for backend config.")

    return _normalize_jsonable(
        {
            key: value
            for key, value in backend_config.items()
            if key not in _BACKEND_CONFIG_EXCLUDED_KEYS
        }
    )


def _build_request_snapshot(
    backend_type: str,
    messages: list[Any],
    request_kwargs: dict[str, Any],
    backend_config: dict[str, Any],
) -> dict[str, Any]:
    request_snapshot: dict[str, Any] = {
        "backend_type": backend_type,
    }
    if backend_config:
        request_snapshot["backend_config"] = backend_config
    request_snapshot["messages"] = [
        {
            "role": (message.role.value if isinstance(message.role, Enum) else str(message.role)),
            "content": message.content,
        }
        for message in messages
    ]
    request_snapshot["request_kwargs"] = _normalize_jsonable(request_kwargs)

    return request_snapshot


def _hash_request_snapshot(request_snapshot: dict[str, Any]) -> str:
    serialized = json.dumps(
        request_snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _serialize_response(response: ChatResponse) -> dict[str, Any]:
    raw_message = None
    raw = response.raw
    if raw is not None:
        try:
            raw_message = raw.choices[0].message
        except (AttributeError, IndexError, TypeError):
            raw_message = None

    return {
        "message": {
            "role": MessageRole.ASSISTANT.value,
            "content": response.message.content,
        },
        "raw_message": {
            "reasoning": getattr(raw_message, "reasoning", None),
            "reasoning_content": getattr(raw_message, "reasoning_content", None),
        },
    }


def _deserialize_response(response_snapshot: dict[str, Any]) -> ChatResponse:
    message_snapshot: dict[str, Any] = response_snapshot.get("message") or {}
    raw_message_snapshot: dict[str, Any] = response_snapshot.get("raw_message") or {}

    raw_message = SimpleNamespace(
        reasoning=raw_message_snapshot.get("reasoning"),
        reasoning_content=raw_message_snapshot.get("reasoning_content"),
    )
    raw = SimpleNamespace(choices=[SimpleNamespace(message=raw_message)])
    return ChatResponse(
        message=LlamaIndexChatMessage(
            role=MessageRole(message_snapshot.get("role", MessageRole.ASSISTANT.value)),
            content=message_snapshot.get("content"),
        ),
        raw=raw,
    )


def _serialize_exception(e: Exception) -> dict[str, Any]:
    return {
        "module": type(e).__module__,
        "qualname": type(e).__qualname__,
        "message": str(e),
    }


def _deserialize_exception(error_snapshot: dict[str, Any]) -> Exception:
    module_name = error_snapshot.get("module")
    qualname = error_snapshot.get("qualname")
    message = error_snapshot.get("message", "")

    exc_cls: type[Exception] | None = None
    if isinstance(module_name, str) and isinstance(qualname, str):
        try:
            module = importlib.import_module(module_name)
            obj: Any = module
            for attr in qualname.split("."):
                obj = getattr(obj, attr)
            if isinstance(obj, type) and issubclass(obj, Exception):
                exc_cls = obj
        except (ImportError, AttributeError, TypeError):
            exc_cls = None

    if exc_cls is None:
        return ValueError(f"{qualname or 'Exception'}: {message}")

    exception_factory = cast(type[Exception], exc_cls)
    try:
        return exception_factory(message)
    except TypeError:
        return ValueError(f"{qualname or 'Exception'}: {message}")


def _write_fixture(
    fixture_path: Path,
    fixture_hash: str,
    request_snapshot: dict[str, Any],
    response_snapshot: dict[str, Any] | None,
    error_snapshot: dict[str, Any] | None,
) -> None:
    payload = {
        "fixture_format_version": FIXTURE_FORMAT_VERSION,
        "fixture_hash": fixture_hash,
        "request": request_snapshot,
        "response": response_snapshot,
        "error": error_snapshot,
    }
    with open(fixture_path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


@pytest.fixture(scope="module")
def llm_chat_replay() -> Generator[None, Any, None]:
    original_chat = cast(Any, OpenAILike.chat)
    monkeypatch = pytest.MonkeyPatch()

    def replay_or_capture(
        self: OpenAILike,
        messages,
        **request_kwargs,
    ) -> ChatResponse:
        backend_type = f"{type(self).__module__}.{type(self).__qualname__}"
        request_snapshot = _build_request_snapshot(
            backend_type=backend_type,
            messages=messages,
            request_kwargs=request_kwargs,
            backend_config=_get_backend_config(self),
        )
        fixture_hash = _hash_request_snapshot(request_snapshot)
        fixture_path = FIXTURE_DIR / f"{fixture_hash}.json"

        if WRITE_LLM_CHAT_FIXTURE_DATA:
            FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
            try:
                response = original_chat.__get__(self, OpenAILike)(
                    messages,
                    **request_kwargs,
                )
            except Exception as e:
                _write_fixture(
                    fixture_path=fixture_path,
                    fixture_hash=fixture_hash,
                    request_snapshot=request_snapshot,
                    response_snapshot=None,
                    error_snapshot=_serialize_exception(e),
                )
                raise

            _write_fixture(
                fixture_path=fixture_path,
                fixture_hash=fixture_hash,
                request_snapshot=request_snapshot,
                response_snapshot=_serialize_response(response),
                error_snapshot=None,
            )
            return response

        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Missing LLM chat fixture: {fixture_path}. "
                "Run the test again with WRITE_LLM_CHAT_FIXTURE_DATA=1 and a reachable backend to create it."
            )

        with open(fixture_path) as f:
            fixture_data = json.load(f)

        error_snapshot = fixture_data.get("error")
        if error_snapshot is not None:
            raise _deserialize_exception(error_snapshot)

        response_snapshot = fixture_data.get("response")
        if response_snapshot is None:
            raise ValueError(f"Fixture {fixture_path} has neither a response nor an error.")
        return _deserialize_response(response_snapshot)

    monkeypatch.setattr(OpenAILike, "chat", replay_or_capture)
    yield
    monkeypatch.undo()
