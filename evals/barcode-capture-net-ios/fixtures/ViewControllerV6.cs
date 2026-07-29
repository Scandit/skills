using CoreFoundation;
using UIKit;

using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.UI.Overlay;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;

namespace MyApp;

public partial class ViewController : UIViewController, IBarcodeCaptureListener
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private Camera? camera;
    private DataCaptureView dataCaptureView = null!;
    private BarcodeCapture barcodeCapture = null!;
    private BarcodeCaptureOverlay overlay = null!;

    public ViewController(IntPtr handle) : base(handle) { }
    public ViewController() { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
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

        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);
        UIView platformView = this.dataCaptureView;
        platformView.AutoresizingMask =
            UIViewAutoresizing.FlexibleHeight | UIViewAutoresizing.FlexibleWidth;
        this.View.AddSubview(this.dataCaptureView);

        this.overlay = BarcodeCaptureOverlay.Create(this.barcodeCapture, this.dataCaptureView);
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.barcodeCapture.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    public void OnBarcodeScanned(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData)
    {
        var barcode = session.NewlyRecognizedBarcode;
        if (barcode == null)
        {
            frameData.Dispose();
            return;
        }

        barcodeCapture.Enabled = false;
        DispatchQueue.MainQueue.DispatchAsync(() => { });

        frameData.Dispose();
    }

    public void OnSessionUpdated(
        BarcodeCapture barcodeCapture,
        BarcodeCaptureSession session,
        IFrameData frameData) => frameData.Dispose();

    public void OnObservationStarted(BarcodeCapture barcodeCapture) { }
    public void OnObservationStopped(BarcodeCapture barcodeCapture) { }
}
