# AgroSnap

AgroSnap is an Android-first agricultural app for Indian farmers. A farmer photographs a crop leaf, or picks an existing photo, and AgroSnap's machine-learning model suggests the likely crop disease. The app explains the result in plain English and links to reviewed crop-care guidance. AgroSnap also provides local weather, farm records and scan history.

> **Status:** Pre-MVP. Phase 1 (audit and planning) is in progress. See [PHASES.md](PHASES.md).
>
> **Important:** AgroSnap gives *model-based suggestions*, not confirmed diagnoses. Farmers should check with a local agricultural extension officer or Krishi Vigyan Kendra (KVK) before taking chemical treatment decisions.

---

## Features (MVP scope)

| Area | What it does |
|---|---|
| **Scan** | Has two independent tabs: **Camera** (live capture) and **Photos** (Android system photo picker). Both lead to one preview screen and one prediction pipeline. |
| **Results** | Shows the crop and disease in plain English, with a confidence explanation, alternative predictions, an "Unable to determine reliably" state and links to reviewed guidance. |
| **Weather** | Shows current conditions, hourly and 7-day forecasts and alerts where available. Cached data is clearly labelled with its last update time. |
| **My Farm** | Stores farms, locations, crops, varieties, sowing dates, crop stages and a diary. |
| **Profile** | Covers account settings, language preference, scan history, privacy controls and account deletion. |

Deferred until after the MVP: market prices, government schemes, AI chat, community features, advanced analytics and on-device inference.

## Repository layout

```
AgroSnap/
├── mobile/          React Native + Expo + TypeScript (Expo Router)
├── backend/         FastAPI + TensorFlow inference + SQLAlchemy/Alembic + PostgreSQL
├── ml/              Training notebooks (incl. AgroSnap_Training_v3.ipynb), evaluation scripts, model artifacts (not in Git)
├── docs/            Architecture, API, model card, deployment, testing, security…
├── PHASES.md        Phased implementation plan and checklist
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .env.example
└── README.md
```

## Documentation index

| Document | Purpose |
|---|---|
| [PHASES.md](PHASES.md) | Development phases, tasks and exit criteria |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Git workflow rules, checks, commit style and non-negotiable rules |
| [docs/AUDIT.md](docs/AUDIT.md) | Phase 1 audit checklist and findings template |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow and key technical choices |
| [docs/API.md](docs/API.md) | REST API reference (`/api/v1`) |
| [docs/DATABASE.md](docs/DATABASE.md) | Schema, constraints, indexes and migrations |
| [docs/MODEL_CARD.md](docs/MODEL_CARD.md) | Model selection, metrics, preprocessing and limitations |
| [docs/UNCERTAINTY_POLICY.md](docs/UNCERTAINTY_POLICY.md) | How low-confidence and unsupported results are handled |
| [docs/SCAN_FLOW.md](docs/SCAN_FLOW.md) | Camera/Photos UX, permissions and edge cases |
| [docs/OFFLINE_AND_NETWORK.md](docs/OFFLINE_AND_NETWORK.md) | Poor-network behaviour, retries and caching |
| [docs/UI_UX.md](docs/UI_UX.md) | Design system and screen guidelines |
| [docs/ADVISORY_CONTENT.md](docs/ADVISORY_CONTENT.md) | Rules for disease guidance and source review |
| [docs/SECURITY_PRIVACY.md](docs/SECURITY_PRIVACY.md) | Security controls, data retention and deletion |
| [docs/TESTING.md](docs/TESTING.md) | Automated tests and the real-device manual test plan |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Environments, hosting, APK/AAB builds |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Open decisions and the decision log |
| [docs/I18N.md](docs/I18N.md) | Localisation architecture (English now, Hindi and others later) |

## Quick start (development)

> These commands assume the scaffolding from Phases 2–3 exists. See each sub-project README for details.

### Prerequisites
- Node.js LTS and npm
- Python 3.11 (must match the TensorFlow version used for training; see the model card)
- PostgreSQL 15+ (or Docker)
- Android Studio or a physical Android device with a development build installed

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # fill in local values, never commit .env
alembic upgrade head
# place the production model artifact at the path set in MODEL_PATH
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open `http://localhost:8000/docs` for the interactive API docs.

### Mobile
```bash
cd mobile
npm install
cp .env.example .env             # only EXPO_PUBLIC_API_BASE_URL; no secrets here
npx expo start
```
Test camera and photo-picker flows on a **physical Android device**. Emulators are not sufficient for acceptance.

### Tests
```bash
cd backend && pytest
cd mobile && npm test && npx tsc --noEmit
```

## Definition of done (MVP)

The MVP is complete only when **all** of the following are verified and recorded in [docs/TESTING.md](docs/TESTING.md):

1. Camera capture works.
2. Gallery photo selection works independently of camera permission.
3. Both image sources produce predictions through the same backend endpoint.
4. Model preprocessing and class mapping have been verified against the notebook.
5. Uncertain predictions are handled responsibly.
6. Weather shows the correct selected location and its update time.
7. Authentication and private-data access controls have been tested.
8. The Android app builds and installs successfully.
9. Core flows have been tested on a real Android phone.
10. Setup, testing, deployment and known limitations are documented.

## Known limitations

- Disease detection **requires an internet connection**. There is no on-device inference in the MVP.
- The model recognises only the 99 classes listed in the model card. Other crops and diseases may be misclassified.
- Confidence scores are model outputs, not guaranteed probabilities of correctness.
- Out-of-distribution detection, such as for non-leaf photos, is best-effort only.

## License

_To be decided. See [docs/DECISIONS.md](docs/DECISIONS.md)._
