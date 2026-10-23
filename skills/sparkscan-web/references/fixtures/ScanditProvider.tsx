// Drop-in React context provider for one-time Scandit SDK configuration.
// Mount <ScanditProvider> once at the app root; it calls DataCaptureContext.forLicenseKey
// (which the SDK caches internally, so the engine initializes only once — even under
// React StrictMode's extra dev mount/unmount/remount). Consumers gate on useScanditReady()
// and then read the context from DataCaptureContext.sharedInstance.
import { barcodeCaptureLoader } from "@scandit/web-datacapture-barcode";
import { BrowserHelper, DataCaptureContext } from "@scandit/web-datacapture-core";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

const ScanditReadyContext = createContext(false);

const multithreadingWarningDismissedKey = "scandit-multithreading-warning-dismissed";
let multithreadingWarningShown = false;

function isMultithreadingWarningDismissed() {
    try {
        return sessionStorage.getItem(multithreadingWarningDismissedKey) === "true";
    } catch {
        return false;
    }
}

function rememberMultithreadingWarningDismissed() {
    try {
        sessionStorage.setItem(multithreadingWarningDismissedKey, "true");
    } catch {}
}

export function ScanditProvider({ children }: { children: ReactNode }) {
    const [ready, setReady] = useState(false);
    const warningRef = useRef<HTMLDialogElement>(null);
    const [multithreadingUnavailable, setMultithreadingUnavailable] = useState(false);
    const [dontShowAgain, setDontShowAgain] = useState(false);

    useEffect(() => {
        if (multithreadingUnavailable && !warningRef.current?.open) {
            warningRef.current?.showModal();
        }
    }, [multithreadingUnavailable]);

    useEffect(() => {
        let cancelled = false;
        async function initialize() {
            BrowserHelper.checkMultithreadingSupport()
                .then((multithreadingSupported) => {
                    if (cancelled) return;
                    if (!multithreadingSupported && !multithreadingWarningShown && !isMultithreadingWarningDismissed()) {
                        multithreadingWarningShown = true;
                        setMultithreadingUnavailable(true);
                    }
                })
                .catch(console.error);

            // forLicenseKey is cached internally by the SDK — the StrictMode dev double-invoke
            // resolves to the same initialization rather than starting a second one. The resolved
            // instance is intentionally not kept here; read it from DataCaptureContext.sharedInstance.
            await DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
                libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
                moduleLoaders: [barcodeCaptureLoader()],
            });
            if (!cancelled) setReady(true);
        }

        initialize().catch(console.error);

        // No dispose() on per-mount cleanup. Release the singleton only at final app teardown
        // (e.g. a window "pagehide" handler) — never on a scanner component or route unmount.
        return () => {
            cancelled = true;
        };
    }, []);

    return (
        <ScanditReadyContext.Provider value={ready}>
            {children}
            {multithreadingUnavailable && (
                <dialog
                    ref={warningRef}
                    onClose={() => {
                        if (dontShowAgain) {
                            rememberMultithreadingWarningDismissed();
                        }
                    }}
                >
                    <form method="dialog">
                        <h2>Scanning may be slower</h2>
                        <p>
                            This browser or device can't use all of its processing power for scanning. You can keep
                            scanning, but scanning may take longer.
                        </p>
                        <p>
                            <a
                                href="https://docs.scandit.com/sdks/web/matrixscan/get-started/#improve-runtime-performance-by-enabling-browser-multithreading"
                                target="_blank"
                                rel="noopener"
                            >
                                Learn more
                            </a>
                        </p>
                        <label>
                            <input
                                type="checkbox"
                                checked={dontShowAgain}
                                onChange={(event) => setDontShowAgain(event.target.checked)}
                            />{" "}
                            Don't show this again during this session
                        </label>
                        <button autoFocus>OK</button>
                    </form>
                </dialog>
            )}
        </ScanditReadyContext.Provider>
    );
}

// True once configuration has completed. Consumers then read the context from
// DataCaptureContext.sharedInstance — no need to thread the instance around.
export function useScanditReady(): boolean {
    return useContext(ScanditReadyContext);
}
