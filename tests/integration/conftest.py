from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
import hashlib
import importlib
import json
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any, cast

from llama_index.core.base.llms.types import ChatResponse, MessageRole
from llama_index.core.llms import ChatMessage as LlamaIndexChatMessage
from llama_index.llms.openai_like import OpenAILike
import pytest

from kibad_llm.config import PROJ_ROOT
from tests.conftest import WRITE_FIXTURE_DATA

FIXTURE_DIR = PROJ_ROOT / "tests" / "fixtures" / "llm_chat"
FIXTURE_FORMAT_VERSION = 1


LEGACY_BACKEND_TYPE = "kibad_llm.llms.openai_like_vllm.OpenAILikeVllm"


def _backend_name_from_model(model: OpenAILike) -> str:
    model_name = getattr(model, "model", None)
    if isinstance(model_name, str) and model_name:
        short_name = model_name.split("/")[-1]
        return re.sub(r"[^a-zA-Z0-9]+", "_", short_name).strip("_") or short_name
    return type(model).__name__


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


def _build_request_snapshot(
    backend_name: str,
    backend_type: str,
    messages: list[Any],
    json_schema: dict[str, Any] | None,
    request_kwargs: dict[str, Any],
) -> dict[str, Any]:
    return {
        "fixture_format_version": FIXTURE_FORMAT_VERSION,
        "backend_name": backend_name,
        "backend_type": backend_type,
        "messages": [
            {
                "role": message.role.value if isinstance(message.role, Enum) else str(message.role),
                "content": message.content,
            }
            for message in messages
        ],
        "json_schema": _normalize_jsonable(json_schema),
        "request_kwargs": _normalize_jsonable(request_kwargs),
    }


def _extract_legacy_wrapper_inputs(
    model: OpenAILike,
    messages: list[Any],
    request_kwargs: dict[str, Any],
) -> tuple[str, str, list[Any], dict[str, Any] | None, dict[str, Any]]:
    normalized_request_kwargs = dict(request_kwargs)
    json_schema = None

    extra_body = normalized_request_kwargs.get("extra_body")
    if isinstance(extra_body, Mapping):
        extra_body = dict(extra_body)
        structured_outputs = extra_body.get("structured_outputs")
        if isinstance(structured_outputs, Mapping):
            json_candidate = structured_outputs.get("json")
            if isinstance(json_candidate, dict):
                json_schema = json_candidate
            extra_body.pop("structured_outputs", None)

        if len(extra_body) == 0:
            normalized_request_kwargs.pop("extra_body", None)
        else:
            normalized_request_kwargs["extra_body"] = extra_body

    return (
        _backend_name_from_model(model),
        LEGACY_BACKEND_TYPE,
        messages,
        json_schema,
        normalized_request_kwargs,
    )


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
    message_snapshot = response_snapshot.get("message") or {}
    raw_message_snapshot = response_snapshot.get("raw_message") or {}

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
    return exception_factory(message)


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


@pytest.fixture
def llm_chat_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    original_chat = cast(Any, OpenAILike.chat)

    def replay_or_capture(
        self: OpenAILike,
        messages,
        **request_kwargs,
    ) -> ChatResponse:
        backend_name, backend_type, legacy_messages, json_schema, normalized_request_kwargs = (
            _extract_legacy_wrapper_inputs(
                model=self,
                messages=messages,
                request_kwargs=request_kwargs,
            )
        )
        request_snapshot = _build_request_snapshot(
            backend_name=backend_name,
            backend_type=backend_type,
            messages=legacy_messages,
            json_schema=json_schema,
            request_kwargs=normalized_request_kwargs,
        )
        fixture_hash = _hash_request_snapshot(request_snapshot)
        fixture_path = FIXTURE_DIR / f"{fixture_hash}.json"

        if WRITE_FIXTURE_DATA:
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
                "Run the test again with WRITE_FIXTURE_DATA=1 and a reachable backend to create it."
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

