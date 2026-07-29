using Scandit.DataCapture.Barcode.Ar.UI.Highlight;
using Scandit.DataCapture.Barcode.Data;

namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    public MainPage()
    {
        this.InitializeComponent();
        this.BarcodeArView.HighlightProvider = new RectangleProvider();
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();

        var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted)
        {
            status = await Permissions.RequestAsync<Permissions.Camera>();
            if (status != PermissionStatus.Granted) return;
        }

        this.BarcodeArView.OnResume();
        this.BarcodeArView.Start();
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        this.BarcodeArView.Stop();
        this.BarcodeArView.OnPause();
    }

    private sealed class RectangleProvider : IBarcodeArHighlightProvider
    {
        public Task<IBarcodeArHighlight?> HighlightForBarcodeAsync(Barcode barcode) =>
            Task.FromResult<IBarcodeArHighlight?>(new BarcodeArRectangleHighlight(barcode));
    }
}
