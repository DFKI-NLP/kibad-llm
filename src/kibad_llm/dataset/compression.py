import bz2
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
import gzip
import io
import logging
import lzma
from pathlib import Path
import tarfile
from typing import Any, Literal
import zipfile

logger = logging.getLogger(__name__)

Compression = Literal["infer", "gzip", "bz2", "xz", "zip", "zstd", "tar", None]


def _infer_compression(path: str | Path) -> Compression:
    """Infer compression from filename suffixes, mirroring pandas' documented list."""
    p = str(path).lower()

    # check multi-suffix first
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
        return "zstd"
    return None


@contextmanager
def open_text(
    path: str | Path,
    *,
    encoding: str = "utf-8",
    compression: Compression | dict[str, Any] = "infer",
    archive_member: str | None = None,
    errors: str = "strict",
    newline: str | None = None,
) -> Iterator[io.TextIOBase]:
    """
    Open possibly-compressed text file, similar to pandas compression='infer'.

    If compression is a dict, expects at least {"method": "..."} and forwards remaining
    keys as options where it makes sense (zipfile / tarfile / zstd).
    """
    options: dict[str, Any] = {}
    method: Compression

    if isinstance(compression, dict):
        method = compression.get("method", "infer")  # type: ignore[assignment]
        options = {k: v for k, v in compression.items() if k != "method"}
    else:
        method = compression

    if method == "infer":
        method = _infer_compression(path)

    with ExitStack() as stack:
        if method is None:
            f = stack.enter_context(open(path, encoding=encoding, errors=errors, newline=newline))
            yield f
            return

        if method == "gzip":
            f = stack.enter_context(
                gzip.open(path, "rt", encoding=encoding, errors=errors, newline=newline)
            )
            yield f
            return

        if method == "bz2":
            f = stack.enter_context(
                bz2.open(path, "rt", encoding=encoding, errors=errors, newline=newline)
            )
            yield f
            return

        if method == "xz":
            f = stack.enter_context(
                lzma.open(path, "rt", encoding=encoding, errors=errors, newline=newline)
            )
            yield f
            return

        if method == "zip":
            zf = stack.enter_context(zipfile.ZipFile(path, **options))
            names = [n for n in zf.namelist() if not n.endswith("/")]
            if archive_member is None:
                if len(names) != 1:
                    raise ValueError(
                        f"ZIP archive must contain exactly one file (found {len(names)}): {names}. "
                        "Pass archive_member=... to select one."
                    )
                archive_member = names[0]
            raw = stack.enter_context(zf.open(archive_member))
            txt = stack.enter_context(
                io.TextIOWrapper(raw, encoding=encoding, errors=errors, newline=newline)
            )
            yield txt
            return

        if method == "tar":
            tf = stack.enter_context(tarfile.open(path, mode="r:*", **options))
            members = [m for m in tf.getmembers() if m.isfile()]
            if archive_member is None:
                if len(members) != 1:
                    names = [m.name for m in members]
                    raise ValueError(
                        f"TAR archive must contain exactly one file (found {len(names)}): {names}. "
                        "Pass archive_member=... to select one."
                    )
                member = members[0]
            else:
                member = tf.getmember(archive_member)

            extracted = tf.extractfile(member)
            if extracted is None:
                raise ValueError(f"Could not extract member {member.name!r} from TAR archive.")
            raw = stack.enter_context(extracted)
            txt = stack.enter_context(
                io.TextIOWrapper(raw, encoding=encoding, errors=errors, newline=newline)
            )
            yield txt
            return

        if method == "zstd":
            # Prefer stdlib in Python 3.14+: compression.zstd.open supports text mode. :contentReference[oaicite:3]{index=3}
            try:
                from compression import zstd as zstd_mod  # Python 3.14+

                f = stack.enter_context(
                    zstd_mod.open(
                        path, "rt", encoding=encoding, errors=errors, newline=newline, **options
                    )
                )
                yield f
                return
            except ModuleNotFoundError:
                pass

            # Fallback: third-party 'zstandard' (what pandas requires for .zst). :contentReference[oaicite:4]{index=4}
            try:
                import zstandard as zstandard  # type: ignore
            except ModuleNotFoundError as e:
                raise ModuleNotFoundError(
                    "Reading .zst requires either Python 3.14+ (compression.zstd) "
                    "or the third-party 'zstandard' package."
                ) from e

            raw_file = stack.enter_context(open(path, "rb"))
            dctx = zstandard.ZstdDecompressor()
            reader = dctx.stream_reader(raw_file)
            stack.callback(reader.close)
            txt = stack.enter_context(
                io.TextIOWrapper(reader, encoding=encoding, errors=errors, newline=newline)
            )
            yield txt
            return

        raise ValueError(f"Unsupported compression method: {method!r}")
