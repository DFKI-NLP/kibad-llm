"""
extract_vocabulary_enums.py

This script extracts all vocabulary enum values from the Faktencheck database.
It looks for:
1. Vocabulary tables (those starting with "vocabulary_") referenced in queries.yaml
2. Direct columns in core_zotaddon and related tables that contain choice values

Inspired by: db_converter.py and database_unique_summary.py

Usage example:
     python extract_vocabulary_enums.py --top-n 100
"""
import argparse
import json
import logging
import os
from pathlib import Path
import re
from typing import Any

from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql
import yaml

from kibad_llm.config import DATA_DIR

logger = logging.getLogger(__name__)


def normalize_table_suffix(s: str) -> str:
    """
    Normalize the table suffix by removing underscores.

    Example:
        "direct_driver" -> "directdriver"
    """
    return re.sub(r"_+", "", s or "")


def extract_vocabulary_table_name(query: str) -> str | None:
    """
    Extract the vocabulary table name (without prefix) from a SQL query.
    """
    pattern = r'vocabulary_(\w+)'
    match = re.search(pattern, query, re.IGNORECASE)
    if match:
        return normalize_table_suffix(match.group(1))
    return None


def query_vocabulary_values(cursor: Any, table_suffix: str) -> list[str]:
    """
    Query all possible values from a specific vocabulary table.
    """
    normalized = normalize_table_suffix(table_suffix)
    table_ident = sql.Identifier(f"vocabulary_{normalized}")
    query = sql.SQL("SELECT name FROM {} ORDER BY name ASC").format(table_ident)

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except psycopg2.Error as e:
        logger.error(f"Error querying vocabulary_{normalized}: {e}")
        cursor.connection.rollback()
        return []


def query_direct_column_values(cursor: Any, table: str, column: str) -> list[Any]:
    """
    Query all distinct values from a specific column in a table.
    """
    table_ident = sql.Identifier(table)
    column_ident = sql.Identifier(column)
    query = sql.SQL("SELECT DISTINCT {} FROM {} WHERE {} IS NOT NULL ORDER BY {} ASC").format(
        column_ident, table_ident, column_ident, column_ident
    )

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except psycopg2.Error as e:
        logger.error(f"Error querying {table}.{column}: {e}")
        cursor.connection.rollback()
        return []


def query_nested_column_values(cursor: Any, query_template: str) -> list[dict[str, Any]]:
    """
    Execute a query that returns nested data (e.g., with multiple columns).

    Returns a list of dictionaries where keys are column names.
    """
    try:
        cursor.execute(query_template.replace("%s", "NULL"))  # Get structure without specific ID
        return []  # Nested values need to be queried per record
    except psycopg2.Error as e:
        logger.error(f"Error with nested query: {e}")
        cursor.connection.rollback()
        return []


# Mapping of fields to their database locations
DIRECT_COLUMNS = {
    "spatial_extent": ("core_zotaddon", "spacial_extent"),
    "spatial_resolution": ("core_zotaddon", "spacial_resolution"),
    "temporal_extent_unit": ("core_zotaddon", "temporal_extent_unit"),
    "temporal_resolution": ("core_zotaddon", "temporal_resolution"),
    "status": ("core_zotaddon", "status"),
}


def extract_all_vocabulary_enums(
    queries_yaml_path: str,
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    top_n: int,
) -> dict[str, list[Any]]:
    """
    Extract all vocabulary enum values from the database.
    Inspired by get_unique_single_and_multi_values() and show_unique_values_summary()
    """
    with open(queries_yaml_path, encoding="utf-8") as f:
        queries_yaml = yaml.safe_load(f)

    vocab_query_names = queries_yaml.get("VOCAB_QUERY_NAMES", {})

    if not vocab_query_names:
        logger.warning("No VOCAB_QUERY_NAMES found in queries.yaml")
        return {}

    logger.info(f"Found {len(vocab_query_names)} vocabulary queries to process")

    # Map field names to their vocabulary table suffixes
    vocab_tables: dict[str, str] = {}
    for field_name, query_key in vocab_query_names.items():
        query = queries_yaml.get(query_key)
        if query:
            table_suffix = extract_vocabulary_table_name(query)
            if table_suffix:
                vocab_tables[field_name] = table_suffix
                logger.info(f"Field '{field_name}' → vocabulary_{table_suffix}")
            else:
                logger.warning(f"Could not extract vocabulary table from query: {query_key}")
        else:
            logger.warning(f"Query key '{query_key}' not found in queries.yaml")

    result: dict[str, list[Any]] = {}

    with psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    ) as conn:
        with conn.cursor() as cursor:
            # Extract from vocabulary tables
            for field_name, table_suffix in vocab_tables.items():
                logger.info(f"Querying vocabulary_{table_suffix}...")
                values = query_vocabulary_values(cursor, table_suffix)

                if len(values) <= top_n:
                    result[field_name] = values
                    logger.info(f"  Found {len(values)} values (included)")
                else:
                    logger.info(f"  Found {len(values)} values (excluded, exceeds top_n={top_n})")

            # Extract from direct columns
            for field_name, (table, column) in DIRECT_COLUMNS.items():
                logger.info(f"Querying {table}.{column}...")
                values = query_direct_column_values(cursor, table, column)

                if len(values) <= top_n:
                    result[field_name] = values
                    logger.info(f"  Found {len(values)} values (included)")
                else:
                    logger.info(f"  Found {len(values)} values (excluded, exceeds top_n={top_n})")

    return result


def main(
    queries_path: Path,
    host: str,
    port: str,
    database: str,
    user: str,
    password: str,
    top_n: int,
):
    """
    Main entry point for running the vocabulary extraction process.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    logger.info(f"Reading queries from: {queries_path}")
    logger.info(f"Connecting to database: {host}:{port}/{database}")
    logger.info(f"Top-N threshold: {top_n}")

    vocab_enums = extract_all_vocabulary_enums(
        queries_yaml_path=str(queries_path),
        host=host,
        port=int(port),
        database=database,
        user=user,
        password=password,
        top_n=top_n,
    )

    logger.info("\n" + "=" * 80)
    logger.info("VOCABULARY ENUM VALUES")
    logger.info("=" * 80 + "\n")

    print(json.dumps(vocab_enums, indent=2, ensure_ascii=False))

    logger.info("\n" + "=" * 80)
    logger.info(f"Total fields included: {len(vocab_enums)}")
    logger.info(f"Total unique values: {sum(len(v) for v in vocab_enums.values())}")
    logger.info("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract vocabulary enum values from Faktencheck database. "
        "Fields with more than --top-n unique values are excluded from output.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--queries-path",
        type=Path,
        default=DATA_DIR / "interim" / "faktencheck-db" / "queries.yaml",
        help="Path to queries.yaml file",
    )
    parser.add_argument(
        "-n",
        "--top-n",
        type=int,
        default=100,
        help="Maximum number of unique values to include per field",
    )

    args = parser.parse_args()
    load_dotenv()

    main(
        queries_path=args.queries_path,
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "kibad"),
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
        top_n=args.top_n,
    )
