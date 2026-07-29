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
            println("Scanned: ${barcode.data}")
        }
    }
}
