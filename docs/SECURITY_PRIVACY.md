# Security and Privacy

## 1. Secrets

- Secrets live only in backend environment variables or the host's secret manager. Never commit `.env` files. `.gitignore` includes `.env*` except `.env.example`.
- The mobile app contains **no secrets**. Its only configuration is `EXPO_PUBLIC_API_BASE_URL`. Anything prefixed `EXPO_PUBLIC_` is visible in the APK.
- The weather provider key is used only by the backend proxy.
- Add secret scanning (for example gitleaks) to CI.

## 2. Authentication

- Passwords are hashed with Argon2id (or bcrypt cost ≥ 12).
- JWT access tokens last 15 minutes. Refresh tokens last 30 days, are rotated on every use, and are stored hashed server-side.
- On the device, tokens are stored with `expo-secure-store` and never in AsyncStorage.
- Login is rate-limited, and errors are generic ("Email or password is incorrect").

## 3. Authorisation and ownership

- Every farm, farm-crop, prediction and image query is filtered by `user_id = current_user.id` in the repository/service layer.
- Accessing another user's resource returns **404**, not 403, so that its existence is not revealed.
- `farm_id` supplied with a prediction must belong to the caller.
- Automated tests create two users and assert cross-access failures for **every** private route (TESTING.md §Auth).

## 4. Uploads

- Maximum size 8 MB, checked before the full body is read where possible.
- Type is checked by magic-byte sniffing, not by file extension or the client-supplied `Content-Type`.
- Decoding uses Pillow with `Image.MAX_IMAGE_PIXELS` set (decompression-bomb protection).
- EXIF metadata, including GPS, is **stripped** before an image is stored.
- Uploaded files are never executed or served from a public path.

## 5. Image storage and retention

| Case | Image stored? | DB row? |
|---|---|---|
| Anonymous prediction | No (in memory only) | No |
| Signed in, "Save to history" off | No | No |
| Signed in, "Save to history" on | Yes, private bucket | Yes |

- The bucket is private. Access uses signed URLs that expire in 5 minutes.
- Object keys are random UUIDs with no user names or emails.
- Default retention: saved scans are kept until the user deletes them or their account (confirm in DECISIONS.md). An optional auto-delete period can be added later.
- Model-improvement use: scan images are **not** used for training unless the user gives a separate, explicit opt-in (not part of the MVP).

## 6. Deletion

- **Delete scan:** removes the `predictions` and `prediction_candidates` rows and the stored object, then returns 204. A failed object deletion is retried by a background job and logged.
- **Delete account** (Profile → Privacy → Delete account): requires the password, marks the user deleted, revokes all tokens, deletes farms, crops, predictions and images, and completes within 30 days (target: immediately). Confirm with an on-screen message.
- Provide an explanatory web page for deletion requests, as required by Google Play's account-deletion policy.

## 7. Location privacy

- Location permission is requested **only** when the user taps "Use my location" for weather or a farm, and only foreground "while using the app" permission.
- Manual selection (state/district search or map pin) is always available.
- Coordinates are rounded to about 1 km before being sent to the weather provider.

## 8. Transport and infrastructure

- HTTPS only in deployed environments, with HSTS. Android cleartext traffic is disabled in release builds.
- CORS is not needed for the native app. Restrict it if a web client is added.
- The database is not publicly reachable, connections use TLS, and the app's DB role has least privilege.
- Logs must not contain images, tokens, passwords or precise coordinates.

## 9. Play Store compliance

- The Data Safety form must match actual behaviour (photos, approximate/precise location, email, name).
- A privacy policy URL is required.
- The final merged manifest is reviewed to remove unneeded permissions (see SCAN_FLOW.md §3).

## 10. Model safety

- Results are never labelled as confirmed diagnoses (UNCERTAINTY_POLICY.md).
- Advisory content follows ADVISORY_CONTENT.md.
