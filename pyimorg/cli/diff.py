from __future__ import annotations

from pathlib import Path

import click

from ..pyimorg.diff import Hasher, diff as _diff

__all__ = ['diff']

@click.argument('src1', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('src2', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('dst', type=click.Path(exists=False))
@click.option('--hasher', '-h', type=click.Choice(['sha256', 'sha512']), default='sha256',
              help='The algorithm used to hash each file. (Default: sha256)')
@click.option('--threads', '-t', type=click.IntRange(min=1), default=1,
              help='Number of threads to use in parallel for I/O operations. (Default: 1)')
def diff(
    src1: str | Path,
    src2: str | Path,
    dst: str | Path,
    *,
    hasher: Hasher,
    threads: int,
):
    """
    Given two sets of images contained in SRC1 and SRC2,
    find the images that exist in both sets, and those that do not.

    Images are matched according to their content and have no relation to their filename.

    The images are outputted under DST, with one directory for each of the following:

    - `both`: Contains the images that exist in both sets.
    The path of each output image is based on that in SRC1.

    - `src1_only`: Contains the images that only exist in SRC1 but not in SRC2.
    The path of each output image is based on that in SRC1.

    - `src2_only`: Contains the images that only exist in SRC2 but not in SRC1.
    The path of each output image is based on that in SRC2.
    """
    return _diff(src1, src2, dst, hasher=hasher, threads=threads)
