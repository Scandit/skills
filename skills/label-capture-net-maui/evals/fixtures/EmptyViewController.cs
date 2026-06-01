using System;
using UIKit;

namespace MyApp;

// Plain .NET for iOS app (net*-ios target framework, no <UseMaui>).
// The root view controller is created in code from AppDelegate / SceneDelegate.
public class ScanViewController : UIViewController
{
    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.View!.BackgroundColor = UIColor.SystemBackground;
    }
}
