using System;
using Microsoft.Maui.Controls;

// POST-migration state: the Scandit ID Capture call sites are intact but still use the
// Forms-only ".Unified" namespaces, so this file does not compile against the .NET binding.
// Every Scandit symbol below must still be present after the migration (relocation is fine,
// deletion is not) — only the namespaces and the initialization change.
using Scandit.DataCapture.Core.Capture.Unified;
using Scandit.DataCapture.Core.Source.Unified;
using Scandit.DataCapture.ID.Capture.Unified;
using Scandit.DataCapture.ID.Data.Unified;
using Scandit.DataCapture.ID.UI.Unified;          // IdCaptureOverlay lives here in the Forms binding

namespace MyIdApp;

public partial class IdScanPage : ContentPage, IIdCaptureListener
{
    private DataCaptureContext dataCaptureContext;
    private IdCapture idCapture;
    private Camera camera;

    public IdScanPage()
    {
        InitializeComponent();

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --");

        var settings = new IdCaptureSettings();
        this.idCapture = IdCapture.Create(this.dataCaptureContext, settings);
        this.idCapture.AddListener(this);

        this.camera = Camera.GetDefaultCamera();
        this.dataCaptureContext.SetFrameSourceAsync(this.camera);

        var overlay = IdCaptureOverlay.Create(this.idCapture, this.dataCaptureView);
        this.dataCaptureView.AddOverlay(overlay);
    }

    public void OnIdCaptured(IdCapture capture, CapturedId capturedId)
    {
        Dispatcher.Dispatch(() => DisplayAlert("Captured", capturedId.FullName, "OK"));
    }

    public void OnIdRejected(IdCapture capture, CapturedId capturedId, RejectionReason reason)
    {
        Dispatcher.Dispatch(() => DisplayAlert("Rejected", reason.ToString(), "OK"));
    }
}
