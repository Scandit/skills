/*
 * Sample KMP Android host screen. BarcodeFindView is constructed and embedded,
 * but lifecycle wiring (onResume/onPause, startSearching/stopSearching) and the
 * finish-button UI listener are not set up yet.
 */

package com.example.kmpapp.android

import android.view.View
import android.view.ViewGroup
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import com.example.kmpapp.shared.FindScreenModel
import com.kmp.datacapture.barcode.find.BarcodeFindView
import com.kmp.datacapture.barcode.ui.toAndroidView

@Composable
fun FindScreen(screenModel: FindScreenModel) {
    val context = LocalContext.current

    val barcodeFindView = remember {
        BarcodeFindView(context, screenModel.barcodeFind, screenModel.viewSettings)
    }

    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = {
            val native: View = barcodeFindView.toAndroidView()
            (native.parent as? ViewGroup)?.removeView(native)
            native
        },
    )
}
