from __future__ import annotations

from collections.abc import Collection
import functools
import hashlib
import mimetypes
from pathlib import Path
import shutil
from typing import Literal

from .func import JobsFailed, map_mt_with_tqdm, map_with_retry
from .logger import get_logger

__all__ = [
    'is_image', 'cksum', 'cksum_parallel',
    'mkdir_p', 'mkdir_p_parallel',
    'cp_p', 'cp_p_parallel',
]

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

def cksum_parallel(path_multi: Collection[Path], *, digest: Literal['sha256', 'sha512'], n_jobs: int, desc: str):
    """Runs :func:`cksum` in parallel and attempts to retry failed invocations."""
    mapper = map_with_retry(OSError, count=5, delay_secs=1.0) \
        (functools.partial(map_mt_with_tqdm, n_jobs=n_jobs, desc=desc))

    try:
        return mapper(path_multi, functools.partial(cksum, digest=digest))
    except JobsFailed as exc:
        exc: JobsFailed[Path]

        msg = f"Failed to calculate checksum: {[job.arg for job in exc.failed_jobs]}"
        raise RuntimeError(msg) from exc


def mkdir_p(path: Path) -> None:
    """
    As the Unix command `mkdir -p`, which automatically creates any parent directories
    along the way if necessary and allows existing directories.
    """
    return path.mkdir(parents=True, exist_ok=True)

def mkdir_p_parallel(path_multi: Collection[Path], *, n_jobs: int, desc: str):
    """Runs :func:`mkdir_p` in parallel and attempts to retry failed invocations."""
    mapper = map_with_retry(OSError, count=5, delay_secs=1.0) \
        (functools.partial(map_mt_with_tqdm, n_jobs=n_jobs, desc=desc))

    try:
        return mapper(path_multi, mkdir_p)
    except JobsFailed as exc:
        exc: JobsFailed[Path]

        msg = f"Failed to create directories: {[job.arg for job in exc.failed_jobs]}"
        raise RuntimeError(msg) from exc


def cp_p(src_dst: tuple[Path, Path]):
    """
    As the Unix command `cp -p`, which copies a file while preserving file metadata
    as best as possible.
    """
    src, dst = src_dst
    return shutil.copy2(src, dst)

def cp_p_parallel(src_dst_multi: Collection[tuple[Path, Path]], *, n_jobs: int, desc: str):
    """Runs :func:`cp_p` in parallel and attempts to retry failed invocations."""
    mapper = map_with_retry(OSError, count=5, delay_secs=1.0) \
        (functools.partial(map_mt_with_tqdm, n_jobs=n_jobs, desc=desc))

    try:
        return mapper(src_dst_multi, cp_p)
    except JobsFailed as exc:
        exc: JobsFailed[tuple[Path, Path]]

        src_dst_multi_str = [f"{job.arg[0]} -> {job.arg[1]}" for job in exc.failed_jobs]
        msg = f"Failed to copy files: {src_dst_multi_str}"
        raise RuntimeError(msg) from exc
