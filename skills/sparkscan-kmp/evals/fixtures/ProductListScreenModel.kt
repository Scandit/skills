package com.example.app.shared

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Shared (commonMain) screen model backing a scanned-product list screen.
 * Scanning has not been added yet — [addProduct] is currently unused.
 */
class ProductListScreenModel {

    private val _scannedProducts = MutableStateFlow<List<String>>(emptyList())
    val scannedProducts: StateFlow<List<String>> = _scannedProducts.asStateFlow()

    private val _total = MutableStateFlow(0)
    val total: StateFlow<Int> = _total.asStateFlow()

    fun addProduct(barcode: String) {
        _scannedProducts.value = _scannedProducts.value + barcode
        updateTotal()
    }

    private fun updateTotal() {
        _total.value = _scannedProducts.value.size
    }
}
