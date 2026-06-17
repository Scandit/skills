# Third-Party Multi-Barcode Scanner → MatrixScan Batch Migration (React Native)

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- Which library is in use (read the imports and `package.json` dependencies).
- Which code types / symbologies are enabled.
- How the project collects "all visible barcodes" (a per-frame callback that receives an array of codes, a frame processor, a continuous-scan loop).
- What result-handling logic exists (deduplication by value, accumulation in a `Map` / `Set` / state array, filtering by type / prefix, a running count or summary).
- What data models are defined.
- How the scanner UI is rendered (a full-screen camera component, an embedded preview).

Common third-party multi-barcode scanners in React Native codebases:

- **react-native-vision-camera** (`useCodeScanner`, `Camera` with a `codeScanner` prop) — `useCodeScanner({ codeTypes, onCodeScanned })` calls `onCodeScanned(codes)` with an **array** of every code detected in the frame. This is the multi-barcode pattern closest to BarcodeBatch: the callback fires per frame with all visible codes, and the app dedupes on its own.
- **react-native-camera / RNCamera** (`onGoogleVisionBarcodesDetected`, `onBarCodeRead`) — deprecated; the Google Vision callback reports `barcodes: [...]` per frame.
- **@react-native-ml-kit/barcode-scanning** / expo-barcode-scanner — single-shot or per-frame barcode arrays.

MatrixScan Batch replaces all of the above: it owns the camera, runs the recognizer on every frame, **tracks each barcode across frames (assigning a stable per-barcode tracking `identifier`)**, and reports additions / updates / removals via `BarcodeBatchListener.didUpdateSession`. There is no per-frame array to dedupe from scratch — the same physical barcode keeps the same `identifier` across frames, and new barcodes arrive in `session.addedTrackedBarcodes`.

---

## Remove

- The third-party dependency from `package.json` (e.g. `react-native-vision-camera`).
- The library imports (`Camera`, `useCameraDevice`, `useCodeScanner`, `Code` from `react-native-vision-camera`).
- The scanner hook and its callback (`useCodeScanner({ codeTypes, onCodeScanned })`).
- The library's camera component and its scanner prop (`<Camera ... codeScanner={codeScanner} />`).
- Any UI specific to the old scanner — custom viewfinder, manually-drawn highlight boxes from the per-code bounding boxes. MatrixScan Batch's `DataCaptureView` + `BarcodeBatchBasicOverlay` (or `BarcodeBatchAdvancedOverlay`) replace all of it.

---

## Integrate MatrixScan Batch

Follow `references/integration.md`. The key shape of the rewrite:

1. **Initialize the context once.** `DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --')`, then use `DataCaptureContext.sharedInstance`.
2. **Replace the scanner's `codeTypes` with `BarcodeBatchSettings`.** `new BarcodeBatchSettings()` + `settings.enableSymbologies([...])`, mapping each code type using the table below. Then `const barcodeBatch = new BarcodeBatch(settings)` and `dataCaptureContext.setMode(barcodeBatch)`.
3. **Replace the library's camera with the Scandit camera pipeline.** `BarcodeBatch.createRecommendedCameraSettings()` → `Camera.withSettings(settings)` → `dataCaptureContext.setFrameSource(camera)` → `camera.switchToDesiredState(FrameSourceState.On)`. Drive on/off from app state / focus as in integration.md.
4. **Replace the library's camera component with `<DataCaptureView>`.** Render `<DataCaptureView context={dataCaptureContext} ref={...} />` and add the overlay with `view.addOverlay(overlay)` in the `ref` callback.
5. **Replace the `onCodeScanned(codes)` callback with `BarcodeBatchListener.didUpdateSession`.** Use the result-pattern mapping table below.
6. **Replace any manually-drawn highlight with `BarcodeBatchBasicOverlay`.** `new BarcodeBatchBasicOverlay(barcodeBatch, BarcodeBatchBasicOverlayStyle.Frame)` (or `Dot`).

When configuring `BarcodeBatchSettings`, map code types from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old library's names** — they differ (e.g. VisionCamera's `'qr'` maps to `Symbology.QR`, and `'ean-13'`/`'upc-a'` both map to `Symbology.EAN13UPCA`).

### Symbology mapping

| react-native-vision-camera `CodeType` | Scandit `Symbology.*` |
|---|---|
| `'qr'` | `Symbology.QR` |
| `'ean-13'` | `Symbology.EAN13UPCA` |
| `'ean-8'` | `Symbology.EAN8` |
| `'upc-a'` | `Symbology.EAN13UPCA` (UPC-A is read by the EAN-13/UPC-A symbology in Scandit) |
| `'upc-e'` | `Symbology.UPCE` |
| `'code-39'` | `Symbology.Code39` |
| `'code-93'` | `Symbology.Code93` |
| `'code-128'` | `Symbology.Code128` |
| `'itf'` | `Symbology.InterleavedTwoOfFive` |
| `'codabar'` | `Symbology.Codabar` |
| `'data-matrix'` | `Symbology.DataMatrix` |
| `'aztec'` | `Symbology.Aztec` |
| `'pdf-417'` | `Symbology.PDF417` |

