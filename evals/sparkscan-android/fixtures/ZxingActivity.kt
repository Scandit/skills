import android.content.Intent
import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.google.zxing.integration.android.IntentIntegrator
import com.google.zxing.integration.android.IntentResult

data class ScannedBarcode(val value: String, val format: String)

class ScannerActivity : AppCompatActivity() {

    private lateinit var resultLabel: TextView
    private val scannedBarcodes = mutableListOf<ScannedBarcode>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_scanner)
        resultLabel = findViewById(R.id.resultLabel)
        startScan()
    }

    private fun startScan() {
        val integrator = IntentIntegrator(this)
        integrator.setDesiredBarcodeFormats(
            IntentIntegrator.EAN_13,
            IntentIntegrator.CODE_128,
            IntentIntegrator.QR_CODE
        )
        integrator.setPrompt("Scan a barcode")
        integrator.setCameraId(0)
        integrator.setBeepEnabled(true)
        integrator.setBarcodeImageEnabled(false)
        integrator.initiateScan()
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        val result: IntentResult = IntentIntegrator.parseActivityResult(requestCode, resultCode, data)
        if (result.contents != null) {
            val barcode = ScannedBarcode(result.contents, result.formatName ?: "UNKNOWN")
            if (scannedBarcodes.none { it.value == barcode.value }) {
                scannedBarcodes.add(barcode)
                resultLabel.text = "Last scan: ${barcode.value} (${scannedBarcodes.size} total)"
            }
            startScan()
        } else {
            super.onActivityResult(requestCode, resultCode, data)
        }
    }
}
