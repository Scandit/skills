using MyApp.ViewModels;
using Scandit.DataCapture.Barcode.Count.UI;

namespace MyApp.Views;

public partial class BarcodeCountPage : ContentPage
{
    private readonly BarcodeCountPageViewModel viewModel;

    public BarcodeCountPage()
    {
        this.InitializeComponent();
        this.viewModel = (BarcodeCountPageViewModel)this.BindingContext;

        this.barcodeCountView.HandlerChanged += this.OnBarcodeCountViewHandlerChanged;
    }

    private void OnBarcodeCountViewHandlerChanged(object? sender, EventArgs e)
    {
        this.barcodeCountView.ListButtonTapped += this.OnListButtonTapped;
        this.barcodeCountView.ExitButtonTapped += this.OnExitButtonTapped;
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

    private void OnListButtonTapped(object? sender, ListButtonTappedEventArgs e)
    {
        // Show current results.
    }

    private void OnExitButtonTapped(object? sender, ExitButtonTappedEventArgs e)
    {
        // Show final results.
    }
}
