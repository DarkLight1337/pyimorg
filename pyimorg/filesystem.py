from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
import shutil
from typing import Literal

from .logger import get_logger

__all__ = ['is_image', 'mkdir_p', 'cp_p']

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

def cp_p(src_dst: tuple[Path, Path]):
    """
    As the Unix command `cp -p`, which copies a file while preserving file metadata
    as best as possible.
    """
    src, dst = src_dst
    return shutil.copy2(src, dst)
