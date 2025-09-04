import json
import os

import argparse
import psycopg2
from dotenv import load_dotenv


load_dotenv()

FILEPATH: str = "results.jsonl"
QUERY: str = """select c.zotitem_ptr_id, c.status,  c.bibtex_author, c.bibtex_title, c.bibtex_year, c.bibtex_type 
from core_zotaddon c
where c.status = 'abgeschlossen' 
order by zotitem_ptr_id asc, bibtex_author asc
limit 10;"""


def to_jsonl(results: list[tuple], filepath: str) -> None:
    """
    Convert a list of tuples to a JSONL file.

    Args:
        results: A list of tuples to convert to JSONL.
        filepath: The path to the JSONL file to write.
    """
    with open(filepath, "w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")


def main(args: argparse.Namespace) -> None:
    with psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "kibad"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(args.query)
            results: list[tuple] = cursor.fetchall()
            print(results)
            # to_jsonl(results, args.filepath)


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--filepath", type=str, default=FILEPATH)
    parser.add_argument("--query", type=str, default=QUERY)
    
    args: argparse.Namespace = parser.parse_args()
    main(args)
