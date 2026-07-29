import android.os.Bundle
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.ListView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class ProductListActivity : AppCompatActivity() {

    private lateinit var listView: ListView
    private lateinit var totalLabel: TextView
    private val scannedProducts = mutableListOf<String>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_product_list)
        listView = findViewById(R.id.listView)
        totalLabel = findViewById(R.id.totalLabel)
        setupList()
    }

    private fun setupList() {
        listView.adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, scannedProducts)
    }

    private fun addProduct(barcode: String) {
        scannedProducts.add(barcode)
        (listView.adapter as ArrayAdapter<*>).notifyDataSetChanged()
        updateTotal()
    }

    private fun updateTotal() {
        totalLabel.text = "Total: ${scannedProducts.size}"
    }
}
