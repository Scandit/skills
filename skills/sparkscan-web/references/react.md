# SparkScan in React

SparkScan ships as a custom element (`<spark-scan-view>`). React's handling of custom elements changed in React 19, and that one difference is the single biggest source of "it just won't start" bugs. Read this whole file before writing React code — several of the points here are silent (no error, or a misleading one).

## Step 0 — Detect the React version first

How you pass `dataCaptureContext` and `sparkScan` to the element depends entirely on the React major version, so determine it before writing any code.

Open `package.json` and read the `react` entry under `dependencies` (fall back to `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` for the resolved version if `package.json` only has a range). Strip any leading `^`/`~`:

- **React 19+** → the declarative property pattern works. React 19 sets unknown JSX props as DOM **properties** on custom elements, so `<spark-scan-view sparkScan={mode}>` reaches the element as a real object.
- **React 18 (or earlier)** → you **must** bind via the element ref. React 18 serializes unknown props to string **attributes**, so `sparkScan={mode}` becomes `sparkscan="[object Object]"`, the property is never set, and the view throws `SparkScan mode is required to be set before calling this method` (or simply never starts). This is the most common React integration failure.

If you can't determine the version, default to the **ref-binding** pattern — it works on both 18 and 19, so it's the safe choice when in doubt.

## `DataCaptureContext` is a process-wide singleton: configure it once in a context provider

`DataCaptureContext.forLicenseKey(...)` initializes a single shared engine for the whole page. Two consequences that bite React specifically:

- **Configure it once for the whole app — not inside a component effect that disposes it on cleanup.** A natural `useEffect` that calls `context.dispose()` in its cleanup tears down the shared engine. The symptom is "it works for a second, then dies," often with `forLicenseKey ... already initializing`.
- **React StrictMode makes this worse in dev.** StrictMode intentionally mounts → unmounts → remounts every component once. If unmount disposes the context, the remount races against a half-torn-down engine. Don't "fix" this by disabling StrictMode — fix the lifecycle.

The idiomatic React home for one-time, app-wide setup is a **context provider**. Mount it once at the app root; it calls `forLicenseKey`, which the SDK caches internally — so the engine initializes only once even when StrictMode invokes the effect twice in dev, and you don't need your own promise guard. Once initialized, the context is reachable anywhere via the static `DataCaptureContext.sharedInstance` — so prefer that over storing the instance in component state, a variable, or a ref. The provider therefore only needs to publish a **readiness** flag, not the instance itself.

```tsx
// ScanditProvider.tsx
import { barcodeCaptureLoader } from "@scandit/web-datacapture-barcode";
import { DataCaptureContext } from "@scandit/web-datacapture-core";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

const ScanditReadyContext = createContext(false);

export function ScanditProvider({ children }: { children: ReactNode }) {
    const [ready, setReady] = useState(false);

    useEffect(() => {
        let cancelled = false;
        // forLicenseKey is cached internally by the SDK, so calling it once per provider
        // mount is safe even under StrictMode's extra dev mount/unmount/remount — the
        // duplicate call resolves to the same initialization rather than starting a second
        // one. We don't keep the resolved instance; read DataCaptureContext.sharedInstance.
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
            libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
            moduleLoaders: [barcodeCaptureLoader()],
        })
            .then(() => {
                if (!cancelled) setReady(true);
            })
            .catch(console.error);
        // No dispose() in the provider's normal lifecycle — release the singleton only at
        // final teardown (see "Disposing the context (final teardown only)" below).
        return () => {
            cancelled = true;
        };
    }, []);

    return <ScanditReadyContext.Provider value={ready}>{children}</ScanditReadyContext.Provider>;
}

// True once configuration has completed. Consumers then read the context from
// DataCaptureContext.sharedInstance — no need to thread the instance around.
export function useScanditReady(): boolean {
    return useContext(ScanditReadyContext);
}
```

Wrap the app once:

```tsx
<ScanditProvider>
    <App />
</ScanditProvider>
```

A ready-to-copy version of this provider is in `evals/fixtures/ScanditProvider.tsx` — drop it into the project and adjust the license key, `libraryLocation`, and module loaders.

### Disposing the context

You can release the engine at any time with `DataCaptureContext.sharedInstance.dispose()`. The key rule is that **`dispose()` and `forLicenseKey()` are a matched pair**: once you dispose, the shared instance is gone, so you must call `forLicenseKey` again before any further SparkScan use.

This pairing is exactly why the "works for a second, then dies" bug happens — disposing the shared context on a scanner component or route unmount frees the engine, but the remount (or another live scanner) then uses it without re-configuring, and StrictMode's dev remount races a re-init. So don't tie `dispose()` to a scanner component's lifecycle unless something re-runs `forLicenseKey` on the way back.

Where disposing is appropriate:

- **Page teardown** — the simplest case: dispose on `pagehide`. The page is going away, so no matching `forLicenseKey` is needed.

  ```tsx
  useEffect(() => {
      const disposeOnTeardown = () => {
          void DataCaptureContext.sharedInstance?.dispose();
      };
      window.addEventListener("pagehide", disposeOnTeardown);
      return () => window.removeEventListener("pagehide", disposeOnTeardown);
  }, []);
  ```

- **Leaving an SDK section to free resources** — let the `ScanditProvider` own *both* ends. Because the provider already calls `forLicenseKey` on mount, disposing in its unmount keeps the pair matched: unmounting the provider disposes, and re-entering remounts it and reconfigures. Just don't put `dispose()` on a *child* scanner's unmount, where no `forLicenseKey` follows.

