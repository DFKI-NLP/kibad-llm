import argparse
from collections.abc import Callable
import json
import logging
from pathlib import Path

from kibad_llm.normalization import normalize_spezies

logger = logging.getLogger(__name__)


def _normalize_names(
    name: str | list[str], func: Callable[..., str | None], **kwargs
) -> tuple[str | None | list[str | None], int, int]:
    """Normalize a scientific name or a homogeneous list of scientific names.

    Args:
        name: A scientific name or a list of scientific names.
        kwargs: Additional keyword arguments to pass to normalize_spezies function.

    Returns:
        A tuple consisting of:
            - The normalized name, or a list of normalized names in the original order.
            - The number of names processed.
            - The number of names successfully normalized.
    """
    if isinstance(name, list):
        if not all(isinstance(item, str) for item in name):
            raise TypeError("Species name lists must contain only strings")
        normalized_names = [func(item, **kwargs) for item in name]
        return (
            normalized_names,
            len(name),
            len([item for item in normalized_names if item is not None]),
        )

    normalized_name = func(name, **kwargs)
    return normalized_name, 1, 1 if normalized_name is not None else 0


def _process_json_object(
    json_value: object, parent_keys: list[str], read_key: str, write_key: str, **kwargs
) -> tuple[int, int]:
    """Find JSON objects through nested dictionaries and lists, then write normalized names.

    Args:
        json_value: Current JSON value to process.
        parent_keys: Remaining dictionary keys to navigate before reading a name.
        read_key: Key containing the name or list of names to normalize.
        write_key: Key receiving the normalized name or list of normalized names.
        kwargs: Additional keyword arguments to pass to normalize_spezies function.

    Returns:
        A tuple consisting of:
         - The number of names processed.
         - The number of names successfully normalized.
    """
    num_processed, num_normalized = 0, 0
    if isinstance(json_value, list):
        for item in json_value:
            new_processed, new_normalized = _process_json_object(
                item, parent_keys, read_key, write_key, **kwargs
            )
            num_processed += new_processed
            num_normalized += new_normalized
        return num_processed, num_normalized

    if not isinstance(json_value, dict):
        return 0, 0

    if parent_keys:
        child = json_value.get(parent_keys[0])
        if child is not None:
            new_processed, new_normalized = _process_json_object(
                child, parent_keys[1:], read_key, write_key, **kwargs
            )
            return new_processed, new_normalized
        return 0, 0

    name = json_value.get(read_key)
    if name is None:
        return num_processed, num_normalized
    if not isinstance(name, (str, list)):
        raise TypeError("Species names must be a string or a list of strings")
    json_value[write_key], new_processed, new_normalized = _normalize_names(name, **kwargs)

    return new_processed, new_normalized


def process_json_lines_file(
    input_path: str,
    read_key: str,
    output_path: str | None = None,
    write_key: str | None = None,
    parent_keys: list[str] | None = None,
    **kwargs,
) -> None:
    """Normalize names in a JSON Lines file.

    Args:
        input_path: Path to the input JSON Lines file.
        read_key: Key to extract the species name or list of names from each JSON object.
        output_path: Path to the normalized JSON Lines file. If not provided,
            the output file will be named "{input_path.stem}_normalized_names.json".
        write_key: Key to write the normalized species name or list of normalized names to.
            If not provided, the result will be written to "{read_key}_normalized.json".
        parent_keys: Parent keys to navigate before reading a name. Each level may contain a
            nested dictionary or a list of nested dictionaries.
        kwargs: Additional keyword arguments to pass to normalize_spezies function.
    """
    logger.info(f"Normalizing species names in JSON Lines file: {input_path}")
    _output_file = output_path or f"{Path(input_path).stem}_normalized_names.json"
    write_key = write_key or f"{read_key}_normalized"
    num_processed, num_normalized, num_lines = 0, 0, 0
    with open(input_path) as input_file:
        with open(_output_file, "w") as output_file:
            for line in input_file:
                json_obj = json.loads(line)
                new_processed, new_normalized = _process_json_object(
                    json_obj, parent_keys or [], read_key, write_key, **kwargs
                )
                num_processed += new_processed
                num_normalized += new_normalized
                output_file.write(json.dumps(json_obj) + "\n")
                num_lines += 1
    logger.info(
        f"Processed {num_lines} lines, normalized {num_normalized} names out of {num_processed} processed."
    )
    logger.info(f"Result was written to: {_output_file}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Normalize species names in a JSON Lines file using GBIF's Species Match API.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input-path", required=True, help="Path to the input JSON Lines file.")
    parser.add_argument(
        "--read-key",
        required=True,
        help="Key to read the species name or list of names from each JSON object.",
    )
    parser.add_argument(
        "--output-path",
        default=None,
        help="Path to the output JSON Lines file. If not provided, the "
        "output file will be named '{input_path.stem}_normalized_names.json'.",
    )
    parser.add_argument(
        "--write-key",
        default=None,
        help="Key to write the normalized species name or list of normalized names to. "
        "If not provided, the result will be written to '{read_key}_normalized'.",
    )
    parser.add_argument(
        "--parent-keys",
        nargs="*",
        default=[],
        help="Parent keys to navigate before reading a name. Each level may contain a nested dictionary "
        "or a list of nested dictionaries.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        help="Minimum GBIF match confidence percentage required to return a name.",
    )
    parser.add_argument(
        "--query-param",
        help="Query parameter name used to send the species name to GBIF.",
    )
    parser.add_argument(
        "--response-field",
        help="Response field containing the normalized species name.",
    )
    args = parser.parse_args()

    kwargs = vars(args)
    process_json_lines_file(func=normalize_spezies, **kwargs)
