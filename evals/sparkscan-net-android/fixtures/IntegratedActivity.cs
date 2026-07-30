using Android.OS;
using AndroidX.AppCompat.App;

using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;
using Scandit.DataCapture.Barcode.Spark.Feedback;
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Barcode.Spark.UI.Platform.Android;
using Scandit.DataCapture.Core.Capture;

namespace MyApp;

[Activity(MainLauncher = true, Label = "@string/app_name")]
public class MainActivity : AppCompatActivity, ISparkScanFeedbackDelegate
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private SparkScan sparkScan = null!;
    private SparkScanView sparkScanView = null!;

    private SparkScanBarcodeSuccessFeedback successFeedback = null!;
    private SparkScanBarcodeErrorFeedback errorFeedback = null!;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        this.SetContentView(Resource.Layout.activity_main);
        this.Initialize();
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.sparkScanView.OnPause();
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.sparkScanView.OnResume();
    }

    private void Initialize()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        SparkScanSettings settings = new SparkScanSettings();
        settings.EnableSymbology(Symbology.Ean13Upca, true);
        settings.EnableSymbology(Symbology.Code128, true);

        this.sparkScan = new SparkScan(settings);
        this.sparkScan.BarcodeScanned += this.OnBarcodeScanned;

        SparkScanCoordinatorLayout container =
            this.FindViewById<SparkScanCoordinatorLayout>(Resource.Id.spark_scan_coordinator)!;
        SparkScanViewSettings viewSettings = new SparkScanViewSettings();

        this.sparkScanView = SparkScanView.Create(
            parentView: container,
            context: this.dataCaptureContext,
            sparkScan: this.sparkScan,
            settings: viewSettings);

        this.successFeedback = new SparkScanBarcodeSuccessFeedback();
        this.errorFeedback = new SparkScanBarcodeErrorFeedback(
            message: "Wrong barcode",
            resumeCapturingDelay: TimeSpan.FromSeconds(60));
        this.sparkScanView.Feedback = this;
    }

    private void OnBarcodeScanned(object? sender, SparkScanEventArgs args)
    {
        var barcode = args.Session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        this.RunOnUiThread(() => { });
    }

    SparkScanBarcodeFeedback ISparkScanFeedbackDelegate.GetFeedbackForBarcode(Barcode barcode) =>
        IsBarcodeValid(barcode) ? this.successFeedback : this.errorFeedback;

    private static bool IsBarcodeValid(Barcode barcode) => barcode.Data != "123456789";
}
