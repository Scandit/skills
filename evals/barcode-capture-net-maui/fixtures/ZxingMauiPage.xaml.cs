using ZXing.Net.Maui;

namespace MyApp.Views;

public record ScannedBarcode(string Value, string Format);

public partial class ScannerPage : ContentPage
{
    private readonly List<ScannedBarcode> scannedBarcodes = new();

    public ScannerPage()
    {
        this.InitializeComponent();
        this.cameraView.Options = new BarcodeReaderOptions
        {
            Formats = BarcodeFormat.Ean13 | BarcodeFormat.Code128 | BarcodeFormat.QrCode,
            AutoRotate = true,
            Multiple = false,
        };
    }

    private void OnBarcodesDetected(object? sender, BarcodeDetectionEventArgs e)
    {
        if (e.Results.Length == 0) return;
        var result = e.Results[0];

        var barcode = new ScannedBarcode(result.Value, result.Format.ToString());
        if (!this.scannedBarcodes.Any(b => b.Value == barcode.Value))
        {
            this.scannedBarcodes.Add(barcode);
            MainThread.BeginInvokeOnMainThread(() =>
            {
                this.resultLabel.Text = $"Last scan: {barcode.Value} ({this.scannedBarcodes.Count} total)";
            });
        }
    }
}
