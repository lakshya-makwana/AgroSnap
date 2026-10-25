# Deployment

## 1. Environments

| Env | Backend | Database | Storage | Mobile build |
|---|---|---|---|---|
| local | `uvicorn --reload` | Docker Postgres | MinIO (Docker) or local folder | Expo dev build |
| staging | Container host | Managed Postgres | Private S3-compatible bucket | EAS `preview` profile (APK) |
| production | Container host (separate service) | Managed Postgres with backups | Private bucket with lifecycle rules | EAS `production` profile (AAB) |

Hosting provider: see DECISIONS.md. Prefer a region in or near India (for example Mumbai) for latency. TensorFlow inference needs at least about 1–2 GB RAM, depending on the chosen model, so measure it in Phase 1.

## 2. Backend container

- Base image: `python:3.11-slim`. Match the TensorFlow version used in training (pin it in `requirements.txt`).
- Use `tensorflow-cpu` if no GPU is used, which gives a smaller image.
- Run with `gunicorn -k uvicorn.workers.UvicornWorker -w <N>`. Each worker loads its own model copy, so size `N` to the available RAM.
- `/api/v1/health` is the container health check.
- Run `alembic upgrade head` as a release step before traffic switches.

## 3. Model artifact delivery

- **Not committed to Git.** Upload `model.keras`, `class_mapping.json` and `model_meta.json` to a private artifacts bucket under `models/<model_version>/`.
- The backend downloads them at start-up (or the image bakes them in at build time) and **verifies the SHA-256** against `MODEL_SHA256`. If the checksum does not match, startup fails.
- Rollback means pointing `MODEL_VERSION` back to the previous folder.

## 4. Environment variables (backend)

| Variable | Example | Notes |
|---|---|---|
| `APP_ENV` | `production` | |
| `DATABASE_URL` | `postgresql+psycopg://…` | secret |
| `JWT_SECRET` | random 64 bytes | secret |
| `JWT_ACCESS_TTL_MIN` | `15` | |
| `JWT_REFRESH_TTL_DAYS` | `30` | |
| `MODEL_PATH` | `/models/current/model.keras` | |
| `MODEL_VERSION` | `agrosnap-…` | |
| `MODEL_SHA256` | `…` | |
| `CLASS_MAPPING_PATH` | `/models/current/class_mapping.json` | |
| `UNCERTAINTY_T_CONF` / `UNCERTAINTY_M_MIN` | from MODEL_CARD | |
| `MAX_UPLOAD_MB` | `8` | |
| `STORAGE_ENDPOINT` / `STORAGE_BUCKET` / `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` | | secrets |
| `WEATHER_PROVIDER` / `WEATHER_API_KEY` | | secret, if the provider needs one |
| `RATE_LIMIT_STORAGE_URL` | `redis://…` (optional) | |
| `SENTRY_DSN` | optional | |

A template is in `/.env.example`.

## 5. Mobile builds (EAS)

`mobile/eas.json` profiles:

| Profile | Output | Use |
|---|---|---|
| `development` | Dev client APK | Daily development on a physical phone |
| `preview` | APK, staging API URL | Internal testers |
| `production` | AAB, production API URL | Play Store |

```bash
cd mobile
npx eas build --profile preview --platform android
npx eas build --profile production --platform android
```

- Set `EXPO_PUBLIC_API_BASE_URL` per profile in `eas.json` `env`.
- Keystore: let EAS manage it, and back up the credentials. **Losing the upload key blocks updates.**
- Increment `android.versionCode` for every store build.
- Before release: inspect the merged manifest permissions (see SCAN_FLOW.md §3).

## 6. Play Store release checklist

- [ ] Internal testing track with real testers.
- [ ] Data Safety form completed and accurate.
- [ ] Privacy policy URL and account-deletion URL published.
- [ ] Content rating questionnaire completed.
- [ ] Target API level meets the current Play requirement.
- [ ] Screenshots from real devices.

## 7. Operations

- Back up the database daily (managed backups) and test a restore once before launch.
- Monitor error rate, p95 inference latency, 5xx count and memory use.
- Log every prediction's model version and status (no images, no precise location) for quality monitoring.
