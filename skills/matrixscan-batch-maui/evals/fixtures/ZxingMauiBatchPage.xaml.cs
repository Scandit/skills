using ZXing.Net.Maui;

namespace MyApp.Views;

public record ScannedBarcode(string Value, string Format);

public partial class MainPage : ContentPage
{
    private readonly List<ScannedBarcode> scannedBarcodes = new();

    public MainPage()
    {
        this.InitializeComponent();

        this.cameraView.Options = new BarcodeReaderOptions
        {
            Formats = BarcodeFormat.Ean13 | BarcodeFormat.Code128 | BarcodeFormat.QrCode,
            AutoRotate = true,
            // Multi-result per frame — emulating MatrixScan Batch with ZXing.
            Multiple = true,
        };
    }

    private void OnBarcodesDetected(object? sender, BarcodeDetectionEventArgs e)
    {
        if (e.Results.Length == 0) return;

        // For each new barcode in this frame, dedupe on Value and append.
        var newOnes = new List<ScannedBarcode>();
        foreach (var result in e.Results)
        {
            var barcode = new ScannedBarcode(result.Value, result.Format.ToString());
            if (!this.scannedBarcodes.Any(b => b.Value == barcode.Value))
            {
                this.scannedBarcodes.Add(barcode);
                newOnes.Add(barcode);
            }
        }

        if (newOnes.Count == 0) return;

        MainThread.BeginInvokeOnMainThread(() =>
        {
            this.resultLabel.Text = $"{this.scannedBarcodes.Count} total scanned";
        });
    }
}
