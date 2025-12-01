import os


def strip_filename_extension(file_path: str) -> str:
    return os.path.splitext(file_path)[0]
