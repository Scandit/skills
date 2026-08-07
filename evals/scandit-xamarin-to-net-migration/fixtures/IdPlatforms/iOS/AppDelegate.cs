using Foundation;
using Microsoft.Maui;

namespace MyIdApp;

// POST-migration state: standard MAUI iOS entry point. ID Capture requires
// ScanditIdCapture.Initialize() HERE (before base.FinishedLaunching(...)).
[Register("AppDelegate")]
public class AppDelegate : MauiUIApplicationDelegate
{
    public override bool FinishedLaunching(UIKit.UIApplication application, NSDictionary launchOptions)
    {
        // TODO: Scandit ID Capture initialization missing.
        return base.FinishedLaunching(application, launchOptions);
    }

    protected override MauiApp CreateMauiApp() => MauiProgram.CreateMauiApp();
}
