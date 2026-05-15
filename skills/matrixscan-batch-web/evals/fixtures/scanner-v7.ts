import { configure, DataCaptureContext } from "@scandit/web-datacapture-core";
import { barcodeCaptureLoader, BarcodeBatch, BarcodeBatchSettings, Symbology } from "@scandit/web-datacapture-barcode";

await configure({
    libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
    licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
    moduleLoaders: [barcodeCaptureLoader()],
});

const context = await DataCaptureContext.create();

const settings = new BarcodeBatchSettings();
settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

const barcodeBatch = await BarcodeBatch.forContext(context, settings);

barcodeBatch.addListener({
    didUpdateSession: (_mode, session) => {
        console.log("Tracked:", Object.keys(session.trackedBarcodes).length);
    },
});
