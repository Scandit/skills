using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;

namespace MyApp.Models;

public class DataCaptureManager
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private static readonly Lazy<DataCaptureManager> instance =
        new(() => new DataCaptureManager(), LazyThreadSafetyMode.PublicationOnly);

    public static DataCaptureManager Instance => instance.Value;

    public DataCaptureContext DataCaptureContext { get; }
    public Camera? CurrentCamera { get; } = Camera.GetCamera(CameraPosition.WorldFacing);
    public IdCapture IdCapture { get; }
    public IdCaptureSettings IdCaptureSettings { get; }

    private DataCaptureManager()
    {
        this.CurrentCamera?.ApplySettingsAsync(IdCapture.RecommendedCameraSettings);

        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);
        this.DataCaptureContext.SetFrameSourceAsync(this.CurrentCamera);

        this.IdCaptureSettings = new IdCaptureSettings
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

        this.IdCapture = IdCapture.Create(this.DataCaptureContext, this.IdCaptureSettings);
    }
}
