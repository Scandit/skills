using Microsoft.Maui;
using Microsoft.Maui.Controls.Hosting;
using Microsoft.Maui.Hosting;

namespace MyIdApp;

// POST-migration state: the MAUI App and MauiProgram exist, but the Scandit wiring is missing.
// NOTE for the migration: ID Capture does NOT have a UseScanditIdCapture() builder extension.
// Only .UseScanditCore(...) belongs here; ScanditIdCapture.Initialize() goes in the platform
// entry points (Platforms/Android/MainApplication.cs and Platforms/iOS/AppDelegate.cs).
public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder
            .UseMauiApp<App>();
        // TODO: Scandit core builder chain missing.
        return builder.Build();
    }
}
