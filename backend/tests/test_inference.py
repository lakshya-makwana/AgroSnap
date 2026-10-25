from pathlib import Path

import numpy as np

from app.services.class_mapping import load_class_mapping
from app.services.inference import apply_temperature, decide
from app.services.model_registry import ModelBundle, Thresholds

MAPPING = load_class_mapping(Path(__file__).resolve().parents[1] / "demo" / "class_mapping.json")
TOMATO = MAPPING.crops["Tomato"]  # [8, 9, 10, 11]


def bundle(**th) -> ModelBundle:
    return ModelBundle(predict_fn=lambda x: x, mapping=MAPPING, version="t", architecture="t",
                       thresholds=Thresholds(**th))


def probs(**by_index) -> np.ndarray:
    p = np.full(MAPPING.num_classes, 1e-6)
    for k, v in by_index.items():
        p[int(k[1:])] = v
    return p / p.sum()


def test_temperature_one_is_identity_and_higher_flattens():
    p = probs(i8=0.7, i9=0.2, i0=0.1)
    assert np.allclose(apply_temperature(p, 1.0), p)
    assert apply_temperature(p, 2.0).max() < p.max()


def test_confident_and_uncertain():
    assert decide(bundle(), probs(i8=0.95, i9=0.05), None, None).status == "confident"
    d = decide(bundle(), probs(i8=0.55, i9=0.45), None, None)
    assert d.status == "uncertain" and d.reason == "low_confidence"
    d = decide(bundle(), probs(i8=0.92, i9=0.08), None, None)
    assert d.status == "confident"
    d = decide(bundle(), probs(i8=0.90, i9=0.85), None, None)  # small margin
    assert d.status == "uncertain"


def test_crop_filter_only_returns_that_crops_classes():
    p = probs(i2=0.5, i8=0.3, i9=0.2)  # unrestricted top is Potato
    d = decide(bundle(), p, "Tomato", None)
    assert all(c.index in TOMATO for c in d.candidates)
    assert d.candidates[0].index == 8
    assert abs(sum(c.score for c in d.candidates) - 1.0) < 0.01  # renormalised within the crop


def test_crop_mismatch_when_model_is_sure_about_another_crop():
    d = decide(bundle(), probs(i2=0.97, i8=0.03), "Tomato", None)
    assert d.crop_mismatch and d.detected_crop == "Potato"
    assert d.status == "uncertain" and d.reason == "crop_mismatch"


def test_uncalibrated_crop_thresholds_are_conservative():
    # Renormalised Tomato score is ~0.95 but the raw score is only 0.57: must NOT be confident.
    p = probs(i8=0.57, i9=0.03, i2=0.40)
    assert decide(bundle(), p, "Tomato", None).status == "uncertain"
    # With calibrated crop thresholds the renormalised score is used.
    assert decide(bundle(t_conf_crop=0.9, m_min_crop=0.1), p, "Tomato", None).status == "confident"


def test_quality_issue_is_unsupported():
    d = decide(bundle(), probs(i8=0.99), None, "too_dark")
    assert d.status == "unsupported" and d.reason == "too_dark"


def test_hindi_names_load():
    m = load_class_mapping(Path(__file__).resolve().parents[1] / "demo" / "class_mapping.json",
                           Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "translations")
    assert m.classes[8].display("hi") == ("टमाटर", "अगेती झुलसा")
    assert m.classes[8].display("en") == ("Tomato", "Early blight")
