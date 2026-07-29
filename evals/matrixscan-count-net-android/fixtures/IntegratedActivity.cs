using Android.OS;
using Android.Widget;

using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Count.UI;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

namespace MyApp;

[Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
public class MainActivity : CameraPermissionActivity
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private Camera? camera;
    private BarcodeCount barcodeCount = null!;
    private BarcodeCountView barcodeCountView = null!;

    private readonly List<Barcode> scannedBarcodes = new();

    protected override async void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera(BarcodeCount.RecommendedCameraSettings);
        if (this.camera is not null)
        {
            await this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        BarcodeCountSettings settings = new BarcodeCountSettings();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });
        this.barcodeCount = BarcodeCount.Create(this.dataCaptureContext, settings);

        var container = new FrameLayout(this);
        this.SetContentView(container);
        this.barcodeCountView = BarcodeCountView.Create(
            this, this.dataCaptureContext, this.barcodeCount, BarcodeCountViewStyle.Icon);
        container.AddView(this.barcodeCountView);

        this.barcodeCountView.ListButtonTapped += (s, e) => this.ShowResults();
        this.barcodeCountView.ExitButtonTapped += (s, e) => this.ShowResults();
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.barcodeCount.Scanned += this.OnBarcodeCountScanned;
        this.barcodeCount.Enabled = true;
        this.RequestCameraPermission();
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
        this.barcodeCount.Scanned -= this.OnBarcodeCountScanned;
    }

    protected override void OnCameraPermissionGranted()
    {
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    protected override void OnDestroy()
    {
        base.OnDestroy();
        this.barcodeCount.Scanned -= this.OnBarcodeCountScanned;
        this.barcodeCountView.Dispose();
        this.barcodeCount.Dispose();
    }

    private void OnBarcodeCountScanned(object? sender, BarcodeCountEventArgs args)
    {
        List<Barcode> recognized = args.Session.RecognizedBarcodes.ToList();
        this.RunOnUiThread(() =>
        {
            this.scannedBarcodes.Clear();
            this.scannedBarcodes.AddRange(recognized);
        });
    }

    private void ShowResults()
    {
        // Present this.scannedBarcodes to the user.
    }
}
