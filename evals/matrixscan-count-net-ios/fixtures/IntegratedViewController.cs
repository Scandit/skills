using System;
using System.Collections.Generic;
using System.Linq;
using UIKit;

using Scandit.DataCapture.Barcode.Count.Capture;
using Scandit.DataCapture.Barcode.Count.UI;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;

namespace MyApp;

public partial class ViewController : UIViewController
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext? dataCaptureContext;
    private Camera? camera;
    private BarcodeCount? barcodeCount;
    private BarcodeCountView? barcodeCountView;

    private readonly List<Barcode> scannedBarcodes = new();

    public ViewController(IntPtr handle) : base(handle)
    {
    }

    public override async void ViewDidLoad()
    {
        base.ViewDidLoad();

        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera();
        if (this.camera is not null)
        {
            this.camera.ApplySettingsAsync(BarcodeCount.RecommendedCameraSettings);
            await this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        BarcodeCountSettings settings = new BarcodeCountSettings();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });
        this.barcodeCount = BarcodeCount.Create(this.dataCaptureContext, settings);

        this.barcodeCountView = BarcodeCountView.Create(
            this.View!.Bounds, this.dataCaptureContext, this.barcodeCount, BarcodeCountViewStyle.Icon);
        UIView platformView = this.barcodeCountView;
        platformView.AutoresizingMask = UIViewAutoresizing.FlexibleWidth | UIViewAutoresizing.FlexibleHeight;
        this.View.AddSubview(this.barcodeCountView);

        this.barcodeCountView.ListButtonTapped += (s, e) => this.ShowResults();
        this.barcodeCountView.ExitButtonTapped += (s, e) => this.ShowResults();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        if (this.barcodeCount is null) return;
        this.barcodeCount.Scanned += this.OnBarcodeCountScanned;
        this.barcodeCount.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Standby);
        if (this.barcodeCount is not null)
        {
            this.barcodeCount.Scanned -= this.OnBarcodeCountScanned;
        }
    }

    private void OnBarcodeCountScanned(object? sender, BarcodeCountEventArgs args)
    {
        List<Barcode> recognized = args.Session.RecognizedBarcodes.ToList();
        UIApplication.SharedApplication.InvokeOnMainThread(() =>
        {
            this.scannedBarcodes.Clear();
            this.scannedBarcodes.AddRange(recognized);
        });
    }

    private void ShowResults()
    {
        // Present this.scannedBarcodes to the user.
    }
}
