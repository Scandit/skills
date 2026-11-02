/* ScannerV5.c - written for Scandit Linux SDK 5.x (does NOT compile against 7.x or 8.x on purpose).
 * Reads GS1 retail labels from still images and parses them.
 */
#include <stdio.h>
#include <string.h>
#include <Scandit/ScRecognitionContext.h>
#include <Scandit/ScBarcodeScanner.h>
#include <Scandit/ScBarcodeScannerSettings.h>
#include <Scandit/ScBarcodeScannerSession.h>
#include <Scandit/ScBarcodeArray.h>
#include <Scandit/ScBarcode.h>
#include <Scandit/ScImageDescription.h>
#include <Scandit/Parser/SpParser.h>

#define SCANDIT_SDK_LICENSE_KEY "-- INSERT YOUR LICENSE KEY HERE --"

int scan_label(const uint8_t *pixels, uint32_t w, uint32_t h) {
    ScRecognitionContext *ctx = sc_recognition_context_new(SCANDIT_SDK_LICENSE_KEY, "/tmp", NULL);
    ScBarcodeScannerSettings *settings = sc_barcode_scanner_settings_new_with_preset(SC_PRESET_ENABLE_SINGLE_FRAME_MODE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_EAN13, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_UPCA, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_CODE128, SC_TRUE);
    sc_barcode_scanner_settings_set_code_caching_duration(settings, 0);
    ScBarcodeScanner *scanner = sc_barcode_scanner_new_with_settings(ctx, settings);
    SpParser *parser = sp_parser_new_with_context(ctx, SP_PARSER_TYPE_GS1_AI, NULL);

    ScImageDescription *desc = sc_image_description_new();
    sc_image_description_set_width(desc, w);
    sc_image_description_set_height(desc, h);
    sc_image_description_set_layout(desc, SC_IMAGE_LAYOUT_GRAY_8U);
    sc_image_description_set_memory_size(desc, w * h);
    sc_recognition_context_start_new_frame_sequence(ctx);
    sc_recognition_context_process_frame(ctx, desc, pixels);
    sc_recognition_context_end_frame_sequence(ctx);

    ScBarcodeArray *codes = sc_barcode_scanner_session_get_newly_recognized_codes(sc_barcode_scanner_get_session(scanner));
    for (uint32_t i = 0; i < sc_barcode_array_get_size(codes); i++) {
        ScData data = sc_barcode_get_data(sc_barcode_array_get_item_at(codes, i));
        SpParserResult *result = NULL;
        if (sp_parser_parse_string(parser, data.c_str, data.length, &result))
            printf("parsed %u fields\n", (unsigned)sp_parser_result_get_fields_count(result));
        sp_parser_result_free(result);
        sc_data_free(data);
    }
    sc_barcode_array_release(codes);
    sp_parser_free(parser);
    sc_image_description_release(desc);
    sc_barcode_scanner_release(scanner);
    sc_barcode_scanner_settings_release(settings);
    sc_recognition_context_release(ctx);
    return 0;
}
