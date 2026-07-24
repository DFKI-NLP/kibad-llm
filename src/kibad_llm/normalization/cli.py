"""Command-line helpers for normalizing names in JSON Lines files.

Functions:
    process_json_lines_file: Normalize names in a JSON Lines file with a normalizer.
    main: Run the command-line interface.
"""

import argparse
from collections.abc import Callable
from dataclasses import dataclass
import json
import logging
from pathlib import Path

from .gbif import add_arguments as add_gbif_arguments
from .gbif import create_normalizer as create_gbif_normalizer

logger = logging.getLogger(__name__)

Normalizer = Callable[[str], str | None]


@dataclass(frozen=True)
class NormalizationMethod:
    """Configure a normalization method for the command-line interface.

    Args:
        add_arguments: Function that adds method-specific command-line arguments.
        create_normalizer: Function that creates a normalizer from parsed command-line arguments.
    """

    add_arguments: Callable[[argparse.ArgumentParser], None]
    create_normalizer: Callable[[argparse.Namespace], Normalizer]


NORMALIZATION_METHODS: dict[str, NormalizationMethod] = {
    "gbif": NormalizationMethod(add_gbif_arguments, create_gbif_normalizer),
}


def _normalize_names(
    name: str | list[str],
    normalizer: Normalizer,
) -> tuple[str | None | list[str | None], int, int]:
    """Normalize a name or a homogeneous list of names.

    Args:
        name: A name or a list of names.
        normalizer: Function used to normalize one name.

    Returns:
        A tuple consisting of:
            - The normalized name, or a list of normalized names in the original order.
            - The number of names processed.
            - The number of names successfully normalized.
    """
    if isinstance(name, list):
        if not all(isinstance(item, str) for item in name):
            raise TypeError("Species name lists must contain only strings")
        normalized_names = [normalizer(item) for item in name]
        return (
            normalized_names,
            len(name),
            len([item for item in normalized_names if item is not None]),
        )

    normalized_name = normalizer(name)
    return normalized_name, 1, 1 if normalized_name is not None else 0


