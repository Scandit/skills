using System.ComponentModel;
using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;

namespace MyApp.ViewModels;

public abstract class BaseViewModel : INotifyPropertyChanged
{
    public virtual Task ResumeAsync() => Task.CompletedTask;
    public virtual Task SleepAsync() => Task.CompletedTask;

    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged(string name) =>
        this.PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public record ScanResult(int Id, string Data, string Symbology);

public class MainPageViewModel : BaseViewModel, IBarcodeBatchListener
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private readonly HashSet<int> seenTrackingIds = new();
    private readonly List<ScanResult> scanResults = new();
    private readonly Camera? camera;

    public DataCaptureContext DataCaptureContext { get; }
    public BarcodeBatch BarcodeBatch { get; }

    public IEnumerable<ScanResult> ScanResults => this.scanResults;

    public MainPageViewModel()
    {
        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        this.camera = Camera.GetCamera(CameraPosition.WorldFacing);
        this.camera?.ApplySettingsAsync(BarcodeBatch.RecommendedCameraSettings);
        this.DataCaptureContext.SetFrameSourceAsync(this.camera);

        var settings = BarcodeBatchSettings.Create();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });

        this.BarcodeBatch = BarcodeBatch.Create(this.DataCaptureContext, settings);
        this.BarcodeBatch.AddListener(this);
    }

    public override async Task SleepAsync()
    {
        // Disable BarcodeBatch first; in-flight frames can still report results
        // during the asynchronous camera-off transition.
        this.BarcodeBatch.Enabled = false;

        if (this.camera != null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.Off);
        }
    }

    public override async Task ResumeAsync()
    {
        var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted)
        {
            status = await Permissions.RequestAsync<Permissions.Camera>();
            if (status != PermissionStatus.Granted) return;
        }

        this.BarcodeBatch.Enabled = true;
        if (this.camera != null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.On);
        }
    }

    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }

    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
        IFrameData frameData)
    {
        try
        {
            var newScans = session.AddedTrackedBarcodes
                .Where(tb => this.seenTrackingIds.Add(tb.Identifier))
                .Select(tb => new ScanResult(
                    tb.Identifier,
                    tb.Barcode.Data ?? string.Empty,
                    new SymbologyDescription(tb.Barcode.Symbology).ReadableName))
                .ToList();

            if (newScans.Count == 0) return;

            MainThread.BeginInvokeOnMainThread(() =>
            {
                this.scanResults.AddRange(newScans);
                this.OnPropertyChanged(nameof(this.ScanResults));
            });
        }
        finally
        {
            // Mandatory on iOS; safe on Android.
            frameData.Dispose();
        }
    }
}
