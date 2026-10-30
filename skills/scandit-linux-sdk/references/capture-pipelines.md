# Feeding frames from your own capture code: OpenCV, GStreamer, libcamera, vendor SDKs, C++

*The SDK doesn't care where a frame comes from: it needs a pointer to the pixels and an `ScImageDescription` that matches them exactly. The examples use OpenCV 4 and GStreamer 1.x. The bundled `samples/opencv_cpp_demo`, `samples/opencv_py_demo` and `samples/gstreamer` are further references.*

## Integration flow

Ask which capture stack the user has (OpenCV, GStreamer, libcamera, a vendor camera SDK, files, shared memory), its pixel format (GRAY8, NV12, YUYV/YUY2, BGR, …), whether the frames form a continuous stream or are unrelated images, and which file does the capturing. Then add the scanning to that file following the matching section below and integration.md (settings, frame sequence, results, teardown), and show the integration.md setup checklist.

## Describing a buffer correctly

| Your format | `ScImageLayout` | Row bytes (plane 0) | Extra |
| --- | --- | --- | --- |
| 8-bit grey, GStreamer `GRAY8`, OpenCV `CV_8UC1` | `SC_IMAGE_LAYOUT_GRAY_8U` | stride ≥ width | best choice |
| NV12 (Y plane + interleaved CbCr) | `SC_IMAGE_LAYOUT_YPCBCR_8U` | Y stride | plane 1: CbCr stride and its offset from the start of the buffer (usually Y stride × height); plane 0 offset 0 |
| NV21 (Y + interleaved CrCb) | `SC_IMAGE_LAYOUT_YPCRCB_8U` | as NV12 | as NV12 |
| I420 / YUV420 planar | `SC_IMAGE_LAYOUT_I420_8U` | Y stride | use `sc_image_description_get_planes_count` and set row bytes and offset for every plane |
| NV16 | `SC_IMAGE_LAYOUT_NV16_8U` (Python `sc.IMAGE_LAYOUT_NV16_U8`) | Y stride | plane 1 as NV12 |
| YUYV / GStreamer `YUY2` | `SC_IMAGE_LAYOUT_YUYV_8U` | ≥ 2 × width | |
| UYVY | `SC_IMAGE_LAYOUT_UYVY_8U` | ≥ 2 × width | |
| BGR (OpenCV `CV_8UC3`) | `SC_IMAGE_LAYOUT_BGR_8U` | ≥ 3 × width | converted to grey by the SDK |
| RGB / RGBA / ARGB | `SC_IMAGE_LAYOUT_RGB_8U` / `RGBA_8U` / `ARGB_8U` | 3 or 4 × width | converted to grey by the SDK |

- **Always use the real stride** reported by your capture stack (GStreamer `GST_VIDEO_INFO_PLANE_STRIDE`, OpenCV `Mat::step` / numpy `strides[0]`, V4L2 `bytesperline`). Rows are often padded; width × bytes per pixel is then wrong and gives status 5 (`INCONSISTENT_IMAGE_DATA`) or garbage.
- Prefer formats with a luminance plane (grey or YUV). Converting a YUV frame to RGB just to pass it to the SDK costs time and adds nothing.
- Pass the frame **before** any scaling, sharpening, thresholding or compression. Cropping is fine if the crop keeps enough pixels per module and is at least 320×160 px.
- The buffer must stay valid and unchanged until `sc_recognition_context_process_frame` returns.
- **Continuous stream:** one frame sequence for the whole stream (`start_new_frame_sequence` once). **Unrelated images:** a new sequence per image.
- All SDK calls for one context happen on one thread. If frames arrive on a capture thread or in a callback, hand them to a single scanning thread (and copy or hold a reference to the buffer).

## C helper for NV12, YUYV and grey buffers

