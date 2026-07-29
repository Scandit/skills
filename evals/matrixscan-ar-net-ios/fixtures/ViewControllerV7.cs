using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using CoreFoundation;
using UIKit;

using Scandit.DataCapture.Barcode.Ar.Capture;
using Scandit.DataCapture.Barcode.Ar.UI;
using Scandit.DataCapture.Barcode.Ar.UI.Highlight;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;

namespace MyApp;

public partial class ScanViewController : UIViewController
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeAr barcodeAr = null!;
    private BarcodeArView barcodeArView = null!;

    public ScanViewController(IntPtr handle) : base(handle) { }
    public ScanViewController() : base() { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();

        // v7 — no SDK initialization in AppDelegate is required; the SDK self-bootstraps.
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        BarcodeArSettings settings = new BarcodeArSettings();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Qr,
        });

        this.barcodeAr = new BarcodeAr(this.dataCaptureContext, settings);
        this.barcodeAr.SessionUpdated += this.OnSessionUpdated;

        BarcodeArViewSettings viewSettings = new BarcodeArViewSettings();
        this.barcodeArView = BarcodeArView.Create(
            parentView: this.View!,
            barcodeAr: this.barcodeAr,
            dataCaptureContext: this.dataCaptureContext,
            settings: viewSettings,
            cameraSettings: null);

        this.barcodeArView.HighlightProvider = new RectangleHighlightProvider();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.barcodeArView.Start();
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.barcodeArView.Stop();
    }

    private void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
    {
        var addedData = args.Session.AddedTrackedBarcodes
            .Select(tb => tb.Barcode.Data)
            .ToList();
        if (addedData.Count == 0) return;

        DispatchQueue.MainQueue.DispatchAsync(() =>
        {
            foreach (var data in addedData)
            {
                _ = data;
            }
        });
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            this.barcodeAr.SessionUpdated -= this.OnSessionUpdated;
            this.barcodeArView?.Dispose();
            this.barcodeAr?.Dispose();
        }
        base.Dispose(disposing);
    }

    private sealed class RectangleHighlightProvider : IBarcodeArHighlightProvider
    {
        public Task<IBarcodeArHighlight?> HighlightForBarcodeAsync(Barcode barcode) =>
            Task.FromResult<IBarcodeArHighlight?>(new BarcodeArRectangleHighlight(barcode));
    }
}
