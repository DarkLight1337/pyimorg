from __future__ import annotations

from pathlib import Path
from typing import Literal

import click

from ..pyimorg import Group, groupby as _groupby

__all__ = ['Group', 'groupby']

@click.argument('src', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('dst', type=click.Path(exists=False))
@click.option('--group', '-g', type=click.Choice(['year', 'month', 'day']), default='month',
              help='Represent each group as one year, one month or one day. (Default: month)')
@click.option('--threads', '-t', type=click.IntRange(min=1), default=1,
              help='Number of threads to use in parallel for I/O operations. (Default: 1)')
def groupby(
    src: str | Path,
    dst: str | Path,
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
    return _groupby(src, dst, group=group, threads=threads)
