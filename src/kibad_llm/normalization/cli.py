"""Command-line helpers for normalizing values in JSON Lines files.

Functions:
    process_json_lines_file: Normalize values in a JSON Lines file with a normalizer.
    main: Run the command-line interface.
"""

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
import json
import logging
from pathlib import Path
from typing import Any, overload

from tqdm import tqdm

from .gbif import CLI_DESCRIPTION_TEXT as GBIF_DESCRIPTION_TEXT
from .gbif import CLI_HELP_TEXT as GBIF_HELP_TEXT
from .gbif import add_arguments as add_gbif_arguments
from .gbif import create_normalizer as create_gbif_normalizer

logger = logging.getLogger(__name__)

Normalizer = Callable[[str], dict[str, Any] | None]


@dataclass(frozen=True)
class NormalizationMethod:
    """Configure a normalization method for the command-line interface.

    Args:
        add_arguments: Function that adds method-specific command-line arguments.
        create_normalizer: Function that creates a normalizer from parsed command-line arguments.
    """

    add_arguments: Callable[[argparse.ArgumentParser], None]
    create_normalizer: Callable[[argparse.Namespace], Normalizer]
    help: str
    description: str


NORMALIZATION_METHODS: dict[str, NormalizationMethod] = {
    "gbif": NormalizationMethod(
        add_gbif_arguments,
        create_gbif_normalizer,
        GBIF_HELP_TEXT,
        GBIF_DESCRIPTION_TEXT,
    ),
}


@overload
def _normalize_values(
    value: str,
    normalizer: Normalizer,
) -> tuple[dict[str, Any] | None, int, int]: ...


@overload
def _normalize_values(
    value: list[str],
    normalizer: Normalizer,
) -> tuple[list[dict[str, Any] | None], int, int]: ...


def _normalize_values(
    value: str | list[str],
    normalizer: Normalizer,
) -> tuple[dict[str, Any] | None | list[dict[str, Any] | None], int, int]:
    """Normalize a value or a homogeneous list of values.

    Args:
        value: A value or a list of values.
        normalizer: Function used to normalize one value.

    Returns:
        A tuple consisting of:\n
            - The normalized value, or a list of normalized values in the original order.
            - The number of values processed.
            - The number of values successfully normalized.
    """
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            raise TypeError("Values lists must contain only strings")
        normalized_values = [normalizer(item) for item in value]
        return (
            normalized_values,
            len(value),
            len([item for item in normalized_values if item is not None]),
        )

    normalized_value = normalizer(value)
    return normalized_value, 1, 1 if normalized_value is not None else 0


def _process_json_object(
    json_value: object,
    parent_keys: list[str],
    read_key: str,
    write_key: str,
    normalizer: Normalizer,
) -> tuple[int, int]:
    """Find JSON objects through nested dictionaries and lists, then write normalized values.

    Args:
        json_value: Current JSON value to process.
        parent_keys: Remaining dictionary keys to navigate before reading a value.
        read_key: Key containing the value or list of values to normalize.
        write_key: Key receiving the normalized value or list of normalized values.
        normalizer: Function used to normalize one value.

    Returns:
        A tuple consisting of:\n
         - The number of values processed.
         - The number of values successfully normalized.
    """
    num_processed, num_normalized = 0, 0
    if isinstance(json_value, list):
        for item in json_value:
            new_processed, new_normalized = _process_json_object(
                item,
                parent_keys,
                read_key,
                write_key,
                normalizer,
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
                child,
                parent_keys[1:],
                read_key,
                write_key,
                normalizer,
            )
            return new_processed, new_normalized
        return 0, 0

    value = json_value.get(read_key)
    if value is None:
        return num_processed, num_normalized
    if not isinstance(value, (str, list)):
        raise TypeError("Values must be a string or a list of strings")
    json_value[write_key], new_processed, new_normalized = _normalize_values(
        value,
        normalizer,
    )

    return new_processed, new_normalized


def _collect_values_json_object(
    json_value: object,
    parent_keys: list[str],
    read_key: str,
) -> list[str]:
    """Collect values from a JSON object through nested dictionaries and lists.

    Args:
        json_value: Current JSON value to process.
        parent_keys: Remaining dictionary keys to navigate before reading a value.
        read_key: Key containing the value or list of values to collect.

    Returns:
        A list of values found in the JSON object.
    """
    values = []
    if isinstance(json_value, list):
        for item in json_value:
            values.extend(_collect_values_json_object(item, parent_keys, read_key))
        return values

    if not isinstance(json_value, dict):
        return []

    if parent_keys:
        child = json_value.get(parent_keys[0])
        if child is not None:
            values.extend(_collect_values_json_object(child, parent_keys[1:], read_key))
        return values

    value = json_value.get(read_key)
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise TypeError("Values must be a string or a list of strings")


