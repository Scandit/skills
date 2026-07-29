using CoreFoundation;
using UIKit;

using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;
using Scandit.DataCapture.Barcode.Spark.Feedback;
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Core.Capture;

namespace MyApp;

public partial class ViewController : UIViewController, ISparkScanFeedbackDelegate
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private SparkScan sparkScan = null!;
    private SparkScanView sparkScanView = null!;

    private SparkScanBarcodeSuccessFeedback successFeedback = null!;
    private SparkScanBarcodeErrorFeedback errorFeedback = null!;

    public ViewController(IntPtr handle) : base(handle) { }
    public ViewController() { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.SetupSparkScan();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.sparkScanView.PrepareScanning();
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.sparkScanView.StopScanning();
    }

    private void SetupSparkScan()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        SparkScanSettings settings = new();
        settings.EnableSymbology(Symbology.Ean13Upca, true);
        settings.EnableSymbology(Symbology.Code128, true);

        this.sparkScan = new SparkScan(settings);
        this.sparkScan.BarcodeScanned += this.BarcodeScanned;

        SparkScanViewSettings viewSettings = new();

        if (this.View == null)
        {
            throw new InvalidOperationException("Cannot initialize view");
        }

        this.sparkScanView = SparkScanView.Create(
            parentView: this.View,
            context: this.dataCaptureContext,
            sparkScan: this.sparkScan,
            settings: viewSettings);

        this.successFeedback = new SparkScanBarcodeSuccessFeedback();
        this.errorFeedback = new SparkScanBarcodeErrorFeedback(
            message: "Wrong barcode",
            resumeCapturingDelay: TimeSpan.FromSeconds(60));
        this.sparkScanView.Feedback = this;
    }

    private void BarcodeScanned(object? sender, SparkScanEventArgs args)
    {
        var barcode = args.Session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        using var imageBuffer = args.FrameData?.ImageBuffers.LastOrDefault();
        using var frame = imageBuffer?.ToImage();

        DispatchQueue.MainQueue.DispatchAsync(() => { });
    }

    SparkScanBarcodeFeedback ISparkScanFeedbackDelegate.GetFeedbackForBarcode(Barcode barcode) =>
        IsBarcodeValid(barcode) ? this.successFeedback : this.errorFeedback;

    private static bool IsBarcodeValid(Barcode barcode) => barcode.Data != "123456789";
}