If you encounter a code type not in this table, fetch the [BarcodeBatch API reference](https://docs.scandit.com/data-capture-sdk/react-native/barcode-capture/api.html) for the correct `Symbology` enum value before writing the code.

### Result-pattern mapping

| Old scanner concept | MatrixScan Batch equivalent |
|---|---|
| `onCodeScanned(codes)` per-frame array callback | `BarcodeBatchListener.didUpdateSession(barcodeBatch, session)` — fires per processed frame; `session.addedTrackedBarcodes` reports the codes newly tracked since the last frame. |
| `code.value` | `trackedBarcode.barcode.data` (`string | null`) |
| `code.type` | `trackedBarcode.barcode.symbology` (a `Symbology` enum value) |
| Per-code bounding box (`code.frame` / `code.corners`) | `trackedBarcode.location` (a `Quadrilateral` in image-space; the basic overlay draws the highlight for you — requires the MatrixScan AR add-on) |
| "Have I seen this code yet?" (manual `Map`/`Set` dedupe on `code.value`) | `trackedBarcode.identifier` is the stable per-barcode tracking id. Dedupe on the identifier rather than the value: the same physical barcode keeps its identifier across frames, and new barcodes arrive in `session.addedTrackedBarcodes`. |
| "Which barcodes are currently visible?" | `session.trackedBarcodes` — a `{ [identifier: string]: TrackedBarcode }` map. Iterate with `Object.values(session.trackedBarcodes)`. |
| A running unique count / summary | Keep your `Set<number>` (or `Map`) of identifiers; update it from `session.addedTrackedBarcodes` and render its `.size`. |

---

## Preserve

- Custom data models — keep them as-is.
- Result accumulation and deduplication logic — move it into `didUpdateSession`. Iterate `session.addedTrackedBarcodes`, dedupe by `trackedBarcode.identifier`, and append to the existing collection / update state.
- The running-count or summary display — drive it from the deduped identifier set.
- Any downstream business logic triggered on a new barcode (network lookup, navigation).
- Validation / reject behavior — if the old scanner had an "is this code valid?" check, port it as a guard when iterating `addedTrackedBarcodes`.

> **Session safety**: The session is only safe to access from inside `didUpdateSession`. Copy the values you keep (`barcode.data`, `identifier`) out of the callback — do not store the `session` object or its arrays and read them later.

---

## Putting it all together

A typical "vision-camera `useCodeScanner` replaced with MatrixScan Batch" shape:

```tsx
import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchSession,
  BarcodeBatchSettings,
  Symbology,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';
import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';

DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
const dataCaptureContext = DataCaptureContext.sharedInstance;

export const ScanScreen = () => {
  const viewRef = useRef<DataCaptureView>(null);
  const cameraRef = useRef<Camera | null>(null);
  // Dedupe by stable tracking identifier, mirroring the old Map-by-value dedupe.
  const seenIdentifiers = useRef<Set<number>>(new Set());
  const [uniqueCount, setUniqueCount] = useState(0);

  const barcodeBatchRef = useRef<BarcodeBatch>(null!);
  if (!barcodeBatchRef.current) {
    const settings = new BarcodeBatchSettings();
    settings.enableSymbologies([
      Symbology.EAN13UPCA, // 'ean-13'
      Symbology.Code128,   // 'code-128'
      Symbology.QR,        // 'qr'
    ]);

    const batch = new BarcodeBatch(settings);
    batch.addListener({
      didUpdateSession: async (_batch: BarcodeBatch, session: BarcodeBatchSession) => {
        // Same dedupe-and-count as the old onCodeScanned, but driven by per-frame deltas.
        session.addedTrackedBarcodes.forEach((trackedBarcode: TrackedBarcode) => {
          if (trackedBarcode.barcode.data && !seenIdentifiers.current.has(trackedBarcode.identifier)) {
            seenIdentifiers.current.add(trackedBarcode.identifier);
          }
        });
        setUniqueCount(seenIdentifiers.current.size);
      },
    });

    dataCaptureContext.setMode(batch);
    barcodeBatchRef.current = batch;
  }

  const overlayRef = useRef<BarcodeBatchBasicOverlay>(null!);
  if (!overlayRef.current) {
    overlayRef.current = new BarcodeBatchBasicOverlay(
      barcodeBatchRef.current,
      BarcodeBatchBasicOverlayStyle.Frame,
    );
  }

  useEffect(() => {
    const initCamera = async () => {
      if (!cameraRef.current) {
        const cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
        const camera = Camera.withSettings(cameraSettings);
        if (!camera) throw new Error('No camera available');
        await dataCaptureContext.setFrameSource(camera);
        await camera.switchToDesiredState(FrameSourceState.On);
        cameraRef.current = camera;
      }
    };
    void initCamera();

    return () => {
      barcodeBatchRef.current.isEnabled = false;
      dataCaptureContext.removeMode(barcodeBatchRef.current);
    };
  }, []);

  return (
    <View style={styles.container}>
      <DataCaptureView
        style={StyleSheet.absoluteFill}
        context={dataCaptureContext}
        ref={view => {
          if (view && !viewRef.current) {
            view.addOverlay(overlayRef.current);
            viewRef.current = view;
          }
        }}
      />
      <View style={styles.counter}>
        <Text style={styles.counterText}>Unique codes: {uniqueCount}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  counter: { position: 'absolute', top: 48, left: 16 },
  counterText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
```

---

When done, show only what changed. Do not list APIs that were unchanged. Include the setup checklist from `references/integration.md` so the user knows which packages to install (`scandit-react-native-datacapture-core`, `scandit-react-native-datacapture-barcode`), to run `npx pod-install` for iOS, to add `NSCameraUsageDescription` to `ios/<App>/Info.plist`, and to replace the license key placeholder.
