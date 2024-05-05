from __future__ import annotations

import logging

from hypothesis import given, note, strategies as st

from pyimorg import Group, groupby

from .utils import (
    ImageDirectory,
    assert_dirs_subtree_equal,
    assert_file_count,
    create_test_images,
    iter_images,
    st_group,
    st_test_images,
    temp_dir_path,
)


@given(st_group())
def test_empty(group: Group):
    with temp_dir_path() as tempdir:
        src = tempdir / 'src'
        dst = tempdir / 'dst'

        groupby(src, dst, group=group, threads=1, logger_level=logging.WARNING, disable_progbar=True)

        assert_file_count(dst, 0)

@given(st_test_images(), st_group())
def test_general(images: ImageDirectory, group: Group):
    with temp_dir_path() as tempdir:
        src = tempdir / 'src'
        dst = tempdir / 'dst'

        create_test_images(src, images)
        groupby(src, dst, group=group, threads=1, logger_level=logging.WARNING, disable_progbar=True)

        assert_file_count(dst, sum(1 for _ in iter_images(images)))

@given(st_test_images())
def test_groupby_year(images: ImageDirectory):
    unique_years = {None if (t := f['timestamp']) is None else t.year for f in iter_images(images)}
    note(f'unique_years={unique_years}')

    with temp_dir_path() as tempdir:
        src = tempdir / 'src'
        dst = tempdir / 'dst'

        create_test_images(src, images)
        groupby(src, dst, group='year', threads=1, logger_level=logging.WARNING, disable_progbar=True)

        assert len([path for path in dst.glob('*') if path.is_dir()]) == len(unique_years)

@given(st_test_images())
def test_groupby_month(images: ImageDirectory):
    unique_months = {None if (t := f['timestamp']) is None else t.month for f in iter_images(images)}
    note(f'unique_months={unique_months}')

    with temp_dir_path() as tempdir:
        src = tempdir / 'src'
        dst = tempdir / 'dst'

        create_test_images(src, images)
        groupby(src, dst, group='month', threads=1, logger_level=logging.WARNING, disable_progbar=True)

        assert len([path for path in dst.glob('*') if path.is_dir()]) == len(unique_months)

@given(st_test_images())
def test_groupby_day(images: ImageDirectory):
    unique_days = {None if (t := f['timestamp']) is None else t.day for f in iter_images(images)}
    note(f'unique_days={unique_days}')

    with temp_dir_path() as tempdir:
        src = tempdir / 'src'
        dst = tempdir / 'dst'

        create_test_images(src, images)
        groupby(src, dst, group='day', threads=1, logger_level=logging.WARNING, disable_progbar=True)

        assert len([path for path in dst.glob('*') if path.is_dir()]) == len(unique_days)

@given(st_test_images(), st_group(), st.integers(min_value=2, max_value=8))
def test_parallel(images: ImageDirectory, group: Group, num_threads: int):
    with temp_dir_path() as tempdir:
        src = tempdir / 'src'
        dst1 = tempdir / 'dst1'
        dst2 = tempdir / 'dst2'

        create_test_images(src, images)
        groupby(src, dst1, group=group, threads=1, logger_level=logging.WARNING, disable_progbar=True)
        groupby(src, dst2, group=group, threads=num_threads, logger_level=logging.WARNING, disable_progbar=True)

        assert_dirs_subtree_equal(dst1, dst2)
