using System.Collections.Generic;
using System.Linq;
using CoreFoundation;
using Foundation;
using UIKit;

using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Tracking.Capture;
using Scandit.DataCapture.Barcode.Tracking.Data;
using Scandit.DataCapture.Barcode.Tracking.UI.Overlay;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;

namespace MyApp;

public partial class ViewController : UIViewController, IBarcodeTrackingListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeTracking barcodeTracking = null!;
    private Camera? camera;

    public ViewController(IntPtr handle) : base(handle) { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.InitializeAndStartTracking();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.barcodeTracking.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.barcodeTracking.Enabled = false;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
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

        var dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);
        UIView platformView = dataCaptureView;
        platformView.AutoresizingMask = UIViewAutoresizing.FlexibleHeight |
                                        UIViewAutoresizing.FlexibleWidth;
        this.View.AddSubview(dataCaptureView);
        this.View.SendSubviewToBack(dataCaptureView);

        BarcodeTrackingBasicOverlay.Create(this.barcodeTracking, dataCaptureView);
    }

    public void OnSessionUpdated(
        BarcodeTracking barcodeTracking,
        BarcodeTrackingSession session,
        IFrameData frameData)
    {
        try
        {
            var addedData = session.AddedTrackedBarcodes
                .Select(tb => tb.Barcode.Data)
                .ToList();

            DispatchQueue.MainQueue.DispatchAsync(() =>
            {
                foreach (var data in addedData)
                {
                    // handle data
                }
            });
        }
        finally
        {
            frameData.Dispose();
        }
    }

    public void OnObservationStarted(BarcodeTracking barcodeTracking) { }
    public void OnObservationStopped(BarcodeTracking barcodeTracking) { }
}
