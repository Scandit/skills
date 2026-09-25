// Drop-in React context provider for one-time Scandit SDK configuration.
// Mount <ScanditProvider> once at the app root; it calls DataCaptureContext.forLicenseKey
// (which the SDK caches internally, so the engine initializes only once — even under
// React StrictMode's extra dev mount/unmount/remount). Consumers gate on useScanditReady()
// and then read the context from DataCaptureContext.sharedInstance.
import { barcodeCaptureLoader } from "@scandit/web-datacapture-barcode";
import { DataCaptureContext } from "@scandit/web-datacapture-core";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

const ScanditReadyContext = createContext(false);

export function ScanditProvider({ children }: { children: ReactNode }) {
    const [ready, setReady] = useState(false);

    useEffect(() => {
        let cancelled = false;
        // forLicenseKey is cached internally by the SDK — the StrictMode dev double-invoke
        // resolves to the same initialization rather than starting a second one. The resolved
        // instance is intentionally not kept here; read it from DataCaptureContext.sharedInstance.
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
            libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
            moduleLoaders: [barcodeCaptureLoader()],
        })
            .then(() => {
                if (!cancelled) setReady(true);
            })
            .catch(console.error);
        // No dispose() on per-mount cleanup. Release the singleton only at final app teardown
        // (e.g. a window "pagehide" handler) — never on a scanner component or route unmount.
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
