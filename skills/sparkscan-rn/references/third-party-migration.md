# Third-Party Scanner → SparkScan Migration (React Native)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm. Replacing a full-screen camera preview with SparkScan's trigger button and mini preview is always one of them.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.
- **Preserve, never invent.** Keep the app's own model, list, dedupe, clear and navigation logic. Do not add symbologies or filters the original did not have; do not silently drop a feature (flag it instead).

This guide replaces **expo-camera** or **react-native-vision-camera** (v4 `useCodeScanner`, v5 + `react-native-vision-camera-barcode-scanner`) with Scandit **SparkScan**. For the full SparkScan API read `references/integration.md`; this guide is the delta.

**Shared with `barcode-capture-rn`.** The format → symbology table, the camera-permission notes and the still-image path are the same for SparkScan. Read them in the `barcode-capture-rn` skill's `references/third-party-migration.md` (sections **Symbology mapping**, **Camera, permission, torch, facing, lifecycle** — permission paragraph only — and **Still images**). If that skill is not installed, fetch it from <https://github.com/Scandit/skills/blob/main/skills/barcode-capture-rn/references/third-party-migration.md>.

## Step 1: Decide whether SparkScan fits

Read the existing code first; do not ask the user to describe it. Identify the library by its imports and `package.json`:

- **expo-camera** — `<CameraView onBarcodeScanned barcodeScannerSettings={{ barcodeTypes }} />`, `useCameraPermissions`, `enableTorch`, `facing`, `scanFromURLAsync`.
- **react-native-vision-camera v4** — `useCodeScanner({ codeTypes, onCodeScanned })`, `<Camera codeScanner={...} device isActive />`, `useCameraDevice`, `useCameraPermission`, `torch`.
- **react-native-vision-camera v5** — `useBarcodeScannerOutput({ barcodeFormats, onBarcodeScanned })`, `<Camera outputs={[output]} />`, `torchMode`, `useBarcodeScanner(...).scanCodesInImageAsync`.

Then decide:

- **SparkScan fits** a screen that scans one code at a time and either keeps going ("scan, add to a list, keep scanning") or stops once, and whose camera UI is just the preview plus a few buttons (torch, flip camera).
- **Use `barcode-capture-rn` instead** (its `references/third-party-migration.md`) when the camera UI must stay as it is: a hand-drawn highlight or scan-box overlay from `corners` / `bounds`, region-of-interest logic, a bespoke preview layout, or a camera owned by a shared component. Say so in one line and continue with that skill.
- **Several codes per frame genuinely needed** (the callback loops over every code and the app uses them all, live highlights)? Use `matrixscan-batch-rn`. SparkScan reports one `session.newlyRecognizedBarcode` per callback.

