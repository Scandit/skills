using Android.OS;
using Android.Widget;
using AndroidX.AppCompat.App;
using ZXing.Mobile;

namespace MyApp;

public record ScannedBarcode(string Value, string Format);

[Activity(MainLauncher = true, Label = "Scanner")]
public class ScannerActivity : AppCompatActivity
{
    private TextView resultLabel = null!;
    private MobileBarcodeScanner scanner = null!;
    private readonly List<ScannedBarcode> scannedBarcodes = new();

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        this.SetContentView(Resource.Layout.activity_scanner);
        this.resultLabel = this.FindViewById<TextView>(Resource.Id.resultLabel)!;
        this.scanner = new MobileBarcodeScanner();
        _ = this.StartScanLoopAsync();
    }

    private async Task StartScanLoopAsync()
    {
        var options = new MobileBarcodeScanningOptions
        {
            PossibleFormats = new List<ZXing.BarcodeFormat>
            {
                ZXing.BarcodeFormat.EAN_13,
                ZXing.BarcodeFormat.CODE_128,
                ZXing.BarcodeFormat.QR_CODE,
            },
            UseFrontCameraIfAvailable = false,
        };

        // "Batch" behavior built on top of a single-scan API: re-trigger the scanner
        // after each result and dedupe by raw value.
        var result = await this.scanner.Scan(options);
        if (result != null && !string.IsNullOrEmpty(result.Text))
        {
            var barcode = new ScannedBarcode(result.Text, result.BarcodeFormat.ToString());
            if (!this.scannedBarcodes.Any(b => b.Value == barcode.Value))
            {
                this.scannedBarcodes.Add(barcode);
                this.resultLabel.Text =
                    $"Last scan: {barcode.Value} ({this.scannedBarcodes.Count} total)";
            }
            _ = this.StartScanLoopAsync();
        }
    }
}
