/* ScannerV7.c - written for Scandit Linux SDK 7.4 (does NOT compile against 8.x on purpose).
 * Scans pallet labels (Code 128, Royal Mail) from a camera, up to 4 codes per frame.
 */
#include <stdio.h>
#include <Scandit/ScRecognitionContext.h>
#include <Scandit/ScBarcodeScanner.h>
#include <Scandit/ScBarcodeScannerSettings.h>
#include <Scandit/ScBarcodeScannerSession.h>
#include <Scandit/ScBarcodeArray.h>
#include <Scandit/ScBarcode.h>
#include <Scandit/ScImageDescription.h>
#include <Scandit/ScCamera.h>

#define SCANDIT_SDK_LICENSE_KEY "-- INSERT YOUR LICENSE KEY HERE --"

int main(void) {
    ScRecognitionContext *ctx = sc_recognition_context_new(SCANDIT_SDK_LICENSE_KEY, "/var/lib/pallet", NULL);
    ScBarcodeScannerSettings *settings = sc_barcode_scanner_settings_new_with_preset(SC_PRESET_NONE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_CODE128, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_RM4SCC, SC_TRUE);
    sc_barcode_scanner_settings_set_max_number_of_codes_per_frame(settings, 4);
    ScBarcodeScanner *scanner = sc_barcode_scanner_new_with_settings(ctx, settings);

    ScCamera *cam = sc_camera_new_from_path("/dev/video0", 4);
    ScSize res = {1920, 1080};
    sc_camera_request_resolution(cam, res);
    sc_camera_start_stream(cam);
    ScImageDescription *desc = sc_image_description_new();
    sc_recognition_context_start_new_frame_sequence(ctx);
    for (int i = 0; i < 1000; i++) {
        const uint8_t *data = sc_camera_get_frame(cam, desc);
        if (!data) break;
        ScProcessFrameResult result = sc_recognition_context_process_frame(ctx, desc, data);
        sc_camera_enqueue_frame_data(cam, data);
        if (result.status != SC_RECOGNITION_CONTEXT_STATUS_SUCCESS) {
            printf("error: %s\n", sc_context_status_flag_get_message(result.status));
            break;
        }
        ScBarcodeArray *codes = sc_barcode_scanner_session_get_newly_recognized_codes(
                sc_barcode_scanner_get_session(scanner));
        for (uint32_t k = 0; k < sc_barcode_array_get_size(codes); k++) {
            const ScBarcode *c = sc_barcode_array_get_item_at(codes, k);
            printf("%s\n", sc_byte_array_get_string(sc_barcode_get_data(c)));
        }
        sc_barcode_array_release(codes);
    }
    sc_recognition_context_end_frame_sequence(ctx);
    sc_camera_stop_stream(cam);
    sc_image_description_release(desc);
    sc_camera_release(cam);
    sc_barcode_scanner_release(scanner);
    sc_barcode_scanner_settings_release(settings);
    sc_recognition_context_release(ctx);
    return 0;
}
