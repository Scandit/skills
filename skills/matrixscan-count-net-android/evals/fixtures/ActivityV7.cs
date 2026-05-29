// Example .NET for Android MatrixScan Count integration on Scandit SDK 7.x.
// This uses the same BarcodeCount surface as 8.x but predates the explicit-init
// requirement, so it has no `MainApplication.cs` and never calls
// `ScanditCaptureCore.Initialize()` / `ScanditBarcodeCapture.Initialize()`.
// Bumping the Scandit .NET SDK to 8.x without adding those calls will crash on
// first launch.
//
// .csproj reference at the time of writing (illustrative):
//   <PackageReference Include="Scandit.DataCapture.Core" Version="7.4.0" />
//   <PackageReference Include="Scandit.DataCapture.Barcode" Version="7.4.0" />

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
        this.RunOnUiThread(() => { /* update UI */ });
    }
}
