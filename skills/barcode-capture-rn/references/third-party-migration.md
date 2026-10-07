# Third-Party Scanner → BarcodeCapture Migration (React Native)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- **Which library** (imports and `package.json`):
  - **react-native-vision-camera v4** — `useCodeScanner({ codeTypes, onCodeScanned })`, `<Camera codeScanner={...} />`.
  - **react-native-vision-camera v5** + `react-native-vision-camera-barcode-scanner` — `useBarcodeScannerOutput({ barcodeFormats, onBarcodeScanned })`, `<Camera outputs={[output]} />`, `useBarcodeScanner(...).scanCodesInImageAsync(image)` for still images.
  - **expo-camera** — `<CameraView onBarcodeScanned barcodeScannerSettings={{ barcodeTypes }} />`, `scanFromURLAsync` for still images.
- Which formats are enabled, what the scan callback does with each result (dedupe, list, navigation, one-shot "scanned" flag), and how the camera is driven (permission, torch, facing, active/focus handling, region of interest, still-image path).
- The installed Scandit SDK version (`scandit-react-native-datacapture-*` in `package.json`; none yet means the latest).

All three sources report **several codes per callback** (an array) and BarcodeCapture reports **one**: `session.newlyRecognizedBarcode` is a single `Barcode | null`. Never loop over a `barcodes` array; if the app genuinely needs every visible code per frame, use `matrixscan-batch-rn` instead.

