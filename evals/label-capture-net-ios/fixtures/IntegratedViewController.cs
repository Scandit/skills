using System;
using System.Collections.Generic;
using System.Linq;
using Foundation;
using UIKit;

using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay;

namespace MyApp;

public class ScanViewController : UIViewController
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private const string FieldBarcode = "Barcode";
    private const string FieldExpiryDate = "Expiry Date";
    private const string LabelName = "Retail Item";

    private DataCaptureContext? dataCaptureContext;
    private Camera? camera;
    private LabelCapture? labelCapture;
    private DataCaptureView? dataCaptureView;
    private LabelCaptureBasicOverlay? overlay;

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera(LabelCapture.RecommendedCameraSettings);
        if (this.camera is not null)
        {
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);
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

        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);
        UIView platformView = this.dataCaptureView;
        platformView.AutoresizingMask = UIViewAutoresizing.FlexibleWidth | UIViewAutoresizing.FlexibleHeight;
        this.View.AddSubview(this.dataCaptureView);

        this.overlay = LabelCaptureBasicOverlay.Create(this.labelCapture);
        this.dataCaptureView.AddOverlay(this.overlay);
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        if (this.labelCapture is null) return;
        this.labelCapture.SessionUpdated += this.OnSessionUpdated;
        this.labelCapture.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
        if (this.labelCapture is not null)
        {
            this.labelCapture.SessionUpdated -= this.OnSessionUpdated;
        }
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

        UIApplication.SharedApplication.InvokeOnMainThread(() =>
        {
            // Present barcodeData / expiryDate.
        });
    }
}
