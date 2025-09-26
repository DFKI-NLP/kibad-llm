"""
This script connects to a database, extracts the most important data and its metadata, then
converts the results to JSONL format and writes to a file.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import psycopg2
import yaml

DEFAULT_FILEPATH: Path = (
    Path("data") / "iterim" / "faktencheck-db" / "faktencheck-db-converted_2025-08-19.jsonl"
)
DEFAULT_QUERIES_PATH: Path = Path("data") / "iterim" / "faktencheck-db" / "queries.yaml"


def query_core(
    cursor: psycopg2.extensions.cursor, query: str, query_vars: tuple | None = None
) -> list[tuple]:
    """
    Queries the core data from the database.

    Args:
        cursor (psycopg2.extensions.cursor): cursor to execute the query
        query (str): query to execute
        query_vars (tuple | None): arguments to pass to the query

    Returns:
        list[tuple]: the results of the query
    """
    cursor.execute(query, query_vars)

    return cursor.fetchall()


def format_result(result: tuple, column_names: list[str]) -> dict[str, Any]:
    """
    Formats a result tuple into a dictionary. If the results contain multiple values, the results
    are paired with their corresponding column names. Otherwise, the result is returned as is.

    Args:
        result (tuple): the result to be formatted
        column_names (list[str]): the column names to be used as keys

    Returns:
        dict[str, Any]: the formatted result
    """
    return dict(zip(column_names, result)) if len(result) > 1 else result[0]


def main(
    filepath: Path,
    queries_path: Path,
    host: str,
    port: str,
    database: str,
    user: str,
    password: str,
) -> None:
    """
    Main function to execute the query and convert the results to JSONL format.

    Args:
        filepath (Path): path to the output file
        queries_path (Path): path to yaml file including SQL queries
        host (str): database host
        port (str): database port
        database (str): database name
        user (str): database user
        password (str): database password
    """

    # load CORE_QUERY and VOCAB_QUERIES queries from queries.yaml
    with open(queries_path, encoding="utf-8") as f:
        queries_yaml = yaml.safe_load(f)

    core_query = queries_yaml["CORE_QUERY"]
    vocab_queries = {k: queries_yaml[v] for k, v in queries_yaml["VOCAB_QUERY_NAMES"].items()}

    with psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    ) as conn:
        with conn.cursor() as cursor:
            if cursor.description is None:
                raise ValueError("Cursor description is None. Query might have failed.")
            results: list[tuple] = query_core(cursor, core_query)
            column_names: list[str] = [desc[0] for desc in cursor.description]
            with open(filepath, "w", encoding="utf-8") as f:
                for result in results:
                    row_dict: dict[str, Any] = dict(zip(column_names, result))
                    for query_name, query in vocab_queries.items():
                        vocab_results: list[tuple] = query_core(cursor, query, (result[0],))
                        vocab_column_names: list[str] = [desc[0] for desc in cursor.description]
                        if vocab_results:
                            row_dict[query_name] = [
                                format_result(vocab_result, vocab_column_names)
                                for vocab_result in vocab_results
                            ]
                        else:
                            row_dict[query_name] = None

                    f.write(json.dumps(row_dict, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument(
        "--filepath",
        type=Path,
        default=Path("data")
        / "iterim"
        / "faktencheck-db"
        / "faktencheck-db-converted_2025-08-19.jsonl",
    )
    parser.add_argument(
        "--queries_path",
        type=Path,
        default=Path("data") / "iterim" / "faktencheck-db" / "queries.yaml",
    )
    args: argparse.Namespace = parser.parse_args()
    load_dotenv()
    main(
        filepath=args.filepath,
        queries_path=args.queries_path,
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "kibad"),
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
    )
