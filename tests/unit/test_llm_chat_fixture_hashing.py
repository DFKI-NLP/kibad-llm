from llama_index.llms.openai_like import OpenAILike

from tests.integration.conftest import (
    _build_request_snapshot,
    _get_backend_config,
    _hash_request_snapshot,
)


def test_get_backend_config_includes_generation_defaults_but_not_secrets():
    kwargs: dict[str, object] = {
        "model": "openai/gpt-oss-20b",
        "api_base": "http://example.com/v1",
        "api_key": "dummy-secret",
        "temperature": 0.7,
        "timeout": 5,
        "max_retries": 2,
        "additional_kwargs": {"top_p": 0.9, "seed": 123},
    }
    model = OpenAILike(**kwargs)

    backend_config = _get_backend_config(model)

    assert backend_config["model"] == "openai/gpt-oss-20b"
    assert backend_config["temperature"] == 0.7
    assert backend_config["additional_kwargs"] == {"top_p": 0.9, "seed": 123}
    assert backend_config["api_base"] == "http://example.com/v1"
    assert "api_key" not in backend_config
    assert "timeout" not in backend_config
    assert "max_retries" not in backend_config


def test_request_hash_changes_when_backend_generation_defaults_change():
    messages = []
    request_kwargs = {"extra_body": {"structured_outputs": {"json": {"type": "object"}}}}

    snapshot_cold = _build_request_snapshot(
        backend_type="llama_index.llms.openai_like.base.OpenAILike",
        messages=messages,
        request_kwargs=request_kwargs,
        backend_config={"model": "openai/gpt-oss-20b", "temperature": 0.1},
    )
    snapshot_warm = _build_request_snapshot(
        backend_type="llama_index.llms.openai_like.base.OpenAILike",
        messages=messages,
        request_kwargs=request_kwargs,
        backend_config={"model": "openai/gpt-oss-20b", "temperature": 0.8},
    )

    assert _hash_request_snapshot(snapshot_cold) != _hash_request_snapshot(snapshot_warm)
