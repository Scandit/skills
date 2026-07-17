using Android.App;
using Android.OS;
using Android.Widget;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;
using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Barcode.UI.Overlay;

namespace MyScanApp
{
    // Xamarin.Android (SDK v6.x) — no explicit ScanditCaptureCore.Initialize() call,
    // because 6.x self-initialized. This is the pre-migration state.
    [Activity(Label = "MyScanApp", MainLauncher = true)]
    public class MainActivity : Activity, IBarcodeCaptureListener
    {
        private DataCaptureContext dataCaptureContext;
        private Camera camera;
        private BarcodeCapture barcodeCapture;
        private DataCaptureView dataCaptureView;

        protected override void OnCreate(Bundle savedInstanceState)
        {
            base.OnCreate(savedInstanceState);

            dataCaptureContext = DataCaptureContext.ForLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --");

            var settings = BarcodeCaptureSettings.Create();
            settings.EnableSymbology(Symbology.Ean13Upca, true);
            settings.EnableSymbology(Symbology.Code128, true);

            barcodeCapture = BarcodeCapture.Create(dataCaptureContext, settings);
            barcodeCapture.AddListener(this);

            camera = Camera.GetDefaultCamera();
            camera?.ApplySettingsAsync(BarcodeCapture.RecommendedCameraSettings);
            dataCaptureContext.SetFrameSourceAsync(camera);

            dataCaptureView = DataCaptureView.Create(dataCaptureContext);
            BarcodeCaptureOverlay.Create(barcodeCapture, dataCaptureView);
            SetContentView(dataCaptureView);
        }

        public void OnBarcodeScanned(BarcodeCapture mode, BarcodeCaptureSession session, IFrameData frameData)
        {
            var code = session.NewlyRecognizedBarcode;
            RunOnUiThread(() => Toast.MakeText(this, code?.Data, ToastLength.Short).Show());
        }

        public void OnObservationStarted(BarcodeCapture mode) { }
        public void OnObservationStopped(BarcodeCapture mode) { }
        public void OnSessionUpdated(BarcodeCapture mode, BarcodeCaptureSession session, IFrameData frameData) { }
    }
}
