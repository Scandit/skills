using System.ComponentModel;
using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

namespace MyApp.ViewModels;

// A working MatrixScan Count MAUI integration that already counts barcodes.
// The camera is managed here; the <scandit:BarcodeCountView> binds to
// DataCaptureContext and BarcodeCount.
public class BarcodeCountPageViewModel : INotifyPropertyChanged
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private readonly DataCaptureContext dataCaptureContext;
    private readonly BarcodeCount barcodeCount;
    private readonly BarcodeCountSettings barcodeCountSettings;
    private readonly Camera? camera;

    private readonly List<Barcode> scannedBarcodes = new();

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
        List<Barcode> recognized = args.Session.RecognizedBarcodes.ToList();
        MainThread.BeginInvokeOnMainThread(() =>
        {
            this.scannedBarcodes.Clear();
            this.scannedBarcodes.AddRange(recognized);
        });
    }
}