```c
/* frame_scanner.h - feed frames from your own capture stack (GStreamer appsink, libcamera, a vendor SDK,
 * shared memory, ...) to the Scandit Linux SDK (8.x). Call every function from the same thread.
 */
#ifndef FRAME_SCANNER_H
#define FRAME_SCANNER_H
#include <stdint.h>
#include <Scandit/ScRecognitionContext.h>
#include <Scandit/ScBarcodeScanner.h>
#include <Scandit/ScBarcodeScannerSettings.h>
#include <Scandit/ScBarcodeScannerSession.h>
#include <Scandit/ScBarcodeArray.h>
#include <Scandit/ScBarcode.h>
#include <Scandit/ScImageDescription.h>

/* Describe a greyscale frame: one plane, `stride` bytes per row (>= width). */
static inline void describe_gray(ScImageDescription *d, uint32_t w, uint32_t h, uint32_t stride) {
    sc_image_description_set_width(d, w);
    sc_image_description_set_height(d, h);
    sc_image_description_set_layout(d, SC_IMAGE_LAYOUT_GRAY_8U);
    sc_image_description_set_plane_row_bytes(d, 0, stride);
}

/* Describe an NV12 frame (Y plane, then interleaved CbCr at half height). Both planes need their
 * row bytes and their offset from the start of the buffer passed to process_frame. */
static inline void describe_nv12(ScImageDescription *d, uint32_t w, uint32_t h,
                                 uint32_t y_stride, uint32_t uv_stride, uint32_t uv_offset) {
    sc_image_description_set_width(d, w);
    sc_image_description_set_height(d, h);
    sc_image_description_set_layout(d, SC_IMAGE_LAYOUT_YPCBCR_8U);   /* NV12; NV21 = YPCRCB_8U */
    sc_image_description_set_plane_row_bytes(d, 0, y_stride);
    sc_image_description_set_plane_offset(d, 0, 0);
    sc_image_description_set_plane_row_bytes(d, 1, uv_stride);
    sc_image_description_set_plane_offset(d, 1, uv_offset);           /* usually y_stride * h */
}

/* Describe a packed YUYV (GStreamer "YUY2") frame: 2 bytes per pixel. */
static inline void describe_yuyv(ScImageDescription *d, uint32_t w, uint32_t h, uint32_t stride) {
    sc_image_description_set_width(d, w);
    sc_image_description_set_height(d, h);
    sc_image_description_set_layout(d, SC_IMAGE_LAYOUT_YUYV_8U);
    sc_image_description_set_plane_row_bytes(d, 0, stride);           /* >= 2 * width */
}

/* Process one frame of a continuous stream and print the new codes. Call
 * sc_recognition_context_start_new_frame_sequence() once before the first frame of a stream.
 * Returns the status flag (1 = SC_RECOGNITION_CONTEXT_STATUS_SUCCESS). */
static inline int scan_frame(ScRecognitionContext *ctx, ScBarcodeScanner *scanner,
                             const ScImageDescription *desc, const uint8_t *buffer,
                             void (*on_code)(const ScBarcode *code)) {
    ScProcessFrameResult r = sc_recognition_context_process_frame(ctx, desc, buffer);
    int flag = (int)r.status.flag;
    sc_process_frame_result_free(r);
    if (flag != SC_RECOGNITION_CONTEXT_STATUS_SUCCESS) return flag;
    ScBarcodeArray *codes =
            sc_barcode_scanner_session_get_newly_recognized_codes(sc_barcode_scanner_get_session(scanner));
    for (uint32_t i = 0; i < sc_barcode_array_get_size(codes); i++)
        on_code(sc_barcode_array_get_item_at(codes, i));             /* valid until the array is released */
    sc_barcode_array_release(codes);
    return flag;
}
#endif
```

## GStreamer (appsink, C)

Ask GStreamer for the format you want with a caps filter before the `appsink`, map each buffer, and take the stride from `GstVideoInfo`.

