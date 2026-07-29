using Scandit.DataCapture.ID.UI.Overlay;

namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    private IdCaptureOverlay? overlay;

    public MainPage()
    {
        this.InitializeComponent();

        this.dataCaptureView.HandlerChanged += this.OnDataCaptureViewHandlerChanged;
    }

    private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
    {
        this.overlay = IdCaptureOverlay.Create(this.viewModel.IdCapture);
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
