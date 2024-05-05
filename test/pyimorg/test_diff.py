from __future__ import annotations

import logging

from hypothesis import given, note, strategies as st

from pyimorg import Hasher, diff

from .utils import (
    ImageDirectory,
    assert_dirs_subtree_equal,
    assert_file_count,
    assert_file_counts_equal,
    assert_files_images_equivalent,
    create_test_images,
    iter_images,
    st_hasher,
    st_test_images,
    temp_dir_path,
)


@given(st_test_images(), st_hasher())
def test_one_empty(images: ImageDirectory, hasher: Hasher):
    with temp_dir_path() as tempdir:
        src1 = tempdir / 'src1'
        src2 = tempdir / 'src2'
        dst = tempdir / 'dst'

        create_test_images(src1, images)
        diff(src1, src2, dst, hasher=hasher, threads=1, logger_level=logging.WARNING, disable_progbar=True)

        assert_file_count(dst / 'both', 0)
        assert_files_images_equivalent(dst / 'src1_only', images)
        assert_file_count(dst / 'src2_only', 0)

@given(st_hasher())
def test_both_empty(hasher: Hasher):
    with temp_dir_path() as tempdir:
        src1 = tempdir / 'src1'
        src2 = tempdir / 'src2'
        dst = tempdir / 'dst'

        diff(src1, src2, dst, hasher=hasher, threads=1, logger_level=logging.WARNING, disable_progbar=True)

        assert_file_count(dst, 0)

@given(st_test_images(), st_hasher())
def test_equal(images: ImageDirectory, hasher: Hasher):
    with temp_dir_path() as tempdir:
        src1 = tempdir / 'src1'
        src2 = tempdir / 'src2'
        dst = tempdir / 'dst'

        create_test_images(src1, images)
        create_test_images(src2, images)
        diff(src1, src2, dst, hasher=hasher, threads=1, logger_level=logging.WARNING, disable_progbar=True)

        assert_files_images_equivalent(dst / 'both', images)
        assert_file_count(dst / 'src1_only', 0)
        assert_file_count(dst / 'src2_only', 0)

@given(st_test_images(min_value=0, max_value=4), st_test_images(min_value=5, max_value=8), st_hasher())
def test_disjoint(images1: ImageDirectory, images2: ImageDirectory, hasher: Hasher):
    with temp_dir_path() as tempdir:
        src1 = tempdir / 'src1'
        src2 = tempdir / 'src2'
        dst = tempdir / 'dst'

        create_test_images(src1, images1)
        create_test_images(src2, images2)
        diff(src1, src2, dst, hasher=hasher, threads=1, logger_level=logging.WARNING, disable_progbar=True)

        assert_file_count(dst / 'both', 0)
        assert_files_images_equivalent(dst / 'src1_only', images1)
        assert_files_images_equivalent(dst / 'src2_only', images2)

@given(st_test_images(), st_test_images(), st_hasher())
def test_general(images1: ImageDirectory, images2: ImageDirectory, hasher: Hasher):
    unique_contents_1 = {(f['value'], f['timestamp']) for f in iter_images(images1)}
    note(f'unique_contents_1={unique_contents_1}')

    unique_contents_2 = {(f['value'], f['timestamp']) for f in iter_images(images2)}
    note(f'unique_contents_2={unique_contents_2}')

    unique_contents_12 = unique_contents_1 & unique_contents_2
    unique_contents_1m2 = unique_contents_1 - unique_contents_2
    unique_contents_2m1 = unique_contents_2 - unique_contents_1

    with temp_dir_path() as tempdir:
        src1 = tempdir / 'src1'
        src2 = tempdir / 'src2'
        dst = tempdir / 'dst'

        create_test_images(src1, images1)
        create_test_images(src2, images2)
        diff(src1, src2, dst, hasher=hasher, threads=1, logger_level=logging.WARNING, disable_progbar=True)

        assert_file_count(dst / 'both', len(unique_contents_12))
        assert_file_count(dst / 'src1_only', len(unique_contents_1m2))
        assert_file_count(dst / 'src2_only', len(unique_contents_2m1))

@given(st_test_images(), st_test_images(), st_hasher(), st.integers(min_value=2, max_value=8))
def test_parallel(images1: ImageDirectory, images2: ImageDirectory, hasher: Hasher, num_threads: int):
    with temp_dir_path() as tempdir:
        src1 = tempdir / 'src1'
        src2 = tempdir / 'src2'
        dst1 = tempdir / 'dst1'
        dst2 = tempdir / 'dst2'

        create_test_images(src1, images1)
        create_test_images(src2, images2)
        diff(src1, src2, dst1, hasher=hasher, threads=1, logger_level=logging.WARNING, disable_progbar=True)
        diff(src1, src2, dst2, hasher=hasher, threads=num_threads, logger_level=logging.WARNING, disable_progbar=True)

        assert_dirs_subtree_equal(dst1, dst2)

@given(st_test_images(), st_test_images(), st_hasher())
def test_mirrored(images1: ImageDirectory, images2: ImageDirectory, hasher: Hasher):
    with temp_dir_path() as tempdir:
        src1 = tempdir / 'src1'
        src2 = tempdir / 'src2'
        dst12 = tempdir / 'dst12'
        dst21 = tempdir / 'dst21'

        create_test_images(src1, images1)
        create_test_images(src2, images2)
        diff(src1, src2, dst12, hasher=hasher, threads=1, logger_level=logging.WARNING, disable_progbar=True)
        diff(src2, src1, dst21, hasher=hasher, threads=1, logger_level=logging.WARNING, disable_progbar=True)

        assert_file_counts_equal(dst12 / 'both', dst21 / 'both')
        assert_dirs_subtree_equal(dst12 / 'src1_only', dst21 / 'src2_only')
        assert_dirs_subtree_equal(dst12 / 'src2_only', dst21 / 'src1_only')
