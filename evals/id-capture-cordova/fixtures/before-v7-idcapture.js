// Existing ID Capture integration written against SDK v7 for Cordova.
// Uses the v7 API that was removed in v8:
//   - Scandit.AamvaBarcodeVerifier.create(context) + verifier.verify(...) (removed)
// The skill should migrate this to the v8 API (settings.rejectForgedAamvaBarcodes
// plus capturedId.verificationResult.aamvaBarcodeVerification).

(function () {
  'use strict';

  var licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

  document.addEventListener('deviceready', function onDeviceReady() {
    var context = Scandit.DataCaptureContext.initialize(licenseKey);

    var settings = new Scandit.IdCaptureSettings();
    settings.acceptedDocuments.push(new Scandit.DriverLicense(Scandit.IdCaptureRegion.Us));
    settings.scanner = new Scandit.IdCaptureScanner(new Scandit.FullDocumentScanner());

    var camera = Scandit.Camera.withSettings(Scandit.IdCapture.createRecommendedCameraSettings());
    context.setFrameSource(camera);

    var idCapture = new Scandit.IdCapture(settings);

    // v7 standalone verifier (removed in v8):
    Scandit.AamvaBarcodeVerifier.create(context).then(function (verifier) {
      idCapture.addListener({
        didCaptureId: function (_, capturedId) {
          idCapture.isEnabled = false;
          // v7 verification call (removed in v8):
          verifier.verify(capturedId).then(function (result) {
            console.log('AAMVA all checks passed:', result.allChecksPassed);
            idCapture.isEnabled = true;
          });
        },
        didRejectId: function (_, rejectedId, reason) {
          console.log('Rejected:', reason);
        },
      });
    });

    context.setMode(idCapture);

    var view = Scandit.DataCaptureView.forContext(context);
    view.connectToElement(document.getElementById('data-capture-view'));
    view.addOverlay(new Scandit.IdCaptureOverlay(idCapture));

    camera.switchToDesiredState(Scandit.FrameSourceState.On);
    idCapture.isEnabled = true;
  }, false);
})();
