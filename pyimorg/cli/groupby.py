from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import logging
from pathlib import Path
from typing import Literal

import click
from tqdm import tqdm

from ..exif import read_captured_timestamp
from ..filesystem import cp_p_parallel, is_image, mkdir_p_parallel
from ..func import map_mt_with_tqdm
from ..logger import set_logger_level

__all__ = ['groupby']

def _get_dst_dir_name(timestamp: datetime, *, groupby: Literal['year', 'month', 'day']) -> str:
    if groupby == 'year':
        return timestamp.strftime(r'%Y')
    elif groupby == 'month':
        return timestamp.strftime(r'%Y%m')
    elif groupby == 'day':
        return timestamp.strftime(r'%Y%m%d')

@click.argument('src', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('dst', type=click.Path(exists=False))
@click.option('--group', '-g', type=click.Choice(['year', 'month', 'day']), default='month',
              help='Represent each group as one year, one month or one day. (Default: month)')
@click.option('--threads', '-t', type=click.IntRange(min=1), default=1,
              help='Number of threads to use in parallel for I/O operations. (Default: 1)')
def groupby(
    src: str,
    dst: str,
    *,
    group: Literal['year', 'month', 'day'],
    threads: int,
):
    """
    Given a set of images contained in SRC,
    group them based on the timestamp when they were captured.

    The images are outputted under DST, with one directory per group.
    The directory name is based on the option given to `--groupby`:

    - `year`: `YYYY` format, where `YYYY` is the year.

    - `month`: `YYYYMM` format, where `YYYY` is the year and `MM` is the month.

    - `day`: `YYYYMMDD` format, where `YYYY` is the year, `MM` is the month,
    and `DD` is the day of the month.
    """
    if Path(dst).exists():
        msg = f'The destination directory ({dst}) already exists.'
        raise ValueError(msg)

    set_logger_level(logging.INFO)

    src_img_paths = [path for path in Path(src).rglob('*') if is_image(path)]
    src_img_captured_timestamps = map_mt_with_tqdm(
        src_img_paths,
        read_captured_timestamp,
        n_jobs=threads,
        desc='Reading metadata of images',
    )

    dst_dir_name_to_src_img_paths: defaultdict[str, list[Path]] = defaultdict(list)
    for src_img_path, captured_timestamp in tqdm(
        zip(src_img_paths, src_img_captured_timestamps),
        desc=f'Grouping images by {group}',
        total=len(src_img_paths),
    ):
        if captured_timestamp is None:
            dst_dir_name = 'UNKNOWN'
        else:
            dst_dir_name = _get_dst_dir_name(captured_timestamp, groupby=group)

        dst_dir_name_to_src_img_paths[dst_dir_name].append(src_img_path)

    src_img_path_to_dst_img_path = {
        src_img_path: Path(dst) / dst_dir_name / src_img_path.name
        for dst_dir_name, src_img_paths in dst_dir_name_to_src_img_paths.items()
        for src_img_path in src_img_paths
    }

    mkdir_p_parallel(
        {path.parent for path in src_img_path_to_dst_img_path.values()},
        n_jobs=threads,
        desc='Creating output directories',
    )

    cp_p_parallel(
        src_img_path_to_dst_img_path.items(),
        n_jobs=threads,
        desc='Writing output images',
    )
