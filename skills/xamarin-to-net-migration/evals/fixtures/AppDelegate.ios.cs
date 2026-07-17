using Foundation;
using UIKit;

namespace MyScanApp.iOS
{
    // Xamarin.iOS (SDK v7.x) AppDelegate — pre-migration state.
    // No ScanditCaptureCore.Initialize() because 7.x self-initialized.
    [Register("AppDelegate")]
    public class AppDelegate : UIApplicationDelegate
    {
        public override UIWindow Window { get; set; }

        public override bool FinishedLaunching(UIApplication application, NSDictionary launchOptions)
        {
            Window = new UIWindow(UIScreen.MainScreen.Bounds);
            Window.RootViewController = new ScannerViewController();
            Window.MakeKeyAndVisible();
            return true;
        }
    }
}
