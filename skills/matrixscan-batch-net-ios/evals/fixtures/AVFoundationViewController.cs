using System.Collections.Generic;
using System.Linq;
using AVFoundation;
using CoreFoundation;
using CoreGraphics;
using Foundation;
using UIKit;

namespace MyApp;

public record ScannedBarcode(string Value, string Format);

public partial class ScannerViewController : UIViewController
{
    private UILabel resultLabel = null!;
    private AVCaptureSession captureSession = null!;
    private AVCaptureVideoPreviewLayer previewLayer = null!;
    private MetadataObjectsDelegate metadataDelegate = null!;
    private readonly List<ScannedBarcode> scannedBarcodes = new();

    public ScannerViewController(IntPtr handle) : base(handle) { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.resultLabel = new UILabel
        {
            Frame = new CGRect(16, 64, this.View!.Bounds.Width - 32, 44),
            TextColor = UIColor.White,
            BackgroundColor = UIColor.FromWhiteAlpha(0, 0.4f),
        };
        this.View.AddSubview(this.resultLabel);

        this.SetUpAvFoundationScanner();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        if (!this.captureSession.Running)
        {
            this.captureSession.StartRunning();
        }
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        if (this.captureSession.Running)
        {
            this.captureSession.StopRunning();
        }
    }

    private void SetUpAvFoundationScanner()
    {
        var device = AVCaptureDevice.GetDefaultDevice(AVMediaTypes.Video);
        if (device == null) return;

        var input = AVCaptureDeviceInput.FromDevice(device, out _);
        this.captureSession = new AVCaptureSession();
        if (input != null && this.captureSession.CanAddInput(input))
        {
            this.captureSession.AddInput(input);
        }

        var metadataOutput = new AVCaptureMetadataOutput();
        if (this.captureSession.CanAddOutput(metadataOutput))
        {
            this.captureSession.AddOutput(metadataOutput);
        }

        // "Batch" behavior emerges from the per-frame metadata callback +
        // a manual dedupe-by-string-value HashSet.
        this.metadataDelegate = new MetadataObjectsDelegate(this.HandleBarcodes);
        metadataOutput.SetDelegate(this.metadataDelegate, DispatchQueue.MainQueue);
        metadataOutput.MetadataObjectTypes =
            AVMetadataObjectType.EAN13Code |
            AVMetadataObjectType.Code128Code |
            AVMetadataObjectType.QRCode;

        this.previewLayer = new AVCaptureVideoPreviewLayer(this.captureSession)
        {
            Frame = this.View!.Bounds,
            VideoGravity = AVLayerVideoGravity.ResizeAspectFill,
        };
        this.View.Layer.AddSublayer(this.previewLayer);
    }

    private void HandleBarcodes(IList<AVMetadataMachineReadableCodeObject> codes)
    {
        foreach (var code in codes)
        {
            if (string.IsNullOrEmpty(code.StringValue)) continue;
            var barcode = new ScannedBarcode(code.StringValue, code.Type.ToString());
            if (this.scannedBarcodes.Any(b => b.Value == barcode.Value)) continue;
            this.scannedBarcodes.Add(barcode);
            this.resultLabel.Text =
                $"Last scan: {barcode.Value} ({this.scannedBarcodes.Count} total)";
        }
    }

    private sealed class MetadataObjectsDelegate : AVCaptureMetadataOutputObjectsDelegate
    {
        private readonly Action<IList<AVMetadataMachineReadableCodeObject>> handler;

        public MetadataObjectsDelegate(
            Action<IList<AVMetadataMachineReadableCodeObject>> handler)
        {
            this.handler = handler;
        }

        public override void DidOutputMetadataObjects(
            AVCaptureMetadataOutput captureOutput,
            AVMetadataObject[] metadataObjects,
            AVCaptureConnection connection)
        {
            var codes = metadataObjects
                .OfType<AVMetadataMachineReadableCodeObject>()
                .ToList();
            this.handler(codes);
        }
    }
}
