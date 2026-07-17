using Xamarin.Forms;

namespace MyScanApp
{
    // Xamarin.Forms App entry point — pre-migration state.
    // Uses DependencyService (needs to become DI) and a custom renderer (needs a MAUI handler).
    public partial class App : Application
    {
        public App()
        {
            InitializeComponent();

            var audio = DependencyService.Get<IAudioService>();
            audio?.PlayBeep();

            MainPage = new NavigationPage(new ScannerPage());
        }

        protected override void OnStart() { }
        protected override void OnSleep() { }
        protected override void OnResume() { }
    }

    public interface IAudioService
    {
        void PlayBeep();
    }
}
