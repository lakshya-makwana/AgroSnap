import numpy as np
import pytest
from PIL import Image

from app.services.preprocessing import preprocess, resize_bilinear_tf


def test_output_contract():
    img = Image.fromarray(np.random.default_rng(0).integers(0, 256, (300, 500, 3), dtype=np.uint8))
    x = preprocess(img)
    assert x.shape == (1, 224, 224, 3)
    assert x.dtype == np.float32
    assert 0.0 <= x.min() and x.max() <= 255.0  # no scaling outside the model


def test_constant_image_stays_constant():
    arr = np.full((256, 256, 3), 77, np.uint8)
    out = resize_bilinear_tf(arr, 224, 224)
    assert np.allclose(out, 77.0)


def test_same_size_is_identity():
    arr = np.random.default_rng(3).integers(0, 256, (224, 224, 3)).astype(np.uint8)
    assert np.array_equal(resize_bilinear_tf(arr, 224, 224), arr.astype(np.float32))


@pytest.mark.parametrize("shape", [(256, 256), (300, 200), (17, 31)])
def test_matches_tensorflow_bilinear(shape):
    tf = pytest.importorskip("tensorflow")
    arr = np.random.default_rng(7).integers(0, 256, (*shape, 3)).astype(np.uint8)
    ref = tf.image.resize(tf.cast(arr, tf.float32), [224, 224], method="bilinear").numpy()
    got = resize_bilinear_tf(arr, 224, 224)
    assert np.max(np.abs(ref - got)) < 1e-3
