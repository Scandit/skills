import { Camera, DataCaptureContext, DataCaptureView, FrameSourceState, ScanditCaptureCorePlugin } from 'scandit-capacitor-datacapture-core';
import { Symbology } from 'scandit-capacitor-datacapture-barcode';
import {
  CustomBarcode,
  ExpiryDateText,
  LabelCapture,
  LabelCaptureSettings,
  LabelCaptureValidationFlowOverlay,
  LabelDefinition,
} from 'scandit-capacitor-datacapture-label';

let labelCapture;

async function runApp() {
  await ScanditCaptureCorePlugin.initializePlugins();
  const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const camera = Camera.withSettings(LabelCapture.createRecommendedCameraSettings());
  context.setFrameSource(camera);

  const barcode = CustomBarcode.initWithNameAndSymbologies('Barcode', [
    Symbology.EAN13UPCA,
    Symbology.Code128,
  ]);
  barcode.optional = false;

  const expiry = new ExpiryDateText('Expiry Date');
  expiry.optional = false;

  const labelDefinition = new LabelDefinition('Perishable Product');
  labelDefinition.fields = [barcode, expiry];

  const settings = LabelCaptureSettings.settingsFromLabelDefinitions([labelDefinition], {});
  labelCapture = new LabelCapture(settings);
  context.setMode(labelCapture);

  const view = DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById('data-capture-view'));

  const validationFlowOverlay = new LabelCaptureValidationFlowOverlay(labelCapture);
  validationFlowOverlay.listener = {
    didCaptureLabelWithFields(fields) {
      labelCapture.isEnabled = false;
      view.webViewContentOnTop = true;
      console.log(fields);
    },
    didSubmitManualInputForField(field, oldValue, newValue) {
      console.log('Manual input', field.name, oldValue, '->', newValue);
    },
  };
  await view.addOverlay(validationFlowOverlay);

  view.webViewContentOnTop = false;
  await camera.switchToDesiredState(FrameSourceState.On);
  labelCapture.isEnabled = true;
}

runApp();
