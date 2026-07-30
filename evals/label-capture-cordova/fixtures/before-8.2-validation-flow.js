let labelCapture;

document.addEventListener('deviceready', () => {
  const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = Scandit.LabelCapture.createRecommendedCameraSettings();
  const camera = Scandit.Camera.default;
  camera.applySettings(cameraSettings);
  context.setFrameSource(camera);

  const barcode = Scandit.CustomBarcode.initWithNameAndSymbologies('Barcode', [
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.Code128,
  ]);
  barcode.optional = false;

  const expiry = new Scandit.ExpiryDateText('Expiry Date');
  expiry.optional = false;

  const labelDefinition = new Scandit.LabelDefinition('Perishable Product');
  labelDefinition.fields = [barcode, expiry];

  const settings = Scandit.LabelCaptureSettings.settingsFromLabelDefinitions([labelDefinition], {});
  labelCapture = new Scandit.LabelCapture(settings);
  context.setMode(labelCapture);

  const view = Scandit.DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById('data-capture-view'));

  const validationFlowOverlay = new Scandit.LabelCaptureValidationFlowOverlay(labelCapture);
  validationFlowOverlay.listener = {
    didCaptureLabelWithFields(fields) {
      labelCapture.isEnabled = false;
      console.log(fields);
    },
  };
  view.addOverlay(validationFlowOverlay);

  camera.switchToDesiredState(Scandit.FrameSourceState.On);
  labelCapture.isEnabled = true;
}, false);
