# API Reference — `/api/v1`

- Base URL: `https://<host>/api/v1`
- Format: JSON, except image uploads, which use `multipart/form-data`.
- Auth: `Authorization: Bearer <access_token>`, where required.
- The interactive schema is served by FastAPI at `/docs` and `/openapi.json`. That generated schema is authoritative. This document explains intent.

## Conventions

### Error envelope
Every error returns:
```json
{
  "error": {
    "code": "IMAGE_TOO_LARGE",
    "message": "The image is larger than 8 MB. Please choose a smaller photo.",
    "details": {}
  }
}
```

| HTTP | Typical codes |
|---|---|
| 400 | `INVALID_REQUEST` |
| 401 | `UNAUTHENTICATED`, `TOKEN_EXPIRED` |
| 403 | `FORBIDDEN` |
| 404 | `NOT_FOUND` (also returned for resources owned by another user, so their existence is not revealed) |
| 409 | `CONFLICT`, `IDEMPOTENCY_MISMATCH` |
| 413 | `IMAGE_TOO_LARGE` |
| 415 | `UNSUPPORTED_MEDIA_TYPE` |
| 422 | `IMAGE_UNREADABLE`, `VALIDATION_ERROR` |
| 429 | `RATE_LIMITED` (with `Retry-After`) |
| 503 | `MODEL_UNAVAILABLE`, `WEATHER_UNAVAILABLE` |

### Pagination
List endpoints use `?limit=20&cursor=<opaque>`. The response includes `{ "items": [...], "next_cursor": "..." | null }`.

---

## Health and model

### `GET /health`
```json
{ "status": "ok", "model_loaded": true, "db": "ok", "version": "0.1.0" }
```

### `GET /model-info`
```json
{
  "model_name": "<selected architecture>",
  "model_version": "agrosnap-<arch>-<yyyymmdd>-<shortsha>",
  "num_classes": 99,
  "input_size": [224, 224],
  "metrics": { "test_macro_f1": null, "test_accuracy": null },
  "supported_crops": ["..."],
  "limitations_url": "/docs/MODEL_CARD.md"
}
```
Metric values come from the verified evaluation in `MODEL_CARD.md`. Use `null` until verified.

---

