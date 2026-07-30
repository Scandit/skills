using System;
using UIKit;

namespace MyApp;

public partial class ViewController : UIViewController
{
    public ViewController(IntPtr handle) : base(handle)
    {
    }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        // Empty view controller — no scanning yet.
    }
}
