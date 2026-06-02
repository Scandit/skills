using Android.OS;
using Android.Views;
using Android.Widget;

using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;
using Scandit.DataCapture.ID.UI.Overlay;

namespace MyApp;

[Activity(Label = "@string/app_name", MainLauncher = true, Theme = "@style/Theme.AppCompat.Light.NoActionBar")]
public class MainActivity : CameraPermissionActivity, IIdCaptureListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private Camera? camera;
    private IdCapture idCapture = null!;
    private DataCaptureView dataCaptureView = null!;
    private IdCaptureOverlay overlay = null!;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);

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

        var container = new FrameLayout(this);
        this.SetContentView(container);
        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
        container.AddView(
            this.dataCaptureView,
            new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MatchParent, ViewGroup.LayoutParams.MatchParent));
        this.overlay = IdCaptureOverlay.Create(this.idCapture, this.dataCaptureView);
        this.overlay.IdLayoutStyle = IdLayoutStyle.Square;
    }

    protected override void OnResume()
    {
        base.OnResume();
        this.idCapture.AddListener(this);
        this.idCapture.Enabled = true;
        this.RequestCameraPermission();
    }

    protected override void OnPause()
    {
        base.OnPause();
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
        this.idCapture.RemoveListener(this);
    }

    protected override void OnCameraPermissionGranted()
    {
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    protected override void OnDestroy()
    {
        base.OnDestroy();
        this.overlay.Dispose();
        this.idCapture.Dispose();
    }

    public void OnIdCaptured(IdCapture mode, CapturedId capturedId)
    {
        string? fullName = capturedId.FullName;
        DateResult? dateOfBirth = capturedId.DateOfBirth;
        string? documentNumber = capturedId.DocumentNumber;

        mode.Enabled = false;
        this.RunOnUiThread(() =>
        {
            // Present fullName / dateOfBirth / documentNumber.
        });
    }

    public void OnIdRejected(IdCapture mode, CapturedId? capturedId, RejectionReason reason)
    {
        mode.Enabled = false;
        this.RunOnUiThread(() =>
        {
            // Show a message based on `reason`.
        });
    }
}
