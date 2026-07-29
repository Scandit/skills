using Android.OS;
using Android.Widget;
using AndroidX.AppCompat.App;

using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.UI.Overlay;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;

namespace MyApp;

[Activity(MainLauncher = true, Label = "@string/app_name")]
public class MainActivity : AppCompatActivity, IBarcodeCaptureListener
{
    private const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeCapture barcodeCapture = null!;
    private Camera? camera;
    private DataCaptureView dataCaptureView = null!;
    private BarcodeCaptureOverlay overlay = null!;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        this.SetContentView(Resource.Layout.activity_main);
        this.InitializeAndStartBarcodeScanning();
    }

    private void InitializeAndStartBarcodeScanning()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        var cameraSettings = new CameraSettings { PreferredResolution = VideoResolution.Auto };
        this.camera = Camera.GetDefaultCamera();
        this.camera?.ApplySettingsAsync(cameraSettings);
        this.dataCaptureContext.SetFrameSourceAsync(this.camera);

        BarcodeCaptureSettings settings = BarcodeCaptureSettings.Create();
        settings.EnableSymbology(Symbology.Ean13Upca, true);
        settings.EnableSymbology(Symbology.Code128, true);

        this.barcodeCapture = BarcodeCapture.Create(this.dataCaptureContext, settings);
        this.barcodeCapture.AddListener(this);

        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
        this.overlay = BarcodeCaptureOverlay.Create(this.barcodeCapture, this.dataCaptureView);

        var container = this.FindViewById<FrameLayout>(Resource.Id.data_capture_view_container);
        container?.AddView(
            this.dataCaptureView,
            new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MatchParent,
                ViewGroup.LayoutParams.MatchParent));
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.barcodeCapture.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.barcodeCapture.Enabled = false;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    protected override void OnDestroy()
    {
        this.barcodeCapture.RemoveListener(this);
        base.OnDestroy();
    }

    public void OnBarcodeScanned(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        barcodeCapture.Enabled = false;
        this.RunOnUiThread(() => { });
    }

    public void OnSessionUpdated(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData) { }

    public void OnObservationStarted(BarcodeCapture barcodeCapture) { }
    public void OnObservationStopped(BarcodeCapture barcodeCapture) { }
}
