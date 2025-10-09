import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from kibad_llm import predict


def _vllm_available(api_base: str, api_key: str) -> bool:
    url = api_base.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        req = Request(url, headers=headers, method="GET")
        with urlopen(req, timeout=1.5) as resp:
            if resp.status != 200:
                return False
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
            return isinstance(payload, dict) and "data" in payload
    except (URLError, HTTPError, TimeoutError, ValueError):
        return False


@pytest.mark.slow
def test_extract_from_pdf_e2e_real_vllm():
    # Read connection details from env (same defaults as CLI)
    api_base = os.getenv("LLM_API_BASE", "http://127.0.0.1:5001/v1")
    api_key = os.getenv("LLM_API_KEY", "dummy")
    model = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

    # if not _vllm_available(api_base, api_key):
    #    pytest.skip(f"vLLM server not reachable at {api_base}; skipping slow e2e test")

    predict.init_llm(model=model, api_base=api_base, api_key=api_key, temperature=0.0)

    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "pdfs"
    pdfs = sorted(p for p in fixtures_dir.iterdir() if p.suffix.lower() == ".pdf")
    if not pdfs:
        pytest.skip("No PDF fixtures found in tests/fixtures/pdfs")

    # Run a real extraction against the live backend
    result = predict.extract_from_pdf(str(pdfs[0]), ["title", "date"], top_k=4)
    assert isinstance(result, dict)
    assert any(k in result for k in ("title", "raw"))
