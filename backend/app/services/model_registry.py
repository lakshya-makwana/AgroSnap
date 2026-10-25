"""Loads the model bundle once at startup: model + class mapping + model_meta.json."""

import hashlib
import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

from app.core.config import Settings
from app.services.class_mapping import ClassMapping, load_class_mapping

log = logging.getLogger("agrosnap.model")

DEMO_VERSION = "demo-stub-NOT-A-REAL-MODEL"


class Predictor(Protocol):
    def __call__(self, x: np.ndarray) -> np.ndarray: ...  # (N,224,224,3) 0-255 -> (N,C) softmax


@dataclass
class Thresholds:
    t_conf: float = 0.90
    m_min: float = 0.10
    # Crop-conditioned thresholds (notebook §12b). None = not calibrated yet.
    t_conf_crop: float | None = None
    m_min_crop: float | None = None


@dataclass
class ModelBundle:
    predict_fn: Predictor
    mapping: ClassMapping
    version: str
    architecture: str
    temperature: float = 1.0
    tta_hflip: bool = True
    thresholds: Thresholds = field(default_factory=Thresholds)
    metrics: dict = field(default_factory=dict)
    compression: dict | None = None
    is_demo: bool = False

    def probabilities(self, x: np.ndarray) -> np.ndarray:
        """Raw softmax, averaged with the horizontal flip when the bundle was calibrated with TTA."""
        p = np.asarray(self.predict_fn(x), dtype=np.float64)
        if self.tta_hflip:
            p = (p + np.asarray(self.predict_fn(x[:, :, ::-1, :]), dtype=np.float64)) / 2.0
        return p


class DemoPredictor:
    """Deterministic fake classifier driven by image colours. Only for building the app before training."""

    def __init__(self, num_classes: int):
        rng = np.random.default_rng(0)
        self.w = rng.normal(0, 1, (num_classes, 3 * 8 * 8)).astype(np.float32)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        n = x.shape[0]
        small = x.reshape(n, 8, 28, 8, 28, 3).mean(axis=(2, 4)).reshape(n, -1) / 255.0
        small = (small - small.mean(1, keepdims=True)) / (small.std(1, keepdims=True) + 1e-6)
        z = small @ self.w.T * 0.6
        z -= z.max(1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(1, keepdims=True)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_keras(path: Path) -> Predictor:
    import keras  # imported lazily: TensorFlow is only needed for a real model

    model = keras.models.load_model(path, compile=False)

    def predict(x: np.ndarray) -> np.ndarray:
        return model(x.astype(np.float32), training=False).numpy()

    return predict


class TFLitePredictor:
    """[A6] Serves the compressed .tflite model. Same contract as the notebook's TFLitePredictor."""

    def __init__(self, path: Path, threads: int = 2):
        try:
            from ai_edge_litert.interpreter import Interpreter  # small runtime, no full TensorFlow needed
        except ImportError:
            import tensorflow as tf

            Interpreter = tf.lite.Interpreter  # noqa: N806
        self.it = Interpreter(model_path=str(path), num_threads=threads)
        self.inp = self.it.get_input_details()[0]
        self.out = self.it.get_output_details()[0]
        self.it.resize_tensor_input(self.inp["index"], [1, 224, 224, 3])
        self.it.allocate_tensors()
        self._lock = threading.Lock()  # one interpreter is not thread-safe

    def __call__(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, np.float32)
        outs = []
        with self._lock:
            for i in range(len(x)):
                self.it.set_tensor(self.inp["index"], x[i : i + 1])
                self.it.invoke()
                outs.append(self.it.get_tensor(self.out["index"])[0].astype(np.float32))
        return np.stack(outs)


def _resolve_model_file(s: Settings, meta: dict) -> Path:
    if s.model_path.exists():
        return s.model_path
    if meta.get("file"):  # the notebook names the deployed file (model.tflite or model.keras)
        return s.model_meta_path.parent / meta["file"]
    return s.model_path


def load_bundle(s: Settings) -> ModelBundle:
    meta = json.loads(s.model_meta_path.read_text(encoding="utf-8")) if s.model_meta_path.exists() else {}
    mapping_path = s.class_mapping_path
    if not mapping_path.exists():
        raise RuntimeError(f"Class mapping not found at {mapping_path}")
    mapping = load_class_mapping(mapping_path, s.translations_dir)
    if meta.get("num_classes") not in (None, mapping.num_classes):
        raise RuntimeError("model_meta.json num_classes does not match class_mapping.json")

    unc = meta.get("uncertainty", {})
    thresholds = Thresholds(
        t_conf=float(s.uncertainty_t_conf if s.uncertainty_t_conf is not None else unc.get("T_conf", 0.90)),
        m_min=float(s.uncertainty_m_min if s.uncertainty_m_min is not None else unc.get("M_min", 0.10)),
        t_conf_crop=unc.get("T_conf_crop"),
        m_min_crop=unc.get("M_min_crop"),
    )
    common = dict(
        mapping=mapping,
        temperature=float(meta.get("calibration", {}).get("temperature", 1.0)),
        thresholds=thresholds,
        metrics=meta.get("metrics_test_tta", meta.get("metrics_test_no_tta", {})),
        compression=meta.get("compression"),
    )

    model_file = _resolve_model_file(s, meta)
    if model_file.exists():
        expected = s.model_sha256 or meta.get("sha256", "")
        if expected:
            actual = _sha256(model_file)
            if actual != expected:
                raise RuntimeError(f"Model checksum mismatch: expected {expected[:12]}…, got {actual[:12]}…")
        predict = TFLitePredictor(model_file) if model_file.suffix == ".tflite" else _load_keras(model_file)
        bundle = ModelBundle(
            predict_fn=predict,
            version=meta.get("model_version", f"unversioned-{model_file.name}"),
            architecture=meta.get("architecture", "unknown"),
            tta_hflip=bool(meta.get("inference", {}).get("tta_hflip", True)),
            **common,
        )
    elif s.demo_model:
        if s.app_env == "production":
            raise RuntimeError("DEMO_MODEL is not allowed in production")
        log.warning("No model file at %s: running the DEMO model. Results are NOT real.", s.model_path)
        bundle = ModelBundle(predict_fn=DemoPredictor(mapping.num_classes), version=DEMO_VERSION,
                             architecture="demo", tta_hflip=False, is_demo=True, **common)
    else:
        raise RuntimeError(f"Model not found at {s.model_path}. Set DEMO_MODEL=true for local app development.")

    log.info("Model loaded: %s (%d classes, T=%.3f, TTA=%s)", bundle.version, mapping.num_classes,
             bundle.temperature, bundle.tta_hflip)
    return bundle
