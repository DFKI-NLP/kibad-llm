"""One-off data integration scripts for acquiring and preparing reference data.

Each submodule is a standalone script (invocable via ``python -m`` or directly):

- :mod:`~kibad_llm.data_integration.db_converter` – export Faktencheck PostgreSQL DB
  to JSONL.
- :mod:`~kibad_llm.data_integration.zotero_download` – download open-access PDFs via
  Semantic Scholar from a Zotero CSV export.
- :mod:`~kibad_llm.data_integration.synch_nextcloud_with_cluster` – bidirectional sync
  between a Nextcloud public share and a local cluster directory.
- :mod:`~kibad_llm.data_integration.database_unique_summary` – inspect unique values in
  the JSONL database export.
- :mod:`~kibad_llm.data_integration.extract_vocabulary_enums` – query vocabulary enum
  values directly from the database.
"""