## Auto-prepare

The view auto-prepares scanning once it is **connected to the DOM and has both a context and a mode** — the order in which you assign those properties doesn't matter. If you'd rather be explicit (or you want to prepare ahead of time), call `prepareScanning()` yourself after setting everything.

---

## React 18 — ref-binding pattern (also safe on 19)

The scanner waits for the provider's readiness via `useScanditReady()`, reads the context from `DataCaptureContext.sharedInstance`, and binds element **properties** through the ref:

```tsx
import {
    type Barcode,
    SparkScan,
    type SparkScanBarcodeFeedback,
    SparkScanBarcodeSuccessFeedback,
    type SparkScanFeedbackDelegate,
    type SparkScanSession,
    SparkScanSettings,
    SparkScanView,
    Symbology,
} from "@scandit/web-datacapture-barcode";
import { DataCaptureContext } from "@scandit/web-datacapture-core";
import { useEffect, useMemo, useRef, useState } from "react";
import { useScanditReady } from "./ScanditProvider";

// Register the custom element once. On a Vite HMR re-eval this module runs again,
// and customElements.define() throws if the element is already defined — so only
// register when it isn't.
if (!customElements.get("spark-scan-view")) {
    SparkScanView.register();
}

export function Scanner() {
    const ready = useScanditReady();
    const [sparkScan, setSparkScan] = useState<SparkScan | null>(null);
    const viewRef = useRef<SparkScanView | null>(null);

    const listener = useMemo(
        () => ({
            didScan(_mode: SparkScan, session: SparkScanSession) {
                const barcode = session.newlyRecognizedBarcode;
                if (barcode?.data) console.log(barcode.symbology, barcode.data);
            },
        }),
        []
    );

    const feedbackDelegate = useMemo<SparkScanFeedbackDelegate>(
        () => ({
            getFeedbackForBarcode(barcode: Barcode): SparkScanBarcodeFeedback | null {
                // Success for every barcode here; return null for default feedback, or a
                // SparkScanBarcodeErrorFeedback to reject. See the "SparkScan feedback API"
                // section in integration.md for usage and the API-reference links.
                return new SparkScanBarcodeSuccessFeedback();
            },
        }),
        []
    );

    useEffect(() => {
        if (!ready) return;
        const settings = new SparkScanSettings();
        settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);
        const mode = SparkScan.forSettings(settings);
        mode.addListener(listener);
        setSparkScan(mode);

        return () => {
            mode.removeListener(listener);
            viewRef.current?.stopScanning().catch(console.error);
            // Do NOT dispose the context here — this is a per-component unmount, not final
            // app teardown. The shared engine must outlive this component.
        };
    }, [ready, listener]);

    if (!ready || !sparkScan) return null;

    return (
        <div style={{ position: "fixed", inset: 0 }}>
            <spark-scan-view
                ref={(el: SparkScanView | null) => {
                    viewRef.current = el;
                    if (!el) return;
                    // Bind as PROPERTIES via the ref — string attributes won't work on React 18.
                    el.dataCaptureContext = DataCaptureContext.sharedInstance;
                    el.feedbackDelegate = feedbackDelegate;
                    el.sparkScan = sparkScan;
                }}
            />
        </div>
    );
}
```

Key points:
- Readiness comes from the provider (`useScanditReady()`); the context is read from `DataCaptureContext.sharedInstance`, never stored in state or a ref.
- The ref callback assigns real object **properties** (`el.sparkScan = mode`), bypassing React 18's string-attribute serialization.
- Once the context and mode are both set, the view auto-prepares (assignment order doesn't matter).
- Cleanup removes the listener and stops the view but does **not** dispose the shared context — that's not a scanner component's job (see "Disposing the context").

## React 19 — declarative property pattern

On React 19 the JSX props are set as element properties directly, so you can skip the ref binding (still read the context from `sharedInstance`):

```tsx
<spark-scan-view
    dataCaptureContext={DataCaptureContext.sharedInstance}
    sparkScan={sparkScan}
    feedbackDelegate={feedbackDelegate}
    ref={(el: SparkScanView | null) => { viewRef.current = el; }}
/>
```

Everything else (the `ScanditProvider`, gating on `useScanditReady()`, no-dispose cleanup) is identical to the React 18 path. You still keep a ref if you need to call `stopScanning()` / `startScanning()` imperatively.

To get type-checking and editor support for the custom-element props, declare them in JSX's intrinsic elements (see `evals/fixtures/spark-scan-view.d.ts` for a complete declaration to copy).

## Unmounting and remounting the Scanner

The `Scanner` component can be unmounted and remounted freely — for example across route changes. On remount it simply re-creates the SparkScan mode and re-binds the view; you don't need to keep it mounted or hide it with CSS.

The only thing that must outlive these mounts is the shared `DataCaptureContext`. Keep the `ScanditProvider` mounted above your routes so the context persists, and don't dispose it on the Scanner's unmount (see the singleton section above) — the Scanner's own cleanup should just remove its listener and call `stopScanning()`.

---

For driving scanning with your own button instead of the built-in trigger, see the **Custom trigger button** section in `integration.md`. Those behaviors apply to React too — wire the same lifecycle calls (`prepareScanning` / `startScanning` / `pauseScanning` / `stopScanning`) through the `viewRef`.
