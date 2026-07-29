using UIKit;

namespace MyApp;

public partial class ScanViewController : UIViewController
{
    public ScanViewController(IntPtr handle) : base(handle) { }
    public ScanViewController() : base() { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.View!.BackgroundColor = UIColor.SystemBackground;
    }
}
