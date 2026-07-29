using MyApp.ViewModels;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;

namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    private BarcodeBatchBasicOverlay overlay = null!;
    private readonly MainPageViewModel viewModel;

    public MainPage()
    {
        this.InitializeComponent();
        this.viewModel = (MainPageViewModel)this.BindingContext;

        // Initialization of the overlay happens on the handler-changed event so the
        // native platform view exists.
        this.dataCaptureView.HandlerChanged += this.OnDataCaptureViewHandlerChanged;
    }

    private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
    {
        this.overlay = BarcodeBatchBasicOverlay.Create(
            this.viewModel.BarcodeBatch,
            BarcodeBatchBasicOverlayStyle.Frame);
        this.dataCaptureView.AddOverlay(this.overlay);
    }

    protected override void OnAppearing()
    {
        base.OnAppearing();
        _ = this.viewModel.ResumeAsync();
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        _ = this.viewModel.SleepAsync();
    }
}
