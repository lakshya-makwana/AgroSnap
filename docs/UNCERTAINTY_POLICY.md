# Uncertainty Policy

AgroSnap must not present an uncertain model output as a diagnosis. This document defines how the backend decides between `confident`, `uncertain` and `unsupported`, and how the app communicates each result.

## 1. Signals available

| Signal | Use |
|---|---|
| Top-1 softmax score `p1` | Primary threshold |
| Margin `p1 − p2` | Detects close calls between similar diseases |
| Entropy of the score vector | Optional secondary signal |
| Image-quality checks (blur, darkness, size) | Flags images that are unsuitable for analysis |
| OOD detector (optional, evaluated) | Flags non-leaf or unsupported content |

## 2. Decision rule (initial form; parameters set from validation data)

```
if image_quality_fails:            status = "unsupported"  (reason: "blurry" | "too_dark" | "too_small")
elif ood_detector_flags (if enabled): status = "unsupported"  (reason: "not_a_leaf_or_unsupported")
elif class.is_supported is False:  status = "uncertain"
elif p1 >= T_conf and (p1 - p2) >= M_min:
                                   status = "confident"
else:                              status = "uncertain"
```

### Choosing `T_conf` and `M_min`
1. Run the production model on the **validation** split only.
2. (Optional) Fit temperature scaling on validation and re-check calibration.
3. Plot accuracy against coverage across thresholds.
4. Pick `T_conf` so that accuracy on the `confident` subset is at least **TBD %** (target agreed in DECISIONS.md), while keeping coverage acceptable.
5. Confirm on the **test** split and on the independent image set. Do not tune on test.
6. Record the values, the date and the model version in MODEL_CARD.md §6. Store them in config, not in code.

Thresholds are tied to a model version. A new model requires new thresholds.

## 3. What a threshold cannot do

A high softmax score does **not** prove that an image shows a supported crop or disease. Softmax classifiers can be confidently wrong on out-of-distribution images. The `unsupported` status is therefore described as best-effort, and the app never claims that it guarantees detection of unsuitable images.

Approaches to investigate later, each only if it is evaluated on held-out OOD images (non-leaf photos, other crops):
- Energy score or max-logit thresholds.
- A small "leaf / not-leaf" binary classifier.
- Embedding-distance checks against class centroids.

An autoencoder is not assumed to be needed. It is considered only if evaluation shows that it beats the simpler options above.

## 4. How the app communicates each status

| Status | Headline | Body | Actions |
|---|---|---|---|
| `confident` | "Likely: Early blight (Tomato)" | Score explanation + reviewed guidance | Save · View guidance · Scan again |
| `uncertain` | "Unable to determine reliably" | "The closest matches were …" as **possibilities**, plus photo tips | Retake photo · Choose another · Contact KVK |
| `unsupported` | "This photo can't be analysed" | The reason in plain words (blurry / dark / not a leaf) and photo tips | Retake photo · Choose another |

### Score wording
- Show the score as a band ("High / Medium / Low match"), with the percentage available on tap.
- Always include: *"This shows how closely the photo matches what the model learned. It is not a guarantee that the result is correct."*
- Never say "diagnosis", "confirmed" or "100% sure".

### Photo tips (shown for uncertain and unsupported results)
- Photograph one leaf, filling most of the frame.
- Use daylight and avoid harsh shadows.
- Hold the phone steady and tap to focus.
- Show the affected area clearly.