```c
/* scan_gstreamer.c - scan barcodes in frames from a GStreamer pipeline (appsink) with the Scandit Linux SDK (8.x).
 * Build: gcc -O2 -std=c99 -o scan_gstreamer scan_gstreamer.c -lscanditsdk \
 *            $(pkg-config --cflags --libs gstreamer-app-1.0 gstreamer-video-1.0)
 * Run:   ./scan_gstreamer "filesrc location=video.mp4 ! decodebin ! videoconvert"
 *        (any GStreamer source works, e.g. a v4l2src element for a camera)
 *        (any source; the program appends "! video/x-raw,format=GRAY8 ! appsink")
 */
#include <stdio.h>
#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <gst/video/video.h>
#include <Scandit/ScRecognitionContext.h>
#include <Scandit/ScBarcodeScanner.h>
#include <Scandit/ScBarcodeScannerSettings.h>
#include <Scandit/ScBarcodeScannerSession.h>
#include <Scandit/ScBarcodeArray.h>
#include <Scandit/ScBarcode.h>
#include <Scandit/ScImageDescription.h>

#ifndef SCANDIT_SDK_LICENSE_KEY
#define SCANDIT_SDK_LICENSE_KEY "-- INSERT YOUR LICENSE KEY HERE --"
#endif
#define SCANDIT_WRITABLE_DATA_PATH "/tmp"   /* use a directory that survives reboots */

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s \"<source pipeline>\"\n", argv[0]); return 2; }
    gst_init(&argc, &argv);

    /* GRAY8 is the cheapest input for the SDK; NV12 and YUY2 work too (see frame_scanner.h). */
    gchar *launch = g_strdup_printf("%s ! video/x-raw,format=GRAY8 ! appsink name=sink max-buffers=2 drop=true", argv[1]);
    GError *gerr = NULL;
    GstElement *pipeline = gst_parse_launch(launch, &gerr);
    g_free(launch);
    if (!pipeline) { fprintf(stderr, "pipeline: %s\n", gerr ? gerr->message : "?"); g_clear_error(&gerr); return 1; }
    GstAppSink *sink = GST_APP_SINK(gst_bin_get_by_name(GST_BIN(pipeline), "sink"));

    ScRecognitionContext *ctx =
            sc_recognition_context_new(SCANDIT_SDK_LICENSE_KEY, SCANDIT_WRITABLE_DATA_PATH, NULL);
    ScBarcodeScannerSettings *settings = sc_barcode_scanner_settings_new_with_preset(SC_PRESET_NONE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_EAN13_UPCA, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_CODE128, SC_TRUE);
    sc_barcode_scanner_settings_set_code_duplicate_filter(settings, 1000);
    ScBarcodeScanner *scanner = ctx ? sc_barcode_scanner_new(ctx) : NULL;
    int ok = scanner != NULL;
    if (ok) {
        ScContextStatus st = sc_barcode_scanner_apply_settings(scanner, settings);
        ok = (st.flag == SC_RECOGNITION_CONTEXT_STATUS_SUCCESS);
        if (!ok) fprintf(stderr, "apply_settings: status %d: %s\n", (int)st.flag, sc_byte_array_get_string(st.message));
        sc_context_status_free(st);
    }

    ScImageDescription *desc = sc_image_description_new();
    if (ok) {
        gst_element_set_state(pipeline, GST_STATE_PLAYING);
        sc_recognition_context_start_new_frame_sequence(ctx);
    }
    while (ok) {
        GstSample *sample = gst_app_sink_pull_sample(sink);   /* NULL at end of stream */
        if (!sample) break;
        GstVideoInfo info;
        GstMapInfo map;
        GstBuffer *buffer = gst_sample_get_buffer(sample);
        if (gst_video_info_from_caps(&info, gst_sample_get_caps(sample)) &&
            gst_buffer_map(buffer, &map, GST_MAP_READ)) {
            /* GStreamer pads rows: always take the stride (and plane offsets) from GstVideoInfo. */
            sc_image_description_set_width(desc, (uint32_t)GST_VIDEO_INFO_WIDTH(&info));
            sc_image_description_set_height(desc, (uint32_t)GST_VIDEO_INFO_HEIGHT(&info));
            sc_image_description_set_layout(desc, SC_IMAGE_LAYOUT_GRAY_8U);
            sc_image_description_set_plane_row_bytes(desc, 0, (uint32_t)GST_VIDEO_INFO_PLANE_STRIDE(&info, 0));

            ScProcessFrameResult r = sc_recognition_context_process_frame(ctx, desc, map.data);
            ok = (r.status.flag == SC_RECOGNITION_CONTEXT_STATUS_SUCCESS);
            if (!ok) fprintf(stderr, "process_frame: status %d: %s\n", (int)r.status.flag,
                             sc_byte_array_get_string(r.status.message));
            sc_process_frame_result_free(r);
            gst_buffer_unmap(buffer, &map);

            ScBarcodeArray *codes =
                    sc_barcode_scanner_session_get_newly_recognized_codes(sc_barcode_scanner_get_session(scanner));
            for (uint32_t i = 0; i < sc_barcode_array_get_size(codes); i++) {
                const ScBarcode *c = sc_barcode_array_get_item_at(codes, i);
                printf("%s: %s\n", sc_symbology_to_string(sc_barcode_get_symbology(c)),
                       sc_byte_array_get_string(sc_barcode_get_data(c)));
            }
            sc_barcode_array_release(codes);
        }
        gst_sample_unref(sample);
    }
    if (ctx) sc_recognition_context_end_frame_sequence(ctx);

    gst_element_set_state(pipeline, GST_STATE_NULL);
    gst_object_unref(sink);
    gst_object_unref(pipeline);
    sc_image_description_release(desc);
    sc_barcode_scanner_release(scanner);
    sc_barcode_scanner_settings_release(settings);
    sc_recognition_context_release(ctx);
    return ok ? 0 : 1;
}
```

