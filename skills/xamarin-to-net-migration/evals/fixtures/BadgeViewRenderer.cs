using Android.Content;
using Xamarin.Forms;
using Xamarin.Forms.Platform.Android;
using MyScanApp;
using MyScanApp.Droid;

[assembly: ExportRenderer(typeof(BadgeView), typeof(BadgeViewRenderer))]
namespace MyScanApp.Droid
{
    // Xamarin.Forms custom renderer — does NOT migrate mechanically.
    // In .NET MAUI this becomes a Handler (Microsoft.Maui.Handlers) or a handler mapper.
    public class BadgeViewRenderer : ViewRenderer
    {
        public BadgeViewRenderer(Context context) : base(context) { }

        protected override void OnElementChanged(ElementChangedEventArgs<View> e)
        {
            base.OnElementChanged(e);
        }
    }

    public class BadgeView : View { }
}
