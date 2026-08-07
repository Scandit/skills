using Android.App;
using Android.Runtime;

namespace MyScanApp
{
    // POST-migration state: .NET for Android Application subclass produced by the
    // upgrade, but with NO Scandit SDK-8 initialization. On SDK 8 this compiles and
    // then crashes at the first Scandit call because the SDK was never initialized.
    [Application]
    public class MainApplication : Application
    {
        public MainApplication(IntPtr handle, JniHandleOwnership ownership)
            : base(handle, ownership) { }

        public override void OnCreate()
        {
            base.OnCreate();
            // TODO: Scandit initialization missing.
        }
    }
}