- For NV12 use `format=NV12` in the caps filter and `describe_nv12(desc, w, h, GST_VIDEO_INFO_PLANE_STRIDE(&info, 0), GST_VIDEO_INFO_PLANE_STRIDE(&info, 1), GST_VIDEO_INFO_PLANE_OFFSET(&info, 1))` from the helper above.
- `max-buffers=2 drop=true` keeps latency low when scanning is slower than the camera: old frames are dropped instead of queued.
- The package also contains a GStreamer **plugin** sample (`samples/gstreamer`, built with meson and ninja) that scans inside a pipeline: `... ! video/x-raw,format=YUY2 ! scanditsdkplugin symbologies=ean13,qr ! autovideosink`. It accepts YUY2 and NV12 only, and its license key is a macro in its source. See its README for the properties (`silent`, `once`, `singleframe`, `draw`, `symbologies`).

## OpenCV (C++), with RAII wrappers

`std::unique_ptr` with the matching release function gives exception-safe cleanup; declaring the context first makes it the last object destroyed.

```cpp
// scan_opencv.cpp - decode barcodes in images loaded with OpenCV, using small RAII wrappers around the
// Scandit Linux SDK C API (8.x).
// Build: g++ -O2 -std=c++17 -o scan_opencv scan_opencv.cpp -lscanditsdk $(pkg-config --cflags --libs opencv4)
// Run:   ./scan_opencv image1.png [image2.jpg ...]
#include <cstdio>
#include <memory>
#include <stdexcept>
#include <string>
#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <Scandit/ScRecognitionContext.h>
#include <Scandit/ScBarcodeScanner.h>
#include <Scandit/ScBarcodeScannerSettings.h>
#include <Scandit/ScBarcodeScannerSession.h>
#include <Scandit/ScBarcodeArray.h>
#include <Scandit/ScBarcode.h>
#include <Scandit/ScImageDescription.h>

#ifndef SCANDIT_SDK_LICENSE_KEY
#define SCANDIT_SDK_LICENSE_KEY "-- INSERT YOUR LICENSE KEY HERE --"
#endif

// Owning pointers that call the matching release function.
template <typename T, void (*Release)(T const *)>
struct Releaser { void operator()(T *p) const { Release(p); } };
using Context = std::unique_ptr<ScRecognitionContext, Releaser<ScRecognitionContext, sc_recognition_context_release>>;
using Scanner = std::unique_ptr<ScBarcodeScanner, Releaser<ScBarcodeScanner, sc_barcode_scanner_release>>;
using Settings = std::unique_ptr<ScBarcodeScannerSettings, Releaser<ScBarcodeScannerSettings, sc_barcode_scanner_settings_release>>;
using Description = std::unique_ptr<ScImageDescription, Releaser<ScImageDescription, sc_image_description_release>>;
using Codes = std::unique_ptr<ScBarcodeArray, Releaser<ScBarcodeArray, sc_barcode_array_release>>;

static std::string text(ScByteArray a) {
    const char *s = sc_byte_array_get_string(a);
    return s ? s : "";
}

// Throws with the status code and message, and always frees the status.
static void check(ScContextStatus status, const char *what) {
    const bool ok = status.flag == SC_RECOGNITION_CONTEXT_STATUS_SUCCESS;
    const std::string msg = std::string(what) + ": status " + std::to_string(int(status.flag)) + ": " +
                            text(status.message);
    sc_context_status_free(status);
    if (!ok) throw std::runtime_error(msg);
}

// Maps a cv::Mat to the SDK's image description: no copy, the stride comes from Mat::step.
static void describe(ScImageDescription *d, const cv::Mat &m) {
    sc_image_description_set_width(d, uint32_t(m.cols));
    sc_image_description_set_height(d, uint32_t(m.rows));
    sc_image_description_set_layout(d, m.type() == CV_8UC1 ? SC_IMAGE_LAYOUT_GRAY_8U : SC_IMAGE_LAYOUT_BGR_8U);
    sc_image_description_set_plane_row_bytes(d, 0, uint32_t(m.step[0]));
}

int main(int argc, char **argv) try {
    if (argc < 2) { std::fprintf(stderr, "usage: %s image...\n", argv[0]); return 2; }

    // Declared in this order so they are destroyed in reverse: everything before the context.
    Context ctx(sc_recognition_context_new(SCANDIT_SDK_LICENSE_KEY, "/tmp", nullptr));
    if (!ctx) throw std::runtime_error("context creation failed");
    Settings settings(sc_barcode_scanner_settings_new_with_preset(SC_PRESET_HIGH_EFFORT));
    sc_barcode_scanner_settings_set_symbology_enabled(settings.get(), SC_SYMBOLOGY_QR, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings.get(), SC_SYMBOLOGY_DATA_MATRIX, SC_TRUE);
    sc_barcode_scanner_settings_set_code_duplicate_filter(settings.get(), SC_DUPLICATE_FILTER_OFF);
    sc_barcode_scanner_settings_set_code_location_constraint_2d(settings.get(), SC_CODE_LOCATION_IGNORE);
    sc_barcode_scanner_settings_set_code_direction_hint(settings.get(), SC_CODE_DIRECTION_NONE);
    Scanner scanner(sc_barcode_scanner_new(ctx.get()));
    if (!scanner) throw std::runtime_error("scanner creation failed (one scanner per context)");
    check(sc_barcode_scanner_apply_settings(scanner.get(), settings.get()), "apply_settings");
    sc_barcode_scanner_wait_for_setup_completed(scanner.get());
    Description desc(sc_image_description_new());

    for (int i = 1; i < argc; ++i) {
        // Greyscale is the cheapest input; a BGR Mat (IMREAD_COLOR) works too with SC_IMAGE_LAYOUT_BGR_8U.
        cv::Mat image = cv::imread(argv[i], cv::IMREAD_GRAYSCALE);
        if (image.empty()) { std::fprintf(stderr, "%s: cannot read\n", argv[i]); continue; }
        describe(desc.get(), image);

        sc_recognition_context_start_new_frame_sequence(ctx.get());    // one sequence per unrelated image
        ScProcessFrameResult r = sc_recognition_context_process_frame(ctx.get(), desc.get(), image.data);
        const bool ok = r.status.flag == SC_RECOGNITION_CONTEXT_STATUS_SUCCESS;
        const std::string msg = text(r.status.message);
        sc_process_frame_result_free(r);
        sc_recognition_context_end_frame_sequence(ctx.get());
        if (!ok) throw std::runtime_error(std::string(argv[i]) + ": " + msg);

        Codes codes(sc_barcode_scanner_session_get_newly_recognized_codes(sc_barcode_scanner_get_session(scanner.get())));
        for (uint32_t k = 0; k < sc_barcode_array_get_size(codes.get()); ++k) {
            const ScBarcode *code = sc_barcode_array_get_item_at(codes.get(), k);
            std::printf("%s: %s: %s\n", argv[i], sc_symbology_to_string(sc_barcode_get_symbology(code)),
                        sc_byte_array_get_string(sc_barcode_get_data(code)));
        }
    }
    return 0;
} catch (const std::exception &e) {
    std::fprintf(stderr, "%s\n", e.what());
    return 1;
}
```

