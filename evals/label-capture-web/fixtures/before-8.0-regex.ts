import { Symbology } from "@scandit/web-datacapture-barcode";
import {
  CustomBarcodeBuilder,
  CustomTextBuilder,
  ExpiryDateTextBuilder,
  LabelCaptureSettingsBuilder,
  LabelDefinitionBuilder,
} from "@scandit/web-datacapture-label";

export async function buildSettings() {
  const expiryBuilder = new ExpiryDateTextBuilder()
    .setDataTypePattern("EXP[:\\s]+")
    .setPattern("\\d{2}/\\d{2}/\\d{2,4}");

  const lotBuilder = new CustomTextBuilder()
    .setDataTypePatterns(["LOT[:\\s]+", "Batch[:\\s]+"])
    .setPatterns(["[A-Z0-9]{6,}"]);

  return await new LabelCaptureSettingsBuilder()
    .addLabel(
      await new LabelDefinitionBuilder()
        .addCustomBarcode(
          await new CustomBarcodeBuilder()
            .setSymbology(Symbology.EAN13UPCA)
            .build("Barcode")
        )
        .addExpiryDateText(await expiryBuilder.build("Expiry Date"))
        .addCustomText(await lotBuilder.build("Lot Number"))
        .build("Perishable Product")
    )
    .build();
}
