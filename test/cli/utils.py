from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from string import digits
from tempfile import TemporaryDirectory
from typing import AbstractSet, Iterable, Optional, Sequence, TypedDict, Union

from hypothesis import note, strategies as st
from jsoncomparison import NO_DIFF, Compare as CompareJSON
from PIL import ExifTags, Image

from pyimorg.cli import Group, Hasher
from pyimorg.exif import EXIF_DATETIME_FORMAT
from pyimorg.filesystem import mkdir_p

__all__ = [
    'temp_dir_path', 'iter_files',
    'ImageDirectory', 'ImageFile', 'iter_images',
    'st_hasher', 'st_group', 'st_test_images',
    'create_test_images',
    'DirectoryJSON', 'FileJSON', 'get_filetree_json',
    'assert_dirs_subtree_equal',
    'assert_files_images_equivalent', 'assert_file_counts_equal',
]


@contextmanager
def temp_dir_path():
    with TemporaryDirectory() as tempdir:
        yield Path(tempdir)


def iter_files(dir_path: Path, *, recursive: bool = True) -> Iterable[Path]:
    return dir_path.rglob('*') if recursive else dir_path.glob('*')


class ImageDirectory(TypedDict):
    name: str
    children: 'Sequence[Union[ImageDirectory, ImageFile]]'

class ImageFile(TypedDict):
    name: str
    value: int    # From 0 to 255 inclusive
    timestamp: Optional[datetime]   # Converted into EXIF attribute

def iter_images(images: ImageDirectory, *, recursive: bool = True) -> Iterable[ImageFile]:
    for image in images['children']:
        if 'children' in image:
            if recursive:
                yield from iter_images(image)
        else:
            yield image


def st_hasher() -> st.SearchStrategy[Hasher]:
    return st.sampled_from(['sha256', 'sha512'])

def st_group() -> st.SearchStrategy[Group]:
    return st.sampled_from(['year', 'month', 'day'])


def _st_test_dir(children: st.SearchStrategy[Sequence[Union[ImageDirectory, ImageFile]]]) -> st.SearchStrategy[ImageDirectory]:
    return st.fixed_dictionaries({
        'name': st.text(digits, min_size=4, max_size=4),
        'children': children,
    })  # pyright: ignore[reportReturnType]

def _st_test_file(
    *,
    min_value: int,
    max_value: int,
    min_timestamp: datetime,
    max_timestamp: datetime,
) -> st.SearchStrategy[ImageFile]:
    if not 0 <= min_value <= 255:
        msg = '`max_value` must be between 0 and 255 (inclusive)'
        raise ValueError(msg)
    if not 0 <= max_value <= 255:
        msg = '`max_value` must be between 0 and 255 (inclusive)'
        raise ValueError(msg)

    # EXIF data does not store microseconds
    st_timestamp = st.datetimes(min_value=min_timestamp, max_value=max_timestamp) \
        .filter(lambda x: x.microsecond == 0)

    return st.fixed_dictionaries({
        'name': st.text(digits, min_size=4, max_size=4).map(lambda x: 'img_' + x + '.png'),
        'value': st.integers(min_value=min_value, max_value=max_value),
        'timestamp': st_timestamp | st.none(),
    })  # pyright: ignore[reportReturnType]

def st_test_images(
    *,
    # Restrict the range to increase the change of duplicates and grouping
    min_value: int = 0,
    max_value: int = 4,
    min_timestamp: Optional[datetime] = None,
    max_timestamp: Optional[datetime] = None,
) -> st.SearchStrategy[ImageDirectory]:
    # Hypothesis expects min/max to be timezone-naive
    if min_timestamp is None:
        min_timestamp = datetime(2000, 1, 1)  # noqa: DTZ001
    if max_timestamp is None:
        max_timestamp = datetime(2100, 12, 31)  # noqa: DTZ001

    st_children = st.lists(_st_test_file(
        min_value=min_value,
        max_value=max_value,
        min_timestamp=min_timestamp,
        max_timestamp=max_timestamp,
    ), max_size=4)

    return st.recursive(st_children, lambda children: _st_test_dir(children).map(lambda x: [x])) \
        .map(lambda x: ImageDirectory(name='ROOT_DIR', children=x)) \
        .filter(lambda x: len(names := [f['name'] for f in iter_images(x)]) == len(set(names)))


