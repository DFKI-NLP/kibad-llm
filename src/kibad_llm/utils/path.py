import os
from pathlib import Path


def strip_filename_extension(file_path: str) -> str:
    return os.path.splitext(file_path)[0]


def list_subdirectories_as_string(dir_path: str | list[str] | None, pattern: str = "*") -> str:
    """Lists subdirectories in the given directory path(s) matching the pattern and returns
    them as a comma-separated string. Useful as an OmegaConf resolver to dynamically get
    directory lists as multirun inputs.
    """
    # this is required so that the resolver does not fail when no input is given (non multirun case)
    if dir_path is None:
        return ""

    if not isinstance(dir_path, list):
        dir_path = [dir_path]
    paths: list[str] = []
    for dir_path in dir_path:
        paths.extend(str(p) for p in Path(dir_path).glob(pattern) if p.is_dir())
    if not paths:
        raise ValueError(f"No directories found in {dir_path!r} with pattern {pattern!r}")

    return ",".join(sorted(paths))
