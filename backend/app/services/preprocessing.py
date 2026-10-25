"""Inference preprocessing. Must reproduce the v3 training pipeline exactly (MODEL_CARD §4).

Training (notebook §3 + §6) did, per image:
  1. PIL open -> ImageOps.exif_transpose -> convert("RGB")
  2. resize to 256x256 with LANCZOS (aspect ratio is NOT kept)
  3. save as JPEG quality 95 (the local cache), later decoded again by tf.io.decode_jpeg
  4. tf.image.resize to 224x224, bilinear (half-pixel centres, no antialias), float32
  5. no scaling: values stay 0-255; the model does its own normalisation

Step 4 is re-implemented in NumPy so the API does not need TensorFlow to preprocess.
`tests/test_preprocessing.py` checks it against TensorFlow when TF is installed.
"""

import io

import numpy as np
from PIL import Image

STORE_SIZE = 256
IMG_SIZE = 224
CACHE_JPEG_QUALITY = 95


def _axis_weights(in_size: int, out_size: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # Same arithmetic as TensorFlow's compute_interpolation_weights with half_pixel_centers=True.
    scale = np.float32(in_size / out_size)
    pos = (np.arange(out_size, dtype=np.float32) + np.float32(0.5)) * scale - np.float32(0.5)
    floor = np.floor(pos)
    lower = np.maximum(floor, 0).astype(np.int64)
    upper = np.minimum(np.ceil(pos), in_size - 1).astype(np.int64)
    lerp = (pos - floor).astype(np.float32)
    return lower, upper, lerp


def resize_bilinear_tf(img: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    """Equivalent of tf.image.resize(img, [out_h, out_w], method="bilinear") for an HxWxC array."""
    x = img.astype(np.float32)
    in_h, in_w = x.shape[:2]
    y0, y1, ly = _axis_weights(in_h, out_h)
    x0, x1, lx = _axis_weights(in_w, out_w)
    lx = lx[None, :, None]
    top_l, top_r = x[y0][:, x0], x[y0][:, x1]
    bot_l, bot_r = x[y1][:, x0], x[y1][:, x1]
    top = top_l + (top_r - top_l) * lx
    bottom = bot_l + (bot_r - bot_l) * lx
    return (top + (bottom - top) * ly[:, None, None]).astype(np.float32)


def to_store_image(img: Image.Image) -> Image.Image:
    """Steps 2-3: the 256x256 JPEG the model saw during training."""
    small = img.convert("RGB").resize((STORE_SIZE, STORE_SIZE), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    small.save(buf, "JPEG", quality=CACHE_JPEG_QUALITY)
    buf.seek(0)
    with Image.open(buf) as decoded:
        return decoded.convert("RGB")


def preprocess(img: Image.Image) -> np.ndarray:
    """RGB PIL image -> float32 array (1, 224, 224, 3) in 0-255, ready for model(x)."""
    arr = np.asarray(to_store_image(img), dtype=np.uint8)
    return resize_bilinear_tf(arr, IMG_SIZE, IMG_SIZE)[None, ...]
