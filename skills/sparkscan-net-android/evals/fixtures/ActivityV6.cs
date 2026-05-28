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
public class MainActivity : AppCompatActivity, ISparkScanListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private SparkScan sparkScan = null!;
    private SparkScanView sparkScanView = null!;

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
        this.sparkScan.AddListener(this);

        // v6-era feedback: a single SparkScanFeedback POCO on the SparkScan itself.
        this.sparkScan.Feedback = new SparkScanFeedback
        {
            Success = new Feedback(Vibration.DefaultVibration, Sound.DefaultSound),
            Error = new Feedback(Vibration.DefaultVibration, Sound.DefaultSound),
        };

        SparkScanCoordinatorLayout container =
            this.FindViewById<SparkScanCoordinatorLayout>(Resource.Id.spark_scan_coordinator)!;

        // v6-era view settings: SoundModeOn / HapticModeOn flags and ContinuousCaptureTimeout.
        SparkScanViewSettings viewSettings = new SparkScanViewSettings
        {
            SoundModeOn = true,
            HapticModeOn = true,
            ContinuousCaptureTimeout = TimeSpan.FromSeconds(10),
        };

        this.sparkScanView = SparkScanView.Create(
            parentView: container,
            context: this.dataCaptureContext,
            sparkScan: this.sparkScan,
            settings: viewSettings);

        // v6-era: per-button visibility setter named *ButtonVisible (renamed to *ControlVisible in v7).
        this.sparkScanView.TorchButtonVisible = true;
    }

    public void OnBarcodeScanned(SparkScan sparkScan, SparkScanSession session, IFrameData? frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        this.RunOnUiThread(() => { });
    }

    public void OnSessionUpdated(SparkScan sparkScan, SparkScanSession session, IFrameData? frameData) { }
}
