# UI/UX Guidelines

**Direction:** modern agricultural technology that is clean, welcoming and readable outdoors. Simplicity comes before density.

## 1. Design tokens (`mobile/src/theme/tokens.ts`)

### Colour
| Token | Value | Use |
|---|---|---|
| `primary` | `#2E7D32` | Primary buttons, selected tab, key icons |
| `primaryDark` | `#1B5E20` | Pressed state, headers |
| `primaryContainer` | `#E3F1E4` | Selected chips, light highlights |
| `background` | `#FAF8F3` | Warm off-white screen background |
| `surface` | `#FFFFFF` | Cards |
| `text` | `#1C1F1A` | Body text |
| `textMuted` | `#5B6157` | Secondary text (still ≥ 4.5:1 on background) |
| `border` | `#E3E1DA` | Card and input borders |
| `warning` | `#B26A00` | Uncertain results, stale data |
| `error` | `#B3261E` | Errors |
| `info` | `#1565C0` | Links, info notes |

Verify every text/background pair for WCAG AA contrast (4.5:1 for body, 3:1 for large text). Do not use colour alone to signal status. Always add an icon and text.

### Typography
| Style | Size / line height | Weight |
|---|---|---|
| Display | 28 / 34 | 700 |
| Title | 22 / 28 | 600 |
| Heading | 18 / 24 | 600 |
| Body | 16 / 24 | 400 |
| Label | 14 / 20 | 500 |
| Caption | 13 / 18 | 400 |

The minimum body size is 16. Respect the system font scale and test at 130%.

### Spacing and shape
- Spacing scale: 4, 8, 12, 16, 24, 32.
- Screen padding: 16. Card radius: 16. Button radius: 12.
- Shadows: subtle elevation 1–2 only.
- Touch targets: at least 48 × 48 dp; primary actions 56 dp high.

## 2. UI library
Use **React Native Paper (MD3)**, themed with the tokens above. It gives accessible, consistent components quickly. (NativeWind is an alternative; record the choice in DECISIONS.md and do not mix both.)

## 3. Component inventory
`Button` (primary / secondary / text), `Card`, `ScreenContainer`, `SegmentedTabs` (Camera | Photos), `ImagePreview`, `ResultCard`, `ConfidenceBadge`, `WeatherSummary`, `StaleBadge`, `EmptyState`, `ErrorState`, `LoadingState`, `OfflineBanner`, `FormField`.

## 4. Screen guidelines

### Home
Greeting with the farm name and location → weather summary card (with update time) → large **"Scan a Leaf"** button → up to 3 recent scans → reminders. No more than 5 blocks in total.

### Scan
- Segmented **[ 📷 Camera ] [ 🖼 Photos ]** control at the top. The selected tab is filled green and the other is outlined.
- The camera viewfinder takes most of the screen, with a framing guide.
- The Photos tab has a centred illustration, a "Choose a photo" button and 3 photo tips.
- The Review screen is identical for both sources.

### Result
1. Status header (confident / uncertain / unsupported) with icon and colour.
2. Crop and disease in plain English (for example "Tomato — Early blight").
3. Confidence band and explanation line.
4. "Other possibilities" (collapsed by default when confident).
5. Guidance sections: Symptoms · Prevention · What to do. Each lists its source and review date.
6. A "Consult your local KVK" note.
7. Actions: Save to history · Scan again.

### Weather
Location label with a change control → current conditions → hourly strip → 7-day list → alerts. "Updated …" stays visible.

### My Farm / Profile
Simple lists and forms. Empty states explain what to add and why.

## 5. Writing style
- Plain English, short sentences, no ML jargon ("model", "softmax", "inference" never appear in the UI).
- Error messages say what happened **and** what to do next.
- Use "possible" or "likely", never "diagnosed".

## 6. States checklist (every screen)
Loading · Empty · Error (with retry) · Offline · Success. Use skeleton loaders for lists. Keep animations at or below 200 ms and respect "reduce motion".

## 7. Accessibility
- Every icon button has an `accessibilityLabel`.
- Images have descriptive labels ("Selected leaf photo").
- Logical focus order and TalkBack tested on the Scan and Result screens.

## 8. Device testing
Test on at least one small (≈5.5"), one mid and one large (≈6.7") Android phone, in bright outdoor light.

## 9. Motion, press feedback and haptics

These rules follow the `animate-expo` skill from [emilkowalski/skills](https://github.com/emilkowalski/skills).

| Situation | Rule for AgroSnap |
|---|---|
| Bottom-tab switches, Camera ↔ Photos tab switch | **No animation** (used many times a day; tabs never slide) |
| Button / card press | `scale: 0.97` over 100–150 ms on press-in; commit on press-out |
| Toggles, chips | 150–200 ms, ease-out |
| Sheets / modals (e.g. location picker) | Expo Router `presentation: 'formSheet'`, spring ≈300 ms |
| Screen transitions | Native stack defaults, never hand-rolled |
| Result card appearing | Fade + scale from 0.95, ≤ 250 ms, ease-out. Never start from `scale(0)` |
| Lists (history, farms) | No `entering` animation on virtualised rows |

- Use Reanimated, which keeps work on the UI thread. Animate only `transform` and `opacity`, never `height`/`width`/`margin`/Android `elevation`.
- Never use ease-in for UI motion. Keep UI animations under 300 ms.
- Haptics (`expo-haptics`): `impactAsync(Light)` on capture; `notificationAsync(Success)` when a result arrives; `notificationAsync(Error)` on failure. One haptic per action, never the only feedback.
- Reduced motion: respect `useReducedMotion()`. Keep opacity and colour changes; drop scale and translation.
- Judge feel in a **release build on the slowest test phone**, not in Expo Go or an emulator.

## 10. Worst-case data checks

Following the `break-ui` skill, test every screen with realistic extremes before Phase 7 sign-off:

- Long crop and disease names (e.g. "Tomato — Spider mites (two-spotted spider mite)"), long farm and village names, and long translated Hindi labels.
- Long email addresses on Profile.
- Empty states: no farms, no scans, no reviewed advisory, no weather yet.
- Single item and very long lists (≈1,000 saved scans).
- Missing optional fields: no variety, no sowing date, no location.
- Broken or expired image URLs in history.
- Timestamps: "just now", yesterday, more than a year ago; weather older than 24 h.
- Numbers: 0 % and 100 % confidence, negative temperatures, 0 mm and 300 mm rainfall.
- A 320 dp-wide screen and 200 % font scale.

Record each break as Broken / Ugly / Fragile with a proposed fix.
