// Existing ID Capture integration written against SDK v6 for Cordova.
// Uses the v6 API that was removed at v7:
//   - settings.supportedDocuments = Scandit.IdDocumentType.<...> bitmask (removed)
//   - settings.supportedSides = Scandit.SupportedSides.<...> (removed)
//   - capturedId.documentType getter (removed)
//   - onIdCaptureTimedOut listener callback (removed)
// The skill should migrate this to the v7+ list-based model
// (settings.acceptedDocuments + settings.scanner = new Scandit.IdCaptureScanner(...))
// and read the document type via capturedId.document?.documentType.

(function () {
  'use strict';

  var licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

  document.addEventListener('deviceready', function onDeviceReady() {
    var context = Scandit.DataCaptureContext.initialize(licenseKey);

    var settings = new Scandit.IdCaptureSettings();
    // v6 bitmask of document types (removed at v7):
    settings.supportedDocuments =
      Scandit.IdDocumentType.IdCardViz |
      Scandit.IdDocumentType.PassportMrz |
      Scandit.IdDocumentType.DrivingLicenseViz;
    // v6 sides selection (removed at v7):
    settings.supportedSides = Scandit.SupportedSides.FrontAndBack;

    var camera = Scandit.Camera.withSettings(Scandit.IdCapture.createRecommendedCameraSettings());
    context.setFrameSource(camera);

    var idCapture = new Scandit.IdCapture(settings);

    idCapture.addListener({
      didCaptureId: function (_, capturedId) {
        idCapture.isEnabled = false;
        // v6 document type getter (removed at v7):
        console.log('Document type:', capturedId.documentType);
        idCapture.isEnabled = true;
      },
      didRejectId: function (_, rejectedId, reason) {
        console.log('Rejected:', reason);
      },
      // v6 timeout callback (removed at v7):
      onIdCaptureTimedOut: function () {
        console.log('Capture timed out');
      },
    });

    context.setMode(idCapture);

    var view = Scandit.DataCaptureView.forContext(context);
    view.connectToElement(document.getElementById('data-capture-view'));
    view.addOverlay(new Scandit.IdCaptureOverlay(idCapture));

    camera.switchToDesiredState(Scandit.FrameSourceState.On);
    idCapture.isEnabled = true;
  }, false);
})();
