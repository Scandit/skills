using Microsoft.Maui;
using Microsoft.Maui.Controls.Hosting;
using Microsoft.Maui.Hosting;

namespace MyScanApp;

// POST-migration state: Microsoft's app-modernization tooling produced the MAUI App
// and MauiProgram, but never added the Scandit builder chain. In MAUI, Scandit is
// initialized through .UseScanditCore(...).UseScanditBarcode() — NOT by calling
// ScanditCaptureCore.Initialize() by hand.
public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder
            .UseMauiApp<App>();
        // TODO: Scandit builder chain missing.
        return builder.Build();
    }
}
