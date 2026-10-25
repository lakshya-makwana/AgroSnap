# Phase 1 Audit — Findings

> Every entry comes from direct inspection of notebook code and saved outputs. Anything that could not be checked is marked **Unverified**. Do not estimate.

Audit date: 2026-10-23 (partial — notebook only)  Source inspected: `Yet_another_copy_of_Models_II.ipynb`

## 1. Sources inspected

| Source | Location | Notes |
|---|---|---|
| Training notebook | `Yet_another_copy_of_Models_II.ipynb` (Colab, T4) | Sections v1 (ran) and v2 (defined, **never ran**) |
| Image source | `/MyDrive/sampled` | Exclusion folders: blurry, md5_duplicate, phash_near_duplicate, duplicates, removed_images, cleaning_logs |
| Split CSV | `/MyDrive/results/dataset_splits.csv` (relative paths); older copy at `/MyDrive/dataset_splits.csv` | |
| Class list | `/MyDrive/results/class_names.json` (52 names, sorted) | |
| Checkpoints | `/MyDrive/best_models/{custom,mobilenet,resnet,efficientnet}_best.keras` | Not opened in this audit |
| Metrics | `/MyDrive/results/baseline_metrics.csv` | Values below |
| Full 13,464-image / 99-class dataset | **Not found in this notebook. Unverified.** | |

## 2. Dataset

| Item | Brief says | Notebook shows | Match? |
|---|---|---|---|
| Total images | 13,464 | **2,095** (2,147 found, 52 below-minimum images dropped) | **No** |
| Classes | 99 | **52** (after dropping classes with < 10 images) | **No** |
| Train / Val / Test | 9,424 / 2,020 / 2,020 | **1,466 / 314 / 315** | **No** |
| Split method | — | Random stratified 70/15/15, `random_state=42` | — |
| Near-duplicates across splits checked? | — | Dup folders excluded at source; splits **not** grouped by duplicates | Partial |
| Images per class | — | 10–50 (subset capped at 50 per class) | — |
| Dropped classes | — | Guava (all leaf/fruit classes, 1–6 images each), Tea classes except bird-eye spot, others below 10 | — |
| Non-leaf classes present | — | Potato tubers (Common_Scab, Dry_Rot, Pink_Rot, Miscellaneous, Healthy_Potatoes), pests (Cotton_Aphids, Cotton_Army_worm, Mango_Cutting_Weevil, Mango_Gall_Midge), Rice_dead_heart, Rice_bacterial_panicle_blight | Needs product decision (D15) |

**Key finding:** the trained models use a **50-per-class sample** of the data, not the full dataset described in the brief.

## 3. Model training status (v1)

| Model | Checkpoint | Trained? | Recipe | Best val acc |
|---|---|---|---|---|
| Custom CNN | `custom_best.keras` | Yes | 60 epochs max from scratch | 0.4745 |
| MobileNetV2 | `mobilenet_best.keras` | Yes | Head 15 ep @1e-3, then last 30 layers @1e-5 | 0.7516 |
| ResNet50 | `resnet_best.keras` | Yes | Head, then last 40 layers @1e-5 | 0.8057 |
| EfficientNetB0 | `efficientnet_best.keras` | Yes | Head, then last 20 layers @1e-5 | 0.7707 |

v2 (288 px, cosine LR, ensemble, distillation): **never executed.** `train_one_v2` is inside a Markdown cell, so `run_all_v2()` would fail with `NameError`, and the trigger cells are commented out.

## 4. Preprocessing per model (v1)

All images: PIL → RGB → Lanczos resize to 224×224 → JPEG q95 on disk → `tf.image.resize` 224 bilinear → `/255`.

| Model | Then applied | Resulting range |
|---|---|---|
| Custom CNN | none | [0, 1] |
| MobileNetV2 | `×255` → `mobilenet_v2.preprocess_input` | [−1, 1] |
| ResNet50 | `×255` → `resnet50.preprocess_input` (RGB→BGR, mean subtract) | ≈[−124, 151] |
| EfficientNetB0 | `×255` (model rescales internally) | [0, 255] |

No double-scaling bug found. Preprocessing lives **outside** the models, which is a parity risk for the backend (fixed in v3).

## 5. Class mapping verification

- Mapping: index = position in `sorted(class_names)`; 52 entries.
- Model output dim = 52. ☑
- Spot-check on known images: **Unverified.**

## 6. Evaluation (v1, from `baseline_metrics.csv`, 315 test images)

| Model | Test acc | Test macro F1 | Weighted F1 | Top-5 | Params | Size MB |
|---|---|---|---|---|---|---|
| ResNet50 | 0.7714 | 0.7928 | 0.7669 | 0.9460 | 23.7 M | 212 |
| MobileNetV2 | 0.7397 | 0.7593 | 0.7355 | 0.9492 | 2.3 M | 21 |
| EfficientNetB0 | 0.7333 | 0.7546 | 0.7310 | 0.9524 | 4.1 M | 27 |
| Custom CNN | 0.4444 | 0.4184 | 0.4136 | 0.8254 | 0.4 M | 5 |

The brief's MobileNetV2 figure (77.72% / 0.7548) does **not** match this notebook, so it came from another run. With 315 test images the 95% CI on accuracy is roughly ±4.6 points, so ResNet50, MobileNetV2 and EfficientNetB0 are not clearly separated. Independent field-photo set: **none exists.** CPU latency: **not measured.**

## 7. Environment

| Item | Value |
|---|---|
| Hardware | Colab T4, mixed_float16 |
| TF / Python versions | **Unverified** (not printed) |
| Saved format | `.keras` |
| Custom objects needed to load | None expected |

## 8. Gaps and risks

1. Training data is a small sample; the full dataset location is unknown.
2. Fine-tuning was shallow, with a very low LR; train ≈0.92 vs val ≈0.76.
3. Weak augmentation; selection on `val_loss` from 314 images.
4. No independent field-photo test set; dataset images may not represent farmers' photos.
5. Non-leaf classes conflict with a "photograph a leaf" product.
6. Preprocessing outside the model (backend parity risk).

## 9. Actions taken

- Added `ml/training/AgroSnap_Training_v3.ipynb`. It addresses items 1–3 and 6, and writes to new folders only. See its first cell for details.

## 10. Recommendation

Production model: **not yet chosen.** Run v3 on the **full** dataset, then pick by validation macro F1, checked against test CIs, latency and field photos. If forced to choose from v1 today, use MobileNetV2 or EfficientNetB0 rather than ResNet50: they are within the CI of ResNet50 at about one-tenth of its size.
