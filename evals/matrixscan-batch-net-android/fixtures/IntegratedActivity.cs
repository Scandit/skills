using Android.OS;
using Android.Widget;
using AndroidX.AppCompat.App;

using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;

namespace MyApp;

[Activity(MainLauncher = true, Label = "@string/app_name")]
public class MainActivity : AppCompatActivity, IBarcodeBatchListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeBatch barcodeBatch = null!;
    private Camera? camera;
    private DataCaptureView dataCaptureView = null!;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        this.SetContentView(Resource.Layout.activity_main);
        this.InitializeAndStartBatchScanning();
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.barcodeBatch.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.barcodeBatch.Enabled = false;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    protected override void OnDestroy()
    {
        this.barcodeBatch.RemoveListener(this);
        this.dataCaptureContext.RemoveCurrentMode();
        base.OnDestroy();
    }

    private void InitializeAndStartBatchScanning()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera();
        if (this.camera != null)
        {
            this.camera.ApplySettingsAsync(BarcodeBatch.RecommendedCameraSettings);
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        BarcodeBatchSettings settings = BarcodeBatchSettings.Create();
        settings.EnableSymbology(Symbology.Ean13Upca, true);
        settings.EnableSymbology(Symbology.Code128, true);

        this.barcodeBatch = BarcodeBatch.Create(this.dataCaptureContext, settings);
        this.barcodeBatch.AddListener(this);

        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
        BarcodeBatchBasicOverlay.Create(
            this.barcodeBatch,
            this.dataCaptureView,
            BarcodeBatchBasicOverlayStyle.Frame);

        var container = FindViewById<FrameLayout>(Resource.Id.data_capture_view_container);
        container?.AddView(
            this.dataCaptureView,
            new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MatchParent,
                ViewGroup.LayoutParams.MatchParent));
    }

    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
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

    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }
}
