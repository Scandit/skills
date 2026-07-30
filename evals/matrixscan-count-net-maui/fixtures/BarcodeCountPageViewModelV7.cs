using System.ComponentModel;
using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

namespace MyApp.ViewModels;

// Scandit .NET MAUI SDK v7 — MatrixScan Count view model.
public class BarcodeCountPageViewModel : INotifyPropertyChanged
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private readonly DataCaptureContext dataCaptureContext;
    private readonly BarcodeCount barcodeCount;
    private readonly BarcodeCountSettings barcodeCountSettings;
    private readonly Camera? camera;

    public event PropertyChangedEventHandler? PropertyChanged;

    public DataCaptureContext DataCaptureContext => this.dataCaptureContext;
    public BarcodeCount BarcodeCount => this.barcodeCount;

    public BarcodeCountPageViewModel()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        this.camera = Camera.GetDefaultCamera(BarcodeCount.RecommendedCameraSettings);
        if (this.camera is not null)
        {
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        this.barcodeCountSettings = new BarcodeCountSettings();
        this.barcodeCountSettings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Ean8,
            Symbology.Code128,
        });

        this.barcodeCount = BarcodeCount.Create(this.dataCaptureContext, this.barcodeCountSettings);
        this.barcodeCount.Scanned += this.OnBarcodeCountScanned;
    }

    public async Task ResumeAsync()
    {
        var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted)
        {
            status = await Permissions.RequestAsync<Permissions.Camera>();
            if (status != PermissionStatus.Granted)
            {
                return;
            }
        }

        this.barcodeCount.Enabled = true;
        if (this.camera is not null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.On);
        }
    }

    public async Task SleepAsync()
    {
        if (this.camera is not null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.Off);
        }
    }

    private void OnBarcodeCountScanned(object? sender, BarcodeCountEventArgs args)
    {
        // Existing scan handling.
    }
}
