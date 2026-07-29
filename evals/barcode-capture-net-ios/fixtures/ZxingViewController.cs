using UIKit;
using ZXing.Mobile;

namespace MyApp;

public record ScannedBarcode(string Value, string Format);

public partial class ScannerViewController : UIViewController
{
    private MobileBarcodeScanner scanner = null!;
    private readonly List<ScannedBarcode> scannedBarcodes = new();
    private UILabel resultLabel = null!;

    public ScannerViewController(IntPtr handle) : base(handle) { }
    public ScannerViewController() { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.View!.BackgroundColor = UIColor.SystemBackground;

        this.resultLabel = new UILabel(this.View.Bounds)
        {
            TextAlignment = UITextAlignment.Center,
            AutoresizingMask = UIViewAutoresizing.FlexibleWidth | UIViewAutoresizing.FlexibleHeight,
        };
        this.View.AddSubview(this.resultLabel);

        this.scanner = new MobileBarcodeScanner();
        _ = this.StartScanAsync();
    }

    private async Task StartScanAsync()
    {
        var options = new MobileBarcodeScanningOptions
        {
            PossibleFormats = new List<ZXing.BarcodeFormat>
            {
                ZXing.BarcodeFormat.EAN_13,
                ZXing.BarcodeFormat.CODE_128,
                ZXing.BarcodeFormat.QR_CODE
            },
            UseFrontCameraIfAvailable = false,
        };

        var result = await this.scanner.Scan(options);
        if (result != null && !string.IsNullOrEmpty(result.Text))
        {
            var barcode = new ScannedBarcode(result.Text, result.BarcodeFormat.ToString());
            if (!this.scannedBarcodes.Any(b => b.Value == barcode.Value))
            {
                this.scannedBarcodes.Add(barcode);
                this.resultLabel.Text = $"Last scan: {barcode.Value} ({this.scannedBarcodes.Count} total)";
            }
            _ = this.StartScanAsync();
        }
    }
}
