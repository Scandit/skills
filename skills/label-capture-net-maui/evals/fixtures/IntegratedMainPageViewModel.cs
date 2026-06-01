using System.ComponentModel;
using MyApp.Services;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay;

namespace MyApp.ViewModels;

public class MainPageViewModel : INotifyPropertyChanged
{
    private readonly ICameraService cameraService;
    private readonly ILabelCaptureService labelCaptureService;
    private LabelCaptureBasicOverlay? overlay;

    public event PropertyChangedEventHandler? PropertyChanged;

    public MainPageViewModel(
        DataCaptureContext dataCaptureContext,
        ICameraService cameraService,
        ILabelCaptureService labelCaptureService)
    {
        this.DataCaptureContext = dataCaptureContext;
        this.cameraService = cameraService;
        this.labelCaptureService = labelCaptureService;
        this.labelCaptureService.Subscribe(this.OnSessionUpdated);
    }

    public DataCaptureContext DataCaptureContext { get; }

    public LabelCaptureBasicOverlay BuildOverlay()
    {
        return this.overlay ??= this.labelCaptureService.BuildOverlay();
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

        await this.cameraService.ResumeFrameSourceAsync();
        this.labelCaptureService.Enable();
    }

    public async Task SleepAsync()
    {
        await this.cameraService.PauseFrameSourceAsync();
        this.labelCaptureService.Disable();
    }

    private void OnSessionUpdated(object? sender, LabelCaptureEventArgs args)
    {
        if (args.Session.CapturedLabels.Count == 0)
        {
            return;
        }

        CapturedLabel label = args.Session.CapturedLabels[0];
        string? barcodeData = label.Fields
            .FirstOrDefault(f => f.Name == LabelCaptureService.FIELD_BARCODE)?.Barcode?.Data;
        string? expiryDate = label.Fields
            .FirstOrDefault(f => f.Name == LabelCaptureService.FIELD_EXPIRY_DATE)?.Text;

        this.labelCaptureService.Disable();

        MainThread.BeginInvokeOnMainThread(() =>
        {
            // Present barcodeData / expiryDate to the user.
        });
    }
}
