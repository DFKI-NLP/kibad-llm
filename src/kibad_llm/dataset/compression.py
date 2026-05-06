"""Transparent decompression context manager for reading text files.

[`open_text`][kibad_llm.dataset.compression.open_text] is a ``contextmanager`` that opens a text file with automatic
decompression based on the file suffix (mirroring pandas' compression inference):
``.gz``, ``.bz2``, ``.xz``, ``.zip``, ``.tar`` / ``.tar.gz`` / ``.tar.bz2``, and
``.zst`` (via stdlib ``compression.zstd`` on Python 3.14+ or third-party
``zstandard``).  For archive formats (zip, tar) with multiple members, the caller
must specify ``archive_member``; single-member archives are opened automatically.
"""

import bz2
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
import gzip
import importlib
import io
import lzma
from pathlib import Path
import tarfile
from typing import Literal
import zipfile

Compression = Literal["infer", "gzip", "bz2", "xz", "zip", "tar", "zst", None]


def _infer_compression(path: str | Path) -> Compression:
    """Infer compression from filename suffixes."""
    p = str(path).lower()
    if p.endswith((".tar.gz", ".tar.bz2", ".tar.xz", ".tar")):
        return "tar"
    if p.endswith(".gz"):
        return "gzip"
    if p.endswith(".bz2"):
        return "bz2"
    if p.endswith(".xz"):
        return "xz"
    if p.endswith(".zip"):
        return "zip"
    if p.endswith(".zst"):
        return "zst"
    return None


@contextmanager
def open_text(
    path: str | Path,
    *,
    encoding: str = "utf-8",
    compression: Compression = "infer",
    archive_member: str | None = None,
    errors: str = "strict",
    newline: str | None = None,
) -> Iterator[io.TextIOBase]:
    """
    Open a file in text mode with optional decompression.

    Supported when compression="infer" (by suffix, mirroring pandas):
      - .gz, .bz2, .xz, .zip, .tar/.tar.gz/.tar.bz2/.tar.xz, .zst

    Notes / limitations:
      - For .zip and .tar* archives: if archive_member is None, the archive must contain
        exactly ONE regular file, otherwise ValueError is raised.
      - For .zst: tries stdlib compression.zstd (Python 3.14+, optional module) first;
        otherwise falls back to third-party 'zstandard' if installed.
      - Only path-like inputs are supported (not already-open file objects).
    """
    method: Compression = _infer_compression(path) if compression == "infer" else compression

    with ExitStack() as stack:
        if method is None:
            yield stack.enter_context(
                open(path, encoding=encoding, errors=errors, newline=newline)
            )
            return

        if method == "gzip":
            yield stack.enter_context(
                gzip.open(path, "rt", encoding=encoding, errors=errors, newline=newline)
            )
            return

        if method == "bz2":
            yield stack.enter_context(
                bz2.open(path, "rt", encoding=encoding, errors=errors, newline=newline)
            )
            return

        if method == "xz":
            yield stack.enter_context(
                lzma.open(path, "rt", encoding=encoding, errors=errors, newline=newline)
            )
            return

        if method == "zip":
            zf = stack.enter_context(zipfile.ZipFile(path))
            names = [n for n in zf.namelist() if not n.endswith("/")]
            if archive_member is None:
                if len(names) != 1:
                    raise ValueError(
                        f"ZIP must contain exactly one file (found {len(names)}): {names}. "
                        "Pass archive_member=... to select one."
                    )
                archive_member = names[0]
            raw = stack.enter_context(zf.open(archive_member))
            yield stack.enter_context(
                io.TextIOWrapper(raw, encoding=encoding, errors=errors, newline=newline)
            )
            return

        if method == "tar":
            tf = stack.enter_context(tarfile.open(path, mode="r:*"))
            members = [m for m in tf.getmembers() if m.isfile()]
            if archive_member is None:
                if len(members) != 1:
                    names = [m.name for m in members]
                    raise ValueError(
                        f"TAR must contain exactly one file (found {len(names)}): {names}. "
                        "Pass archive_member=... to select one."
                    )
                member = members[0]
            else:
                member = tf.getmember(archive_member)

            extracted = tf.extractfile(member)
            if extracted is None:
                raise ValueError(f"Could not extract {member.name!r} from TAR.")
            raw = stack.enter_context(extracted)
            yield stack.enter_context(
                io.TextIOWrapper(raw, encoding=encoding, errors=errors, newline=newline)
            )
            return

        if method == "zst":
            # 1) Prefer stdlib in Python 3.14+: compression.zstd.open(..., 'rt', ...)
            try:
                zstd = importlib.import_module("compression.zstd")
                yield stack.enter_context(
                    zstd.open(path, "rt", encoding=encoding, errors=errors, newline=newline)
                )
                return
            except ModuleNotFoundError:
                pass

            # 2) Fallback: third-party 'zstandard'
            try:
                zstandard = importlib.import_module("zstandard")
            except ModuleNotFoundError as e:
                raise ModuleNotFoundError(
                    "Reading .zst requires either Python 3.14+ with the optional stdlib "
                    "'compression.zstd' module available, or installing 'zstandard'."
                ) from e

            raw_file = stack.enter_context(open(path, "rb"))
            dctx = zstandard.ZstdDecompressor()
            reader = dctx.stream_reader(raw_file)
            stack.callback(reader.close)
            yield stack.enter_context(
                io.TextIOWrapper(reader, encoding=encoding, errors=errors, newline=newline)
            )
            return

        raise ValueError(f"Unsupported compression={method!r}")
