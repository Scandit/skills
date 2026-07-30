package com.example.myapp

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

/**
 * A plain Android screen with no scanning yet. The user wants to add MatrixScan Count
 * (bulk barcode counting) here.
 */
class ScanActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val label = TextView(this).apply {
            text = "Inventory"
        }
        setContentView(label)
    }
}