Also read the installed Scandit SDK version (`scandit-react-native-datacapture-*` in `package.json`; none yet means the latest). **8.6.x → `SparkScanView`** (this guide's default, Steps 2–6). **8.7 or newer →** `SparkScanAioView` is an option (see **SDK 8.7+: SparkScanAioView**). Do not mix the two.

## Step 2: Remove the third-party scanner

- The packages from `package.json` once nothing imports them: `expo-camera`, `react-native-vision-camera`, `react-native-vision-camera-barcode-scanner`, `react-native-nitro-image` (only if nothing else uses it).
- The imports, the scanner hook / output (`useCodeScanner`, `useBarcodeScannerOutput`, `useBarcodeScanner`), the camera component and its scanner props (`CameraView`, `Camera`, `codeScanner`, `outputs`, `onBarcodeScanned`, `barcodeScannerSettings`), `useCameraDevice`, and the library's permission hook.
- The app's own torch / flip-camera buttons and any hand-drawn highlight boxes: SparkScan's toolbar replaces them (Step 5). Keep the rest of the UI: lists, summaries, clear and "Scan again" buttons.

## Step 3: Map formats to symbologies

Use the `barcode-capture-rn` **Symbology mapping** table (one column each for vision-camera v4, v5 and expo-camera). Map **only** the formats the app scanned; `'qr'` is `Symbology.QR`, never `QRCode`. "All formats" (no `barcodeTypes` / `codeTypes`, or v5 `'all-formats'`) follows that guide's rule: enable what the app really consumes, or the recommended default set under that table plus a summary line "symbologies were not narrowed by the original; confirm this list".

Symbologies go on `SparkScanSettings`:

```ts
const settings = new SparkScanSettings();
settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128, Symbology.QR]);
const sparkScan = new SparkScan(settings);
```

`settings.codeDuplicateFilter` is in milliseconds (`-1` = report each code once). Leave it at the default unless the old code throttled repeats; any value you set is a judgment call.

## Step 4: Replace the callback with `SparkScanListener.didScan`

| Old | SparkScan |
|---|---|
| `onBarcodeScanned(result)` / `onCodeScanned(codes)` / `onBarcodeScanned(barcodes)` | `sparkScan.addListener({ didScan: async (mode, session) => ... })` — read `session.newlyRecognizedBarcode` (a single `Barcode \| null`); never loop over an array |
| `result.data` / `code.value` / `barcode.rawValue` | `barcode.data` (`string \| null`; keep the old null guard) |
| `result.type` / `code.type` / `barcode.format` | `barcode.symbology`; `new SymbologyDescription(barcode.symbology).readableName` for display only. If the app stores or compares the old format string, keep that contract with a small `Symbology` → old-string lookup. |
| `cornerPoints` / `bounds` | `barcode.location`; SparkScan draws no app overlay, so a screen that needs them belongs on `barcode-capture-rn` (Step 1). |

`didScan` must be `async` (the 8.6 listener returns `Promise<void>`). Move the old callback's body in unchanged: dedupe, list state, navigation, lookups. Copy `data` and `symbology` out; do not keep `session` outside the callback.

Flow shapes:

- **Scan and continue** (running list, dedupe, clear): nothing else; SparkScan keeps scanning.
- **Scan once** (`scanned ? undefined : handler`, "Scan again" button): keep the app's `scanned` state as a guard at the top of `didScan` (return when a result is shown) and call `viewRef.current?.pauseScanning()` after storing the result; "Scan again" clears that state and calls `viewRef.current?.startScanning()`.
- **Scan once and navigate away:** `pauseScanning()` first, then navigate, so a second callback cannot navigate twice.

## Step 5: Wrap the screen in `SparkScanView`

`SparkScanView` **wraps** the screen: delete the camera component and make the rest of the screen (list, summary, buttons) its children. The native trigger button, toolbar and mini preview render on top of them. The working shape, compiled against 8.6.1 (keep the app's own list UI and styles):

```tsx
import React, { useEffect, useRef, useState } from 'react';
import { FlatList, Platform, PermissionsAndroid, Pressable, Text, View } from 'react-native';
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';
import {
  SparkScan,
  SparkScanListener,
  SparkScanSettings,
  SparkScanView,
  SparkScanViewSettings,
  Symbology,
  SymbologyDescription,
} from 'scandit-react-native-datacapture-barcode';

DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
const dataCaptureContext = DataCaptureContext.sharedInstance;

async function requestCameraPermission(): Promise<boolean> {
  if (Platform.OS !== 'android') return true;
  const status = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA);
  return status === PermissionsAndroid.RESULTS.GRANTED;
}

export const ScanScreen = () => {
  const [permission, setPermission] = useState<boolean | null>(null);
  const [scanned, setScanned] = useState<{ value: string; type: string }[]>([]);
  const [sparkScan] = useState(() => {
    const settings = new SparkScanSettings();
    settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128, Symbology.QR]);
    return new SparkScan(settings);
  });
  const [viewSettings] = useState(() => new SparkScanViewSettings());
  const viewRef = useRef<SparkScanView | null>(null);

  useEffect(() => {
    const listener: SparkScanListener = {
      didScan: async (_mode, session) => {
        const barcode = session.newlyRecognizedBarcode;
        const value = barcode?.data;
        if (barcode == null || value == null) return;
        const type = new SymbologyDescription(barcode.symbology).readableName;
        setScanned(prev => (prev.some(c => c.value === value) ? prev : [...prev, { value, type }]));
      },
    };
    sparkScan.addListener(listener);
    void requestCameraPermission().then(setPermission);
    return () => {
      sparkScan.removeListener(listener);
      dataCaptureContext.removeMode(sparkScan);
    };
  }, [sparkScan]);

  if (permission === false) return <Text>Camera permission denied</Text>;
  if (permission === null) return null;
  return (
    <SparkScanView
      style={{ flex: 1 }}
      context={dataCaptureContext}
      sparkScan={sparkScan}
      sparkScanViewSettings={viewSettings}
      torchControlVisible={true}
      ref={view => {
        viewRef.current = view;
      }}
    >
      <View style={{ flex: 1 }}>
        <Text>Scanned: {scanned.length}</Text>
        <FlatList
          data={scanned}
          keyExtractor={item => item.value}
          renderItem={({ item }) => <Text>{item.type}: {item.value}</Text>}
        />
        <Pressable onPress={() => setScanned([])}>
          <Text>Clear</Text>
        </Pressable>
      </View>
    </SparkScanView>
  );
};
```

`torchControlVisible` is there because this screen had a torch button; leave it out when the original had none. `viewRef` is what the Step 4 `pauseScanning()` / `startScanning()` calls use; drop it if the screen only scans and continues. On 8.6.1 `context`, `sparkScan`, `sparkScanViewSettings` and `style` are required props. Create the mode and view settings once (`useState` initialiser or `useRef`), never per render. In an app that already has a `CaptureContext` module (`references/integration.md` Step 10), import its context instead of initialising a second one.

## Step 6: Permission, torch, facing, lifecycle

- **Permission.** Follow the `barcode-capture-rn` permission notes: replace `useCameraPermission` / `useCameraPermissions` with a `PermissionsAndroid` request (above); iOS prompts on first use and needs `NSCameraUsageDescription`. That helper returns granted on iOS without checking; if the original showed a denied screen on iOS, keep it by reading the real status (`react-native-permissions`), otherwise flag it. Keep the app's denied and no-camera screens.
- **Torch** (`enableTorch`, `torch`, `torchMode` and the app's button) → the view's toolbar control: `torchControlVisible={true}`. SparkScan owns the camera, so there is no `Camera` object to set a torch state on. Delete the app's torch button and its state, and list the UI change as a judgment call.
- **Facing** (`facing="front"`, `useCameraDevice('front')`) → `cameraSwitchButtonVisible={true}` for a user-controlled switch. A fixed front camera is `viewSettings.defaultCameraPosition = CameraPosition.UserFacing` (`CameraPosition` from core); flag it.
- **Active / focus** (`isActive`, `active`, `useIsFocused`) → remove; the view starts and stops the camera itself on mount, unmount and app background. With React Navigation, pass `navigation={navigation}` so a screen kept in the stack releases the camera when it loses focus. Pause around app-driven navigation with `pauseScanning()` / `startScanning()`.
- **Per-frame throttles, zoom gestures, quality gates** have no SparkScan equivalent; say they were removed and why.
- **Teardown** on unmount: `removeListener`, then `dataCaptureContext.removeMode(sparkScan)`. Never call `dataCaptureContext.dispose()`.

## Step 7: Still images

expo-camera `scanFromURLAsync` and vision-camera v5 `scanCodesInImageAsync` have no SparkScan equivalent: SparkScan owns its camera and takes no other frame source. Decode the photo with a `BarcodeCapture` mode and `ImageFrameSource`, as the `barcode-capture-rn` **Still images** section shows, and feed its `didScan` result into the same list. The native context runs one mode at a time (core's `.d.ts`: adding a non-coexisting mode evicts the others, so adding `BarcodeCapture` evicts SparkScan), so put the photo decode on its own route that the button navigates to, not inside the mounted `SparkScanView`. Never drop the button or answer "there is no API for it"; list the moved path as a judgment call to check on a device. If the screen's main job is decoding photos, SparkScan does not fit: use `barcode-capture-rn` for the whole screen.

## SDK 8.7+: SparkScanAioView

On 8.7 or newer you may use the all-in-one `SparkScanAioView` instead. It creates the context-attached mode and view, wires the listener, and handles focus and app background. Props are from the 8.7 source (`SparkScanAioView.tsx`); check them against the installed `.d.ts`.

- It must be rendered inside a root **`<ScanditProvider licenseKey="...">`** from `scandit-react-native-datacapture-core` (wrap the app or the navigator once). The provider calls `DataCaptureContext.initialize` itself, so drop the module-level `initialize` / `sharedInstance` lines on this path. Without the provider the view throws "must be rendered inside a `<ScanditProvider>`".
- It does **not** request camera permission: keep the permission request and render the view only once it is granted.

| Old | `SparkScanAioView` |
|---|---|
| format list | `symbologies={[Symbology.EAN13UPCA, ...]}` (required, or `sparkScanSettings`) |
| scan callback | `didScan={(barcodes, session) => ...}`: an array holding at most one barcode |
| duplicate filter | `codeDuplicateFilter={...}` (milliseconds) |
| `isActive` | `disabled={...}`, or `ref.current?.disable()` / `enable()` on the `SparkScanAioViewHandle` |
| scan once / "Scan again" | `ref.current?.pauseScanning()` / `startScanning()` |
| `useIsFocused` / navigation focus | `navigation={navigation}` |
| torch / facing buttons | `torchControlVisible`, `cameraSwitchButtonVisible` |

```tsx
<ScanditProvider licenseKey="-- ENTER YOUR SCANDIT LICENSE KEY HERE --">
  <SparkScanAioView
    style={{ flex: 1 }}
    symbologies={[Symbology.EAN13UPCA, Symbology.Code128, Symbology.QR]}
    didScan={barcodes => {
      const value = barcodes[0]?.data;
      if (value != null) addCode(value);
    }}
    torchControlVisible
  >
    {/* the screen's list and buttons */}
  </SparkScanAioView>
</ScanditProvider>
```

## Step 8: Verify

Type-check the migrated file (`npx tsc --noEmit`) and fix every error. The usual ones: `Symbology.QRCode` (it is `QR`), `data` used as `string` without the null guard, a missing `sparkScanViewSettings` prop, a non-`async` `didScan`, a leftover import of the old library. No `CameraView`, `useCodeScanner`, `useBarcodeScannerOutput`, `codeScanner`, `onBarcodeScanned`, `barcodeScannerSettings` or new `TODO` may remain.

## Step 9: Setup checklist and summary

**Setup checklist:**
1. Remove the old scanner packages from `package.json`; install `npm install scandit-react-native-datacapture-core scandit-react-native-datacapture-barcode`.
2. Run `npx pod-install` (iOS). Android auto-links. **Expo app:** Scandit's packages are native modules and do not run in Expo Go; build a development client (`npx expo prebuild`, then `npx expo run:ios` / `npx expo run:android`) and set `NSCameraUsageDescription` under `expo.ios.infoPlist` in `app.json`.
3. Keep or add `NSCameraUsageDescription` in `ios/<App>/Info.plist`. On Android the plugin declares the manifest permission; the screen requests it at runtime.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key (see **Licence key** in `SKILL.md`).
5. Restart Metro with `--reset-cache`.

**Summary:** list what was removed and added, the format → symbology mapping, and every judgment call (new scanning UI with trigger button and mini preview, torch / camera-switch buttons moved to the SparkScan toolbar, duplicate filter, removed throttles, symbologies not narrowed, still-image path moved to `BarcodeCapture` + `ImageFrameSource`). Do not list code that was already correct.

## API reference

- SparkScan API: https://docs.scandit.com/data-capture-sdk/react-native/barcode-capture/api.html
- Get Started: https://docs.scandit.com/sdks/react-native/sparkscan/get-started/
