using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;
using Scandit.DataCapture.Barcode.Spark.Feedback;
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Core.Capture;

namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    public DataCaptureContext DataCaptureContext { get; }
    public SparkScan SparkScan { get; }
    public SparkScanViewSettings ViewSettings { get; }

    public MainPage()
    {
        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        SparkScanSettings settings = new SparkScanSettings();
        settings.EnableSymbology(Symbology.Ean13Upca, true);
        settings.EnableSymbology(Symbology.Code128, true);

        this.SparkScan = new SparkScan(settings);
        this.SparkScan.BarcodeScanned += this.OnBarcodeScanned;

        // v6-era feedback: a single SparkScanFeedback POCO on the SparkScan itself.
        this.SparkScan.Feedback = new SparkScanFeedback
        {
            Success = new Feedback(Vibration.DefaultVibration, Sound.DefaultSound),
            Error = new Feedback(Vibration.DefaultVibration, Sound.DefaultSound),
        };

        // v6-era view settings.
        this.ViewSettings = new SparkScanViewSettings
        {
            SoundModeOn = true,
            HapticModeOn = true,
            ContinuousCaptureTimeout = TimeSpan.FromSeconds(10),
        };

        this.InitializeComponent();
        this.BindingContext = this;

        // v6-era control name.
        this.SparkScanView.TorchButtonVisible = true;
    }

    protected override void OnAppearing()
    {
        base.OnAppearing();
        this.SparkScanView.OnAppearing();
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        this.SparkScanView.OnDisappearing();
    }

    private void OnBarcodeScanned(object? sender, SparkScanEventArgs args)
    {
        var barcode = args.Session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        MainThread.BeginInvokeOnMainThread(() => { });
    }
}
