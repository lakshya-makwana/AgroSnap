import io
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import Settings
from app.main import create_app

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        model_path=tmp_path / "missing.keras",
        model_meta_path=tmp_path / "missing_meta.json",
        class_mapping_path=BACKEND / "demo" / "class_mapping.json",
        translations_dir=BACKEND.parent / "ml" / "artifacts" / "translations",
        demo_model=True,
        feedback_dir=tmp_path / "feedback",
    )


@pytest.fixture
def client(settings: Settings):
    with TestClient(create_app(settings)) as c:
        yield c


def jpeg_bytes(size=(400, 300), color=(60, 140, 50), noise=True, fmt="JPEG") -> bytes:
    rng = np.random.default_rng(1)
    arr = np.zeros((size[1], size[0], 3), np.uint8) + np.array(color, np.uint8)
    if noise:
        arr = np.clip(arr.astype(int) + rng.integers(-40, 40, arr.shape), 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, fmt)
    return buf.getvalue()
