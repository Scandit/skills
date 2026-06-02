using CoreFoundation;
using UIKit;

using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;
using Scandit.DataCapture.ID.UI.Overlay;

namespace MyApp;

public partial class IdCaptureViewController : UIViewController, IIdCaptureListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private Camera? camera;
    private IdCapture idCapture = null!;
    private DataCaptureView dataCaptureView = null!;
    private IdCaptureOverlay overlay = null!;

    public IdCaptureViewController(IntPtr handle) : base(handle) { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera();
        if (this.camera is not null)
        {
            _ = this.camera.ApplySettingsAsync(IdCapture.RecommendedCameraSettings);
            _ = this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        var settings = new IdCaptureSettings
        {
            AcceptedDocuments =
            [
                new Passport(IdCaptureRegion.Any),
                new DriverLicense(IdCaptureRegion.Any),
                new IdCard(IdCaptureRegion.Any),
            ],
            Scanner = new IdCaptureScanner(
                physicalDocument: new FullDocumentScanner(),
                mobileDocument: null),
        };

        this.idCapture = IdCapture.Create(this.dataCaptureContext, settings);

        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);
        UIView platformView = this.dataCaptureView;
        platformView.AutoresizingMask = UIViewAutoresizing.FlexibleWidth | UIViewAutoresizing.FlexibleHeight;
        this.View.AddSubview(this.dataCaptureView);

        this.overlay = IdCaptureOverlay.Create(this.idCapture, this.dataCaptureView);
        this.overlay.IdLayoutStyle = IdLayoutStyle.Square;
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.idCapture.AddListener(this);
        this.idCapture.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.idCapture.RemoveListener(this);
        this.idCapture.Enabled = false;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    public void OnIdCaptured(IdCapture mode, CapturedId capturedId)
    {
        string? fullName = capturedId.FullName;
        DateResult? dateOfBirth = capturedId.DateOfBirth;
        string? documentNumber = capturedId.DocumentNumber;

        mode.Enabled = false;
        DispatchQueue.MainQueue.DispatchAsync(() =>
        {
            // Present fullName / dateOfBirth / documentNumber.
        });
    }

    public void OnIdRejected(IdCapture mode, CapturedId? capturedId, RejectionReason reason)
    {
        mode.Enabled = false;
        DispatchQueue.MainQueue.DispatchAsync(() =>
        {
            // Show a message based on `reason`.
        });
    }
}
