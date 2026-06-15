"""LLM-based information extraction and evaluation framework.

Imports [`config`][kibad_llm.config] on package initialisation to set
global constants and load environment variables.

Modules:
    config: Package-wide constants and environment variable loading.
    predict: Entrypoint for running LLM inference on preprocessed documents.
    evaluate: Entrypoint for evaluating predictions against reference datasets.
    preprocessing: PDF-to-markdown conversion utilities.
    metric: Base class defining the metric interface.
    data_integration: Utilities for downloading and syncing source data (Zotero, Nextcloud, database).
    dataset: Dataset I/O helpers for CSV, JSON, and prediction files.
    extractors: Structured-output extractors for parsing LLM responses.
    llms: LLM provider integrations (OpenAI, vLLM).
    metrics: Concrete metric implementations (F1, confusion matrix, error collection).
    schema: Shared type definitions and schema utilities.
    hydra_callbacks: Hydra lifecycle callbacks.
    utils: General-purpose helpers.
"""

from kibad_llm import config  # noqa: F401