**Which Scandit surface.** On SDK 8.6.x use `DataCaptureView` + `BarcodeCapture` + `BarcodeCaptureOverlay` (this guide's default; `references/integration.md` has the details). From SDK 8.7 the all-in-one `BarcodeCaptureAioView` is an option that owns the camera and its lifecycle (see **SDK 8.7+: BarcodeCaptureAioView**); 8.6.x ships the same component as `BarcodeCaptureView` and 8.7 renamed it, so prefer `DataCaptureView` on 8.6. Do not mix the two.

---

## Remove

- The third-party packages from `package.json` once nothing imports them (the still-image path migrates too, see **Still images**): `react-native-vision-camera`, `react-native-vision-camera-barcode-scanner`, `react-native-nitro-image` (only if nothing else uses it), `expo-camera`.
- The imports, the scanner hook / output (`useCodeScanner`, `useBarcodeScannerOutput`, `useBarcodeScanner`), the camera component and its scanner prop (`codeScanner`, `outputs`, `onBarcodeScanned`, `barcodeScannerSettings`), and the library's permission hook.
- Any UI specific to the old scanner (hand-drawn highlight boxes from `corners` / `bounds`). `BarcodeCaptureOverlay` replaces them. Keep the surrounding app UI (lists, summaries, buttons).

## Integrate BarcodeCapture

Follow `references/integration.md`. The shape of the rewrite:

1. `DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --')` once, then `DataCaptureContext.sharedInstance`.
2. `BarcodeCaptureSettings` + `settings.enableSymbologies([...])` from the table below, `new BarcodeCapture(settings)`, `dataCaptureContext.addMode(barcodeCapture)`.
3. `Camera.withSettings(BarcodeCapture.createRecommendedCameraSettings())` → `dataCaptureContext.setFrameSource(camera)` → `camera.switchToDesiredState(FrameSourceState.On)`.
4. `<DataCaptureView context={dataCaptureContext} />` replaces the library's camera component; add `new BarcodeCaptureOverlay(barcodeCapture)` in its `ref` callback.
5. The scan callback becomes `barcodeCapture.addListener({ didScan })`.

### Symbology mapping

Map **only** the formats the app actually scanned; fewer symbologies scan faster and more accurately. Do not derive Scandit names from the old library's names.

Names are the vision-camera (v4 and v5) spelling; expo-camera drops the dash (`'ean13'`, `'code128'`, `'datamatrix'`). Exceptions are in brackets.

| Source format | Scandit `Symbology.*` |
|---|---|
| `'qr'` (v5: `'qr-code'`) | `QR` (**not** `QRCode`) |
| `'ean-13'`, `'upc-a'` (expo: `'upc_a'`) | `EAN13UPCA` (UPC-A is read as EAN-13/UPC-A) |
| `'ean-8'` | `EAN8` |
| `'upc-e'` (expo: `'upc_e'`) | `UPCE` |
| `'code-39'` / `'code-93'` / `'code-128'` | `Code39` / `Code93` / `Code128` |
| `'itf'`, v4 `'itf-14'` (expo: `'itf14'`) | `InterleavedTwoOfFive` (no ITF-14 member; ITF-14 is a 14-digit Interleaved 2 of 5) |
| `'codabar'` | `Codabar` |
| `'data-matrix'` | `DataMatrix` |
| `'aztec'` | `Aztec` |
| `'pdf-417'` | `PDF417` |
| v4 only: `'gs1-data-bar'`, `-limited`, `-expanded` | `GS1Databar`, `GS1DatabarLimited`, `GS1DatabarExpanded` |

**"All formats"** (v5 `'all-formats'`, or no `barcodeTypes` / `codeTypes` filter). Never leave it to a guess: an agent that picks one symbology silently drops the rest. Search the project for what the app really consumes and enable exactly that. If nothing narrows it, enable the 12 non-GS1 symbologies in the table (`QR` through `PDF417`) and add a summary line "symbologies were not narrowed by the original; confirm this list". If a symbology is not in the table, look it up in the API reference before writing it.

## Result mapping

| Old | BarcodeCapture |
|---|---|
| `onCodeScanned(codes)` / `onBarcodeScanned(barcodes)` / `onBarcodeScanned(result)` | `didScan(mode, session)` — read `session.newlyRecognizedBarcode` (a single `Barcode \| null`) |
| `code.value` / `barcode.rawValue` / `result.data` | `barcode.data` (`string \| null`; keep the old null guard) |
| `code.type` / `barcode.format` / `result.type` | `barcode.symbology` (`Symbology`); show `new SymbologyDescription(barcode.symbology).readableName`. App models that stored the old type string now store a `Symbology` or that name. |
| `code.corners` / `barcode.cornerPoints` / `result.cornerPoints`, `bounds` | `barcode.location` (`Quadrilateral` in **frame** coordinates). To compare with anything laid out in the view call `await view.viewQuadrilateralForFrameQuadrilateral(barcode.location)` on the `DataCaptureView`. |
| "scanned once" flag (`scanned ? undefined : handleScan`) | `barcodeCapture.isEnabled = false` at the top of `didScan`; the old "Scan again" button sets it back to `true`. |
| Duplicate suppression by value | keep the app's own dedupe in `didScan`; `settings.codeDuplicateFilter` (milliseconds, `-1` = once) only changes how often the SDK repeats a code. Mention a changed filter as a judgment call. |

Move the body of the old callback into `didScan` unchanged (dedupe, state updates, navigation, haptics, lookups). Do not hold `session` or its barcode outside the callback; copy `data` and `symbology` out.

## Camera, permission, torch, facing, lifecycle

`DataCaptureView` does not request camera permission on Android: replace the library's `useCameraPermission` / `useCameraPermissions` with the `requestCameraPermission()` helper from `references/integration.md` Step 14 (`PermissionsAndroid` on Android; iOS prompts when the camera first starts and needs `NSCameraUsageDescription`). Core 8.6+ also exports a `useCameraPermission()` hook, but it is optimistic on iOS, so keep the explicit request. Keep the original's denied screen. The working shape, compiled against 8.6.1 (keep the app's own list UI and styles):

```tsx
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AppState, Button, Text, View } from 'react-native';
import {
  BarcodeCapture,
  BarcodeCaptureListener,
  BarcodeCaptureOverlay,
  BarcodeCaptureSettings,
  Symbology,
  SymbologyDescription,
} from 'scandit-react-native-datacapture-barcode';
import { Camera, DataCaptureContext, DataCaptureView, FrameSourceState, TorchState } from 'scandit-react-native-datacapture-core';
import { requestCameraPermission } from './permissions'; // integration.md Step 14 helper, exported

DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
const dataCaptureContext = DataCaptureContext.sharedInstance;

export const ScanScreen = () => {
  const [permission, setPermission] = useState<boolean | null>(null);
  const [scanned, setScanned] = useState<{ value: string; type: string }[]>([]);
  const [torchOn, setTorchOn] = useState(false);
  const cameraRef = useRef<Camera | null>(null);
  const [barcodeCapture] = useState(() => {
    const settings = new BarcodeCaptureSettings();
    settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128, Symbology.QR]);
    return new BarcodeCapture(settings);
  });
  const [overlay] = useState(() => new BarcodeCaptureOverlay(barcodeCapture));
  const attachOverlay = useCallback((view: DataCaptureView | null) => void view?.addOverlay(overlay), [overlay]);

  useEffect(() => {
    const listener: BarcodeCaptureListener = {
      didScan: async (_mode, session) => {
        const barcode = session.newlyRecognizedBarcode;
        const value = barcode?.data;
        if (barcode == null || value == null) return;
        const type = new SymbologyDescription(barcode.symbology).readableName;
        setScanned(prev => (prev.some(c => c.value === value) ? prev : [...prev, { value, type }]));
      },
    };
    dataCaptureContext.addMode(barcodeCapture);
    barcodeCapture.isEnabled = true;
    barcodeCapture.addListener(listener);
    void requestCameraPermission().then(setPermission);
    return () => {
      barcodeCapture.removeListener(listener);
      barcodeCapture.isEnabled = false;
      void cameraRef.current?.switchToDesiredState(FrameSourceState.Off);
      dataCaptureContext.removeMode(barcodeCapture);
    };
  }, [barcodeCapture]);

  useEffect(() => {
    if (!permission) return;
    const startCamera = async () => {
      if (!cameraRef.current) {
        const camera = Camera.withSettings(BarcodeCapture.createRecommendedCameraSettings());
        if (!camera) return; // no camera: show the app's no-camera screen
        cameraRef.current = camera;
        await dataCaptureContext.setFrameSource(camera);
      }
      await cameraRef.current.switchToDesiredState(FrameSourceState.On);
    };
    void startCamera();
    const subscription = AppState.addEventListener('change', state => {
      void cameraRef.current?.switchToDesiredState(state === 'active' ? FrameSourceState.On : FrameSourceState.Off);
    });
    return () => subscription.remove();
  }, [permission]);

  useEffect(() => {
    if (cameraRef.current) cameraRef.current.desiredTorchState = torchOn ? TorchState.On : TorchState.Off;
  }, [torchOn, permission]);

  if (permission === false) return <Text>Camera permission denied</Text>;
  return (
    <View style={{ flex: 1 }}>
      <DataCaptureView style={{ flex: 1 }} context={dataCaptureContext} ref={attachOverlay} />
      <Button title={torchOn ? 'Torch off' : 'Torch on'} onPress={() => setTorchOn(on => !on)} />
      <Text>Scanned: {scanned.length}</Text>
    </View>
  );
};
```

Rules this encodes:

- **Torch.** `torch` / `torchMode` / `enableTorch` becomes `camera.desiredTorchState = TorchState.On | Off`. Keep the app's torch state and button, and wire the button to it.
- **Facing.** `facing` / `useCameraDevice('front')` becomes `Camera.atPosition(CameraPosition.UserFacing)` (`WorldFacing` for back); `Camera.withSettings(...)` is world-facing. Apply `BarcodeCapture.createRecommendedCameraSettings()` with `camera.applySettings(...)` for the positional factory.
- **Active / focus.** `isActive={...}` and `useIsFocused` / `useFocusEffect` become `switchToDesiredState(FrameSourceState.On | Off)`; a backgrounded app turns the camera off (the `AppState` handler above). If the original gated the camera on a prop, gate the same call on it.
- **Region of interest** (v4 `regionOfInterest`, or a hand-rolled "scan box" test on `bounds`) → `settings.locationSelection = RectangularLocationSelection.withSize(new SizeWithUnit(new NumberWithUnit(0.75, MeasureUnit.Fraction), new NumberWithUnit(0.28, MeasureUnit.Fraction)))`. The semantics differ (the whole code must be inside the region); flag it as a judgment call.
- **Per-frame throttles and quality gates** have no BarcodeCapture equivalent; Scandit processes frames itself. Say they were removed and why.
- **Full teardown, in this order:** `removeListener`, `isEnabled = false`, camera off, `removeMode`. Never call `dataCaptureContext.dispose()`.

## SDK 8.7+: BarcodeCaptureAioView

On 8.7 or newer you may replace the whole camera section above with one component. It creates the mode, camera and overlay, and handles app foreground/background itself. It does **not** request camera permission: keep `requestCameraPermission()` and render the view only once it is granted. Props are from the 8.7 source (`BarcodeCaptureAioView.tsx`); check them against the installed `.d.ts`.

| Old | `BarcodeCaptureAioView` |
|---|---|
| format list | `symbologies={[Symbology.EAN13UPCA, ...]}` (required, or `barcodeCaptureSettings`) |
| scan callback | `didScan={(barcodes, session) => ...}`: an array holding at most one barcode |
| `isActive`, "scanned once" flag | `disabled={...}`, or `ref.current?.disable()` / `enable()` on the `BarcodeCaptureAioViewHandle` |
| `useIsFocused` / navigation focus | `navigation={navigation}` |
| torch prop and button | `torchSwitchControl={new TorchSwitchControl()}`, Scandit's on-screen button; there is no torch prop, so flag the UI change |
| `regionOfInterest`, duplicate filter | `locationSelection`, `codeDuplicateFilter` |
| corners to view coordinates | `ref.current?.viewQuadrilateralForFrameQuadrilateral(barcode.location)` |

```tsx
<BarcodeCaptureAioView
  style={{ flex: 1 }}
  symbologies={[Symbology.EAN13UPCA, Symbology.Code128, Symbology.QR]}
  didScan={barcodes => {
    const value = barcodes[0]?.data;
    if (value != null) addCode(value);
  }}
  torchSwitchControl={torchControl}
/>
```

The AIO view owns the frame source, so an app with a scan-from-photo path (see **Still images**) stays on `DataCaptureView`.

## Still images

vision-camera v5 `scanCodesInImageAsync(image)` and expo-camera `scanFromURLAsync(url, types)` decode a file; Scandit does this with `ImageFrameSource`, so the still-image path migrates too (never answer "there is no API for it"). Read the file as a **base64 string**, create the source, make it the frame source and switch it on; the result arrives in the same `didScan`. Read the file with the library the app already has: `expo-file-system` (`await new File(uri).base64()`) in an Expo app, otherwise `react-native-fs` (`RNFS.readFile(path, 'base64')`; add the dependency). Compiled against 8.6.1:

```ts
import RNFS from 'react-native-fs';
import { Camera, DataCaptureContext, FrameSourceState, ImageFrameSource } from 'scandit-react-native-datacapture-core';
import { BarcodeCapture } from 'scandit-react-native-datacapture-barcode';

const dataCaptureContext = DataCaptureContext.sharedInstance;

export const scanImageFile = async (path: string, camera: Camera | null, barcodeCapture: BarcodeCapture) => {
  const base64 = await RNFS.readFile(path, 'base64');
  barcodeCapture.isEnabled = true;
  const source = ImageFrameSource.create(base64);
  source.addListener({
    didChangeState: (_source, state) => {
      if (state !== FrameSourceState.Off || !camera) return;
      void dataCaptureContext.setFrameSource(camera).then(() => camera.switchToDesiredState(FrameSourceState.On));
    },
  });
  await dataCaptureContext.setFrameSource(source);
  await source.switchToDesiredState(FrameSourceState.On);
};
```

The source delivers its image once per switch to `On` and then turns itself off. Create a new source per picked image, and set the camera back only when the source reports `Off`; restoring it right after `switchToDesiredState(On)` can swap the camera in before the image is processed. Drop the camera restart if live scanning should stay paused. A one-shot screen keeps its guard: skip the image scan while a result is shown, since `isEnabled = true` would resume live scanning behind it. A photo that decodes nothing produces no `didScan`; if the old code showed "no barcode found", say it needs a timeout of the app's own. expo-camera's `scanFromURLAsync` decodes only QR on iOS; mention that the Scandit path reads every enabled symbology.

## Preserve and verify

Keep the app's data models, list state, dedupe, summary, clear and navigation logic, its permission-denied and no-camera screens, and any validation as a guard at the top of `didScan`. Add nothing the original lacked; flag anything you could not carry over.

Type-check the migrated file (`npx tsc --noEmit`) and fix every error. The usual ones: `Symbology.QRCode` (it is `QR`), `data` used as `string` without the `null` guard, a leftover import of the old library. No `useCodeScanner`, `useBarcodeScannerOutput`, `CameraView`, `codeScanner`, `onBarcodeScanned` or new `TODO` may remain.

## Setup checklist and summary

**Setup checklist:**
1. Remove the old scanner packages from `package.json`; install `npm install scandit-react-native-datacapture-core scandit-react-native-datacapture-barcode` (plus `react-native-fs` only if the still-image path needs it).
2. Run `npx pod-install` (iOS). Android auto-links.
3. Keep or add `NSCameraUsageDescription` in `ios/<App>/Info.plist`. On Android the plugin declares the manifest permission; the screen requests it at runtime.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key (see **Licence key** in `SKILL.md`).
5. Restart Metro with `--reset-cache`.

**Summary:** list what was removed and added, the format → symbology mapping, and every judgment call (duplicate filter, region semantics, removed throttles, symbologies not narrowed, still-image path moved to `ImageFrameSource`). Do not list code that was already correct.

## API reference

- BarcodeCapture API: https://docs.scandit.com/data-capture-sdk/react-native/barcode-capture/api.html
- Get Started: https://docs.scandit.com/sdks/react-native/barcode-capture/get-started/