def _process_json_object(
    json_value: object,
    parent_keys: list[str],
    read_key: str,
    write_key: str,
    normalizer: Normalizer,
) -> tuple[int, int]:
    """Find JSON objects through nested dictionaries and lists, then write normalized names.

    Args:
        json_value: Current JSON value to process.
        parent_keys: Remaining dictionary keys to navigate before reading a name.
        read_key: Key containing the name or list of names to normalize.
        write_key: Key receiving the normalized name or list of normalized names.
        normalizer: Function used to normalize one name.

    Returns:
        A tuple consisting of:
         - The number of names processed.
         - The number of names successfully normalized.
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

    name = json_value.get(read_key)
    if name is None:
        return num_processed, num_normalized
    if not isinstance(name, (str, list)):
        raise TypeError("Species names must be a string or a list of strings")
    json_value[write_key], new_processed, new_normalized = _normalize_names(
        name,
        normalizer,
    )

    return new_processed, new_normalized


def _collect_names_json_object(
    json_value: object,
    parent_keys: list[str],
    read_key: str,
) -> list[str]:
    """Collect names from a JSON object through nested dictionaries and lists.

    Args:
        json_value: Current JSON value to process.
        parent_keys: Remaining dictionary keys to navigate before reading a name.
        read_key: Key containing the name or list of names to collect.

    Returns:
        A list of names found in the JSON object.
    """
    names = []
    if isinstance(json_value, list):
        for item in json_value:
            names.extend(_collect_names_json_object(item, parent_keys, read_key))
        return names

    if not isinstance(json_value, dict):
        return []

    if parent_keys:
        child = json_value.get(parent_keys[0])
        if child is not None:
            names.extend(_collect_names_json_object(child, parent_keys[1:], read_key))
        return names

    name = json_value.get(read_key)
    if name is None:
        return []
    if isinstance(name, str):
        return [name]
    if isinstance(name, list) and all(isinstance(item, str) for item in name):
        return name
    raise TypeError("Species names must be a string or a list of strings")


def process_json_lines_file(
    input_path: str,
    read_key: str,
    normalizer: Normalizer,
    output_path: str | None = None,
    write_key: str | None = None,
    parent_keys: list[str] | None = None,
) -> None:
    """Normalize names in a JSON Lines file.

    Args:
        input_path: Path to the input JSON Lines file.
        read_key: Key to extract the name or list of names from each JSON object.
        output_path: Path to the normalized JSON Lines file. If not provided,
            the output file will be written beside the input as
            "{input_path.stem}_normalized_names.jsonl".
        write_key: Key to write the normalized name or list of normalized names to.
            If not provided, the result will be written to "{read_key}_normalized".
        parent_keys: Parent keys to navigate before reading a name. Each level may contain a
            nested dictionary or a list of nested dictionaries.
        normalizer: Function used to normalize one name.

    """
    logger.info(f"Normalizing species names in JSON Lines file: {input_path}")
    input_file_path = Path(input_path)
    _output_file = output_path or str(
        input_file_path.with_name(f"{input_file_path.stem}_normalized_names.jsonl")
    )
    if Path(_output_file).is_file():
        logger.warning(f"Output file {_output_file} already exists. It will be overwritten.")

    # first, collect all unique names
    with open(input_file_path) as input_file:
        all_names = []
        for line in input_file:
            json_obj = json.loads(line)
            names = _collect_names_json_object(json_obj, parent_keys or [], read_key)
            all_names.extend(names)

    all_unique_names = set(all_names)
    logger.info(
        f"Unique names found for key={read_key} and parent_keys={parent_keys}: {len(all_unique_names)}"
    )

    # then, normalize all unique names
    name2normalized = {name: normalizer(name) for name in all_unique_names}
    logger.info(
        f"Normalized names found: {len([n for n in name2normalized.values() if n is not None])}"
    )

    # finally, process the file again and write normalized names

    write_key = write_key or f"{read_key}_normalized"
    num_processed, num_normalized, num_lines = 0, 0, 0
    with open(input_path) as input_file:
        with open(_output_file, "w") as output_file:
            for line in input_file:
                json_obj = json.loads(line)
                new_processed, new_normalized = _process_json_object(
                    json_obj,
                    parent_keys or [],
                    read_key,
                    write_key,
                    lambda name: name2normalized.get(name),
                )
                num_processed += new_processed
                num_normalized += new_normalized
                output_file.write(json.dumps(json_obj) + "\n")
                num_lines += 1
    logger.info(
        f"Processed {num_lines} lines, normalized {num_normalized} names out of {num_processed} processed."
    )
    logger.info(f"Result was written to: {_output_file}")


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add JSON Lines processing options to a command-line parser."""
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
        "output file will be written beside the input as "
        "'{input_path.stem}_normalized_names.jsonl'.",
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
        help="Parent keys to navigate before reading a name. Each level may contain a nested "
        "dictionary or a list of nested dictionaries.",
    )


def main() -> None:
    """Parse command-line arguments and normalize names in a JSON Lines file."""
    parser = argparse.ArgumentParser(
        description="Normalize names in a JSON Lines file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    method_parsers = parser.add_subparsers(dest="method", required=True)
    for method_name, method in NORMALIZATION_METHODS.items():
        method_parser = method_parsers.add_parser(
            method_name,
            help=f"Normalize names with {method_name.upper()}.",
        )
        _add_common_arguments(method_parser)
        method.add_arguments(method_parser)

    args = parser.parse_args()
    method = NORMALIZATION_METHODS[args.method]
    process_json_lines_file(
        input_path=args.input_path,
        read_key=args.read_key,
        output_path=args.output_path,
        write_key=args.write_key,
        parent_keys=args.parent_keys,
        normalizer=method.create_normalizer(args),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
