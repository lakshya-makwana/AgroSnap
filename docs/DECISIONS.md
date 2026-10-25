# Decisions

## 1. Open decisions (need owner input)

| # | Decision | Options | Suggested default | Needed by |
|---|---|---|---|---|
| D1 | Production model | Custom CNN / MobileNetV2 / ResNet50 / EfficientNetB0 | Decide from Phase 1 evaluation | Phase 2 |
| D2 | Minimum accuracy target on the "confident" subset | e.g. 90% / 95% | 90%, revisit after calibration | Phase 2 |
| D3 | Can users scan without an account? | Yes (not saved) / No | Yes; saving history requires an account | Phase 2 |
| D4 | UI library | React Native Paper / NativeWind | React Native Paper | Phase 3 |
| D5 | Weather provider | Open-Meteo / OpenWeather / Tomorrow.io / IMD-based source | Compare India coverage, alerts, licence and cost; Open-Meteo is a candidate for forecasts but alert coverage must be checked | Phase 6 |
| D6 | Hosting | Render / Railway / Fly.io / AWS / GCP (Mumbai region) | Decide by RAM cost for TF inference | Phase 7 |
| D7 | Object storage | AWS S3 / Cloudflare R2 / GCS / Supabase Storage | Any S3-compatible private bucket | Phase 5 |
| D8 | Login method | Email + password / phone OTP / Google | Email + password for MVP; phone OTP likely better for farmers later (SMS cost) | Phase 7 |
| D9 | Image retention | Until user deletes / auto-delete after N days | Until user deletes | Phase 5 |
| D10 | Advisory reviewer | Agronomist / university partner / KVK contact | Needs a named qualified person | Phase 5 |
| D11 | Independent test set | Who collects field photos, how many per class | ≥ 3–5 per top-priority crop | Phase 1 |
| D12 | Licence | Proprietary / MIT / Apache-2.0 | Decide; check dataset licence first | Before public repo |
| D13 | Dataset licence and attribution | — | Confirm the dataset's source and terms | Phase 1 |
| D14 | Which dataset is canonical? The notebook trains on `/MyDrive/sampled` (2,095 images, 52 classes); the brief describes 13,464 images / 99 classes | Full set / sampled set | Use the full set; set `SOURCE_DIR` in the v3 notebook | **Now** |
| D15 | Keep non-leaf classes (potato tubers, insect pests, panicle/dead-heart)? | Keep and change app wording / drop for a leaf-only MVP | Decide with product scope; it affects the Scan copy and the model card | Phase 1 |

## 2. Decision log

Record each decision once it is made. Do not delete old entries; supersede them instead.

| ID | Date | Decision | Reason | Decided by | Supersedes |
|---|---|---|---|---|---|
| ADR-001 | 2026-10-23 | Server-side inference for MVP; on-device inference deferred | One model version, simpler updates, low-end phones | Project plan | — |
| ADR-002 | 2026-10-23 | Gallery uses the system photo picker with no media-library permission | Privacy, Play policy, independence from camera permission | Project plan | — |
| ADR-003 | 2026-10-23 | Client never sends class labels; server maps indices | Prevents mismatch and tampering | Project plan | — |
| ADR-004 | 2026-10-23 | Advisories shown only when reviewed and sourced | Farmer safety | Project plan | — |
| ADR-005 | 2026-10-23 | Model preprocessing is built into the exported model (input = RGB float32 0–255, 224×224) | Removes train/serve preprocessing mismatch | v3 notebook | — |
| ADR-006 | 2026-10-23 | Production model chosen on validation macro F1; test set used only for reporting | Avoids tuning on test | v3 notebook | — |
| ADR-007 | 2026-10-24 | [A1] Crop-first scan: scores restricted to the chosen crop and renormalised; separate crop thresholds fitted on validation; until they exist the backend judges on the un-renormalised score (stricter) | Removes cross-crop errors without new data, without overstating confidence | Team | — |
| ADR-008 | 2026-10-24 | [A6] Model compression is the project's novelty: post-training quantization to TFLite; ship the smallest variant within 1 val macro-F1 point; re-fit temperature and thresholds on the shipped file | Smaller and faster model; path to on-device inference | Team | — |
| ADR-009 | 2026-10-24 | D4 resolved: small in-house components on the UI_UX tokens instead of React Native Paper | Full control of high-contrast and large-text modes [A5]; fewer dependencies | Team | — |
| ADR-010 | 2026-10-24 | Weather provider for the MVP: Open-Meteo (no API key, no alerts) | Free, India coverage; alerts still open under D5 | Team | — |

### Template
```
ADR-NNN — <title>
Date:
Context:
Decision:
Consequences:
Alternatives considered:
```
