from __future__ import annotations

from collections.abc import Collection
import hashlib
import mimetypes
from pathlib import Path
import shutil
import time
from typing import Literal

from .func import map_mt_with_tqdm
from .logger import get_logger

__all__ = ['is_image', 'mkdir_p', 'mkdir_p_parallel', 'cp_p', 'cp_p_parallel']

logger = get_logger()

def is_image(path: Path) -> bool:
    """Tests if a file is an image or not."""
    filetype, _ = mimetypes.guess_type(path)
    return filetype is not None and filetype.startswith('image/')

def cksum(path: Path, *, digest: Literal['sha256', 'sha512']) -> str:
    """As the Unix command `cksum`, which computes the checksum of a file."""
    if digest == 'sha256':
        hasher = hashlib.sha256()
    elif digest == 'sha512':
        hasher = hashlib.sha512()

    try:
        hasher.update(path.read_bytes())
    except Exception:
        logger.warning('File (%s) cannot be opened.', path, exc_info=True)
        return ''

    return hasher.hexdigest()

def mkdir_p(path: Path) -> None:
    """
    As the Unix command `mkdir -p`, which automatically creates any parent directories
    along the way if necessary and allows existing directories.
    """
    return path.mkdir(parents=True, exist_ok=True)

def _mkdir_p_passthrough_on_fail(path: Path) -> Path | None:
    """As :func:`mkdir_p`, but returns the original arguments if the operation fails."""
    try:
        mkdir_p(path)
    except OSError:
        return path

def mkdir_p_parallel(path_multi: Collection[Path], *, n_jobs: int, desc: str, retry_count: int = 5):
    """Runs :func:`mkdir_p` in parallel and attempts to retry failed invocations."""
    if retry_count <= 0:
        msg = '`retry_count` must be a positive integer'
        raise ValueError(msg)

    for i in range(retry_count + 1):
        path_multi = [
            result for result in map_mt_with_tqdm(
                path_multi,
                _mkdir_p_passthrough_on_fail,
                n_jobs=n_jobs,
                desc=desc,
            )
            if result is not None
        ]

        if len(path_multi) == 0:
            return

        if i < retry_count:
            logger.warning('Failed to create %s directories. Retrying...', len(path_multi), exc_info=True)
            time.sleep(1)
        else:
            msg = f"Failed to create directories: {path_multi}"
            raise RuntimeError(msg)

    msg = "Should never be reached"
    raise AssertionError(msg)

def cp_p(src_dst: tuple[Path, Path]):
    """
    As the Unix command `cp -p`, which copies a file while preserving file metadata
    as best as possible.
    """
    src, dst = src_dst
    return shutil.copy2(src, dst)

def _cp_p_passthrough_on_fail(src_dst: tuple[Path, Path]) -> tuple[Path, Path] | None:
    """As :func:`cp_p`, but returns the original arguments if the operation fails."""
    try:
        cp_p(src_dst)
    except OSError:
        return src_dst

def cp_p_parallel(src_dst_multi: Collection[tuple[Path, Path]], *, n_jobs: int, desc: str, retry_count: int = 5):
    """Runs :func:`cp_p` in parallel and attempts to retry failed invocations."""
    if retry_count <= 0:
        msg = '`retry_count` must be a positive integer'
        raise ValueError(msg)

    for i in range(retry_count + 1):
        src_dst_multi = [
            result for result in map_mt_with_tqdm(
                src_dst_multi,
                _cp_p_passthrough_on_fail,
                n_jobs=n_jobs,
                desc=desc,
            )
            if result is not None
        ]

        if len(src_dst_multi) == 0:
            return

        if i < retry_count:
            logger.warning('Failed to copy %s files. Retrying...', len(src_dst_multi), exc_info=True)
            time.sleep(1)
        else:
            src_dst_multi_str = [f"{src} -> {dst}" for src, dst in src_dst_multi]
            msg = f"Failed to copy files: {src_dst_multi_str}"
            raise RuntimeError(msg)

    msg = "Should never be reached"
    raise AssertionError(msg)
