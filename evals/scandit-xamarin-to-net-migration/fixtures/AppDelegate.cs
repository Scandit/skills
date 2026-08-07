using Foundation;
using UIKit;

namespace MyScanApp.iOS
{
    // POST-migration state: .NET for iOS AppDelegate produced by the upgrade, but with
    // NO Scandit SDK-8 initialization. On SDK 8 the SDK must be initialized in
    // FinishedLaunching before the root view controller is created.
    [Register("AppDelegate")]
    public class AppDelegate : UIApplicationDelegate
    {
        public override UIWindow? Window { get; set; }

        public override bool FinishedLaunching(UIApplication application, NSDictionary launchOptions)
        {
            Window = new UIWindow(UIScreen.MainScreen.Bounds);
            Window.RootViewController = new ScannerViewController();
            Window.MakeKeyAndVisible();
            return true;
        }
    }
}
