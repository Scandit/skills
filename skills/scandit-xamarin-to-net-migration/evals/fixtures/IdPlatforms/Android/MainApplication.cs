using Android.App;
using Android.Runtime;
using Microsoft.Maui;

namespace MyIdApp;

// POST-migration state: standard MAUI Android entry point. ID Capture requires
// ScanditIdCapture.Initialize() HERE (before base.OnCreate()) — it is not a MauiProgram concern.
[Application]
public class MainApplication : MauiApplication
{
    public MainApplication(IntPtr handle, JniHandleOwnership ownership)
        : base(handle, ownership) { }

    public override void OnCreate()
    {
        // TODO: Scandit ID Capture initialization missing.
        base.OnCreate();
    }

    protected override MauiApp CreateMauiApp() => MauiProgram.CreateMauiApp();
}
