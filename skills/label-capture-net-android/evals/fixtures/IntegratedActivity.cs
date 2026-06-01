using Android.OS;
using Android.Views;
using Android.Widget;

using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay;

namespace MyApp;

[Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
public class MainActivity : CameraPermissionActivity
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private const string FieldBarcode = "Barcode";
    private const string FieldExpiryDate = "Expiry Date";
    private const string LabelName = "Retail Item";

    private DataCaptureContext dataCaptureContext = null!;
    private Camera? camera;
    private LabelCapture labelCapture = null!;
    private DataCaptureView dataCaptureView = null!;
    private LabelCaptureBasicOverlay overlay = null!;

    protected override async void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera(LabelCapture.RecommendedCameraSettings);
        if (this.camera is not null)
        {
            await this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        var fields = new List<LabelFieldDefinition>
        {
            CustomBarcode.Builder()
                .SetSymbologies(new List<Symbology> { Symbology.Ean13Upca, Symbology.Code128 })
                .Build(FieldBarcode),
            ExpiryDateText.Builder()
                .Build(FieldExpiryDate),
        };
        LabelDefinition labelDefinition = LabelDefinition.Create(LabelName, fields);
        LabelCaptureSettings settings =
            LabelCaptureSettings.Create(new List<LabelDefinition> { labelDefinition });

        this.labelCapture = LabelCapture.Create(this.dataCaptureContext, settings);

        var container = new FrameLayout(this);
        this.SetContentView(container);
        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
        container.AddView(
            this.dataCaptureView,
            new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MatchParent, ViewGroup.LayoutParams.MatchParent));
        this.overlay = LabelCaptureBasicOverlay.Create(this.labelCapture);
        this.dataCaptureView.AddOverlay(this.overlay);
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.labelCapture.SessionUpdated += this.OnSessionUpdated;
        this.labelCapture.Enabled = true;
        this.RequestCameraPermission();
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
        this.labelCapture.SessionUpdated -= this.OnSessionUpdated;
    }

    protected override void OnCameraPermissionGranted()
    {
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    private void OnSessionUpdated(object? sender, LabelCaptureEventArgs args)
    {
        if (args.Session.CapturedLabels.Count == 0)
        {
            return;
        }

        CapturedLabel label = args.Session.CapturedLabels[0];
        string? barcodeData = label.Fields.FirstOrDefault(f => f.Name == FieldBarcode)?.Barcode?.Data;
        string? expiryDate = label.Fields.FirstOrDefault(f => f.Name == FieldExpiryDate)?.Text;

        this.labelCapture.Enabled = false;

        this.RunOnUiThread(() =>
        {
            // Present barcodeData / expiryDate.
        });
    }
}
