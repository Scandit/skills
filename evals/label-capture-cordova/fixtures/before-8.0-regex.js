document.addEventListener('deviceready', () => {
  const context = Scandit.DataCaptureContext.forLicenseKey('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = Scandit.LabelCapture.createRecommendedCameraSettings();
  const camera = Scandit.Camera.default;
  camera.applySettings(cameraSettings);
  context.setFrameSource(camera);

  const sku = new Scandit.CustomText('SKU');
  sku.pattern = '\\d{8}';
  sku.dataTypePattern = 'SKU\\s*:';
  sku.optional = false;

  const labelDefinition = new Scandit.LabelDefinition('Shipping Label');
  labelDefinition.fields = [sku];

  const settings = Scandit.LabelCaptureSettings.settingsFromLabelDefinitions([labelDefinition], {});
  const labelCapture = new Scandit.LabelCapture(settings);
  context.setMode(labelCapture);

  const view = Scandit.DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById('data-capture-view'));
  view.addOverlay(new Scandit.LabelCaptureBasicOverlay(labelCapture));

  camera.switchToDesiredState(Scandit.FrameSourceState.On);
  labelCapture.isEnabled = true;
}, false);
