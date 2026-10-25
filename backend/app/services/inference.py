"""Probabilities -> calibrated scores -> optional crop filter -> uncertainty policy (UNCERTAINTY_POLICY.md)."""

from dataclasses import dataclass

import numpy as np

from app.services.model_registry import ModelBundle

TOP_K = 3


def apply_temperature(p: np.ndarray, t: float) -> np.ndarray:
    """Same as notebook §12 apply_T: softmax(log(p) / T)."""
    z = np.log(np.clip(p, 1e-12, 1.0)) / t
    z -= z.max(-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(-1, keepdims=True)


@dataclass
class Candidate:
    index: int
    score: float


@dataclass
class Decision:
    status: str  # confident | uncertain | unsupported
    reason: str | None
    candidates: list[Candidate]
    crop: str | None = None
    crop_mismatch: bool = False
    detected_crop: str | None = None


def decide(bundle: ModelBundle, probs: np.ndarray, crop: str | None, quality_issue: str | None) -> Decision:
    """probs: raw (TTA-averaged) softmax for ONE image, shape (C,)."""
    mapping, th = bundle.mapping, bundle.thresholds
    cal = apply_temperature(probs, bundle.temperature)

    if crop is None:
        scores, allowed = cal, np.arange(mapping.num_classes)
        t_conf, m_min = th.t_conf, th.m_min
        conservative = None
    else:
        allowed = np.asarray(mapping.crops[crop])
        mass = float(cal[allowed].sum())
        scores = np.zeros_like(cal)
        scores[allowed] = cal[allowed] / max(mass, 1e-12)
        if th.t_conf_crop is not None:
            t_conf, m_min, conservative = float(th.t_conf_crop), float(th.m_min_crop or th.m_min), None
        else:
            # Crop thresholds not calibrated yet: judge confidence on the un-renormalised score,
            # which is never higher than the renormalised one, so this can only be stricter.
            t_conf, m_min, conservative = th.t_conf, th.m_min, cal

    order = allowed[np.argsort(scores[allowed])[::-1]]
    top = order[:TOP_K]
    candidates = [Candidate(int(i), float(scores[i])) for i in top]

    decision = Decision(status="uncertain", reason=None, candidates=candidates, crop=crop)
    if crop is not None:
        unrestricted_top = int(np.argmax(cal))
        other_crop = mapping.classes[unrestricted_top].crop
        if other_crop != crop and cal[unrestricted_top] >= th.t_conf:
            decision.crop_mismatch, decision.detected_crop = True, other_crop

    if quality_issue:
        decision.status, decision.reason = "unsupported", quality_issue
        return decision
    if decision.crop_mismatch:
        decision.reason = "crop_mismatch"
        return decision

    judge = conservative if conservative is not None else scores
    p1 = float(judge[top[0]])
    p2 = float(judge[top[1]]) if len(top) > 1 else 0.0
    if not mapping.classes[int(top[0])].is_supported:
        decision.reason = "class_not_supported"
    elif p1 >= t_conf and (p1 - p2) >= m_min:
        decision.status = "confident"
    else:
        decision.reason = "low_confidence"
    return decision


def score_band(score: float) -> str:
    return "high" if score >= 0.80 else "medium" if score >= 0.50 else "low"
