# Model Card — AgroSnap Leaf Disease Classifier

> **Status: DRAFT.** v1 results (52 classes, sampled data) are recorded in `AUDIT.md` §6. Fill this card from `results_v3/metrics_v3.csv` and `best_models_v3/production/model_meta.json` after running `ml/training/AgroSnap_Training_v3.ipynb`.
>
> **Note:** Fields marked `TBD` must be filled from the Phase 1 evaluation script output. Do not copy numbers from memory or earlier notebooks without re-running them.

## 1. Model details

| Field | Value |
|---|---|
| Production architecture | TBD (candidates: Custom CNN, MobileNetV2, ResNet50, EfficientNetB0) |
| Model version string | TBD (`agrosnap-<arch>-<yyyymmdd>-<shortsha>`) |
| Framework | TensorFlow/Keras, version TBD |
| Saved format | TBD (`.keras` preferred) |
| Artifact SHA-256 | TBD |
| Input | RGB image, TBD × TBD px |
| Output | Softmax over 99 classes |
| Owner | TBD |

## 2. Intended use

- **Intended:** a decision-support suggestion of a likely crop disease from a single close-up leaf photo, for farmers and extension workers in India.
- **Not intended:** a confirmed diagnosis, a basis for chemical dosing, crops or diseases outside the 99 classes, non-leaf images, or whole-field images.

## 3. Training data

| Item | Value |
|---|---|
| Total images | 13,464 (re-verify) |
| Classes | 99 |
| Split | Train 9,424 / Val 2,020 / Test 2,020 |
| Split strategy | TBD (stratified? leakage check result?) |
| Sources | TBD (lab-background vs field photos; proportion) |
| Class balance | min TBD / max TBD images per class |
| Augmentation | TBD |

## 4. Preprocessing (must match the backend exactly)

| Step | Value |
|---|---|
| Decode | Pillow, EXIF transpose, convert to RGB |
| Resize | v3: Lanczos to 256×256 (stretch), then bilinear to 224×224 |
| Scaling | v3: **none outside the model**. The model expects RGB float32 0–255; architecture-specific scaling is a layer inside it |
| Dtype / layout | float32, NHWC |

Reference implementation: `ml/evaluation/preprocess.py`, mirrored in `backend/app/services/preprocessing.py`. The parity test is in `backend/tests/test_parity.py`.

## 5. Evaluation (all models, same script, same splits)

| Model | Test acc | Test macro F1 | Val macro F1 | Independent set acc | CPU ms/img | Size MB | Trained fully? |
|---|---|---|---|---|---|---|---|
| Custom CNN | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| MobileNetV2 | TBD (v1 notebook: 73.97%, 52 classes) | TBD (v1: 0.7593) | TBD | TBD | TBD | TBD | TBD |
| ResNet50 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| EfficientNetB0 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### Selection rationale
TBD. The decision must weigh macro F1, worst-class F1, independent-image performance, latency and size, and must not rest on accuracy alone.

## 5b. Model compression [A6] (project novelty)

Produced by v3 pipeline §13b → `results_v3/compression_v3.csv`. All variants take RGB float32 0–255 and use the same flip-TTA evaluation.

| Variant | Size MB | × smaller | CPU ms/img | Val macro F1 | Test acc | Test macro F1 | Top-1 agreement with full model |
|---|---|---|---|---|---|---|---|
| Full Keras (fp32) | TBD | 1.0 | TBD | TBD | TBD | TBD | 100% |
| TFLite fp32 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| TFLite fp16 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| TFLite dynamic-range int8 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| TFLite full int8 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

**Rule:** deploy the smallest variant whose validation macro F1 is at most 1 point (`MAX_F1_DROP`) below the full model. Temperature and thresholds are then re-fitted on that variant (validation only), because quantization changes the scores. Also check the per-class report: a variant that is fine on average can still hurt one class badly.

**Crop-first accuracy [A1]:** `metrics_crop_first` in `model_meta.json` gives accuracy when the farmer picks the true crop first. Record it here: TBD.

### Per-class results
Attach `ml/evaluation/reports/<version>/per_class.csv` and the confusion matrix. List here:
- 10 lowest-F1 classes: TBD
- Most-confused class pairs: TBD
- Classes marked `is_supported = false`: TBD

## 6. Uncertainty calibration
- Threshold(s) chosen on the **validation** set: TBD (see UNCERTAINTY_POLICY.md)
- Expected Calibration Error (before / after temperature scaling, if used): TBD
- Coverage vs accuracy at the chosen threshold: TBD

## 7. Limitations and known risks

- Accuracy measured on dataset images may be **much higher than on real field photos** (backgrounds, lighting, multiple leaves, blur). The independent-set result is the more realistic indicator.
- The model may give high scores to images that are not leaves or that show unsupported crops. Out-of-distribution detection is best-effort.
- Visually similar diseases are commonly confused (see the confusion matrix).
- Nutrient deficiencies, pest damage and abiotic stress may be predicted as diseases.
- Scores are not calibrated probabilities unless calibration is applied and verified.

## 8. Supported classes

Generated from `ml/artifacts/class_mapping.json`:

| Index | class_key | Crop | Disease | Healthy? | Supported? |
|---|---|---|---|---|---|
| 0 | TBD | | | | |
| … | | | | | |
| 98 | TBD | | | | |

## 9. Versioning and updates

- Every new artifact gets a new version string and SHA-256. The backend logs both at startup and returns them in every response.
- A model update requires: re-running the evaluation, updating this card, passing the parity test, and re-seeding `disease_classes` if the mapping changed.
- Model artifacts are stored outside Git (object storage or Git LFS). See DEPLOYMENT.md.
