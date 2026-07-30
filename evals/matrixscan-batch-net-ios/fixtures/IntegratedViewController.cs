using System.Collections.Generic;
using System.Linq;
using CoreFoundation;
using Foundation;
using UIKit;

using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;

namespace MyApp;

public partial class ViewController : UIViewController, IBarcodeBatchListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeBatch barcodeBatch = null!;
    private Camera? camera;

    private readonly HashSet<string> scannedData = new();

    public ViewController(IntPtr handle) : base(handle) { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.InitializeAndStartBatchScanning();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.barcodeBatch.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.barcodeBatch.Enabled = false;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    private void InitializeAndStartBatchScanning()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera();
        if (this.camera != null)
        {
            CameraSettings cameraSettings = BarcodeBatch.RecommendedCameraSettings;
            cameraSettings.PreferredResolution = VideoResolution.FullHd;
            this.camera.ApplySettingsAsync(cameraSettings);
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        BarcodeBatchSettings settings = BarcodeBatchSettings.Create();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });

        this.barcodeBatch = BarcodeBatch.Create(this.dataCaptureContext, settings);
        this.barcodeBatch.AddListener(this);

        var dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);
        UIView platformView = dataCaptureView;
        platformView.AutoresizingMask = UIViewAutoresizing.FlexibleHeight |
                                        UIViewAutoresizing.FlexibleWidth;
        this.View.AddSubview(dataCaptureView);
        this.View.SendSubviewToBack(dataCaptureView);

        BarcodeBatchBasicOverlay.Create(
            this.barcodeBatch,
            dataCaptureView,
            BarcodeBatchBasicOverlayStyle.Frame);
    }

    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
        IFrameData frameData)
    {
        try
        {
            var addedData = session.AddedTrackedBarcodes
                .Select(tb => tb.Barcode.Data)
                .Where(d => d != null)
                .Cast<string>()
                .ToList();

            DispatchQueue.MainQueue.DispatchAsync(() =>
            {
                foreach (var data in addedData)
                {
                    this.scannedData.Add(data);
                }
            });
        }
        finally
        {
            frameData.Dispose();
        }
    }

    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }
}
