import ScanditBarcodeCapture
import ScanditLabelCapture

func buildSettings() throws -> LabelCaptureSettings {
    let labelDefinition = LabelDefinition(
        name: "Perishable Product",
        fields: [
            CustomBarcode(name: "Barcode", symbologies: [.ean13UPCA]),

            ExpiryDateText(name: "Expiry Date")
                .setDataTypePattern("EXP[:\\s]+")
                .setPattern("\\d{2}/\\d{2}/\\d{2,4}"),

            CustomText(name: "Lot Number")
                .setDataTypePatterns(["LOT[:\\s]+", "Batch[:\\s]+"])
                .setPatterns(["[A-Z0-9]{6,}"])
                .optional(true),
        ]
    )
    return try LabelCaptureSettings(labelDefinitions: [labelDefinition])
}
