"""PHASES 2.11: API preprocessing + deployed model file vs the notebook's expected top-3.

Runs only when a real bundle exists. Point PARITY_BUNDLE at best_models_v3/production (it holds
model.tflite or model.keras, model_meta.json and parity_fixtures/).
"""

import json
import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.core.config import Settings
from app.services.model_registry import load_bundle
from app.services.preprocessing import IMG_SIZE, resize_bilinear_tf

BUNDLE = Path(os.environ.get("PARITY_BUNDLE", Path(__file__).resolve().parents[2] / "ml" / "artifacts"))
FIXTURES = BUNDLE / "parity_fixtures"
SCORE_TOL = 1e-3


@pytest.mark.skipif(not (FIXTURES / "expected.json").exists(), reason="no parity fixtures (train the model first)")
def test_parity_with_notebook():
    meta = json.loads((BUNDLE / "model_meta.json").read_text())
    s = Settings(model_path=BUNDLE / meta["file"], model_meta_path=BUNDLE / "model_meta.json",
                 class_mapping_path=BUNDLE / "class_mapping.json")
    bundle = load_bundle(s)
    for case in json.loads((FIXTURES / "expected.json").read_text()):
        # Fixtures are the notebook's 256x256 cache JPEGs, so start from the step after the cache.
        arr = np.asarray(Image.open(FIXTURES / case["file"]).convert("RGB"), np.uint8)
        x = resize_bilinear_tf(arr, IMG_SIZE, IMG_SIZE)[None]
        p = bundle.predict_fn(x)[0]  # raw softmax, no TTA / temperature, like the notebook
        top = np.argsort(p)[::-1][:3]
        assert int(top[0]) == case["top3"][0], case["file"]
        assert np.allclose([p[i] for i in case["top3"]], case["scores"], atol=SCORE_TOL), case["file"]
