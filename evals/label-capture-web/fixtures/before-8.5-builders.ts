import { Symbology } from "@scandit/web-datacapture-barcode";
import {
  CustomBarcodeBuilder,
  ExpiryDateTextBuilder,
  LabelCaptureSettingsBuilder,
  LabelDefinitionBuilder,
  TotalPriceTextBuilder,
} from "@scandit/web-datacapture-label";

export async function buildSettings() {
  return await new LabelCaptureSettingsBuilder()
    .addLabel(
      await new LabelDefinitionBuilder()
        .addCustomBarcode(
          await new CustomBarcodeBuilder()
            .setSymbology(Symbology.EAN13UPCA)
            .build("Barcode")
        )
        .addExpiryDateText(await new ExpiryDateTextBuilder().build("Expiry Date"))
        .addTotalPriceText(await new TotalPriceTextBuilder().build("Total Price"))
        .build("Perishable Product")
    )
    .build();
}
