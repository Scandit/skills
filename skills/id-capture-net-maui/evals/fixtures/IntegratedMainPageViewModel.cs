using System.Text;
using MyApp.Models;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.ID.Capture;
using Scandit.DataCapture.ID.Data;

namespace MyApp.ViewModels;

public class MainPageViewModel : IIdCaptureListener
{
    private readonly DataCaptureManager model = DataCaptureManager.Instance;

    public DataCaptureContext DataCaptureContext => this.model.DataCaptureContext;
    public IdCapture IdCapture => this.model.IdCapture;

    public MainPageViewModel()
    {
        this.IdCapture.AddListener(this);
        this.IdCapture.Enabled = true;
    }

    public void OnIdCaptured(IdCapture mode, CapturedId capturedId)
    {
        mode.Enabled = false;

        string message = GetDescriptionForCapturedId(capturedId);

        MainThread.BeginInvokeOnMainThread(async () =>
        {
            await Application.Current!.Windows[0].Page!.DisplayAlert("Document", message, "OK");
            mode.Enabled = true;
        });
    }

    public void OnIdRejected(IdCapture mode, CapturedId? capturedId, RejectionReason reason)
    {
        mode.Enabled = false;

        string message = reason switch
        {
            RejectionReason.NotAcceptedDocumentType => "Document not supported. Try scanning another document.",
            _ => $"Document capture was rejected. Reason={reason}.",
        };

        MainThread.BeginInvokeOnMainThread(async () =>
        {
            await Application.Current!.Windows[0].Page!.DisplayAlert("Scandit", message, "OK");
            mode.Enabled = true;
        });
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

        if (this.model.CurrentCamera is not null)
        {
            await this.model.CurrentCamera.SwitchToDesiredStateAsync(FrameSourceState.On);
        }
    }

    public async Task SleepAsync()
    {
        if (this.model.CurrentCamera is not null)
        {
            await this.model.CurrentCamera.SwitchToDesiredStateAsync(FrameSourceState.Off);
        }
    }

    private static string GetDescriptionForCapturedId(CapturedId result)
    {
        var builder = new StringBuilder();
        builder.AppendLine($"Full Name: {result.FullName}");
        builder.AppendLine($"Date of Birth: {result.DateOfBirth?.LocalDate:d}");
        builder.AppendLine($"Date of Expiry: {result.DateOfExpiry?.LocalDate:d}");
        builder.AppendLine($"Document Number: {result.DocumentNumber}");
        return builder.ToString();
    }
}
