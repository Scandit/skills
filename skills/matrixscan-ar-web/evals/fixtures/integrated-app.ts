import {
  BarcodeAr,
  BarcodeArSession,
  BarcodeArSettings,
  BarcodeArView,
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
  BarcodeArHighlightProvider,
  BarcodeArAnnotationProvider,
  BarcodeArPopoverAnnotation,
  BarcodeArPopoverAnnotationButton,
  barcodeCaptureLoader,
  Barcode,
  Symbology,
} from "@scandit/web-datacapture-barcode";
import { DataCaptureContext, ScanditIconBuilder, ScanditIconType } from "@scandit/web-datacapture-core";

async function run(): Promise<void> {
  await DataCaptureContext.forLicenseKey(
    "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
    {
      libraryLocation: new URL("library/engine/", document.baseURI).toString(),
      moduleLoaders: [barcodeCaptureLoader()],
    }
  );

  const settings: BarcodeArSettings = new BarcodeArSettings();
  settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.EAN8, Symbology.Code128]);

  const barcodeAr: BarcodeAr = await BarcodeAr.forContext(DataCaptureContext.sharedInstance, settings);

  barcodeAr.addListener({
    didUpdateSession: (_barcodeAr: BarcodeAr, session: BarcodeArSession) => {
      for (const tracked of Object.values(session.addedTrackedBarcodes)) {
        console.log("New barcode:", tracked.barcode.data);
      }
    },
  });

  const container: HTMLElement = document.getElementById("barcode-ar-view")!;
  const barcodeArView: BarcodeArView = await BarcodeArView.create(container, DataCaptureContext.sharedInstance, barcodeAr);
  barcodeArView.shouldShowTorchControl = true;

  const highlightProvider: BarcodeArHighlightProvider = {
    async highlightForBarcode(barcode: Barcode, callback: (highlight: BarcodeArCircleHighlight | null) => void): Promise<void> {
      const highlight: BarcodeArCircleHighlight = BarcodeArCircleHighlight.create(barcode, BarcodeArCircleHighlightPreset.Dot);
      callback(highlight);
    },
  };
  barcodeArView.highlightProvider = highlightProvider;

  const annotationProvider: BarcodeArAnnotationProvider = {
    async annotationForBarcode(barcode: Barcode, callback: (annotation: BarcodeArPopoverAnnotation | null) => void): Promise<void> {
      const annotation: BarcodeArPopoverAnnotation = BarcodeArPopoverAnnotation.create(barcode);

      const detailsIcon = await new ScanditIconBuilder().withIcon(ScanditIconType.InspectItem).build();
      const detailsButton: BarcodeArPopoverAnnotationButton = BarcodeArPopoverAnnotationButton.create(detailsIcon, "Details");
      detailsButton.addEventListener("click", () => {
        console.log("Details clicked for:", barcode.data);
      });

      const cartIcon = await new ScanditIconBuilder().withIcon(ScanditIconType.Checkmark).build();
      const addToCartButton: BarcodeArPopoverAnnotationButton = BarcodeArPopoverAnnotationButton.create(cartIcon, "Add to Cart");
      addToCartButton.addEventListener("click", () => {
        console.log("Add to Cart clicked for:", barcode.data);
      });

      annotation.append(detailsButton, addToCartButton);
      callback(annotation);
    },
  };
  barcodeArView.annotationProvider = annotationProvider;

  await barcodeArView.start();
}

run();
