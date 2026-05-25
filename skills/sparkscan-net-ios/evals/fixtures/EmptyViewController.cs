using UIKit;

namespace MyApp;

public partial class ViewController : UIViewController
{
    public ViewController(IntPtr handle) : base(handle) { }
    public ViewController() { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.View!.BackgroundColor = UIColor.SystemBackground;
    }
}
