# Scandit Linux SDK: barcode scanning integration (C / C++ / Python)

*Based on the [Linux overview](https://docs.scandit.com/sdks/linux/overview/), [Installation](https://docs.scandit.com/sdks/linux/add-sdk/), [Samples](https://docs.scandit.com/sdks/linux/samples/) and the [C API reference](https://docs.scandit.com/stable/c_api/annotated.html). The programs target SDK 8.6; for other 8.x versions check names against the headers in `/usr/include/Scandit/`, for 7.x and older see migration.md.*

The Linux SDK has no UI and no stream management. You wire it up by hand: a **recognition context** (license, one per process), **scanner settings** (symbologies, preset, areas), a **barcode scanner** (one per context), an **image description** for your buffer, a **frame sequence** around the frames you process, and the scanner **session** where the results appear.

## Prerequisites

- **Package:** the SDK zip from the Scandit dashboard contains `libscandit-barcodescanner-<version>-amd64.deb` and `-arm64.deb`, `scanditsdk.py` and `samples/`. Install the one for the machine's architecture:
  ```bash
  sudo dpkg -i libscandit-barcodescanner-<version>-amd64.deb   # or -arm64.deb (Jetson, Raspberry Pi 4/5)
  ```
  It installs `libscanditsdk.so` into `/usr/lib`, the headers into `/usr/include/Scandit/` and the recognition models into `/usr/share/scanditsdk/resources/` (the SDK loads them at runtime: never delete or move them).
- **glibc 2.31 or newer** (Ubuntu 20.04 / Debian 11 or newer). On older systems the SDK fails at link or load time. Check with `ldd --version`.
- **Python** (optional): Python 3 and the `scanditsdk.py` from the same package on `PYTHONPATH`. The examples use `numpy` and `Pillow`.
- **Camera** (optional): a V4L2 device (`/dev/videoN`) the process may open (usually membership in the `video` group). For build dependencies of the bundled samples: `libv4l-dev libsdl2-dev libsdl2-image-dev libpng-dev`.
- **License key** for the Linux platform: see **Licence key** in this skill's `SKILL.md`.

## Integration flow

Ask the user, in one message, only what isn't clear yet:
1. **Language:** C, C++ or Python.
2. **Input:** single images or files; a V4L2 camera (`/dev/videoN`); or frames their own code already captures (OpenCV, GStreamer, libcamera, a vendor SDK). For the last one also load [capture-pipelines.md](capture-pipelines.md).
3. **Symbologies** they need to scan. Mention that enabling only the symbologies they actually need improves speed and accuracy, and ask about unusual code lengths (symbol counts) and light-on-dark codes.
4. **One or several codes per frame.** Several codes per frame needs multi-scan and the "tracking" license feature; tracking codes across frames with stable IDs is MatrixScan: use [matrixscan.md](matrixscan.md).
5. **Which file** to integrate into (or whether to create a new program).

Once the user responds, write the integration code directly into that file, starting from the matching complete example below (single image or camera, C or Python). Do not just show the code in chat; apply it to the file. Keep the user's structure (functions, error handling, logging) and change only what the integration needs.

After writing the code, show this setup checklist:

**Setup checklist:**
1. Install the `.deb` for your architecture (`sudo dpkg -i libscandit-barcodescanner-<version>-<arch>.deb`) and check `ldd --version` shows glibc 2.31 or newer.
2. C/C++: build with `-lscanditsdk` (e.g. `gcc -O2 -std=c99 -o scanner scanner.c -lscanditsdk`). Python: put the folder containing the package's `scanditsdk.py` on `PYTHONPATH` and install `numpy` (and `pillow` for image files).
3. Replace `-- INSERT YOUR LICENSE KEY HERE --` with your Linux license key (see **Licence key** in `SKILL.md`). Its executable name must match your binary's name, or `python3` for Python, or be empty.
4. Set the writable data path to a directory that exists, is writable by the process and survives reboots (the examples use `/tmp` only for trying them out).
5. Camera only: make sure the process may open the device and request a resolution the camera actually offers (`v4l2-ctl --list-formats-ext -d /dev/video0`).

## How the pieces fit

| Step | C | Python | Notes |
| --- | --- | --- | --- |
| Context | `sc_recognition_context_new(key, writable_path, NULL)` | `sc.RecognitionContext(key, writable_path)` | One per process. Creation succeeds even with a bad key: the license status appears at `apply_settings` / `process_frame`. |
| Settings | `sc_barcode_scanner_settings_new_with_preset(SC_PRESET_…)` + setters, or `sc_barcode_scanner_settings_new_from_json` | `sc.BarcodeScannerSettings(preset=sc.PRESET_…)`, `enable_symbology`, properties, `BarcodeScannerSettings.from_json` | All symbologies off by default. |
| Scanner | `sc_barcode_scanner_new(ctx)` + `sc_barcode_scanner_apply_settings` (check + free the status) | `sc.BarcodeScanner(context)`, `scanner.apply_settings(settings)` → `status.is_success()` | One per context. `wait_for_setup_completed` blocks until it's ready. |
| Image | `sc_image_description_new` + width, height, layout, row bytes (+ plane offsets for NV12/NV21) | `sc.ImageDescription()` + `width`, `height`, `layout`, `set_plane_row_bytes(0, …)` | Greyscale or YUV is best; set the real stride. |
| Frames | `sc_recognition_context_start_new_frame_sequence` → `sc_recognition_context_process_frame` → `sc_recognition_context_end_frame_sequence` | `seq = context.start_new_frame_sequence()` → `seq.process_frame(descr, data)` → `seq.end()` | New sequence per unrelated image; one sequence per continuous stream. |
| Results | `sc_barcode_scanner_session_get_newly_recognized_codes(sc_barcode_scanner_get_session(scanner))` | `scanner.session.newly_recognized_codes` | Read after every frame. C: release the array. |
| Teardown | release scanner, settings, descriptions, arrays, then the context | objects are released when garbage-collected | C: the context last. |

## Complete example: single image (C)

Reads a binary greyscale **PGM** (`P5`) file so no image library is needed. Convert other formats losslessly first (e.g. `convert input.png -colorspace Gray frame.pgm` with ImageMagick). Pass the original frame, not a screenshot or a resized or recompressed copy. For OpenCV, PNG/JPEG loading or buffers from your own code, see [capture-pipelines.md](capture-pipelines.md).

Single images: `SC_PRESET_HIGH_EFFORT`, a **new frame sequence per image**, duplicate filter off, and no location or direction assumptions. Recommended input is 800×600 to 1920×1080 (FullHD or 4K for small codes), uncompressed, without pre-cropping, filtering or binarizing; if you restrict the area, keep it at least 320×160 px.

```c
/* scan_image.c - decode the barcodes in one greyscale PGM image with the Scandit Linux SDK (8.x).
 * Build: gcc -O2 -std=c99 -o scan_image scan_image.c -lscanditsdk
 * Run:   ./scan_image frame.pgm
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <Scandit/ScRecognitionContext.h>
#include <Scandit/ScBarcodeScanner.h>
#include <Scandit/ScBarcodeScannerSettings.h>
#include <Scandit/ScBarcodeScannerSession.h>
#include <Scandit/ScBarcodeArray.h>
#include <Scandit/ScBarcode.h>
#include <Scandit/ScImageDescription.h>
#include <Scandit/ScCommon.h>

#ifndef SCANDIT_SDK_LICENSE_KEY
#define SCANDIT_SDK_LICENSE_KEY "-- INSERT YOUR LICENSE KEY HERE --"
#endif
/* Files the SDK writes (license and device data). Use a directory that survives reboots. */
#define SCANDIT_WRITABLE_DATA_PATH "/tmp"

/* Minimal reader for binary PGM (P5, maxval <= 255, no comment lines). */
static uint8_t *read_pgm(const char *path, uint32_t *w, uint32_t *h) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    int maxval = 0;
    if (fscanf(f, "P5 %u %u %d", w, h, &maxval) != 3 || maxval > 255) { fclose(f); return NULL; }
    fgetc(f);                                   /* the single whitespace after the header */
    size_t n = (size_t)(*w) * (*h);
    uint8_t *px = malloc(n);
    if (px && fread(px, 1, n, f) != n) { free(px); px = NULL; }
    fclose(f);
    return px;
}

/* Logs a failed status (code and message) and frees it. Returns 1 on success. */
static int check(ScContextStatus st, const char *what) {
    int ok = (st.flag == SC_RECOGNITION_CONTEXT_STATUS_SUCCESS);
    if (!ok)
        fprintf(stderr, "%s failed: status %d: %s\n", what, (int)st.flag,
                sc_byte_array_get_string(st.message));
    sc_context_status_free(st);                 /* by value, not a pointer */
    return ok;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s image.pgm\n", argv[0]); return 2; }

    uint32_t w = 0, h = 0;
    uint8_t *pixels = read_pgm(argv[1], &w, &h);
    if (!pixels) { fprintf(stderr, "cannot read %s (binary PGM P5 expected)\n", argv[1]); return 2; }

    printf("Scandit SDK %s\n", sc_get_information_string(SC_INFORMATION_KEY_SDK_VERSION));

    /* 1. One context per process. NULL device name = no device name sent. */
    ScRecognitionContext *ctx =
            sc_recognition_context_new(SCANDIT_SDK_LICENSE_KEY, SCANDIT_WRITABLE_DATA_PATH, NULL);
    if (!ctx) { fprintf(stderr, "context creation failed\n"); free(pixels); return 1; }

    /* 2. Settings: all symbologies are disabled by default - enable only the ones you need. */
    ScBarcodeScannerSettings *settings = sc_barcode_scanner_settings_new_with_preset(SC_PRESET_HIGH_EFFORT);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_EAN13_UPCA, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_CODE128, SC_TRUE);
    sc_barcode_scanner_settings_set_code_duplicate_filter(settings, SC_DUPLICATE_FILTER_OFF);
    /* Codes can be anywhere and in any orientation in a still image. */
    sc_barcode_scanner_settings_set_code_location_constraint_1d(settings, SC_CODE_LOCATION_IGNORE);
    sc_barcode_scanner_settings_set_code_location_constraint_2d(settings, SC_CODE_LOCATION_IGNORE);
    sc_barcode_scanner_settings_set_code_direction_hint(settings, SC_CODE_DIRECTION_NONE);

    /* 3. One scanner per context; settings only take effect after apply_settings. */
    ScBarcodeScanner *scanner = sc_barcode_scanner_new(ctx);
    int ok = scanner != NULL && check(sc_barcode_scanner_apply_settings(scanner, settings), "apply_settings");
    if (ok) sc_barcode_scanner_wait_for_setup_completed(scanner);

    /* 4. Describe the buffer: width, height, layout and row bytes are required. */
    ScImageDescription *desc = sc_image_description_new();
    sc_image_description_set_width(desc, w);
    sc_image_description_set_height(desc, h);
    sc_image_description_set_layout(desc, SC_IMAGE_LAYOUT_GRAY_8U);
    sc_image_description_set_plane_row_bytes(desc, 0, w);   /* the real stride; larger if rows are padded */

    /* 5. One frame sequence per independent image. */
    if (ok) {
        sc_recognition_context_start_new_frame_sequence(ctx);
        ScProcessFrameResult r = sc_recognition_context_process_frame(ctx, desc, pixels);
        ok = (r.status.flag == SC_RECOGNITION_CONTEXT_STATUS_SUCCESS);
        if (!ok)
            fprintf(stderr, "process_frame failed: status %d: %s\n", (int)r.status.flag,
                    sc_byte_array_get_string(r.status.message));
        sc_process_frame_result_free(r);
        sc_recognition_context_end_frame_sequence(ctx);
    }

    /* 6. Read the results from the session (owned by the scanner). */
    if (ok) {
        ScBarcodeScannerSession *session = sc_barcode_scanner_get_session(scanner);
        ScBarcodeArray *codes = sc_barcode_scanner_session_get_newly_recognized_codes(session);
        uint32_t n = sc_barcode_array_get_size(codes);
        for (uint32_t i = 0; i < n; i++) {
            const ScBarcode *code = sc_barcode_array_get_item_at(codes, i);
            ScByteArray data = sc_barcode_get_data(code);
            ScQuadrilateral q = sc_barcode_get_location(code);
            printf("%s: %s (%u bytes) at (%d,%d) (%d,%d) (%d,%d) (%d,%d)\n",
                   sc_symbology_to_string(sc_barcode_get_symbology(code)),
                   sc_byte_array_get_string(data), sc_byte_array_get_size(data),
                   q.top_left.x, q.top_left.y, q.top_right.x, q.top_right.y,
                   q.bottom_right.x, q.bottom_right.y, q.bottom_left.x, q.bottom_left.y);
        }
        if (n == 0) {
            /* Nothing decoded: was a code found at all? (diagnostic only; expect false positives) */
            ScBarcodeArray *loc = sc_barcode_scanner_session_get_newly_localized_codes(session);
            printf("no code decoded; %u localized but not decoded\n", sc_barcode_array_get_size(loc));
            sc_barcode_array_release(loc);
        }
        sc_barcode_array_release(codes);
    }

    /* 7. Teardown: everything created from the context first, the context last. */
    sc_image_description_release(desc);
    sc_barcode_scanner_release(scanner);
    sc_barcode_scanner_settings_release(settings);
    sc_recognition_context_release(ctx);
    free(pixels);
    return ok ? 0 : 1;
}
```

Notes:
- Reuse the context and scanner for many images (creating them is expensive); start a new frame sequence per image.
- Barcode data can contain NUL bytes (binary 2D codes): use `sc_byte_array_get_data` + `sc_byte_array_get_size` instead of treating it as a C string.
- Items from `sc_barcode_array_get_item_at` are owned by the array: release only the array.
- If nothing is decoded, use [code-readability.md](code-readability.md) (pixels per module, blur, contrast, settings) before changing settings at random.

## Complete example: single image (Python)

```python
"""scan_image.py - decode the barcodes in one image with the Scandit Linux SDK Python bindings (8.x).

Setup: put the folder with scanditsdk.py on PYTHONPATH; pip install pillow numpy
Run:   python3 scan_image.py image.png
"""
import sys

import numpy as np
import scanditsdk as sc
from PIL import Image

LICENSE_KEY = "-- INSERT YOUR LICENSE KEY HERE --"
WRITABLE_DATA_PATH = "/tmp"  # use a directory that survives reboots


def main(path: str) -> int:
    # Greyscale, contiguous rows: row bytes = width.
    image = np.ascontiguousarray(np.asarray(Image.open(path).convert("L")))
    height, width = image.shape

    descr = sc.ImageDescription()
    descr.width = width
    descr.height = height
    descr.layout = sc.IMAGE_LAYOUT_GRAY_8U
    descr.set_plane_row_bytes(0, image.strides[0])

    context = sc.RecognitionContext(LICENSE_KEY, WRITABLE_DATA_PATH)

    # All symbologies are disabled by default: enable only the ones you scan.
    settings = sc.BarcodeScannerSettings(preset=sc.PRESET_HIGH_EFFORT)
    settings.enable_symbology(sc.SYMBOLOGY_EAN13_UPCA, True)
    settings.enable_symbology(sc.SYMBOLOGY_CODE128, True)
    settings.code_duplicate_filter = sc.DUPLICATE_FILTER_OFF
    # A still image: codes can be anywhere and in any orientation.
    settings.code_location_constraint_1d = sc.CODE_LOCATION_IGNORE
    settings.code_location_constraint_2d = sc.CODE_LOCATION_IGNORE
    settings.code_direction_hint = sc.CODE_DIRECTION_NONE

    scanner = sc.BarcodeScanner(context)  # one scanner per context
    status = scanner.apply_settings(settings)
    if not status.is_success():
        print(f"apply_settings failed: status {status.flag}: {status.message}")
        return 1
    scanner.wait_for_setup_completed()

    frame_seq = context.start_new_frame_sequence()  # one sequence per independent image
    result = frame_seq.process_frame(descr, image.ctypes.data)
    frame_seq.end()
    if not result.is_success():
        print(f"process_frame failed: status {result.flag}: {result.message}")
        return 1

    codes = scanner.session.newly_recognized_codes
    for code in codes:
        corners = [(p.x, p.y) for p in code.location.all_corners]
        print(f"{code.symbology_string}: {code.data} at {corners}")
    if len(codes) == 0:
        print(f"no code decoded; {len(scanner.session.newly_localized_codes)} localized but not decoded")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python3 scan_image.py image.png")
    sys.exit(main(sys.argv[1]))
```

- `process_frame` takes the address of the pixel buffer (`image.ctypes.data`); keep the array alive until the call returns.
- Set the stride with `descr.set_plane_row_bytes(0, …)`. There is no `memory_size` or `first_plane_row_bytes` property: assigning those silently does nothing.
- Python processes are licensed under the executable name `python3`.

## V4L2 camera

`ScCamera` is a thin V4L2 wrapper with no exposure or focus control. Start from the bundled samples in the SDK package: `samples/CommandLineBarcodeScannerCameraSample.c` (C) and `samples/CommandLineBarcodeScannerCameraSample.py` (Python), and apply the same settings as above (only the symbologies you scan, `SC_PRESET_NONE` for video or `SC_PRESET_SINGLE_CODE_HAND_HELD` for a hand-held device, a duplicate filter in ms). Run them first with `./CommandLineBarcodeScannerCameraSample /dev/video0 640 480` to confirm the camera works before integrating.

Camera essentials (API details in api-reference.md, Camera section):
- Drivers report resolutions either as a **discrete** list or a **stepwise** range. Query the one `sc_camera_get_resolution_mode` reports; the other query returns 0 and looks like "the camera supports nothing".
- Some drivers report an unrealistic stepwise maximum (e.g. 16376×16376). Requesting it fails with `Could not request buffers: Cannot allocate memory`. Request a real sensor mode (`v4l2-ctl --list-formats-ext -d /dev/video0`) and check the return value of `sc_camera_request_resolution`.
- Prefer a greyscale or YUV layout (`sc_camera_request_image_layout`, before `start_stream`, never while streaming).
- `sc_camera_get_frame` fills the `ScImageDescription` for exactly that frame: pass it straight to `process_frame`.
- Call `sc_camera_enqueue_frame_data` for every frame you took, or the stream stalls after as many frames as there are buffers. Python: `with camera.frame as frame:` returns the buffer when the block ends.
- One frame sequence for the whole stream.
- Frames from OpenCV, GStreamer, libcamera or a vendor SDK instead of `ScCamera`: [capture-pipelines.md](capture-pipelines.md).

## Reading results

| Need | C | Python |
| --- | --- | --- |
| Codes decoded in the last frame | `sc_barcode_scanner_session_get_newly_recognized_codes` | `session.newly_recognized_codes` |
| All codes since the last clear | `sc_barcode_scanner_session_get_all_recognized_codes`, `sc_barcode_scanner_session_clear` | `session.all_recognized_codes`, `session.clear()` |
| Codes found but not decoded (diagnostics: location only, expect false positives) | `sc_barcode_scanner_session_get_newly_localized_codes` | `session.newly_localized_codes` |
| Data | `sc_barcode_get_data` → `ScByteArray` (`sc_byte_array_get_string`, `_get_data`, `_get_size`); `sc_barcode_get_data_encoding` | `code.data` (decoded text), `code.raw_data`, `code.data_encoding` |
| Symbology | `sc_barcode_get_symbology`, `sc_symbology_to_string` | `code.symbology`, `code.symbology_string` |
| Position (image pixels, origin top-left) | `sc_barcode_get_location` → `ScQuadrilateral` | `code.location` (`top_left` … , `all_corners`) |
| Module count (for pixels per module) | `sc_barcode_get_module_counts` | not in the 8.6 bindings |
| GS1 / composite / split codes | `sc_barcode_is_gs1_data_carrier`, `sc_barcode_get_composite_flag`, `sc_barcode_get_file_id` / `_segment_index` / `_segment_count` | `code.is_gs1_data_carrier`, `code.composite_flag`, `code.file_id`, `code.segment_index`, `code.segment_count` |
| Light-on-dark | `sc_barcode_is_color_inverted` | not in the 8.6 bindings |

Every array a C session getter returns transfers ownership: release it with `sc_barcode_array_release`. A barcode's data is only valid while the array holding it is alive: copy what you keep.

## Settings recipes

| Situation | Settings |
| --- | --- |
| Single images, server or batch processing | `SC_PRESET_HIGH_EFFORT`, duplicate filter `SC_DUPLICATE_FILTER_OFF`, location constraints `SC_CODE_LOCATION_IGNORE`, direction `SC_CODE_DIRECTION_NONE`, new frame sequence per image |
| Fixed camera, codes pass by (conveyor) | `SC_PRESET_NONE`, duplicate filter in ms (e.g. 1000), one frame sequence for the stream; optionally a 1D "laser line" area (advanced.md) |
| Hand-held device, one code at a time | `SC_PRESET_SINGLE_CODE_HAND_HELD` (smart scan intention: at most one code per frame, no accidental background scans) |
| Several codes in one frame | `sc_barcode_scanner_settings_set_multi_scan_enabled(settings, SC_TRUE)` + `sc_barcode_scanner_settings_set_max_num_locations_to_process_per_frame(settings, N)` (N > 0; default 5), and the "tracking" license feature. Python: `settings.multi_scan_enabled = True`, `settings.max_num_locations_to_process_per_frame = N` |
| Fixed-focus camera | Direction hint `SC_CODE_DIRECTION_NONE` |
| Light-on-dark codes | per symbology `sc_symbology_settings_set_color_inverted_enabled` (Python: `settings.symbologies[sym].color_inverted_enabled = True`); on by default only for QR and MicroQR |

By default the scanner searches 1D codes in a centered horizontal strip (the "code location area 1D", constraint HINT) and assumes left-to-right 1D codes. That suits a hand-held scanner aimed at a code; for images and fixed cameras with codes anywhere, set the constraints to `SC_CODE_LOCATION_IGNORE` and the direction hint to NONE as in the examples. More (JSON settings, add-ons, composites, areas, symbol counts, extensions): [advanced.md](advanced.md).

## Threads and processes

- The API is **not thread-safe**, although the SDK uses several threads itself. Make every call for a context and its scanner from **one thread** (`sc_object_tracker_release` is the documented exception).
- **One scanner per context** and one context per process.
- For more throughput, run several worker **processes**, each with its own context and scanner.
- Release everything created from a context (scanner, settings, parser, tracker, arrays) before the last release of the context.

## Production checklist

- [ ] Linux key with the right executable name (or none) and the features you use; non-trial keys kept out of version control.
- [ ] Only the symbologies you need; symbol counts cover your code lengths; inversion enabled for light-on-dark codes.
- [ ] Every `ScContextStatus` / `ScProcessFrameResult` checked (log code **and** message) and freed.
- [ ] SDK version logged at startup (`sc_get_information_string(SC_INFORMATION_KEY_SDK_VERSION)`).
- [ ] Effective settings logged once (`sc_barcode_scanner_settings_as_json`, free with `sc_free`).
- [ ] Greyscale or YUV input with the real row stride; original, not re-encoded, frames.
- [ ] Enough pixels per module for the smallest code at the largest distance (code-readability.md).
- [ ] Single images: HIGH_EFFORT, new frame sequence per image, duplicate filter off. Video: one sequence per continuous stream.
- [ ] All SDK calls for an instance on one thread; teardown order respected; writable data path persistent.
- [ ] Release notes checked before upgrading (some versions tighten validation on purpose; see migration.md).

## Links

| Topic | URL |
| --- | --- |
| Linux overview | https://docs.scandit.com/sdks/linux/overview/ |
| Installation | https://docs.scandit.com/sdks/linux/add-sdk/ |
| Samples | https://docs.scandit.com/sdks/linux/samples/ |
| C API reference (class list) | https://docs.scandit.com/stable/c_api/annotated.html |
| Release notes | https://docs.scandit.com/sdks/linux/release-notes/ |
| Free trial | https://www.scandit.com/trial/ |
| Support | support@scandit.com |
