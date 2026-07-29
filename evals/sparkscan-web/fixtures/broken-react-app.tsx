// ⚠️ INTENTIONALLY BROKEN — test input only, do NOT copy this as a pattern.
// This component reproduces the "works for a second, then dies" bug:
//   - it disposes the process-wide DataCaptureContext on unmount, and
//   - under <React.StrictMode> the dev mount→unmount→remount tears down the
//     shared engine, surfacing "forLicenseKey ... already initializing".
// The skill should diagnose this and rewrite it into the ScanditProvider +
// DataCaptureContext.sharedInstance pattern — not reproduce it.
import {
    barcodeCaptureLoader,
    SparkScan,
    type SparkScanSession,
    SparkScanSettings,
    SparkScanView,
    Symbology,
} from "@scandit/web-datacapture-barcode";
import { DataCaptureContext } from "@scandit/web-datacapture-core";
import { useEffect, useRef, useState } from "react";

SparkScanView.register();

export function Scanner() {
    const [context, setContext] = useState<DataCaptureContext | null>(null);
    const [sparkScan, setSparkScan] = useState<SparkScan | null>(null);
    const viewRef = useRef<SparkScanView | null>(null);

    const listener = {
        didScan(_mode: SparkScan, session: SparkScanSession) {
            const barcode = session.newlyRecognizedBarcode;
            if (barcode?.data) console.log(barcode.symbology, barcode.data);
        },
    };

    useEffect(() => {
        async function init() {
            const ctx = await DataCaptureContext.forLicenseKey(
                "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
                {
                    libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
                    moduleLoaders: [barcodeCaptureLoader()],
                }
            );
            const settings = new SparkScanSettings();
            settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);
            const mode = SparkScan.forSettings(settings);
            mode.addListener(listener);
            setContext(ctx);
            setSparkScan(mode);
        }
        init();

        return () => {
            sparkScan?.removeListener(listener);
            viewRef.current?.stopScanning().catch(console.error);
            context?.dispose(); // BUG: tears down the shared singleton on every unmount
        };
    }, []);

    return (
        <div style={{ position: "fixed", inset: 0 }}>
            {context && sparkScan && (
                <spark-scan-view
                    dataCaptureContext={context}
                    sparkScan={sparkScan}
                    ref={(el: SparkScanView | null) => {
                        viewRef.current = el;
                    }}
                />
            )}
        </div>
    );
}
