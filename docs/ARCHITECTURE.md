# Architecture

## 1. System overview

```
┌──────────────────────────┐        HTTPS (JSON + multipart)        ┌─────────────────────────────┐
│  Android app (Expo / RN) │ ─────────────────────────────────────▶ │  FastAPI backend (/api/v1)  │
│                          │                                        │                             │
│  Scan: Camera | Photos   │                                        │  Image validation           │
│  Image Review            │                                        │  Preprocessing (exact)      │
│  Results / History       │ ◀───────────────────────────────────── │  TF/Keras model (loaded 1×) │
│  Weather (cached)        │                                        │  Uncertainty policy         │
│  My Farm / Profile       │                                        │  Auth (JWT) · Ownership     │
│  Secure token storage    │                                        │  Weather proxy + cache      │
└──────────────────────────┘                                        └──────┬───────────┬──────────┘
                                                                           │           │
                                                                  ┌────────▼───┐ ┌─────▼──────────┐
                                                                  │ PostgreSQL │ │ Object storage │
                                                                  │ (Alembic)  │ │ (private, S3-  │
                                                                  └────────────┘ │  compatible)   │
                                                                                 └────────────────┘
                                                                           │
                                                                  ┌────────▼─────────┐
                                                                  │ Weather provider │  (API key server-side only)
                                                                  └──────────────────┘
```

## 2. Key principles

1. **The server is the source of truth for labels.** The client never sends a class index or disease name. The backend maps model output indices to names using the verified `class_mapping.json`.
2. **One prediction pipeline.** Camera and Photos produce the same normalised JPEG and call the same endpoint.
3. **Preprocessing parity.** `backend/app/services/preprocessing.py` reproduces the training preprocessing exactly, and a parity test against notebook output guards it.
4. **No secrets in the APK.** The weather key, DB credentials and storage keys live only on the backend. The app knows only `EXPO_PUBLIC_API_BASE_URL`.
5. **Private by default.** Scans are not stored unless the user is signed in and opts in. Images are kept in private object storage and served through short-lived signed URLs.
6. **Honest uncertainty.** Low-confidence results return status `uncertain`, not a disease name presented as fact.

## 3. Mobile app structure

> **As built (2026-10-24):** Expo SDK 58 puts routes in `mobile/src/app/` (not `mobile/app/`); `review` and `result` are stack screens above the tabs. See `mobile/README.md` for the current route list. The tree below is the target layout.

```
mobile/
├── app/                         Expo Router routes
│   ├── (tabs)/
│   │   ├── _layout.tsx          Bottom tabs: Home, Scan, Weather, My Farm, Profile
│   │   ├── index.tsx            Home
│   │   ├── scan/
│   │   │   ├── index.tsx        Camera | Photos tabs
│   │   │   ├── review.tsx       Shared Image Review
│   │   │   └── result.tsx       Result + guidance
│   │   ├── weather.tsx
│   │   ├── farm/…
│   │   └── profile/…
│   └── (auth)/login.tsx, register.tsx
├── src/
│   ├── components/              Button, Card, ScreenContainer, States, OfflineBanner
│   ├── features/
│   │   ├── detection/           useCameraCapture, usePhotoPicker, normaliseImage, usePrediction
│   │   ├── weather/             useWeather (with cache), WeatherCard
│   │   └── farm/                farm and crop forms, hooks
│   ├── services/                apiClient, authStore (secure-store), netinfo
│   ├── i18n/                    en.json (+ hi.json later)
│   ├── theme/                   tokens.ts
│   └── types/                   API types (ideally generated from OpenAPI)
└── assets/
```

**State:** use TanStack Query for server state (caching, retries, deduplication) and a small Zustand store for the in-progress scan (image URI, source, idempotency key).

## 4. Backend structure

```
backend/app/
├── main.py                  App factory, lifespan (loads model once), routers, middleware
├── core/                    config (pydantic-settings), security (JWT, hashing), logging, rate limit
├── api/v1/                  health, model_info, auth, users, predictions, weather, farms, crops, advisories
├── db/                      session, base, Alembic env
├── models/                  SQLAlchemy ORM models
├── schemas/                 Pydantic request/response models
└── services/
    ├── model_registry.py    Loads artifact, checksum, version, class mapping
    ├── image_validation.py  Size, MIME sniff, decode, EXIF, HEIC
    ├── preprocessing.py     Exact training preprocessing
    ├── inference.py         Predict → top-k → uncertainty policy
    ├── storage.py           Private object storage, signed URLs
    └── weather.py           Provider client + server cache
```

**Model loading:** load in FastAPI's `lifespan` handler into a singleton. Run inference in a threadpool (`run_in_threadpool`) so that the event loop is not blocked. Cap concurrency with a semaphore to bound memory use.

## 5. Prediction sequence

1. The app normalises the image (EXIF rotate, downscale so the long edge is at most 1600 px, JPEG quality around 85) and generates an `Idempotency-Key` UUID.
2. `POST /api/v1/predictions` (multipart: `image`, optional `farm_id`, `save`).
3. The backend validates size and type, decodes with Pillow, applies EXIF transpose and converts to RGB.
4. Preprocessing → `model.predict` → softmax scores (99).
5. Top-k (k=3) indices → `disease_classes` lookup.
6. The uncertainty policy returns `confident` / `uncertain` / `unsupported`.
7. If `save` is true and the user is authenticated, the image is uploaded to storage and the `predictions` and `prediction_candidates` rows are written.
8. The response includes the status, top-k results, model version, inference time and an advisory reference.

## 6. Key technical choices and alternatives

| Choice | Reason | Alternative considered |
|---|---|---|
| Server-side inference | One model version, easier updates, works on low-end phones | TFLite on-device (deferred; needs parity tests) |
| Expo + dev build | Fast iteration, EAS builds, good camera/picker modules | Bare React Native |
| PostgreSQL | Relational ownership constraints, mature | — |
| S3-compatible storage | Signed URLs, lifecycle rules for retention | DB blobs (rejected) |
| JWT access + refresh | Stateless API, refresh rotation | Server sessions |
