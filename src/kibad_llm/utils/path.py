import os
from pathlib import Path


def strip_filename_extension(file_path: str) -> str:
    return os.path.splitext(file_path)[0]


def get_directories_with_file(
    paths: str | list[str] | None, filename: str, leafs_only: bool = False
) -> list[str]:
    """Find all directories in the given paths that contain a file with the specified filename.

    Args:
        paths: List of paths.
        filename: Name of the file to search for in the directories.
        leafs_only: If True, only return the leaf directories (i.e., those that are not
            parents of other directories in the list).
    Returns:
        List of directory paths where each directory contains the specified filename.
    """
    # this is required so that the resolver does not fail when no input is given (non multirun case)
    if paths is None:
        return []

    if isinstance(paths, str):
        paths = [paths]

    result_paths = []
    for path in paths:
        # raise an error if path contains glob patterns
        if any(char in path for char in "*?[]{}"):
            raise ValueError(
                f"Path '{path}' contains glob patterns. Please provide explicit paths without glob patterns."
            )
        current_paths = Path(path).glob(f"**/{filename}")
        for p in current_paths:
            result_paths.extend([p.parent])

    # deduplicate and sort
    result_paths = sorted(set(result_paths))

    # filter to only keep leaf directories if requested
    if leafs_only:
        result_paths = [
            p
            for p in result_paths
            if not any(other != p and other.is_relative_to(p) for other in result_paths)
        ]

    result = [str(p) for p in result_paths]
    return result
