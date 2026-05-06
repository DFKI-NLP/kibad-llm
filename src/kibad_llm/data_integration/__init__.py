"""One-off data integration scripts for acquiring and preparing reference data.

Each submodule is a standalone script (invocable via ``python -m`` or directly):

- [`db_converter`][kibad_llm.data_integration.db_converter] – export Faktencheck PostgreSQL DB
  to JSONL.
- [`zotero_download`][kibad_llm.data_integration.zotero_download] – download open-access PDFs via
  Semantic Scholar from a Zotero CSV export.
- [`synch_nextcloud_with_cluster`][kibad_llm.data_integration.synch_nextcloud_with_cluster] – bidirectional sync
  between a Nextcloud public share and a local cluster directory.
- [`database_unique_summary`][kibad_llm.data_integration.database_unique_summary] – inspect unique values in
  the JSONL database export.
- [`extract_vocabulary_enums`][kibad_llm.data_integration.extract_vocabulary_enums] – query vocabulary enum
  values directly from the database.
"""
