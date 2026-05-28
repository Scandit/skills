using Android.OS;
using AndroidX.AppCompat.App;

namespace MyApp;

[Activity(MainLauncher = true, Label = "@string/app_name")]
public class MainActivity : AppCompatActivity
{
    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        this.SetContentView(Resource.Layout.activity_main);
    }
}
