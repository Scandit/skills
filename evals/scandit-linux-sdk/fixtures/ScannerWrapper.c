/* ScannerWrapper.c - implementation for Scandit Linux SDK 7.6 (does NOT compile against 8.x on purpose). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <Scandit/ScRecognitionContext.h>
#include <Scandit/ScBarcodeScanner.h>
#include <Scandit/ScBarcodeScannerSettings.h>
#include <Scandit/ScBarcodeScannerSession.h>
#include <Scandit/ScBarcodeArray.h>
#include <Scandit/ScBarcode.h>
#include <Scandit/ScImageDescription.h>
#include "ScannerWrapper.h"

#define SCANDIT_SDK_LICENSE_KEY "-- INSERT YOUR LICENSE KEY HERE --"

struct scanner {
    ScRecognitionContext *ctx;
    ScBarcodeScanner *scanner;
    ScImageDescription *desc;
};

scanner_t *scanner_create(const char *data_dir, char *err, int err_len) {
    scanner_t *s = calloc(1, sizeof *s);
    s->ctx = sc_recognition_context_new(SCANDIT_SDK_LICENSE_KEY, data_dir, NULL);
    ScBarcodeScannerSettings *settings = sc_barcode_scanner_settings_new_with_preset(SC_PRESET_HIGH_EFFORT);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_CODE128, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_DATA_MATRIX, SC_TRUE);
    sc_barcode_scanner_settings_set_max_number_of_codes_per_frame(settings, 8);
    s->scanner = sc_barcode_scanner_new_with_settings(s->ctx, settings);
    sc_barcode_scanner_settings_release(settings);
    if (!s->scanner) { snprintf(err, err_len, "scanner creation failed"); scanner_destroy(s); return NULL; }
    s->desc = sc_image_description_new();
    return s;
}

int scanner_scan_gray(scanner_t *s, const uint8_t *pixels, uint32_t width, uint32_t height, uint32_t stride,
                      scan_result_t *results, int max_results) {
    sc_image_description_set_width(s->desc, width);
    sc_image_description_set_height(s->desc, height);
    sc_image_description_set_layout(s->desc, SC_IMAGE_LAYOUT_GRAY_8U);
    sc_image_description_set_plane_row_bytes(s->desc, 0, stride);
    sc_recognition_context_start_new_frame_sequence(s->ctx);
    ScProcessFrameResult r = sc_recognition_context_process_frame(s->ctx, s->desc, pixels);
    sc_recognition_context_end_frame_sequence(s->ctx);
    if (r.status != SC_RECOGNITION_CONTEXT_STATUS_SUCCESS) {
        fprintf(stderr, "scan failed: %s\n", sc_context_status_flag_get_message(r.status));
        return -1;
    }
    ScBarcodeArray *codes = sc_barcode_scanner_session_get_newly_recognized_codes(sc_barcode_scanner_get_session(s->scanner));
    int n = 0;
    for (uint32_t i = 0; i < sc_barcode_array_get_size(codes) && n < max_results; i++, n++) {
        const ScBarcode *c = sc_barcode_array_get_item_at(codes, i);
        snprintf(results[n].text, sizeof results[n].text, "%s", sc_byte_array_get_string(sc_barcode_get_data(c)));
        snprintf(results[n].symbology, sizeof results[n].symbology, "%s", sc_symbology_to_string(sc_barcode_get_symbology(c)));
    }
    sc_barcode_array_release(codes);
    return n;
}

void scanner_destroy(scanner_t *s) {
    if (!s) return;
    sc_image_description_release(s->desc);
    sc_barcode_scanner_release(s->scanner);
    sc_recognition_context_release(s->ctx);
    free(s);
}
