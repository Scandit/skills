using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.UI.Overlay;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

namespace MyApp.Views;

public partial class MainPage : ContentPage
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    public DataCaptureContext DataCaptureContext { get; }
    private readonly Camera? camera;
    private readonly BarcodeCapture barcodeCapture;
    private BarcodeCaptureOverlay? overlay;

    public MainPage()
    {
        this.InitializeComponent();

        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        this.camera = Camera.GetCamera(CameraPosition.WorldFacing);
        this.camera?.ApplySettingsAsync(BarcodeCapture.RecommendedCameraSettings);
        this.DataCaptureContext.SetFrameSourceAsync(this.camera);

        var settings = BarcodeCaptureSettings.Create();
        settings.EnableSymbology(Symbology.Ean13Upca, true);
        settings.EnableSymbology(Symbology.Code128, true);

        this.barcodeCapture = BarcodeCapture.Create(this.DataCaptureContext, settings);
        this.barcodeCapture.BarcodeScanned += this.OnBarcodeScanned;

        this.BindingContext = this;
        this.dataCaptureView.HandlerChanged += this.OnDataCaptureViewHandlerChanged;
    }

    private void OnDataCaptureViewHandlerChanged(object? sender, EventArgs e)
    {
        this.overlay = BarcodeCaptureOverlay.Create(this.barcodeCapture);
        this.dataCaptureView.AddOverlay(this.overlay);
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

        this.barcodeCapture.Enabled = true;
        if (this.camera != null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.On);
        }
    }

    protected override async void OnDisappearing()
    {
        base.OnDisappearing();
        this.barcodeCapture.Enabled = false;
        if (this.camera != null)
        {
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.Off);
        }
    }

    private void OnBarcodeScanned(object? sender, BarcodeCaptureEventArgs args)
    {
        var barcode = args.Session.NewlyRecognizedBarcode;
        if (barcode == null) return;

        this.barcodeCapture.Enabled = false;
        MainThread.BeginInvokeOnMainThread(() => { });
    }
}
