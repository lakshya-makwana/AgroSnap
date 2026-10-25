# AgroSnap — Implementation Phases

This plan builds AgroSnap in small, testable phases. Each phase has goals, tasks, deliverables and **exit criteria**. A phase is closed only when its exit criteria are met and evidence is recorded, for example as test output, screenshots or notes in `docs/TESTING.md`.

**Working rules for every phase** (Git workflow rules are in [CONTRIBUTING.md](CONTRIBUTING.md#git-workflow-rules))
- State the files to be changed before changing them.
- Make focused changes and preserve working functionality.
- Never overwrite or retrain existing ML checkpoints without explicit approval.
- Run the relevant tests. Fix errors rather than hiding or skipping them.
- Close each phase with a summary: what was done, what was tested, what remains.
- Never mark something as implemented or tested unless it actually is.

Status legend: ☐ not started · ◐ in progress · ☑ done · ⊘ deferred

## MVP additions (agreed 2026-10-24)

Five features added to the MVP scope. Each one is broken into tasks inside the phases below, tagged **[A1]–[A5]**.

| Tag | Feature | Why | Phases |
|---|---|---|---|
| **A1** | **Crop-first scan.** The farmer picks the crop before scanning; the server only considers that crop's classes. | Removes cross-crop mistakes cheaply; the biggest accuracy win available without new data. | 1, 2, 4 |
| **A2** | **"Was this correct?" feedback.** Yes / No / pick the right disease, with an opt-in to share the photo. | Collects real field photos for retraining and for the independent test set (D11). | 2, 5 |
| **A3** | **Read the result aloud** (`expo-speech`, English and Hindi voices). | Helps farmers who read little English. | 5 |
| **A4** | **Hindi from the start** (moved forward from "Deferred"). | Most target users prefer Hindi; the i18n setup already supports it. | 3, 5 |
| **A5** | **Outdoor-friendly UI**: high-contrast mode, large text, large touch targets. | The app is used in bright sunlight. | 3 |
| **A6** | **Model compression (project novelty).** Post-training quantization to TFLite (fp16, dynamic-range int8, full int8), each evaluated like the full model; ship the smallest variant within 1 macro-F1 point and re-calibrate its thresholds. | Smaller, faster model → cheaper server, faster answers on slow networks, and the path to on-device (offline) detection. | 1, 2 |

---

## Phase 1 — Audit and planning

**Goal:** Know exactly what exists before building anything.

| # | Task | Status |
|---|---|---|
| 1.1 | Inventory the Colab notebook(s), Drive folders, checkpoints, metadata, dataset manifest and class mapping | ☐ |
| 1.2 | Determine which of the Custom CNN, MobileNetV2, ResNet50 and EfficientNetB0 models actually completed training | ☑ (v1 all four; v2 never ran) |
| 1.3 | Record the exact preprocessing for each model (input size, colour order, scaling, `preprocess_input` variant, resize method) | ☑ (AUDIT §4) |
| 1.4 | Verify the 99-class index → label mapping against the training generator or dataset | ☐ |
| 1.5 | Re-evaluate every completed model on the **same** validation and test splits with one evaluation script | ◐ (v3 notebook ready; not yet run) |
| 1.6 | Compute accuracy, macro F1, per-class precision/recall/F1 and a confusion matrix | ☐ |
| 1.7 | Assemble a small **independent image set** (real field photos not taken from the dataset) and evaluate on it | ☐ |
| 1.8 | Measure inference latency and memory on CPU for each candidate model | ☐ |
| 1.9 | Select the production model and record the rationale in `docs/MODEL_CARD.md` | ☐ |
| 1.10 | Check for data leakage (near-duplicate images across splits) | ◐ (implemented in v3) |
| 1.11 | Resolve the open decisions in `docs/DECISIONS.md` | ☐ |
| 1.12 | **[A1]** Evaluate crop-conditioned accuracy (softmax restricted to the true crop's classes) and derive separate `T_conf_crop` thresholds on validation | ◐ (added to v3 pipeline §12b; smoke-tested; not yet run on real data) |
| 1.13 | **[A1]** Export `crops` (crop → class indices) inside `class_mapping.json` | ◐ (added to v3 pipeline; not yet run) |
| 1.14 | **[A6]** Quantize the production model (TFLite fp32 / fp16 / dynamic int8 / full int8); compare size, CPU latency, val/test macro F1 and top-1 agreement in `compression_v3.csv` | ◐ (v3 pipeline §13b; smoke-tested end to end on synthetic data; not yet run on real data) |
| 1.15 | **[A6]** Ship the smallest variant within `MAX_F1_DROP` (1 pt) on validation; re-fit temperature and thresholds on it | ◐ (v3 pipeline §13b–14) |
| 1.16 | **[A6]** Report the compression results in `MODEL_CARD.md` §5b (size ×, latency, accuracy change, per-class changes) | ☐ |

**Deliverables:** completed `docs/AUDIT.md`, draft `docs/MODEL_CARD.md`, `ml/artifacts/class_mapping.json` (verified), an evaluation script under `ml/evaluation/`.

**Exit criteria**
- [ ] The production model is chosen on macro F1, per-class performance, independent-image results and latency, not accuracy alone.
- [ ] The class mapping and preprocessing are written down and reproducible.
- [ ] Every reported metric was actually produced by the evaluation script. None are copied from memory.
- [ ] Open decisions are answered or have an agreed default.

---

## Phase 2 — Backend and inference

**Goal:** A FastAPI service that returns trustworthy predictions.

| # | Task | Status |
|---|---|---|
| 2.1 | Scaffold `backend/` (FastAPI, Pydantic settings, logging, error handlers) | ◐ (scaffolded; settings + error envelope + logging) |
| 2.2 | `GET /api/v1/health` and `GET /api/v1/model-info` | ☑ (tested) |
| 2.3 | Load the model **once** at startup, with a version string and a checksum | ☑ (lifespan load, sha256 check, tested in demo mode) |
| 2.4 | Image validation: size limit, MIME sniffing, decode, EXIF orientation, HEIC handling, corrupt-file rejection | ◐ (size, format sniff, EXIF, HEIC opener, corrupt → 4xx; tested except HEIC) |
| 2.5 | Preprocessing module reproducing training preprocessing exactly | ☑ (NumPy bilinear == TF 2.20 bilinear, tested) |
| 2.6 | `POST /api/v1/predictions` (anonymous allowed; not persisted unless authenticated and opted in) | ◐ (anonymous, never persisted; saving needs Phase 7 auth) |
| 2.7 | Uncertainty policy implementation (see `docs/UNCERTAINTY_POLICY.md`) | ◐ (confident/uncertain/unsupported + crop rule; thresholds come from the trained bundle) |
| 2.8 | Idempotency key support to prevent duplicate predictions | ☑ (in-memory, single worker; tested) |
| 2.9 | Rate limiting on prediction endpoint | ☐ |
| 2.10 | Tests: preprocessing parity, class mapping, invalid/corrupt/oversized images, response schema | ◐ (24 API/inference tests; parity fixtures pending a trained model) |
| 2.11 | **Parity test:** API top-k vs notebook top-k on a fixed image set (tolerance documented) | ◐ (test written; skips until the trained bundle exists) |
| 2.12 | **[A1]** Optional `crop` field on `POST /predictions`: restrict and renormalise scores to that crop's classes, apply crop thresholds; `GET /crops` lists supported crops | ☑ (tested) |
| 2.14 | **[A6]** Serve `model.tflite` (LiteRT / `tf.lite.Interpreter`) with the same preprocessing; parity test runs against the deployed file | ◐ (implemented; parity needs a trained bundle) |
| 2.13 | **[A2]** `POST /feedback`: verdict (correct / wrong / unsure), corrected class, opt-in photo storage with the model version | ☑ (tested; SQLite by default) |

**Exit criteria**
- [ ] The parity test passes: same top-1 class on all fixtures, with scores within the documented tolerance.
- [ ] Invalid inputs return structured 4xx errors and never 500.
- [ ] Inference duration and model version appear in every response.

---

## Phase 3 — Android foundation

**Goal:** A navigable, well-designed app shell.

| # | Task | Status |
|---|---|---|
| 3.1 | Expo + TypeScript + Expo Router project in `mobile/` | ☑ (Expo SDK 58, routes in src/app) |
| 3.2 | Bottom tabs: Home, Scan, Weather, My Farm, Profile | ☑ |
| 3.3 | Design tokens (colours, typography, spacing) and UI library setup (see `docs/UI_UX.md`) | ☑ (in-house components, ADR-009) |
| 3.4 | Reusable components: Button, Card, ScreenContainer, EmptyState, ErrorState, LoadingState, OfflineBanner | ◐ (Button, Card, Chip, Notice, OfflineBanner; no skeleton loaders yet) |
| 3.5 | API client with timeouts, typed responses, error mapping | ☑ |
| 3.6 | Network-status detection (`@react-native-community/netinfo`) | ☑ |
| 3.7 | i18n scaffolding with **English and Hindi** (see `docs/I18N.md`) **[A4]** | ◐ (en + hi; Hindi needs native-speaker review) |
| 3.8 | Lint, type-check and unit-test setup | ◐ (tsc + jest pass; eslint not set up) |
| 3.9 | **[A4]** Language picker in Profile; choice saved on the device; Noto Sans Devanagari-capable font | ◐ (picker done; Devanagari font not bundled, system font used) |
| 3.10 | **[A5]** High-contrast theme + "Large text" setting in Profile; primary buttons ≥ 56 dp | ◐ (implemented; not checked outdoors) |

**Exit criteria**
- [ ] The app runs on a physical Android device as a development build.
- [ ] No user-facing strings are hard-coded outside the i18n resource files.
- [ ] Every screen is usable in Hindi and in high-contrast mode, checked outdoors in daylight.
- [ ] Hindi strings reviewed by a native speaker.
- [ ] `tsc --noEmit` and lint pass.

---

## Phase 4 — Camera and Photos (core MVP feature)

**Goal:** Two independent, reliable ways to get a leaf image into the prediction pipeline.

| # | Task | Status |
|---|---|---|
| 4.0 | **[A1]** Crop picker before scanning (remembers the last crop; "Not sure" allowed) | ◐ (implemented; not device-tested) |
| 4.1 | Scan screen with clearly distinct **[ Camera ] [ Photos ]** tabs | ◐ (implemented; not device-tested) |
| 4.2 | Camera tab: request camera permission **only when this tab opens**; live preview, capture, switch camera, torch if available | ◐ (implemented; not device-tested) |
| 4.3 | Camera denied/unavailable states with "Open settings" and "Use Photos instead" | ◐ (implemented; not device-tested) |
| 4.4 | Photos tab: Android system photo picker, with **no media-library permission requested** | ◐ (implemented; merged manifest not yet inspected) |
| 4.5 | Handle picker cancellation, unsupported formats, HEIC and very large images | ◐ (implemented; not device-tested) |
| 4.6 | Client-side normalisation (EXIF rotate, downscale, re-encode JPEG) per `docs/SCAN_FLOW.md` | ◐ (implemented; EXIF behaviour of the manipulator must be checked on a phone) |
| 4.7 | Shared Image Review screen: large preview, Retake / Choose another, **Detect Disease** | ◐ (implemented; not device-tested) |
| 4.8 | Single prediction call used by both sources; button disabled while in flight | ◐ (implemented; not device-tested) |
| 4.9 | Retry failed uploads without re-selecting the image | ◐ (same file + key on retry; not device-tested) |
| 4.10 | Manual device tests (see `docs/TESTING.md` §Scan) | ☐ |

**Exit criteria**
- [ ] Gallery selection works with camera permission **denied**, verified on a physical device.
- [ ] Both sources hit the same endpoint and produce consistent results for the same image.
- [ ] Repeated taps produce exactly one prediction request.

---

## Phase 5 — Results, guidance and history

| # | Task | Status |
|---|---|---|
| 5.1 | Result screen: plain-English crop and disease, confidence explanation, alternatives | ◐ (implemented; not device-tested) |
| 5.2 | Uncertain and unsupported states with guidance on retaking the photo | ◐ (implemented; not device-tested) |
| 5.3 | Seed `disease_classes` from the verified mapping | ☐ |
| 5.4 | Advisory content pipeline and review workflow (see `docs/ADVISORY_CONTENT.md`) | ☐ |
| 5.5 | `GET /api/v1/advisories/{class_id}` that returns only reviewed content | ☐ |
| 5.6 | "Save to history" opt-in; history list and detail; delete scan | ☐ |
| 5.7 | Private image storage with short-lived signed URLs | ☐ |
| 5.8 | **[A2]** "Was this correct?" card on the result screen: Yes / No → pick the right disease / Not sure; photo-sharing consent checkbox, off by default | ◐ (implemented; not device-tested) |
| 5.9 | **[A2]** `ml/feedback/export_feedback.py`: turn consented feedback into a labelled folder for retraining and the independent test set | ◐ (script written; not run on real feedback yet) |
| 5.10 | **[A3]** "Listen" button on the result screen reads the headline, score band and next step in the app language | ◐ (implemented; not device-tested) |
| 5.11 | **[A4]** Hindi crop and disease names (`hi` names in `class_mapping.json` or a translations table) | ◐ (crop names + a few disease names in ml/artifacts/translations/hi.json; draft) |

**Exit criteria**
- [ ] Feedback photos are stored only with explicit consent and can be deleted.
- [ ] "Listen" works in English and Hindi on a real phone (falls back to English if no Hindi voice is installed).
- [ ] No advisory is shown unless it has `reviewed_by`, `reviewed_at` and `source_url`.
- [ ] No pesticide dosages or chemical instructions appear unless they are quoted from a reviewed source.
- [ ] Deleting a scan removes its database rows and its stored image.

---

## Phase 6 — Weather and farm

| # | Task | Status |
|---|---|---|
| 6.1 | Backend weather proxy (API key server-side only) with caching | ☑ (Open-Meteo, 20 min cache; tested with a fake provider) |
| 6.2 | Current, hourly, 7-day and alerts (where provider supports) | ◐ (current, hourly, 7-day; no alerts from Open-Meteo) |
| 6.3 | Location: farm location, device location (requested only on demand) or manual selection | ◐ (device on tap or city list; farm location needs Phase 6 farms) |
| 6.4 | Client weather cache with a visible "Last updated …" label and a stale indicator | ◐ (Updated + Not current + >24 h rule; cache is in memory, not persisted) |
| 6.5 | Farm CRUD and farm crops CRUD | ☐ |
| 6.6 | Crop diary and simple reminders (local notifications) | ☐ |
| 6.7 | Home screen: greeting, weather summary, Scan a Leaf, recent detections, reminders | ◐ (greeting, weather, Scan a Leaf, tips; no recent scans/reminders) |

**Exit criteria**
- [ ] Weather always shows which location and which update time it refers to.
- [ ] Cached weather is never presented as current.
- [ ] Location permission is never requested at app start.

---

## Phase 7 — Authentication, deployment and testing

| # | Task | Status |
|---|---|---|
| 7.1 | Register, login, refresh, `users/me`, account deletion | ☐ |
| 7.2 | Tokens stored with `expo-secure-store` | ☐ |
| 7.3 | Ownership checks on every farm, scan and image route, with tests for cross-user access | ☐ |
| 7.4 | Deploy PostgreSQL, object storage and the API over HTTPS | ☐ |
| 7.5 | EAS build: internal-testing APK | ☐ |
| 7.6 | Full manual test pass on at least 2–3 real Android devices (different OS versions and screen sizes) | ☐ |
| 7.7 | Slow-network and offline testing | ☐ |
| 7.8 | Production AAB and Play Console data-safety form | ☐ |
| 7.9 | Final documentation review against the Definition of Done | ☐ |

**Exit criteria:** All 10 Definition of Done items in `README.md` are verified, with evidence.

---

## Deferred (post-MVP)

| Feature | Note |
|---|---|
| On-device (offline) inference | TFLite conversion + parity tests; only claim offline detection once built and tested |
| Offline crop-care library | Cache reviewed advisories locally |
| Other Indian languages (Hindi moved into the MVP as A4) | Architecture prepared in Phase 3 |
| Market prices, government schemes | Need reliable data sources |
| AI chat assistant | Needs a safety review for agricultural advice |
| Community, social, advanced analytics | Out of scope |
