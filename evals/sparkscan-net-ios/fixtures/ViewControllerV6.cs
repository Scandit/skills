using CoreFoundation;
using UIKit;

using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;
using Scandit.DataCapture.Barcode.Spark.Feedback;
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Core.Capture;

namespace MyApp;

public partial class ViewController : UIViewController, ISparkScanListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private SparkScan sparkScan = null!;
    private SparkScanView sparkScanView = null!;

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

        SparkScanSettings settings = new SparkScanSettings();
        settings.EnableSymbology(Symbology.Ean13Upca, true);
        settings.EnableSymbology(Symbology.Code128, true);

        this.sparkScan = new SparkScan(settings);
        this.sparkScan.AddListener(this);

        // v6-era feedback: a single SparkScanFeedback POCO on the SparkScan itself.
        this.sparkScan.Feedback = new SparkScanFeedback
        {
            Success = new Feedback(Vibration.DefaultVibration, Sound.DefaultSound),
            Error = new Feedback(Vibration.DefaultVibration, Sound.DefaultSound),
        };

        // v6-era view settings: SoundModeOn / HapticModeOn flags and ContinuousCaptureTimeout.
        SparkScanViewSettings viewSettings = new SparkScanViewSettings
        {
            SoundModeOn = true,
            HapticModeOn = true,
            ContinuousCaptureTimeout = TimeSpan.FromSeconds(10),
        };

        this.sparkScanView = SparkScanView.Create(
            parentView: this.View!,
            context: this.dataCaptureContext,
            sparkScan: this.sparkScan,
            settings: viewSettings);

        // v6-era: per-button visibility named *ButtonVisible (renamed to *ControlVisible in v7).
        this.sparkScanView.TorchButtonVisible = true;
    }

    public void OnBarcodeScanned(SparkScan sparkScan, SparkScanSession session, IFrameData? frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        DispatchQueue.MainQueue.DispatchAsync(() => { });
    }

    public void OnSessionUpdated(SparkScan sparkScan, SparkScanSession session, IFrameData? frameData) { }
}
