import { Camera, DataCaptureContext, DataCaptureView, FrameSourceState, ScanditCaptureCorePlugin } from 'scandit-capacitor-datacapture-core';
import {
  CustomText,
  LabelCapture,
  LabelCaptureBasicOverlay,
  LabelCaptureSettings,
  LabelDefinition,
} from 'scandit-capacitor-datacapture-label';

async function runApp() {
  await ScanditCaptureCorePlugin.initializePlugins();
  const context = DataCaptureContext.forLicenseKey('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const camera = Camera.withSettings(LabelCapture.createRecommendedCameraSettings());
  context.setFrameSource(camera);

  const sku = new CustomText('SKU');
  sku.pattern = '\\d{8}';
  sku.dataTypePattern = 'SKU\\s*:';
  sku.optional = false;

  const labelDefinition = new LabelDefinition('Shipping Label');
  labelDefinition.fields = [sku];

  const settings = LabelCaptureSettings.settingsFromLabelDefinitions([labelDefinition], {});
  const labelCapture = new LabelCapture(settings);
  context.setMode(labelCapture);

  const view = DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById('data-capture-view'));
  await view.addOverlay(new LabelCaptureBasicOverlay(labelCapture));

  view.webViewContentOnTop = false;
  await camera.switchToDesiredState(FrameSourceState.On);
  labelCapture.isEnabled = true;
}

runApp();