- `cv::imread(path, cv::IMREAD_GRAYSCALE)` gives `CV_8UC1` (`SC_IMAGE_LAYOUT_GRAY_8U`); `IMREAD_COLOR` gives **BGR** (`SC_IMAGE_LAYOUT_BGR_8U`, not RGB).
- For `cv::VideoCapture` streams keep one frame sequence open across frames, as in the Python example below.
- The bundled `opencv_cpp_demo` builds with CMake; for a single file `g++ ... $(pkg-config --cflags --libs opencv4)` is enough.

## OpenCV (Python)

```python
"""scan_opencv.py - scan barcodes in frames from OpenCV (video file, image sequence or camera index) with the Python bindings (8.x).

Setup: pip install opencv-python numpy; scanditsdk.py on PYTHONPATH
Run:   python3 scan_opencv.py video.mp4      (or a camera index such as 0)
"""
import sys

import cv2
import numpy as np
import scanditsdk as sc

LICENSE_KEY = "-- INSERT YOUR LICENSE KEY HERE --"
WRITABLE_DATA_PATH = "/tmp"


def describe(descr: sc.ImageDescription, frame: np.ndarray) -> None:
    """Map an OpenCV frame (greyscale or BGR, uint8) to the SDK's image description, without a copy."""
    descr.width = frame.shape[1]
    descr.height = frame.shape[0]
    descr.layout = sc.IMAGE_LAYOUT_GRAY_8U if frame.ndim == 2 else sc.IMAGE_LAYOUT_BGR_8U
    descr.set_plane_row_bytes(0, frame.strides[0])


def main(source: str) -> int:
    capture = cv2.VideoCapture(int(source) if source.isdigit() else source)
    if not capture.isOpened():
        print(f"cannot open {source}")
        return 1

    context = sc.RecognitionContext(LICENSE_KEY, WRITABLE_DATA_PATH)
    settings = sc.BarcodeScannerSettings(preset=sc.PRESET_NONE)
    settings.enable_symbology(sc.SYMBOLOGY_QR, True)
    settings.enable_symbology(sc.SYMBOLOGY_CODE128, True)
    settings.code_duplicate_filter = 1000
    scanner = sc.BarcodeScanner(context)
    status = scanner.apply_settings(settings)
    if not status.is_success():
        print(f"apply_settings failed: status {status.flag}: {status.message}")
        return 1

    descr = sc.ImageDescription()
    frame_seq = context.start_new_frame_sequence()  # one sequence for a continuous stream
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            gray = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            describe(descr, gray)
            result = frame_seq.process_frame(descr, gray.ctypes.data)
            if not result.is_success():
                print(f"process_frame failed: status {result.flag}: {result.message}")
                return 1
            for code in scanner.session.newly_recognized_codes:
                print(f"{code.symbology_string}: {code.data}")
    finally:
        frame_seq.end()
        capture.release()
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python3 scan_opencv.py <video file | camera index>")
    sys.exit(main(sys.argv[1]))
```

For a BGR frame without conversion, `describe()` already selects `sc.IMAGE_LAYOUT_BGR_8U`; make sure the array is contiguous (`np.ascontiguousarray`) and set the stride from `frame.strides[0]`.

## libcamera, vendor SDKs, shared memory

- libcamera (Raspberry Pi camera stack) and most vendor SDKs deliver NV12/YUV420 or grey frames with explicit strides and plane offsets: map them with the table above (`describe_nv12` for NV12).
- Raspberry Pi cameras can also be used through V4L2 (`ScCamera`, integration.md); request a real sensor mode, not the reported stepwise maximum.
- The image layouts are 8-bit. For cameras that deliver 10/12/16-bit data, convert to 8-bit grey first (a fixed shift or lookup table rather than per-frame contrast stretching, so codes keep their contrast).
