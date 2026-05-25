using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Spark.Capture;
using Scandit.DataCapture.Barcode.Spark.Feedback;
using Scandit.DataCapture.Barcode.Spark.UI;
using Scandit.DataCapture.Core.Capture;

namespace MyApp.Views;

public partial class MainPage : ContentPage, ISparkScanFeedbackDelegate
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    public DataCaptureContext DataCaptureContext { get; }
    public SparkScan SparkScan { get; }
    public SparkScanViewSettings ViewSettings { get; } = new();

    private readonly SparkScanBarcodeSuccessFeedback successFeedback = new();
    private readonly SparkScanBarcodeErrorFeedback errorFeedback =
        new(message: "Wrong barcode", resumeCapturingDelay: TimeSpan.FromSeconds(60));

    public MainPage()
    {
        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        SparkScanSettings settings = new();
        settings.EnableSymbology(Symbology.Ean13Upca, true);
        settings.EnableSymbology(Symbology.Code128, true);

        this.SparkScan = new SparkScan(settings);
        this.SparkScan.BarcodeScanned += this.OnBarcodeScanned;

        this.InitializeComponent();
        this.BindingContext = this;
        this.SparkScanView.Feedback = this;
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();
        this.SparkScanView.OnAppearing();

        var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted)
        {
            await Permissions.RequestAsync<Permissions.Camera>();
        }
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

    SparkScanBarcodeFeedback ISparkScanFeedbackDelegate.GetFeedbackForBarcode(Barcode barcode) =>
        IsBarcodeValid(barcode) ? this.successFeedback : this.errorFeedback;

    private static bool IsBarcodeValid(Barcode barcode) => barcode.Data != "123456789";
}
