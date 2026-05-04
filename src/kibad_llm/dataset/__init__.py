"""Dataset loaders for predictions and reference data used in the evaluation pipeline.

Submodules:

- [`prediction`][kibad_llm.dataset.prediction] – load prediction JSONL files, optionally
  together with Hydra run metadata.
- [`json`][kibad_llm.dataset.json] – generic JSON / JSON Lines loader with compression
  and preprocessing support.
- [`csv`][kibad_llm.dataset.csv] – CSV loaders for structured reference data (e.g.,
  organism trends).
- [`utils`][kibad_llm.dataset.utils] – merge predictions with references into the
  ``{"prediction": …, "reference": …}`` format consumed by metrics.
- [`compression`][kibad_llm.dataset.compression] – transparent decompression for file I/O.
"""
