# AgroSnap Backend

FastAPI service for disease prediction, auth, farms, weather proxy and advisories.

## Stack
Python 3.11 · FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · PostgreSQL · TensorFlow/Keras (CPU) · Pillow (+ pillow-heif)

## Layout
```
app/
├── main.py          app factory; lifespan loads the model once
├── api/v1/          routers
├── core/            config, security, logging, rate limiting
├── db/              session, base
├── models/          ORM models
├── schemas/         Pydantic schemas
└── services/        model_registry, image_validation, preprocessing, inference, storage, weather
alembic/
scripts/             seed_disease_classes.py, load_advisories.py
tests/
└── fixtures/        parity images + expected notebook outputs (small, committed)
```

## Run locally

**Status (2026-10-24):** health, model-info, crops, predictions (with crop filter and idempotency), feedback and weather are implemented and tested. Auth, farms, history, advisories, Alembic migrations and rate limiting are not built yet (Phases 5–7). The database is SQLite by default (`DATABASE_URL` switches to PostgreSQL).

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pip install -r requirements-ml.txt                      # only to serve a real model

# A) Before the model is trained: demo model (fake results, clearly labelled in every response)
DEMO_MODEL=true CLASS_MAPPING_PATH=demo/class_mapping.json uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# B) With the trained bundle: copy best_models_v3/production/* into ../ml/artifacts/
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On Windows PowerShell set the variables first: `$env:DEMO_MODEL="true"; $env:CLASS_MAPPING_PATH="demo/class_mapping.json"`.

## Model bundle [A6]
The backend serves either `model.tflite` (compressed, via LiteRT or `tf.lite.Interpreter`) or `model.keras`, whichever `model_meta.json` names. It also reads from that file:
- `inference.tta_hflip`: average with the horizontal flip, because calibration was fitted that way.
- `calibration.temperature`, `uncertainty.T_conf / M_min / T_conf_crop / M_min_crop`.
- `sha256`: startup fails if the model file does not match.

To reach the API from a phone on the same Wi-Fi, use your computer's LAN IP in the mobile `EXPO_PUBLIC_API_BASE_URL` (for example `http://192.168.1.20:8000/api/v1`). Allow cleartext only in development builds.

## Tests
```bash
pytest -q
pytest tests/test_parity.py -v   # requires the model artifact at MODEL_PATH
```

## Notes
- The model loads once at startup. If it fails to load or the checksum does not match, the app fails fast.
- TensorFlow calls run in a threadpool behind a concurrency semaphore.
- See `../docs/API.md`, `../docs/DATABASE.md` and `../docs/SECURITY_PRIVACY.md`.
