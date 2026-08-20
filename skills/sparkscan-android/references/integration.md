# SparkScan Android Integration Guide

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows. It overlays a trigger button on top of any screen so users can scan without leaving their workflow.

## Prerequisites

- Scandit Data Capture SDK for Android — add via Gradle. Before writing the dependency, fetch the latest published version from `https://central.sonatype.com/artifact/com.scandit.datacapture/barcode` and extract the latest version number from the page. Then add both dependencies:
  ```gradle
  dependencies {
      implementation "com.scandit.datacapture:barcode:<latest-version>"
      implementation "com.scandit.datacapture:core:<latest-version>"
  }
  ```
  The SDK is distributed via Maven Central.
- `minSdk` 24 or higher.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test
- Camera permission in `AndroidManifest.xml`:
  ```xml
  <uses-feature
        android:name="android.hardware.camera"
        android:required="true" />
  <uses-permission android:name="android.permission.CAMERA" />
  ```
  Request the permission at runtime using the standard Android permission API before scanning starts.

## Minimal Integration (Kotlin)

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which Activity or Fragment they'd like to integrate SparkScan into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**

1. Add `implementation "com.scandit.datacapture:barcode:<latest-version>"` and `implementation "com.scandit.datacapture:core:<latest-version>"` to your `build.gradle` dependencies (the version was already fetched and filled in above)
2. Add `<uses-permission android:name="android.permission.CAMERA" />` to `AndroidManifest.xml`
3. Request the `CAMERA` permission at runtime before scanning starts
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com

```kotlin
import android.os.Bundle
import android.view.ViewGroup
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.barcode.spark.capture.SparkScan
import com.scandit.datacapture.barcode.spark.capture.SparkScanListener
import com.scandit.datacapture.barcode.spark.capture.SparkScanSession
import com.scandit.datacapture.barcode.spark.capture.SparkScanSettings
import com.scandit.datacapture.barcode.spark.ui.SparkScanView
import com.scandit.datacapture.barcode.spark.ui.SparkScanViewSettings
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.data.FrameData

class MainActivity : AppCompatActivity(), SparkScanListener {

    private lateinit var dataCaptureContext: DataCaptureContext
    private lateinit var sparkScan: SparkScan
    private lateinit var sparkScanView: SparkScanView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        setupScanning()
    }

    override fun onResume() {
        super.onResume()
        sparkScanView.onResume()
    }

    override fun onPause() {
        sparkScanView.onPause()
        super.onPause()
    }

    private fun setupScanning() {
        dataCaptureContext = DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

        val settings = SparkScanSettings().apply {
            enableSymbologies(setOf(Symbology.EAN13_UPCA, Symbology.CODE128))
        }
        sparkScan = SparkScan(settings)
        sparkScan.addListener(this)

        val viewSettings = SparkScanViewSettings()
        sparkScanView = SparkScanView.newInstance(
            findViewById<ViewGroup>(android.R.id.content),
            dataCaptureContext,
            sparkScan,
            viewSettings
        )
    }

    override fun onBarcodeScanned(
        sparkScan: SparkScan,
        session: SparkScanSession,
        data: FrameData?,
    ) {
        val barcode = session.newlyRecognizedBarcode ?: return
        runOnUiThread {
            // Handle the barcode
            println("Scanned: ${barcode.data}")
        }
    }
}
```

## Custom Feedback

To reject barcodes and show error messages, implement `SparkScanFeedbackDelegate`:

```kotlin
import com.scandit.datacapture.barcode.spark.feedback.SparkScanBarcodeFeedback
import com.scandit.datacapture.barcode.spark.feedback.SparkScanFeedbackDelegate
import com.scandit.datacapture.core.time.TimeInterval

class MainActivity : AppCompatActivity(), SparkScanListener, SparkScanFeedbackDelegate {

    // ... existing setup code ...

    private fun setupScanning() {
        // ... existing setup ...
        sparkScanView.feedbackDelegate = this
    }

    override fun getFeedbackForBarcode(barcode: Barcode): SparkScanBarcodeFeedback? {
        return if (isValidBarcode(barcode)) {
            SparkScanBarcodeFeedback.Success()
        } else {
            SparkScanBarcodeFeedback.Error(
                message = "Wrong barcode",
                resumeCapturingDelay = TimeInterval.seconds(30f)
            )
        }
    }
}
```

> **Note:** `getFeedbackForBarcode` is called on a background thread. Do not update UI directly inside it.

## Hardware Trigger Support

For gloved-hand workflows where users scan with physical buttons:

```kotlin
val viewSettings = SparkScanViewSettings().apply {
    hardwareTriggerEnabled = true
}
sparkScanView = SparkScanView.newInstance(parentView, dataCaptureContext, sparkScan, viewSettings)
```

## Aim-to-Scan (Target Mode)

For precise scanning in crowded environments:

```kotlin
import com.scandit.datacapture.barcode.spark.ui.SparkScanPreviewBehavior
import com.scandit.datacapture.barcode.spark.ui.SparkScanScanningBehavior
import com.scandit.datacapture.barcode.spark.ui.SparkScanScanningMode

val viewSettings = SparkScanViewSettings().apply {
    defaultScanningMode = SparkScanScanningMode.Target(
        SparkScanScanningBehavior.SINGLE,
        SparkScanPreviewBehavior.DEFAULT
    )
}
```

## Custom Trigger Button

To hide the built-in trigger and control scanning programmatically:

```kotlin
sparkScanView.triggerButtonVisible = false

// Start scanning (e.g. from a custom button tap)
sparkScanView.startScanning()

// Pause scanning
sparkScanView.pauseScanning()
```

## Tracking View State

To react to scanner state changes (e.g. update a custom button's label):

```kotlin
import com.scandit.datacapture.barcode.spark.capture.SparkScanViewUiListener
import com.scandit.datacapture.barcode.spark.ui.SparkScanScanningMode
import com.scandit.datacapture.barcode.spark.ui.SparkScanViewState

class MainActivity : AppCompatActivity(), SparkScanListener, SparkScanViewUiListener {

    // ... existing setup code ...

    private fun setupScanning() {
        // ... existing setup ...
        sparkScanView.setListener(this)
    }

    override fun onViewStateChanged(newState: SparkScanViewState) {
        runOnUiThread {
            when (newState) {
                SparkScanViewState.ACTIVE -> myButton.text = "STOP SCANNING"
                else -> myButton.text = "START SCANNING"
            }
        }
    }

    override fun onScanningModeChange(newScanningMode: SparkScanScanningMode) { }
    override fun onBarcodeFindButtonTap(view: SparkScanView) { }
    override fun onBarcodeCountButtonTap(view: SparkScanView) { }
    override fun onLabelCaptureButtonTap(view: SparkScanView) { }
}
```
