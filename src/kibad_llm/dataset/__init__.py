"""Dataset loaders for predictions and reference data used in the evaluation pipeline.

Submodules:

- :mod:`~kibad_llm.dataset.prediction` – load prediction JSONL files, optionally
  together with Hydra run metadata.
- :mod:`~kibad_llm.dataset.json` – generic JSON / JSON Lines loader with compression
  and preprocessing support.
- :mod:`~kibad_llm.dataset.csv` – CSV loaders for structured reference data (e.g.,
  organism trends).
- :mod:`~kibad_llm.dataset.utils` – merge predictions with references into the
  ``{"prediction": …, "reference": …}`` format consumed by metrics.
- :mod:`~kibad_llm.dataset.compression` – transparent decompression for file I/O.
"""
