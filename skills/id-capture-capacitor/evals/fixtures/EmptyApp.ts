// Empty starter for the ID Capture Capacitor integration eval.
// The skill should fill in: the ScanditCaptureCorePlugin.initializePlugins()
// call, DataCaptureContext.initialize(licenseKey), IdCaptureSettings +
// IdCapture + listener wiring, Camera.withSettings(...), DataCaptureView +
// view.connectToElement(div), and a Capacitor App-plugin-based lifecycle.

// Expected HTML in www/index.html:
//   <div id="data-capture-view" style="width:100vw;height:100vh;z-index:-1"></div>

export async function bootstrap(): Promise<void> {
  // TODO: initialize Scandit plugins, create context, set up ID Capture,
  // create camera, attach view to #data-capture-view, register listener.
}

document.addEventListener('DOMContentLoaded', () => {
  bootstrap();
});
