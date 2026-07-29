using MyApp.ViewModels;
using Scandit.DataCapture.Label.UI.Overlay;

namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    private LabelCaptureBasicOverlay? labelCaptureOverlay;
    private readonly MainPageViewModel viewModel;

    public MainPage(MainPageViewModel viewModel)
    {
        this.viewModel = viewModel;
        this.InitializeComponent();
        this.BindingContext = viewModel;

        this.dataCaptureView.HandlerChanged += this.OnDataCaptureViewHandlerChanged;
    }

    private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
    {
        this.labelCaptureOverlay = this.viewModel.BuildOverlay();
        this.dataCaptureView.AddOverlay(this.labelCaptureOverlay);
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
