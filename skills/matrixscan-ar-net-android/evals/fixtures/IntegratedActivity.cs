using Android.OS;
using Android.Widget;

using Scandit.DataCapture.Barcode.Ar.Capture;
using Scandit.DataCapture.Barcode.Ar.UI;
using Scandit.DataCapture.Barcode.Ar.UI.Highlight;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;

namespace MyApp;

[Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
public class MainActivity : CameraPermissionActivity
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeAr barcodeAr = null!;
    private BarcodeArView barcodeArView = null!;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        BarcodeArSettings settings = new BarcodeArSettings();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });

        this.barcodeAr = new BarcodeAr(this.dataCaptureContext, settings);
        this.barcodeAr.SessionUpdated += this.OnSessionUpdated;

        var container = new FrameLayout(this);
        this.SetContentView(container);

        BarcodeArViewSettings viewSettings = new BarcodeArViewSettings();
        this.barcodeArView = BarcodeArView.Create(
            parentView: container,
            barcodeAr: this.barcodeAr,
            dataCaptureContext: this.dataCaptureContext,
            settings: viewSettings,
            cameraSettings: null);

        this.barcodeArView.HighlightProvider = new RectangleHighlightProvider();
        this.barcodeArView.Start();
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.barcodeArView.OnResume();
        this.RequestCameraPermission();
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.barcodeArView.OnPause();
    }

    protected override void OnDestroy()
    {
        base.OnDestroy();
        this.barcodeAr.SessionUpdated -= this.OnSessionUpdated;
        this.barcodeArView.Dispose();
        this.barcodeAr.Dispose();
    }

    protected override void OnCameraPermissionGranted() { }

    private void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
    {
        IReadOnlyList<TrackedBarcode> added = args.Session.AddedTrackedBarcodes;
        if (added.Count == 0) return;
        this.RunOnUiThread(() =>
        {
            foreach (TrackedBarcode tracked in added)
            {
                _ = tracked.Barcode.Data;
            }
        });
    }

    private sealed class RectangleHighlightProvider : IBarcodeArHighlightProvider
    {
        public Task<IBarcodeArHighlight?> HighlightForBarcodeAsync(Barcode barcode) =>
            Task.FromResult<IBarcodeArHighlight?>(new BarcodeArRectangleHighlight(barcode));
    }
}
