# Offline and Poor-Network Handling

Many farmers have weak or intermittent connections. AgroSnap must stay understandable and must never lose the farmer's photo because of a network failure.

> **Disease detection requires the internet in the MVP.** The app must never claim offline detection unless an on-device model has been built and tested (deferred; see PHASES.md).

## 1. Network detection

- Use `@react-native-community/netinfo` for connectivity, and also treat request timeouts as "offline-like".
- A global `OfflineBanner` reads: "You're offline. Some features are unavailable."
- Do not block the UI on NetInfo alone. Sometimes it reports "connected" while requests still fail.

## 2. Disease detection

| Situation | Behaviour |
|---|---|
| Offline before tapping Detect | Button shows "Detect Disease (needs internet)". Tapping shows: "Online disease detection is unavailable. Your photo is kept. Try again when you have a connection." |
| Request times out | Timeout 30 s for the upload; message + **Try again** using the same file and idempotency key |
| 5xx / 503 | "Our service is busy. Please try again." + Retry |
| 429 | "Too many scans in a short time. Please wait N seconds." |
| Retry | Automatic retry once with backoff for network errors only, then manual. Never auto-retry 4xx. |
| Photo persistence | The normalised image stays in the app cache until the scan finishes or the user discards it. It survives an app restart for the pending scan (optional; Phase 4.9). |

The idempotency key guarantees that a retry after a lost response does not create a duplicate saved scan.

## 3. Weather caching

- Cache the last successful response per location (TanStack Query persisted to AsyncStorage, or MMKV).
- Always show **"Updated <relative time> (<local time>)"** next to the weather.
- If data is older than 1 hour, or the fetch failed, show a **"Not current"** badge, a muted style and "Showing last saved weather from …".
- Never hide the timestamp, and never show cached data without the stale indicator when it is stale.
- Data older than 24 hours is not shown as weather, only as: "Weather unavailable. Last update was more than a day ago."

## 4. Other data

| Data | Offline behaviour (MVP) |
|---|---|
| Farm list and crops | Read from the query cache if available; edits are disabled offline with a message (no offline write queue in the MVP) |
| Scan history | Cached list shown with a "may be out of date" note; images may not load |
| Advisories | Previously viewed advisories may be shown from cache, labelled with their review date. A full offline crop-care library is deferred. |
| Login | Needs a connection. Existing sessions continue with cached data. |

## 5. Bandwidth care

- Upload only the normalised JPEG (≤ 1600 px long edge), usually a few hundred KB.
- Use thumbnails for history lists (generated server-side) and load full images only on the detail screen.
- Avoid polling. Refresh weather when the screen is focused, at most every 15 minutes.

## 6. Testing

See TESTING.md §Network: airplane mode, Android developer-options network throttling, and toggling connectivity mid-upload.
