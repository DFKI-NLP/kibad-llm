from pathlib import Path

from hydra import compose, initialize
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, open_dict
import pytest

from kibad_llm.config import PROJ_ROOT


def cfg_global(
    overrides=None, out_dir: str | Path | None = None, config_name="predict.yaml"
) -> DictConfig:
    with initialize(version_base="1.3", config_path="../configs"):
        cfg = compose(config_name=config_name, return_hydra_config=True, overrides=overrides)

        # set defaults for all tests
        with open_dict(cfg):
            cfg.paths.root_dir = str(PROJ_ROOT)
            # cfg.extras.print_config = False
            # cfg.extras.enforce_tags = False
            # cfg.logger = None

        if out_dir is not None:
            with open_dict(cfg):
                cfg.paths.output_dir = str(out_dir)
                cfg.paths.log_dir = str(out_dir)
                cfg.paths.save_dir = str(out_dir)

    return cfg


# this is called by each test which uses `cfg_predict` arg
# each test generates its own temporary logging path
@pytest.fixture(scope="function")
def cfg_predict(tmp_path) -> DictConfig:  # type: ignore
    cfg = cfg_global(out_dir=tmp_path)

    yield cfg

    GlobalHydra.instance().clear()
