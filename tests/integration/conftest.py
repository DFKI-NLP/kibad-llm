from hydra import compose, initialize
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, open_dict
import pytest

from kibad_llm.config import PROJ_ROOT


def cfg_predict_global(overrides=None) -> DictConfig:
    with initialize(version_base="1.3", config_path="../../configs"):
        cfg = compose(
            config_name="predict.yaml", return_hydra_config=True, overrides=overrides
        )

        # set defaults for all tests
        with open_dict(cfg):
            cfg.paths.root_dir = str(PROJ_ROOT)
            # cfg.extras.print_config = False
            # cfg.extras.enforce_tags = False
            # cfg.logger = None

    return cfg


# this is called by each test which uses `cfg_eval` arg
# each test generates its own temporary logging path
@pytest.fixture(scope="function")
def cfg_predict(tmp_path) -> DictConfig:  # type: ignore
    cfg = cfg_predict_global()

    with open_dict(cfg):
        cfg.paths.output_dir = str(tmp_path)
        cfg.paths.log_dir = str(tmp_path)
        cfg.paths.save_dir = str(tmp_path)

    yield cfg

    GlobalHydra.instance().clear()

