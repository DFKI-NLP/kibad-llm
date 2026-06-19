"""Configuration of constants and packages for package-wide use.

Attributes:
    PROJ_ROOT: Absolute path to the repository root.
    DATA_DIR: Path to the top-level data directory.
    RAW_DATA_DIR: Path to raw (unprocessed) input data.
    INTERIM_DATA_DIR: Path to intermediate, partially processed data.
    PROCESSED_DATA_DIR: Path to fully processed, analysis-ready data.
    EXTERNAL_DATA_DIR: Path to third-party or externally sourced data.
    MODELS_DIR: Path to serialised model artefacts.
    REPORTS_DIR: Path to generated reports.
    FIGURES_DIR: Path to generated figures within the reports directory.
    RESULT_FORMAT_VERSION_KEY: Key used to store the result-format version in output dicts.
"""

from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file if it exists
load_dotenv()

# Paths
PROJ_ROOT = Path(__file__).resolve().parents[2]
logger.info(f"PROJ_ROOT path is: {PROJ_ROOT}")

DATA_DIR = PROJ_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

MODELS_DIR = PROJ_ROOT / "models"

REPORTS_DIR = PROJ_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

RESULT_FORMAT_VERSION_KEY = "version"

# If tqdm is installed, configure loguru with tqdm.write
# https://github.com/Delgan/loguru/issues/135
try:
    from tqdm import tqdm

    logger.remove(0)
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
except ModuleNotFoundError:
    pass
