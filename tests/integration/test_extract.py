import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest
from hydra.core.hydra_config import HydraConfig
from omegaconf import open_dict

from kibad_llm.config import PROJ_ROOT
from kibad_llm.predict import predict, extract_from_pdf, init_llm


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

    init_llm(model=model, api_base=api_base, api_key=api_key, temperature=0.0)

    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "pdfs"
    pdfs = sorted(p for p in fixtures_dir.iterdir() if p.suffix.lower() == ".pdf")
    # if not pdfs:
    #    pytest.skip("No PDF fixtures found in tests/fixtures/pdfs")

    prompt_questions = """
    Bitte lese den folgenden Text vollständig. Der Text ist eine Studie zu einem Ökosystem. Beantworte die folgenden Fragen auf Deutsch, auch wenn der Text auf Englisch ist.  Wenn Antwortmöglichkeiten nach einer Frage gegeben sind, wähle eine von den durch Komma getrennten Antwortmöglichkeiten aus.

    1. Frage: In welchem Lebensraum wurde die Studie durchgeführt? Antwortmöglichkeiten: Wald, Agrar- und Offenland, Binnengewässer und Auen, Küste und Küstengewässer, Urbane Räume, Boden

    2. Frage: In welchem Naturgroßraum wurde die Studie durchgeführt? Antwortmöglichkeiten: Alpen, Alpenvorland, Mittelgebirgsschwelle, Norddeutsches Tiefland, Nord- und Ostsee oder Schichtsstufenland beidseits des Oberrheingrabens

    3. Frage: Welchen Ökosystemtyp hat die Studie betrachtet? Antwortmöglichkeiten: Binnenland: Waldfreie Niedermoore und Sümpfe, Grünland nasser bis feuchter Standorte; Binnenland: Laub(Misch)Wälder und -Forste (Laubbaumanteil über 50 Prozent); Binnengewässer: Stehende Gewässer; Meere und Küsten: Benthal der Nordsee

    4. Frage: In welchem Bundesland liegt das betrachtete Ökosystem der Studie? Antwortmöglichkeiten: Baden-Württemberg, Bayern, Niedersachsen, Brandenburg, Berlin, Bremen, Hamburg, Hessen,  Mecklenburg-Vorpommern, Niedersachsen, Nordrhein-Westfalen, Rheinland-Pfalz, Saarland, Sachsen, Sachsen-Anhalt, Schleswig-Holstein, Thüringen
    """
    # Run a real extraction against the live backend
    result = extract_from_pdf(
        pdf_path=str(pdfs[0]), prompt_questions=prompt_questions
    )
    assert isinstance(result, dict)
    # assert any(k in result for k in ("title", "raw"))


@pytest.mark.slow
def test_predict(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_file = PROJ_ROOT / "tests" / "fixtures" / "pdfs" / "7T8NZA5Q.pdf"

    HydraConfig().set_config(cfg_predict)
    predict(cfg_predict)
