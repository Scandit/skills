using Android.OS;
using Android.Widget;
using AndroidX.AppCompat.App;

using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Tracking.Capture;
using Scandit.DataCapture.Barcode.Tracking.Data;
using Scandit.DataCapture.Barcode.Tracking.UI.Overlay;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;

namespace MyApp;

[Activity(MainLauncher = true, Label = "@string/app_name")]
public class MainActivity : AppCompatActivity, IBarcodeTrackingListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeTracking barcodeTracking = null!;
    private Camera? camera;
    private DataCaptureView dataCaptureView = null!;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        this.SetContentView(Resource.Layout.activity_main);
        this.InitializeAndStartTracking();
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.barcodeTracking.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.barcodeTracking.Enabled = false;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    protected override void OnDestroy()
    {
        this.barcodeTracking.RemoveListener(this);
        this.dataCaptureContext.RemoveCurrentMode();
        base.OnDestroy();
    }

    private void InitializeAndStartTracking()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        // v6 pattern: hand-rolled CameraSettings instead of BarcodeTracking.RecommendedCameraSettings.
        var cameraSettings = new CameraSettings { PreferredResolution = VideoResolution.FullHd };
        this.camera = Camera.GetDefaultCamera();
        if (this.camera != null)
        {
            this.camera.ApplySettingsAsync(cameraSettings);
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        BarcodeTrackingSettings settings = BarcodeTrackingSettings.Create();
        settings.EnableSymbology(Symbology.Ean13Upca, true);
        settings.EnableSymbology(Symbology.Code128, true);

        this.barcodeTracking = BarcodeTracking.Create(this.dataCaptureContext, settings);
        this.barcodeTracking.AddListener(this);

        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
        BarcodeTrackingBasicOverlay.Create(this.barcodeTracking, this.dataCaptureView);

        var container = FindViewById<FrameLayout>(Resource.Id.data_capture_view_container);
        container?.AddView(
            this.dataCaptureView,
            new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MatchParent,
                ViewGroup.LayoutParams.MatchParent));
    }

    public void OnSessionUpdated(
        BarcodeTracking barcodeTracking,
        BarcodeTrackingSession session,
        IFrameData frameData)
    {
        var addedData = session.AddedTrackedBarcodes
            .Select(tb => tb.Barcode.Data)
            .ToList();

        this.RunOnUiThread(() =>
        {
            foreach (var data in addedData)
            {
                // handle data
            }
        });
    }

    public void OnObservationStarted(BarcodeTracking barcodeTracking) { }
    public void OnObservationStopped(BarcodeTracking barcodeTracking) { }
}