## Authentication

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/auth/register` | `{name, email, password, preferred_language?}` | `201` user + tokens |
| POST | `/auth/login` | `{email, password}` | `{access_token, refresh_token, token_type, expires_in}` |
| POST | `/auth/refresh` | `{refresh_token}` | New token pair (refresh rotation; old token revoked) |
| POST | `/auth/logout` | `{refresh_token}` | `204` |
| GET | `/users/me` | — | Current user |
| PATCH | `/users/me` | `{name?, preferred_language?}` | Updated user |
| DELETE | `/users/me` | `{password}` | `202`: deletes account, farms, scans and stored images (see SECURITY_PRIVACY.md) |

Password rules: at least 8 characters, checked against a common-password list, hashed with Argon2id or bcrypt.

---

## Predictions

### `POST /predictions`
Auth is optional. Anonymous predictions are never persisted.

Headers: `Idempotency-Key: <uuid>` (required)

Multipart fields:
| Field | Type | Notes |
|---|---|---|
| `image` | file | JPEG/PNG/WebP/HEIC, at most 8 MB |
| `source` | `camera` \| `gallery` | Analytics only; does not change processing |
| `save` | bool | Default `false`; ignored if unauthenticated |
| `farm_id` | uuid? | Must belong to the caller |
| `crop` | string? | **[A1]** A crop name from `GET /crops`. Scores are restricted to that crop's classes and renormalised; crop-specific thresholds apply. Omit for "Not sure". |

With `crop` set, the response also has `crop_filter: {crop, applied: true, mismatch: bool}`. `mismatch` is true when the unrestricted model is confident the photo shows a **different** crop. The status is then `uncertain`, and the app asks the farmer to check the crop.

Response `200`:
```json
{
  "id": "uuid-or-null",
  "status": "confident",
  "top_prediction": {
    "class_id": 42,
    "class_key": "tomato___early_blight",
    "crop": "Tomato",
    "disease": "Early blight",
    "is_healthy": false,
    "score": 0.83
  },
  "alternatives": [
    { "class_id": 47, "crop": "Tomato", "disease": "Septoria leaf spot", "score": 0.09 },
    { "class_id": 51, "crop": "Tomato", "disease": "Target spot", "score": 0.03 }
  ],
  "score_explanation": "This score shows how strongly the model matched the photo to this class. It is not a guarantee that the result is correct.",
  "advisory_available": true,
  "model_version": "agrosnap-…",
  "inference_ms": 184,
  "saved": false
}
```

`status` values:
- `confident`: the top score passes the policy threshold.
- `uncertain`: the result is below the threshold. `top_prediction` may still be returned as "possible" with a "Unable to determine reliably" message.
- `unsupported`: the image appears unsuitable (best-effort; see UNCERTAINTY_POLICY.md).

Idempotency: the same key with the same image hash returns the cached response for 10 minutes. The same key with a different image returns `409 IDEMPOTENCY_MISMATCH`.

### `POST /feedback` **[A2]**
Auth optional. Multipart fields:

| Field | Type | Notes |
|---|---|---|
| `verdict` | `correct` \| `wrong` \| `unsure` | Required |
| `predicted_class_id` | int | The class the app showed |
| `correct_class_id` | int? | Only with `wrong`; must exist in the mapping |
| `crop` | string? | The crop the farmer picked |
| `model_version` | string | From the prediction response |
| `share_photo` | bool | Default `false`. The photo is stored only when this is `true` |
| `image` | file? | Required when `share_photo` is `true` |

Response `201`: `{ "id": "uuid", "photo_stored": true }`. Stored photos are used only for retraining and evaluation (see SECURITY_PRIVACY.md).

### `GET /predictions`
Auth required. Returns only the caller's saved predictions, newest first.

### `GET /predictions/{id}`
Auth required, owner only. Includes `image_url` as a short-lived signed URL (about 5 minutes).

### `DELETE /predictions/{id}`
Auth required, owner only. Deletes the rows **and** the stored image. Returns `204`.

---

## Weather

| Method | Path | Query |
|---|---|---|
| GET | `/weather/current` | `lat`, `lon` **or** `farm_id` |
| GET | `/weather/forecast` | `lat`, `lon` **or** `farm_id`; `hourly=true`, `days=7` |

Response always includes:
```json
{
  "location": { "lat": 19.07, "lon": 72.88, "label": "Mumbai, Maharashtra", "source": "farm|device|manual" },
  "fetched_at": "2026-10-23T11:20:00Z",
  "provider": "<name>",
  "current": { "temp_c": 30.1, "humidity_pct": 74, "rain_mm": 0.0, "wind_kph": 12 },
  "alerts": []
}
```
Coordinates are rounded to 2 decimals (about 1 km) before they are sent to the provider. The server caches responses for 15–30 minutes per rounded location.

---

## Farms (auth required, owner only)

| Method | Path | Notes |
|---|---|---|
| GET | `/farms` | List caller's farms |
| POST | `/farms` | `{name, state?, district?, latitude?, longitude?}` |
| GET | `/farms/{id}` | Includes crops |
| PATCH | `/farms/{id}` | Partial update |
| DELETE | `/farms/{id}` | Cascades to farm crops; predictions keep `farm_id = null` |
| GET/POST | `/farms/{id}/crops` | `{crop_name, variety?, sowing_date?, crop_stage?, status}` |
| PATCH/DELETE | `/farms/{id}/crops/{crop_id}` | |

---

## Crops and advisories

### `GET /crops`
Returns the list of crops and classes the model supports, grouped by crop.

### `GET /advisories/{class_id}`
Returns **only reviewed** advisory content:
```json
{
  "class_id": 42,
  "symptoms": "…",
  "prevention": "…",
  "treatment_guidance": "…",
  "sources": [{ "title": "…", "url": "https://…" }],
  "reviewed_by": "…",
  "reviewed_at": "2026-…",
  "disclaimer": "Consult your local KVK or agriculture officer before applying any chemical treatment."
}
```
If no reviewed advisory exists, the endpoint returns `404 NOT_FOUND`, and the app shows generic photo-retake and KVK-contact guidance instead.

---

## Rate limits (initial)

| Endpoint | Limit |
|---|---|
| `POST /predictions` | 10/min per user or IP, 200/day |
| `POST /auth/login` | 5/min per IP + email |
| Weather | 30/min per user or IP |