def process_json_lines_file(
    input_path: Path,
    output_path: Path,
    read_key: str,
    write_key: str,
    normalizer: Normalizer,
    parent_keys: list[str] | None = None,
    encoding: str = "utf-8",
    replace_input: bool = False,
) -> None:
    """Normalize values in a JSON Lines file.

    Args:
        input_path: Path to the input JSON Lines file.
        output_path: Path to the normalized JSON Lines file.
        read_key: Key to extract the value or list of values from each JSON object.
        write_key: Key to write the normalized value or list of normalized values to.
        normalizer: Function used to normalize one value.
        parent_keys: Parent keys to navigate before reading a value. Each level may contain a
            nested dictionary or a list of nested dictionaries.
        encoding: Encoding to use for reading and writing JSON Lines files.
        replace_input: If True, the input file will be replaced with the normalized output.
            A backup of the original input file will be saved to output_path.

    """
    logger.info(f"Normalizing values in JSON Lines file: {input_path}")
    if input_path == output_path:
        raise ValueError("Input and output paths must be different.")
    if output_path.is_file():
        logger.warning(f"Output file {output_path} already exists. It will be overwritten.")

    if replace_input:
        # in the case of when we want to replace the input file, we first save a backup of
        # the original input file to the output path and then swap the input and output paths
        # so that the normalized values are written to the original input file
        backup_path = output_path
        input_path.replace(backup_path)
        logger.info(f"Backup of the original input file was saved to: {backup_path}")
        output_path = input_path
        input_path = backup_path

    # first, collect all unique values
    with open(input_path, encoding=encoding) as input_file:
        all_values = []
        for line in input_file:
            json_obj = json.loads(line)
            values = _collect_values_json_object(json_obj, parent_keys or [], read_key)
            all_values.extend(values)

    all_unique_values = set(all_values)
    logger.info(
        f"Unique values found for key={read_key} and parent_keys={parent_keys}: {len(all_unique_values)}"
    )

    # then, normalize all unique values (show progress bar since this may take some time)
    value2normalized = {value: normalizer(value) for value in tqdm(sorted(all_unique_values))}
    logger.info(
        f"Normalized values found: {len([v for v in value2normalized.values() if v is not None])}"
    )

    # finally, process the file again and write normalized values
    num_processed, num_normalized, num_lines = 0, 0, 0
    with open(input_path, encoding=encoding) as input_file:
        with open(output_path, "w", encoding=encoding) as output_file:
            for line in input_file:
                json_obj = json.loads(line)
                new_processed, new_normalized = _process_json_object(
                    json_obj,
                    parent_keys or [],
                    read_key,
                    write_key,
                    lambda value: value2normalized.get(value),
                )
                num_processed += new_processed
                num_normalized += new_normalized
                output_file.write(json.dumps(json_obj, ensure_ascii=False) + "\n")
                num_lines += 1
    logger.info(
        f"Processed {num_lines} lines, normalized {num_normalized} values out of {num_processed} processed."
    )
    logger.info(f"Result was written to: {output_path}")


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add JSON Lines processing options to a command-line parser."""
    parser.add_argument(
        "--input-path",
        required=True,
        type=Path,
        nargs="+",
        help="One or multiple paths to the input JSON Lines files.",
    )
    parser.add_argument(
        "--output-path",
        default=None,
        nargs="+",
        help="Path(s) to the output JSON Lines files. If provided, has to have the same number "
        "of paths as input files. If not provided, the output files will be written beside "
        "the input files as '{input_path.stem}_{read_key}_normalized.jsonl' or "
        "'{input_path.stem}_{read_key}_backup.jsonl' if --replace-input is enabled.",
    )
    parser.add_argument(
        "--replace-input",
        action="store_true",
        help="Replace the input files with the normalized output. If enabled, --output-path is used "
        "to save a backup of the original input files.",
    )
    parser.add_argument(
        "--read-key",
        required=True,
        help="Key to read the value or list of values from each JSON object.",
    )
    parser.add_argument(
        "--write-key",
        default=None,
        help="Key to write the normalized value or list of normalized values to. "
        "If not provided, the result will be written to '{method}_normalized'.",
    )
    parser.add_argument(
        "--parent-keys",
        nargs="*",
        default=[],
        help="Parent keys to navigate before reading a value. Each level may contain a nested "
        "dictionary or a list of nested dictionaries.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Encoding of the input and output JSON Lines files.",
    )
    parser.add_argument(
        "--cache-size",
        type=int,
        default=10_000,
        help="Maximum size of the LRU cache for the normalizer.",
    )


def main() -> None:
    """Parse command-line arguments and normalize values in one or multiple JSON Lines files."""
    parser = argparse.ArgumentParser(
        description="Normalize values in one or multiple JSON Lines files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    method_parsers = parser.add_subparsers(
        dest="method", required=True, help="Normalization method to use."
    )
    for method_name, method in NORMALIZATION_METHODS.items():
        method_parser = method_parsers.add_parser(
            method_name,
            description=method.description,
            help=method.help,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        _add_common_arguments(method_parser)
        method.add_arguments(method_parser)

    args = parser.parse_args()
    method = NORMALIZATION_METHODS[args.method]
    write_key = args.write_key or f"{args.method}_normalized"
    normalizer = lru_cache(maxsize=args.cache_size)(method.create_normalizer(args))

    if args.output_path is not None:
        if len(args.input_path) != len(args.output_path):
            raise ValueError(
                "Number of input paths must match number of output paths if both are provided."
            )
        output_path = args.output_path
    else:
        if args.replace_input:
            output_path = [
                input_path.with_name(f"{input_path.stem}_{args.read_key}_backup.jsonl")
                for input_path in args.input_path
            ]
        else:
            output_path = [
                input_path.with_name(f"{input_path.stem}_{args.read_key}_normalized.jsonl")
                for input_path in args.input_path
            ]

    for input_path, output_path in zip(args.input_path, output_path):
        process_json_lines_file(
            input_path=input_path,
            read_key=args.read_key,
            output_path=output_path,
            write_key=write_key,
            parent_keys=args.parent_keys,
            normalizer=normalizer,
            replace_input=args.replace_input,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
