"""This script converts a SQLite database to a JSONL file."""

import argparse
import json
import sqlite3

from queries import Queries, QueryTypes


def query_db(cursor: sqlite3.Cursor, query_type: str) -> sqlite3.Cursor:
    """
    Queries the database and returns the results.

    Args:
        cursor (sqlite3.Cursor): the cursor to use to query the database
        query_type (str): the type of query to execute

    Returns:
        sqlite3.Cursor: the results of the query

    Raises:
        ValueError: if the specified query type is invalid
    """
    match query_type:
        case QueryTypes.SINGLE.value:
            return cursor.execute(Queries.SINGLE.value)
        case _:
            raise ValueError(f"Invalid query type: {query_type}")


def results_to_json(results: sqlite3.Cursor, jsonl_path: str) -> None:
    """
    Writes the query results to a JSONL file.

    Args:
        results (sqlite3.Cursor): the results of the query
        jsonl_path (str): the path to the JSONL file
    """
    with open(jsonl_path, "w") as f:
        for row in results:
            f.write(f'{json.dumps(row)}\n')


def main(args: argparse.Namespace) -> None:
    """
    Connects to a database, queries it, then writes the results to a JSONL file.

    Args:
        args (argparse.Namespace): the arguments
    """
    connection: sqlite3.Connection = sqlite3.connect(args.db_path)
    cursor: sqlite3.Cursor = connection.cursor()
    results: sqlite3.Cursor = query_db(cursor, args.query_type)
    results_to_json(results, args.jsonl_path)


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--db_path", type=str, required=True)
    parser.add_argument("--jsonl_path", type=str, required=True)
    parser.add_argument("--query_type", type=str, default="single", choices=QueryTypes.list())
    args: argparse.Namespace = parser.parse_args()
    main(args)
