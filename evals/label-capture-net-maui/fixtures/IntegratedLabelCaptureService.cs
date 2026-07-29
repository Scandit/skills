using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay;

namespace MyApp.Services;

internal class LabelCaptureService(DataCaptureContext dataCaptureContext) : ILabelCaptureService
{
    public const string FIELD_BARCODE = "Barcode";
    public const string FIELD_EXPIRY_DATE = "Expiry Date";
    public const string LABEL_RETAIL_ITEM = "Retail Item";

    private readonly LabelCapture labelCapture =
        LabelCapture.Create(dataCaptureContext, BuildLabelCaptureSettings());

    public bool IsEnabled => this.labelCapture.Enabled;

    public void Enable() => this.labelCapture.Enabled = true;

    public void Disable() => this.labelCapture.Enabled = false;

    public LabelCaptureBasicOverlay BuildOverlay()
    {
        return LabelCaptureBasicOverlay.Create(this.labelCapture);
    }

    public CapturedLabel? GetFirstLabel(LabelCaptureSession session)
    {
        return session.CapturedLabels.Count > 0 ? session.CapturedLabels[0] : null;
    }

    public void Subscribe(EventHandler<LabelCaptureEventArgs> handler)
    {
        this.labelCapture.SessionUpdated += handler;
    }

    public void Unsubscribe(EventHandler<LabelCaptureEventArgs> handler)
    {
        this.labelCapture.SessionUpdated -= handler;
    }

    private static LabelCaptureSettings BuildLabelCaptureSettings()
    {
        var fields = new List<LabelFieldDefinition>();

        fields.Add(CustomBarcode.Builder()
            .SetSymbologies(new List<Symbology>
            {
                Symbology.Ean13Upca,
                Symbology.Code128,
            })
            .Build(FIELD_BARCODE));

        fields.Add(ExpiryDateText.Builder()
            .SetLabelDateFormat(new LabelDateFormat(LabelDateComponentFormat.MDY, acceptPartialDates: false))
            .Build(FIELD_EXPIRY_DATE));

        var labelDefinition = LabelDefinition.Create(LABEL_RETAIL_ITEM, fields);
        return LabelCaptureSettings.Create(new List<LabelDefinition> { labelDefinition });
    }
}
