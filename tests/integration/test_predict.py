import json

from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, open_dict
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.predict import predict
from tests.conftest import cfg_global

PDF_DIR = PROJ_ROOT / "tests" / "fixtures" / "pdfs"
FILE_NAMES = sorted([f.name for f in PDF_DIR.glob("*.pdf")])
PREDICTION_DIR = PROJ_ROOT / "tests" / "fixtures" / "results"


@pytest.fixture(scope="module")
def cfg_predict_module(tmp_path_factory) -> DictConfig:  # type: ignore
    module_tmp_path = tmp_path_factory.mktemp("module")
    cfg = cfg_global(config_name="predict.yaml", out_dir=module_tmp_path)

    yield cfg

    GlobalHydra.instance().clear()


@pytest.fixture(scope="module")
def predictions_dict(cfg_predict_module) -> dict[str, dict]:

    with open_dict(cfg_predict_module):
        cfg_predict_module.pdf_directory = str(PDF_DIR)
        cfg_predict_module.disable_extraction_caching = True

    HydraConfig().set_config(cfg_predict_module)
    predict(cfg_predict_module)
    # read json line file from cfg_predict_module.output_file
    with open(cfg_predict_module.output_file) as f:
        lines = f.readlines()

    # create result as dict keyed by file_name
    results = {}
    for line in lines:
        result = json.loads(line)
        results[result["file_name"]] = result

    return results


# small fixture to run test for each file and have good names in pytest output
@pytest.fixture(params=FILE_NAMES)
def file_name(request) -> str:
    return request.param


@pytest.mark.slow
def test_prediction(file_name, predictions_dict):
    prediction = predictions_dict[file_name]

    prediction_path = PREDICTION_DIR / f"{file_name}.json"

    # write fixture data
    # with open(prediction_path, "w") as f:
    #     json.dump(prediction, f, indent=4, ensure_ascii=False)

    # read fixture data
    with open(prediction_path) as f:
        result_expected = json.load(f)

    # just check keys since the actual values are not deterministic
    assert set(prediction["structured"]) == set(result_expected["structured"])


@pytest.mark.slow
def test_predict_fast_dev_run(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_directory = str(PDF_DIR)
        cfg_predict.fast_dev_run = True
        cfg_predict.disable_extraction_caching = True

    HydraConfig().set_config(cfg_predict)
    predict(cfg_predict)

    # read json line file from cfg_predict.output_file
    with open(cfg_predict.output_file) as f:
        lines = f.readlines()
    results = [json.loads(line) for line in lines]

    assert len(results) == 1
    result = results[0]

    fixture_path = PREDICTION_DIR / f"{result['file_name']}.json"

    # write fixture data
    # with open(fixture_path, "w") as f:
    #   json.dump(result, f, indent=4, ensure_ascii=False)

    # read fixture data
    with open(fixture_path) as f:
        fixture_data = json.load(f)

    # just check keys since the actual values are not deterministic
    assert set(result["structured"]) == set(fixture_data["structured"])


@pytest.fixture(scope="function")
def cfg_predict_without_schema(tmp_path) -> DictConfig:  # type: ignore
    cfg = cfg_global(config_name="predict.yaml", out_dir=tmp_path, overrides=["extractor=simple"])

    with open_dict(cfg):
        cfg.pdf_directory = str(PDF_DIR)
        cfg.fast_dev_run = True
        cfg.disable_extraction_caching = True

    yield cfg

    GlobalHydra.instance().clear()


@pytest.mark.slow
def test_predict_without_schema_fast_dev_run(cfg_predict_without_schema):

    HydraConfig().set_config(cfg_predict_without_schema)
    predict(cfg_predict_without_schema)

    # read json line file from cfg_predict.output_file
    with open(cfg_predict_without_schema.output_file) as f:
        lines = f.readlines()
    results = [json.loads(line) for line in lines]

    assert len(results) == 1
    result = results[0]

    fixture_path = PREDICTION_DIR / f"{result['file_name']}.json"

    # read fixture data
    with open(fixture_path) as f:
        fixture_data = json.load(f)

    # just check keys since the actual values are not deterministic
    assert set(result["structured"]) == set(fixture_data["structured"])


@pytest.fixture(scope="function")
def cfg_predict_pdf_errors(tmp_path) -> DictConfig:  # type: ignore
    cfg = cfg_global(config_name="predict.yaml", out_dir=tmp_path)

    with open_dict(cfg):
        cfg.pdf_directory = str(PROJ_ROOT / "tests" / "fixtures" / "pdfs_error")
        cfg.disable_extraction_caching = True

    yield cfg

    GlobalHydra.instance().clear()


@pytest.mark.slow
def test_prediction_on_pdf_errors(cfg_predict_pdf_errors):
    predict(cfg_predict_pdf_errors)
    # read json line file from cfg_predict_module.output_file
    with open(cfg_predict_pdf_errors.output_file) as f:
        lines = f.readlines()

    # create result as dict keyed by file_name
    results = {}
    for line in lines:
        result = json.loads(line)
        results[result["file_name"]] = result

    # check long PDF error
    file_name_long_pdf = "2E9XWUUE.pdf"
    assert file_name_long_pdf in results
    result_long_pdf = results[file_name_long_pdf]
    # assert that there was some quite long input text
    text_long_pdf = result_long_pdf.get("text", None)
    assert text_long_pdf is not None and len(text_long_pdf) == 1427535
    # assert that there is no structured output ...
    structured_long_pdf = result_long_pdf.get("structured", None)
    assert structured_long_pdf is None
    # ... but an error message about max tokens
    error_long_pdf = result_long_pdf.get("error", None)
    assert (
        error_long_pdf
        == "Error code: 400 - {'error': {'message': 'max_tokens must be at least 1, got -328820.', "
        "'type': 'BadRequestError', 'param': None, 'code': 400}}"
    )
