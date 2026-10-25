# AgroSnap Mobile (Android)

React Native + Expo SDK 58 + TypeScript, with Expo Router (routes in `src/app/`).

## Screens
| Route | What it does |
|---|---|
| `(tabs)/index` | Home: greeting, weather summary, **Scan a Leaf**, photo tips |
| `(tabs)/scan` | **[A1]** crop picker → **[ Camera ] [ Photos ]** tabs |
| `review` | Shared preview → **Detect Disease** (one idempotency key per photo, retry reuses it) |
| `result` | Status, match band, alternatives, crop-mismatch warning, **[A3] Listen**, **[A2] Was this correct?**, KVK note |
| `(tabs)/weather` | Current, 24 h, 7 days; device location on tap or a city; "Updated …" + "Not current" |
| `(tabs)/farm` | Empty state until accounts exist (Phase 6/7) |
| `(tabs)/profile` | **[A4]** English / हिन्दी, **[A5]** high contrast + large text, model version and compression size |

## Key libraries
| Purpose | Library |
|---|---|
| Navigation | `expo-router` |
| UI | In-house components on the `docs/UI_UX.md` tokens (`src/components/ui.tsx`, ADR-009) |
| Text-to-speech [A3] | `expo-speech` |
| Camera | `expo-camera` (`CameraView`, `useCameraPermissions`) |
| Gallery | `expo-image-picker` (`launchImageLibraryAsync`, system photo picker) |
| Image normalisation | `expo-image-manipulator` |
| Image display | `expo-image` |
| Secure tokens | `expo-secure-store` |
| Location (on demand) | `expo-location` |
| Network status | `@react-native-community/netinfo` |
| Haptics | `expo-haptics` |
| Server state | `@tanstack/react-query` |
| Local state | `zustand` |
| i18n | `i18next`, `react-i18next`, `expo-localization` |

## Setup
```bash
npm install
cp .env.example .env    # EXPO_PUBLIC_API_BASE_URL only
npx expo prebuild --platform android   # only if inspecting native config
npx eas build --profile development --platform android   # install the dev client on your phone
npx expo start --dev-client
```

Expo Go may not reflect the exact permissions of a production build. Use a **development build** to test camera and photo-picker permissions.

## Permissions policy
- `CAMERA`: requested only when the Camera tab opens.
- Photos: system photo picker, **no media-library permission** requested for selection.
- Location: foreground only, requested only when the user taps "Use my location".
- After every dependency change, check the merged manifest:
  `npx expo prebuild --platform android --clean` and inspect `android/app/src/main/AndroidManifest.xml` (or the APK's manifest). Remove unwanted permissions with `android.blockedPermissions` in `app.json`.

## Scripts
```bash
npm test            # jest
npx tsc --noEmit    # types
npx eslint .        # lint
```

See `../docs/SCAN_FLOW.md`, `../docs/UI_UX.md`, `../docs/OFFLINE_AND_NETWORK.md`.

## Design-engineering skills (for Claude Code / AI agents)

Install the skills from [emilkowalski/skills](https://github.com/emilkowalski/skills) in this repo:

```bash
npx skills@latest add emilkowalski/skills
```

The ones relevant to AgroSnap:
- `animate-expo`: motion, gestures, sheets and haptics in Expo (rules summarised in `docs/UI_UX.md` §9)
- `review-animations` / `improve-animations`: audit motion before each release
- `animation-performance`: fix dropped frames on low-end phones
- `break-ui`: worst-case data testing (`docs/UI_UX.md` §10)
- `find-animation-opportunities`: decide where motion helps and where it should stay out

These are web-oriented (`apple-design`, `mobile-native`, `ask-sonner`, `pick-ui-library`) or iOS-only (`write-swift`), so skip them for this Android Expo app.

Packages implied by those rules: `react-native-reanimated`, `react-native-gesture-handler` (wrap the app in `GestureHandlerRootView`), `expo-haptics`. Install them with `npx expo install` so the versions match the SDK.
