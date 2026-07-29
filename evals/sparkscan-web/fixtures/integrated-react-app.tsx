import {
    type Barcode,
    barcodeCaptureLoader,
    SparkScan,
    SparkScanBarcodeErrorFeedback,
    SparkScanBarcodeSuccessFeedback,
    type SparkScanSession,
    SparkScanSettings,
    SparkScanView,
    Symbology,
    SymbologyDescription,
} from "@scandit/web-datacapture-barcode";
import { DataCaptureContext } from "@scandit/web-datacapture-core";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

SparkScanView.register();

export function SparkScanScannerComponent() {
    const [dataCaptureContext, setDataCaptureContext] = useState<DataCaptureContext | null>(null);
    const [sparkScan, setSparkScan] = useState<SparkScan | null>(null);
    const [scannedCodes, setScannedCodes] = useState<string[]>([]);
    const sparkScanViewRef = useRef<SparkScanView | null>(null);

    const addCode = useCallback((data: string) => {
        setScannedCodes((prev) => [...prev, data]);
    }, []);

    const sparkScanListener = useMemo(
        () => ({
            didScan(_mode: SparkScan, session: SparkScanSession) {
                const barcode = session.newlyRecognizedBarcode;
                if (barcode?.data) {
                    const symbology = new SymbologyDescription(barcode.symbology).readableName;
                    addCode(`${barcode.data} (${symbology})`);
                }
            },
        }),
        [addCode]
    );

    useEffect(() => {
        let isMounted = true;

        async function initialize() {
            await DataCaptureContext.forLicenseKey(
                "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
                {
                    libraryLocation: new URL("library/engine/", document.baseURI).toString(),
                    moduleLoaders: [barcodeCaptureLoader()],
                }
            );

            const settings = new SparkScanSettings();
            settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

            const mode = SparkScan.forSettings(settings);
            mode.addListener(sparkScanListener);

            if (isMounted) {
                setDataCaptureContext(DataCaptureContext.sharedInstance);
                setSparkScan(mode);
            }
        }

        initialize();

        return () => {
            isMounted = false;
            mode.removeListener(sparkScanListener);
            sparkScanViewRef.current?.stopScanning().catch(console.error);
        };
    }, [sparkScanListener]);

    return (
        <>
            {dataCaptureContext && sparkScan ? (
                <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%' }}>
                    <spark-scan-view
                        dataCaptureContext={dataCaptureContext}
                        sparkScan={sparkScan}
                        ref={(view: SparkScanView | null) => {
                            sparkScanViewRef.current = view;
                        }}
                    />
                </div>
            ) : null}
            <ul>
                {scannedCodes.map((code, i) => (
                    <li key={i}>{code}</li>
                ))}
            </ul>
        </>
    );
}