def _create_test_images(dir_path: Path, images: Sequence[Union[ImageDirectory, ImageFile]]) -> None:
    mkdir_p(dir_path)

    for image in images:
        if 'children' in image:
            _create_test_images(dir_path / image['name'], image['children'])
        else:
            value, timestamp = image['value'], image['timestamp']

            imobj = Image.new('RGB', (16, 16), value)

            exif = imobj.getexif()
            if timestamp is not None:
                exif[ExifTags.Base.DateTimeDigitized] = timestamp.strftime(EXIF_DATETIME_FORMAT)

            imobj.save(dir_path / image['name'], exif=exif)

def create_test_images(base_path: Path, images: ImageDirectory) -> None:
    _create_test_images(base_path / images['name'], images['children'])


class DirectoryJSON(TypedDict):
    name: str
    children: 'Sequence[Union[DirectoryJSON, FileJSON]]'

class FileJSON(TypedDict):
    name: str

def get_filetree_json(dir_path: Path, *, ignore_files: Optional[AbstractSet[str]] = None) -> DirectoryJSON:
    children: Sequence[Union[DirectoryJSON, FileJSON]] = []

    for child_path in dir_path.iterdir():
        if child_path.is_dir():
            children.append(get_filetree_json(child_path, ignore_files=ignore_files))
        else:
            if ignore_files is None or child_path.name not in ignore_files:
                children.append({'name': child_path.name})

    return {'name': dir_path.name, 'children': children}

def assert_dirs_subtree_equal(dir1: Path, dir2: Path, *, ignore_files: Optional[AbstractSet[str]] = None):
    assert dir1.is_dir() == dir2.is_dir()

    if dir1.is_dir() and dir2.is_dir():
        tree1 = get_filetree_json(dir1, ignore_files=ignore_files)['children']
        note(f'tree1={tree1}')

        tree2 = get_filetree_json(dir2, ignore_files=ignore_files)['children']
        note(f'tree2={tree2}')

        diffs = CompareJSON().check(tree1, tree2)
        note(f'diffs={diffs}')
        assert diffs == NO_DIFF

    return True


def _count_files(files: Iterable[Path]) -> int:
    return sum(1 for f in files if f.is_file())

def _count_unique_images(images: Iterable[ImageFile]) -> int:
    return len({(f['value'], f['timestamp']) for f in images})

def assert_file_count(files: Path, value: int, *, recursive: bool = True):
    file_count = _count_files(iter_files(files, recursive=recursive))
    note(f'file_count={file_count}')

    note(f'value={value}')

    try:
        assert file_count == value
    except AssertionError:
        file_tree = get_filetree_json(files)['children']
        note(f'file_tree={file_tree}')

        raise

    return True

def assert_files_images_equivalent(files: Path, images: ImageDirectory):
    file_count = _count_files(iter_files(files))
    note(f'file_count={file_count}')

    image_count = _count_unique_images(iter_images(images))
    note(f'image_count={image_count}')

    try:
        assert file_count == image_count
    except AssertionError:
        file_tree = get_filetree_json(files)['children']
        note(f'file_tree={file_tree}')

        raise

    return True

def assert_file_counts_equal(files1: Path, files2: Path, *, recursive: bool = True):
    file_count1 = _count_files(iter_files(files1, recursive=recursive))
    note(f'file_count1={file_count1}')

    file_count2 = _count_files(iter_files(files2, recursive=recursive))
    note(f'file_count2={file_count2}')

    try:
        assert file_count1 == file_count2
    except AssertionError:
        file_tree1 = get_filetree_json(files1)['children']
        note(f'file_tree1={file_tree1}')

        file_tree2 = get_filetree_json(files2)['children']
        note(f'file_tree2={file_tree2}')

        raise

    return True
