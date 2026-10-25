# Scan Flow — Camera and Photos

This is the core MVP feature. Camera and Photos are **independent**, and both lead to the **same** Image Review screen and prediction call.

## 1. Screen flow

```
Scan screen
├── [ Camera ]  ──capture──┐
│                          ├──▶ Image Review ──Detect Disease──▶ Uploading… ──▶ Result
└── [ Photos ]  ──select───┘        │                                  │
                                    └─ Retake / Choose another         └─ Error → Retry (same image)
```

The selected tab is obvious: a filled green background with a white label and icon. The unselected tab is outlined. Tabs are at least 48 dp high.

## 2. Camera tab

| Step | Behaviour |
|---|---|
| Tab opened | Check permission status with `useCameraPermissions()` (expo-camera). **Only now** is camera permission requested, if it is undetermined. |
| Granted | Live `CameraView` preview, large capture button (≥ 72 dp), switch-camera (if more than one camera), torch toggle (if supported), and a framing guide overlay ("Fill the frame with one leaf"). |
| Capture | `takePictureAsync({ quality: 0.85 })` → normalise → navigate to Review with `source: "camera"`. |
| Denied, can ask again | Explanation + "Allow camera" button. |
| Denied permanently | Explanation + **"Open settings"** (`Linking.openSettings()`) + **"Use Photos instead"**, which switches tabs. |
| No camera / error | "Camera is not available on this device" + "Use Photos instead". |
| Leaving tab / app background | Pause or unmount the preview to save battery and release the camera. |

## 3. Photos tab

| Step | Behaviour |
|---|---|
| Tab opened | Shows a "Choose a photo" button and short tips. It does not auto-open the picker on every tab switch. |
| Tap Choose | `ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], allowsMultipleSelection: false, quality: 1 })`. On supported Android versions this opens the **system photo picker**, which needs no media-library permission. |
| Permissions | Do **not** call `requestMediaLibraryPermissionsAsync()` for selection. Do **not** declare `READ_MEDIA_IMAGES` / `READ_EXTERNAL_STORAGE` unless testing shows that a supported device needs them. Verify the final merged `AndroidManifest.xml`. |
| Cancelled | Stay on the Photos tab silently, with no error. |
| Selected | Normalise → navigate to Review with `source: "gallery"`. |
| Unsupported type | "This file type isn't supported. Please choose a JPEG or PNG photo." |
| Works with camera denied | **Required.** No code path in Photos checks or depends on camera permission. |

> Confirm the picker behaviour, and which permissions the build actually declares, on physical devices across Android versions (for example Android 10, 12 and 14). Record the results in TESTING.md.

## 4. Client-side image normalisation (shared)

Implemented once in `src/features/detection/normaliseImage.ts` with `expo-image-manipulator`:

1. Read width/height. Reject images whose shorter side is below 224 px ("Photo is too small").
2. Apply EXIF orientation.
3. Downscale so the long edge is at most 1600 px. Never upscale.
4. Re-encode as JPEG at about 0.85 quality. This also converts HEIC/PNG/WebP to JPEG.
5. If the result is still larger than 8 MB, reduce quality once more, then fail with a clear message.

The server repeats all validation. Client normalisation only reduces upload size and HEIC risk.

## 5. Image Review screen (shared)

- A large preview (`contentFit="contain"`) with the same layout for both sources.
- Secondary button: **"Retake"** when the source is camera, **"Choose another photo"** when it is gallery.
- Primary button: **"Detect Disease"**, full width.
- While uploading: the button is disabled, a spinner and "Checking your photo…" are shown, and a Cancel option is available.
- On error: an inline error card, with **"Try again"** reusing the same normalised file URI and idempotency key.

## 6. Duplicate-request prevention

- Generate one `Idempotency-Key` per selected image when Review opens.
- Disable "Detect Disease" while a request is in flight and guard against double taps in the mutation hook.
- Choosing a new image creates a new key.
- The server deduplicates on the key (API.md).

## 7. Edge cases checklist

| Case | Expected |
|---|---|
| Camera denied, Photos used | Works fully |
| Picker cancelled | No error, stays on tab |
| 20+ MB photo | Downscaled on device; uploads succeed |
| HEIC photo | Converted to JPEG; succeeds, or a clear message appears if the device cannot decode it |
| Screenshot / non-leaf image | Prediction runs; likely `uncertain` or `unsupported` |
| Rotated photo | Displayed and analysed upright |
| App backgrounded during upload | Request completes or fails cleanly; Retry available |
| Offline when tapping Detect | Offline message; image kept; Retry when back online |
| Rapid double tap | Exactly one request |
