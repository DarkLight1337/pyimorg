from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

import exifread
from exifread.classes import IfdTag
from PIL import ExifTags, Image, UnidentifiedImageError

from .logger import get_logger

__all__ = ['read_exif_tags', 'EXIF_DATETIME_FORMAT', 'read_captured_timestamp']

logger = get_logger()


def read_exif_tags(img_path: Path) -> Mapping[int, object]:
    """Reads the EXIF tags stored in an image file."""
    try:
        with Image.open(img_path) as img:
            return img.getexif()
    except UnidentifiedImageError:
        try:
            with img_path.open('rb') as f:
                tags = exifread.process_file(f, details=False)  # pyright: ignore[reportArgumentType]

            exif_tags: dict[int, object] = {}
            for tag_info in tags.values():
                if isinstance(tag_info, IfdTag):
                    exif_tags[tag_info.tag] = tag_info.values  # noqa: PD011
                else:
                    logger.info('Skipping unrecognized EXIF tag (%s).', tag_info)

            return exif_tags
        except Exception:
            logger.warning('File (%s) cannot be opened as an image.', img_path, exc_info=True)
            return {}
    except Exception:
        logger.warning('File (%s) cannot be opened as an image.', img_path, exc_info=True)
        return {}


EXIF_DATETIME_FORMAT = r'%Y:%m:%d %H:%M:%S'

def _try_parse_exif_datetime(exif_tags: Mapping[int, object], tag_key: int, *, img_path: Path) -> datetime | None:
    tag_value = exif_tags.get(tag_key)
    if tag_value is None:
        return None

    if not isinstance(tag_value, str):
        logger.info(
            'Image (%s) has invalid datetime format for tag %s. Reason: Not a string (found type: %s).',
            img_path, tag_key, type(tag_value).__name__,
        )
        return None

    try:
        return datetime.strptime(tag_value, EXIF_DATETIME_FORMAT).astimezone()
    except ValueError:
        logger.info(
            'Image (%s) has invalid datetime format for tag %s. Reason: Not in "YYYY:MM:DD HH:MM:SS" form (found value: %s).',
            img_path, tag_key, tag_value,
        )
        return None


def read_captured_timestamp(img_path: Path) -> datetime | None:
    """Reads the timestamp when an image was captured, based on its EXIF tags."""
    exif_tags = read_exif_tags(img_path)

    captured_timestamp: datetime | None = None
    # Check the following flags in the following order of preference
    for tag_key in (ExifTags.Base.DateTimeOriginal, ExifTags.Base.DateTimeDigitized, ExifTags.Base.DateTime):
        captured_timestamp = _try_parse_exif_datetime(exif_tags, tag_key, img_path=img_path)
        if captured_timestamp is not None:
            return captured_timestamp

    logger.info('Image (%s) does not have a timestamp when it was captured. EXIF attributes:\n%s', img_path, exif_tags)
    return None
