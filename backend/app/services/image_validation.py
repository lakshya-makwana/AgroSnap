"""Decode and validate an uploaded photo. Every failure is a structured 4xx, never a 500."""

import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import ApiError

try:  # HEIC/HEIF photos from some phones
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover
    pass

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF", "HEIC", "MPO"}
Image.MAX_IMAGE_PIXELS = 60_000_000  # rejects decompression bombs


@dataclass
class DecodedImage:
    image: Image.Image  # RGB, upright
    quality_issue: str | None  # "too_small" | "too_dark" | None


UNSUPPORTED = "This file type isn't supported. Please choose a JPEG or PNG photo."
UNREADABLE = "This photo could not be read. Please choose another photo."


def decode_upload(data: bytes, max_mb: float, min_side: int, dark_luma: float) -> DecodedImage:
    if not data:
        raise ApiError(422, "IMAGE_UNREADABLE", "The photo is empty. Please choose another photo.")
    if len(data) > max_mb * 1024 * 1024:
        raise ApiError(413, "IMAGE_TOO_LARGE",
                       f"The image is larger than {max_mb:g} MB. Please choose a smaller photo.")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = (probe.format or "").upper()
            probe.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError) as e:
        raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", UNSUPPORTED) from e
    except Exception as e:
        raise ApiError(422, "IMAGE_UNREADABLE", UNREADABLE) from e
    if fmt not in ALLOWED_FORMATS:
        raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", UNSUPPORTED)
    try:
        with Image.open(io.BytesIO(data)) as im:
            img = ImageOps.exif_transpose(im).convert("RGB")  # same steps as training (notebook §3)
            img.load()
    except Exception as e:
        raise ApiError(422, "IMAGE_UNREADABLE", UNREADABLE) from e

    issue = None
    if min(img.size) < min_side:
        issue = "too_small"
    else:
        luma = np.asarray(img.convert("L").resize((64, 64)), dtype=np.float32).mean()
        if luma < dark_luma:
            issue = "too_dark"
    return DecodedImage(img, issue)
