from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import click

from ..filesystem import cksum, cp_p_parallel, is_image, mkdir_p_parallel
from ..func import map_mt_with_tqdm
from ..logger import set_logger_level

__all__ = ['diff']

@click.argument('src1', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('src2', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('dst', type=click.Path(exists=False))
@click.option('--hasher', '-h', type=click.Choice(['sha256', 'sha512']), default='sha256',
              help='The algorithm used to hash each file. (Default: sha256)')
@click.option('--threads', '-t', type=click.IntRange(min=1), default=1,
              help='Number of threads to use in parallel for I/O operations. (Default: 1)')
def diff(
    src1: str,
    src2: str,
    dst: str,
    *,
    hasher: Literal['sha256', 'sha512'],
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
    if Path(dst).exists():
        msg = f'The destination directory ({dst}) already exists.'
        raise ValueError(msg)

    set_logger_level(logging.INFO)

    src1_img_paths = [path for path in Path(src1).rglob('*') if is_image(path)]
    src1_img_hashes = map_mt_with_tqdm(
        src1_img_paths,
        lambda path: cksum(path, digest=hasher),
        n_jobs=threads,
        desc='Hashing images from src1',
    )
    src1_img_hash_to_path = {
        img_hash: img_path
        for img_path, img_hash in zip(src1_img_paths, src1_img_hashes)
    }

    src2_img_paths = [path for path in Path(src2).rglob('*') if is_image(path)]
    src2_img_hashes = map_mt_with_tqdm(
        src2_img_paths,
        lambda path: cksum(path, digest=hasher),
        n_jobs=threads,
        desc='Hashing images from src2',
    )
    src2_img_hash_to_path = {
        img_hash: img_path
        for img_path, img_hash in zip(src2_img_paths, src2_img_hashes)
    }

    hashes_in_src1 = set(src1_img_hashes)
    hashes_in_src2 = set(src2_img_hashes)
    hashes_in_both = hashes_in_src1 & hashes_in_src2
    hashes_in_src1_only = hashes_in_src1 - hashes_in_src2
    hashes_in_src2_only = hashes_in_src2 - hashes_in_src1

    in_both_src_path_to_dst_path = {
        src1_img_hash_to_path[img_hash]: Path(dst) / 'both' / src1_img_hash_to_path[img_hash].relative_to(src1)
        for img_hash in hashes_in_both
    }

    mkdir_p_parallel(
        {path.parent for path in in_both_src_path_to_dst_path.values()},
        n_jobs=threads,
        desc='Creating output directories for images that exist in both',
    )

    cp_p_parallel(
        in_both_src_path_to_dst_path.items(),
        n_jobs=threads,
        desc='Writing output images that exist in both',
    )

    in_src1_only_src_path_to_dst_path = {
        src1_img_hash_to_path[img_hash]: Path(dst) / 'src1_only' / src1_img_hash_to_path[img_hash].relative_to(src1)
        for img_hash in hashes_in_src1_only
    }

    mkdir_p_parallel(
        {path.parent for path in in_src1_only_src_path_to_dst_path.values()},
        n_jobs=threads,
        desc='Creating output directories for images that exist in src1 only',
    )

    cp_p_parallel(
        in_src1_only_src_path_to_dst_path.items(),
        n_jobs=threads,
        desc='Writing output images that exist in src1 only',
    )

    in_src2_only_src_path_to_dst_path = {
        src2_img_hash_to_path[img_hash]: Path(dst) / 'src2_only' / src2_img_hash_to_path[img_hash].relative_to(src2)
        for img_hash in hashes_in_src2_only
    }

    mkdir_p_parallel(
        {path.parent for path in in_src2_only_src_path_to_dst_path.values()},
        n_jobs=threads,
        desc='Creating output directories for images that exist in src2 only',
    )

    cp_p_parallel(
        in_src2_only_src_path_to_dst_path.items(),
        n_jobs=threads,
        desc='Writing output images that exist in src2 only',
    )
