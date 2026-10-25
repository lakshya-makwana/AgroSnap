# Testing

Testing has two layers: **automated** (backend, ML parity, mobile unit tests) and **manual on real Android devices**. A Definition-of-Done item counts only when its evidence is recorded here.

## 1. Automated — backend (`pytest`)

| Area | Tests |
|---|---|
| Health | `/health` returns ok; reports `model_loaded` |
| Model info | Version, class count = 99, input size match the artifact |
| Class mapping | Mapping has 99 unique indices 0–98; keys match the `disease_classes` seed; model output dim = 99 |
| Preprocessing | Known input → expected tensor (shape, dtype, min/max, checksum) |
| **Parity** | For a fixed fixture set (≥ 20 images across classes), API top-3 = notebook top-3; scores within `abs_tol = 1e-4` (tolerance documented) |
| Image validation | Empty, truncated JPEG, text file renamed `.jpg`, 9 MB file, 1×1 px, PNG with alpha, rotated EXIF, HEIC → correct 4xx codes, never 500 |
| Uncertainty | Mocked scores produce the expected status for boundary values |
| Idempotency | Same key + same image → same response, one DB row; same key + different image → 409 |
| Rate limit | Exceeding the limit → 429 with `Retry-After` |
| Auth | Register, login, refresh rotation, reuse of old refresh token rejected, logout |
| **Ownership** | User B gets 404 on User A's farms, crops, predictions and image URLs for GET/PATCH/DELETE |
| Deletion | Deleting a scan removes rows and calls storage delete; deleting an account removes everything |
| Advisories | Draft/unreviewed advisories are never returned |
| Weather | Provider mocked; response includes location + `fetched_at`; provider failure → 503 |

Run: `cd backend && pytest -q --cov=app`. CI target: ≥ 80% coverage on `services/`.

## 2. Automated — ML (`ml/evaluation/`)

- `evaluate.py --model <path> --split test` writes metrics JSON, per-class CSV and a confusion-matrix PNG to `ml/evaluation/reports/<model_version>/`.
- `export_parity_fixtures.py` stores the notebook's top-k outputs for the fixture images (used by the backend parity test).

## 3. Automated — mobile

- `npx tsc --noEmit` and `npx eslint .`
- Jest + React Native Testing Library:
  - `normaliseImage` (dimension and size logic, with mocked manipulator)
  - `usePrediction` (single request on double tap; retry reuses the key)
  - Result screen renders confident/uncertain/unsupported correctly
  - Weather card shows the "Not current" badge for stale data
  - No hard-coded strings (lint rule or i18n key check)

## 4. Manual — real-device test plan

Record each run: date, tester, device model, Android version, build number, pass/fail, notes or screenshot.

### Devices (minimum)
| # | Device | Android | Screen |
|---|---|---|---|
| D1 | | 10–11 | small |
| D2 | | 13 | mid |
| D3 | | 14+ | large |

### Scan — permissions and sources
| ID | Steps | Expected | D1 | D2 | D3 |
|---|---|---|---|---|---|
| S1 | Fresh install → Scan → Photos → choose photo | System picker opens; **no permission dialog**; Review shows image | | | |
| S2 | Fresh install → Camera tab → **Deny** → Photos → choose photo → Detect | Photos flow works fully with camera denied | | | |
| S3 | Camera tab → Allow → capture | Preview, capture, Review shows upright photo | | | |
| S4 | Camera denied permanently → Camera tab | "Open settings" and "Use Photos instead" shown and work | | | |
| S5 | Photos → open picker → back/cancel | No error; stays on tab | | | |
| S6 | Review → Retake / Choose another | Returns to correct source; new image replaces old | | | |
| S7 | Pick a > 15 MB photo | Upload succeeds (downscaled) | | | |
| S8 | Pick a HEIC photo (if available) | Succeeds or shows a clear message | | | |
| S9 | Same leaf photo via camera vs gallery copy | Same endpoint; consistent result | | | |
| S10 | Tap Detect rapidly 5× | One request (check server logs) | | | |
| S11 | Check the installed app's permissions in Settings | Only Camera (and Location if used); no "Photos and videos" | | | |

### Results
| ID | Steps | Expected |
|---|---|---|
| R1 | Clear diseased-leaf photo of a supported class | Confident result, plain-English names, explanation line, guidance with source |
| R2 | Blurry or dark photo | Uncertain/unsupported with tips |
| R3 | Photo of a chair or face | Not presented as a confident disease (record actual behaviour honestly) |
| R4 | Save to history → view → delete | Appears in history; deletion removes it |

### Network
| ID | Steps | Expected |
|---|---|---|
| N1 | Airplane mode → Detect | Offline message; image kept |
| N2 | Re-enable network → Try again | Succeeds without re-selecting |
| N3 | Disable network mid-upload | Clean failure + Retry; no duplicate saved scan |
| N4 | Throttle network (2G/slow 3G) → full scan | Usable; progress visible |
| N5 | Load weather → go offline → reopen later | Cached weather with "Updated …" and "Not current" |

### Weather and farm
| ID | Steps | Expected |
|---|---|---|
| W1 | First launch | No location prompt at start |
| W2 | Weather → Use my location → Allow | Correct place name shown |
| W3 | Deny location → choose manually | Manual location works |
| W4 | Switch between two farms | Weather location label changes accordingly |
| F1 | Create/edit/delete farm and crop | Persists after app restart |

### Auth and privacy
| ID | Steps | Expected |
|---|---|---|
| A1 | Register, log out, log in | Works; tokens not visible in AsyncStorage dump |
| A2 | Two accounts on two phones | Neither sees the other's data |
| A3 | Delete account | Data gone; login fails |

## 5. Definition of Done evidence

| # | Item | Evidence (link / test ID / date) | Status |
|---|---|---|---|
| 1 | Camera capture works | S3 | ☐ |
| 2 | Gallery works independently of camera permission | S1, S2, S11 | ☐ |
| 3 | Both sources use the same backend | S9 + API logs | ☐ |
| 4 | Preprocessing and class mapping verified | Parity test run | ☐ |
| 5 | Uncertain predictions handled responsibly | R2, R3, uncertainty tests | ☐ |
| 6 | Weather shows correct location and update time | W2–W4, N5 | ☐ |
| 7 | Auth and private access tested | Ownership tests, A1–A3 | ☐ |
| 8 | Android app builds and installs | EAS build ID | ☐ |
| 9 | Core flows tested on a real phone | Device table above | ☐ |
| 10 | Setup, testing, deployment, limitations documented | Docs review | ☐ |
