# Linux SDK: API and documentation reference

*Exact API names, status codes, settings and version history for the Linux SDK, based on the [Linux guides](https://docs.scandit.com/sdks/linux/overview/) and the [C API reference](https://docs.scandit.com/stable/c_api/annotated.html). Use it to answer "how do I…" and "what does this error mean" questions.*

*Names and defaults are for SDK **8.6**. For other versions, check against the headers of that version (`/usr/include/Scandit/`).*

Always check which SDK version is in use: many names changed in **8.0** (see §11).

**Contents:** 1 What the C API is · 2 Installation and samples · 3 Lifecycle and memory · 4 Recognition context and status codes · 5 Scanner settings (presets, setters, JSON, properties) · 6 Symbology settings (inversion, checksums, symbol counts, extensions, add-on/composite/GS1, structured append) · 7 Session and results (`module_counts`) · 8 Images · 9 Camera (discrete vs stepwise modes, framerates, layouts, streaming loop) · 10 Tracker, parser, generator, version · 11 Migrating to 8.0 · 12 Release notes
---

## 1. What the C API is

- **Low-level C API**: no UI, no stream management, no advanced camera control. You integrate it into your own application and capture stack.
- **Platforms**: Debian packages for amd64 and arm64. arm64 covers e.g. Jetson and Raspberry Pi 4/5.
- **Python** is covered by the bindings (`scanditsdk.py`), which wrap this C API: concepts, call order, settings and status codes are the same, only the names are Pythonic. Check exact Python names in `scanditsdk.py` and the bundled Python samples. When a problem only shows up in Python, reproduce it in C to separate bindings from input.
- **Coordinates** are image coordinates: origin top-left, y pointing down. Relative areas run from (0,0) top-left to (1,1) bottom-right.

## 2. Installation and samples

```bash
sudo dpkg -i libscandit-barcodescanner-X.Y.Z-amd64.deb   # or -arm64.deb
```

- Python: add the folder with `scanditsdk.py` to `PYTHONPATH`.
- **Raspberry Pi 3/4/5 camera via V4L2:** install the package `v4l-utils`, add `bcm2835-v4l2` to `/etc/modules-load.d/modules.conf`, and reboot.
- Sample build dependencies (packages): `libv4l-dev`, `libsdl2-dev`, `libsdl2-image-dev`, `python3-sdl2`, `libpng-dev`.
- **The license key must be inserted into the sample sources** before building.
- Samples in the package:

| Sample | Run |
| --- | --- |
| Image file | `./CommandLineBarcodeScannerImageProcessingSample ean13-code.png` |
| V4L2 camera | `./CommandLineBarcodeScannerCameraSample /dev/video0 640 480` |
| Multi-code tracking camera | `./CommandLineMatrixScanCameraSample /dev/video0 1920 1080` |
| Barcode generator | `./CommandLineBarcodeGeneratorSample` |
| Python image file | `python3 CommandLineBarcodeScannerImageProcessingSample.py <image>` |
| GStreamer | see `samples/gstreamer/README.md` |
| OpenCV (C++ and Python) | `samples/opencv_py_demo`; Python needs `../public_api/python/scanditsdk.py` and `LD_LIBRARY_PATH` pointing to `libscanditsdk.so` |

## 3. Object lifecycle and memory

- Release everything you create with `*_new`, everything you `*_retain`, and every return value that **transfers ownership** (e.g. `sc_barcode_scanner_session_get_newly_recognized_codes` → `sc_barcode_array_release`).
- **Release every object created from a context before the last release of that context.**
- Statuses: `ScContextStatus {flag, message}` → `sc_context_status_free(status)`; `ScProcessFrameResult {status, frame_id}` → `sc_process_frame_result_free(result)` (both 8.0; both take the struct **by value**, not a pointer; `message` is an `ScByteArray`, print it with `sc_byte_array_get_string`). Strings from `*_as_json` → `sc_free`. `ScError` → `sc_error_free`.
- `sc_barcode_get_data` is valid only as long as the barcode. Binary data may contain NUL bytes, so use `sc_byte_array_get_size` rather than `strlen`.

**Minimal lifecycle (8.x):**

```c
ScRecognitionContext *ctx = sc_recognition_context_new("-- INSERT YOUR LICENSE KEY HERE --", "/var/lib/myapp/scandit", NULL);
ScBarcodeScannerSettings *settings = sc_barcode_scanner_settings_new_with_preset(SC_PRESET_HIGH_EFFORT);
sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_CODE128, SC_TRUE);
ScBarcodeScanner *scanner = sc_barcode_scanner_new(ctx);          // NULL if the context already has a scanner
ScContextStatus st = sc_barcode_scanner_apply_settings(scanner, settings);
/* check st.flag (1 = success), log sc_byte_array_get_string(st.message) */ sc_context_status_free(st);

sc_recognition_context_start_new_frame_sequence(ctx);
ScProcessFrameResult r = sc_recognition_context_process_frame(ctx, image_description, pixels);
/* check r.status.flag, then read the session */ sc_process_frame_result_free(r);
ScBarcodeArray *codes = sc_barcode_scanner_session_get_newly_recognized_codes(sc_barcode_scanner_get_session(scanner));
/* ... */ sc_barcode_array_release(codes);
sc_recognition_context_end_frame_sequence(ctx);

sc_barcode_scanner_release(scanner);
sc_barcode_scanner_settings_release(settings);
sc_recognition_context_release(ctx);   // last
```

Check exact signatures against the headers of the SDK version in use. A complete, buildable walkthrough is in the integration guide.

## 4. Recognition context

- `sc_recognition_context_new(license_key, writable_data_path, device_name)`. `device_name` is used for analytics; `NULL` disables it.
- **Use one context per application** (per process).- **One scanner per context:** `sc_barcode_scanner_new(ctx)` returns `NULL` if the context already has one (8.0).
- Calling `process_frame` without `start_new_frame_sequence` returns status 3.
- A wrong or missing license key does **not** make `sc_recognition_context_new` fail: the license status is reported by `sc_barcode_scanner_apply_settings` and `process_frame`.
- `sc_recognition_context_set_camera_properties` exists for camera metadata.

### Status / error codes (`ScContextStatusFlag`)

| Code | Name | What to do |
| --- | --- | --- |
| 0 | UNKNOWN | — |
| 1 | SUCCESS | — |
| 2 | INTERNAL_ERROR | Collect logs, version, repro |
| 3 | FRAME_SEQUENCE_NOT_STARTED | Call `start_new_frame_sequence` first |
| 4 | UNSUPPORTED_IMAGE_DATA | Check the layout enum (§8) |
| 5 | INCONSISTENT_IMAGE_DATA | Buffer smaller than width × height × layout; check row bytes and plane offsets |
| 6 | NO_NETWORK_CONNECTION | Key needs network (e.g. test keys); connect or get the right key |
| 11 | LICENSE_VALIDATION_FAILED_403 | Check the app key and the device activations |
| 12 | LICENSE_KEY_MISSING | Empty key string |
| 13 | LICENSE_KEY_EXPIRED | New key |
| 14 | INVALID_PLATFORM | Key not issued for Linux |
| 15 | INVALID_APP_ID | The key's app ID doesn't match the **executable name** (first element of the process command line; `python3` for a Python script, not the script name). Create a key without an executable name or with the right one |
| 16 | INVALID_DEVICE | Key bound to other devices |
| 17 | INVALID_SDK_VERSION | Key doesn't cover this SDK version |
| 18 | LICENSE_KEY_INVALID | Malformed or truncated key (copy/paste, quotes, line breaks) |
| 19 | DEVICE_ACTIVATION_FAILED | Connect to the network and restart |
| 20 | TIME_EXCEEDED | Time-limited key used up |
| 21 | SCANS_EXCEEDED | Scan-limited key used up |
| 22 | REGISTRATION_MANDATORY_BUT_NOT_REGISTERED | Device must register (network) |
| 23 | INVALID_EXTERNAL_ID | — |
| 24 | UNLICENSED_SYMBOLOGY_ENABLED | Disable the symbology or add it to the license |
| 26 | INVALID_LICENSE_KEY_VERSION | Key format too new/old for this SDK |
| 27 | UNLICENSED_SYMBOLOGY_EXTENSION_ENABLED | Disable the extension or license it |
| 28 | MISSING_RESOURCE_ERROR | Models missing/broken in the resources folder; also OCR fallback without its resources (8.1+) |
| 29 | UNLICENSED_TEXT_RECOGNIZER | OCR fallback / text feature not on the license |
| 30 | OCR_ERROR | — |
| 255–512 | UNLICENSED_FEATURE range | Read `status.message`; e.g. multi-scan/tracking without the "tracking" feature |

Always print `status.message` together with the code; it names the missing feature.

## 5. Scanner settings

### Presets (`sc_barcode_scanner_settings_new_with_preset`)

| Preset | Value | Use | Recommended input |
| --- | --- | --- | --- |
| `SC_PRESET_NONE` | 0x00 | Default balance of speed and accuracy on frame sequences, single and multi-scan | FullHD |
| `SC_PRESET_HIGH_EFFORT` | 0x02 (7.1+) | Best accuracy, more time per frame; **recommended for single images and server/cloud processing** | FullHD or 4K |
| `SC_PRESET_SINGLE_CODE_HAND_HELD` | 0x08 (7.1+) | Hand-held devices scanning one code in a static scene. Smart scan intention prevents background scans and scans during fast movement. Returns **at most one code (or group) per frame**. Fixed in **8.3.0** (smart scan intention setup) | FullHD or 4K |

Presets can't be combined; if several bits are set, the lowest value wins. There is **no single-frame-mode preset in 8.x**; for single images use `SC_PRESET_HIGH_EFFORT`.
### Main setters

- Symbologies: `sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_X, SC_TRUE)` or via `sc_barcode_scanner_settings_get_symbology_settings` (§6). **All symbologies are disabled by default.**
- Multi-scan (8.0): `sc_barcode_scanner_settings_set_multi_scan_enabled` + `sc_barcode_scanner_settings_set_max_num_locations_to_process_per_frame` (cannot be 0; default 5). **Multi-scan needs the "tracking" license feature.**
- Search area (relative, applies to 1D and 2D): `sc_barcode_scanner_settings_set_search_area`.
- Code location areas per 1D/2D: `set_code_location_area_1d/2d` + `set_code_location_constraint_1d/2d` with `SC_CODE_LOCATION_RESTRICT` (1, decode only there; localization off), `HINT` (2, default) or `IGNORE` (3).
  - Default 1D area: a centered horizontal strip (x 0, y 0.375, width 1, height 0.25), HINT, direction LEFT_TO_RIGHT. Default 2D area: the whole image, HINT.
  - "Laser line" setup: 1D area strip + RESTRICT + matching direction hint; set a larger 2D area if 2D codes are also needed.
- Circle of interest (5.25): `set_circle_of_interest(settings, center, radius)`. Radius ≥ 0 → only results touching the circle, closest to the center first. `SC_CIRCLE_RADIUS_INFINITE` (-1) or negative (6.24+) → hint only, results from the whole image.
- Code direction hint: NONE, LEFT_TO_RIGHT (default), RIGHT_TO_LEFT, TOP_TO_BOTTOM, BOTTOM_TO_TOP, VERTICAL, HORIZONTAL. It is in **image** coordinates: a portrait-mounted camera needs BOTTOM_TO_TOP for horizontal codes. For devices without autofocus use NONE.
- Duplicate filter: `set_code_duplicate_filter` with `SC_DUPLICATE_FILTER_OFF` (0, default), `SC_DUPLICATE_FILTER_INFINITE` (-1, until `sc_barcode_scanner_session_clear`), or a value in ms. The code caching duration caps it. **Turn it off for single-image tests.** Session settings don't affect the object tracker.
- Settings take effect only after **`sc_barcode_scanner_apply_settings`**, which returns a status to check and free.
- Dump the effective configuration with `sc_barcode_scanner_settings_as_json` (free with `sc_free`). **Share this JSON** (not a description of the code) when you ask for help.

### JSON settings (`sc_barcode_scanner_settings_new_from_json(json, &error)`)

```json
{
  "symbologies": {
    "code128": { "enabled": true, "activeSymbolCounts": [10, 11, 12], "extensions": ["strip_leading_fnc1"] },
    "data-matrix": { "enabled": true, "colorInvertedEnabled": true }
  },
  "searchArea": { "x": 0.0, "y": 0.25, "width": 1.0, "height": 0.5 },
  "codeLocation1d": { "area": { "x": 0, "y": 0.4, "width": 1, "height": 0.2 }, "constraint": "hint" },
  "codeDirectionHint": "left-to-right",
  "codeDuplicateFilter": 0
}
```

- `{}` = everything disabled. **Unknown keys are silently ignored**, so a typo is a silent no-op: e.g. `maxNumberOfCodesPerFrame` (removed in 8.0) leaves multi-scan off. Use `multiScanEnabled` and `maxNumLocationsToProcessPerFrame`. Compare against `as_json` output.
- A symbology's `extensions` array **replaces** its default extensions (Code 128 and Data Matrix lose `strip_leading_fnc1` unless listed). `sc_symbology_settings_set_extension_enabled` adds to the defaults instead.
- Code location `constraint` accepts `"restrict"`, `"hint"` and `"ignore"`. The top level must be an object (`settings must be a JSON object`).
- Names are case-insensitive. Symbology keys: `aruco`, `australian-post-4state`, `aztec`, `codabar`, `code11`, `code128`, `code32`, `code39`, `code93`, `code25`, `databar`, `databar-expanded`, `databar-limited`, `data-matrix`, `dotcode`, `ean13upca`, `ean8`, `five-digit-add-on`, `two-digit-add-on`, `french-post`, `iata2of5`, `itf`, `kix`, `lapa4sc`, `matrix2of5`, `maxicode`, `micropdf417`, `microqr`, `msi-plessey`, `pdf417`, `qr`, `royal-mail-4state` (`rm4scc` before 8.0; still accepted as input in 8.6), `upce`, `upu-4state`, `usps-intelligent-mail`.
- Per symbology: `enabled`, `colorInvertedEnabled`, `activeSymbolCounts`, `extensions`, `checksums`, `ocrFallbackRegex`. Other keys: `multiScanEnabled`, `maxNumLocationsToProcessPerFrame`, `codeDuplicateFilter`, `searchArea`, `codeLocation1d`, `codeLocation2d`, `codeDirectionHint` (`left-to-right`, `right-to-left`, `bottom-to-top`, `top-to-bottom`, `none`, `vertical`, `horizontal`), `arucoDictionaryPreset`.
- Write float settings with a decimal point (`1.0`, not `1`).
## 6. Symbology settings

- `sc_symbology_settings_set_enabled` covers **dark-on-light only**. For light-on-dark also call `sc_symbology_settings_set_color_inverted_enabled`. Enable both if both polarities occur.
- Color inversion is off by default except for **QR and MicroQR**. Supported: EAN/UPC and add-ons, Code 128, Code 39, Code 93, Aztec, Data Matrix, DotCode, QR, MicroQR, ArUco. **Not supported:** PDF417, MicroPDF417, MaxiCode, ITF, Codabar, DataBar, MSI, Code 11, Code 25, IATA 2of5, Matrix 2of5, Code 32, postal codes.
- Checksums (`sc_symbology_settings_set_checksums`, bitfield; a code passes if **any** enabled checksum matches): NONE 0, MOD_10 0x01, MOD_11 0x02, MOD_47 0x04, MOD_103 0x10, MOD_1010 0x20, MOD_1110 0x40, MOD_43 0x100, MOD_16 0x200. Optional checksum digits are always included in the returned data.
- Code 32 and Code 39 can't be told apart; enable only the one you use.

### Active symbol counts

`sc_symbology_settings_set_active_symbol_counts(ss, const uint16_t *counts, uint16_t num_counts)`, where `num_counts` is the **number of elements** (not bytes). Ignored for EAN/UPC and 2D; out-of-range values are silently ignored. Codes outside the active range are not returned: a common reason for "short/long codes don't scan".

Defaults are those of SDK 8.6 (as reported by `sc_barcode_scanner_settings_as_json`); allowed ranges are from the documentation.

| Symbology | Default | Allowed | How to count |
| --- | --- | --- | --- |
| EAN-13 / UPC-A | 12 | 12 | fixed |
| EAN-8 | 8 | 8 | fixed |
| UPC-E | 6 | 6 | fixed |
| Code 128 | 4–40 (6–40 before 8.5) | 4–50 | characters (code sets A/B) or digit pairs (set C) + start + stop + check. "ABC123" in A = 9; "123456" in C = 6. **8.5:** minimum lowered from 6 to 4 (stricter for short codes) |
| Code 39 | 6–40 | 3–50 | characters + 2 (start/stop). 17 characters = 19. Default therefore covers 4–38 characters |
| Code 93 | 6–40 | 5–60 | characters + 2 checks + 2 guards. "ABCDE12345" = 14 |
| ITF | 6–40 | 4–50 | number of digits (always even) |
| Codabar | 7–20 | 3–34 | digits + 2 (start/stop) |
| Code 11 | 7–20 | 5–34 | digits + 1 check (< 10 digits) or + 2 checks; mod11 checksum on by default |
| MSI Plessey | 6–32 | 3–32 | digits (mod10 checksum by default) |
| Code 25 / IATA 2of5 / Matrix 2of5 | 7–20 | 3–32 | digits |
| Code 32 | 8 | 8 | fixed |
| DataBar 14 / Expanded / Limited | 2 / none set / 1 | same | finder patterns |
| RM4SCC / KIX | 7–24 | 4–50 / — | characters |
| USPS IM / UPU / AusPost / LAPA / French Post | 65 / 57–75 / 37, 52, 67 / 16 / 46–84 | same | — |

### Extensions (`sc_symbology_settings_set_extension_enabled(ss, "name", SC_TRUE)`)

| Extension | Symbologies | Effect |
| --- | --- | --- |
| `full_ascii` | Code 39 (always on for Code 93) | Full ASCII interpretation |
| `relaxed_sharp_quiet_zone_check` | EAN-13, EAN-8, Code 39, DataBar Limited | Accepts tighter quiet zones; may add false positives |
| `return_as_upca`, `remove_leading_upca_zero` | EAN-13/UPC-A, UPC-E | Output format of leading zeros |
| `strip_leading_fnc1` | Code 128; Data Matrix (on by default) | Removes the leading FNC1 |
| `direct_part_marking_mode` | Data Matrix | DPM (dot-peen, laser) codes; slower, so restrict the area |
| `strict` | several 1D (e.g. EAN/UPC) | Fewer false positives, lower scan rate |
| `relaxed` | Code 39 (8.5+) | Restores the pre-8.5 looser filter; only with external validation |
| `no_checksum_dependent_validation` | ITF (8.4+) | Turns off checksum-dependent scoring |
| `remove_delimiter_data` | Codabar | Strips the A/B/C/D start/stop characters |
| `fluorescent_orange_ink` | UPU, French Post, RM4SCC | Orange-ink postal codes |
| `force_table_c`, `force_table_n`, `decode_bar_states` | Australia Post | Customer-field decoding |
| `swiss_post_decoding` | UPU | Swiss Post variant |
| `ocr_fallback` | EAN-13, Code 128, Code 39, Codabar | Reads the human-readable text when the bars fail (see below) |

- The MaxiCode `mirrored` extension was removed in **8.6**: mirrored MaxiCode is now read by default.
- **OCR fallback** needs smart scan intention (on Linux: `SC_PRESET_SINGLE_CODE_HAND_HELD`), the text-recognition resources and the license feature (errors 28 / 29). It triggers after about 1 s of a stationary code. Set a validation regex with `sc_symbology_settings_set_ocr_fallback_regex` (7.4+, must match the whole text); without one, Code 128/39 OCR results are alphanumeric only.

### Add-on and composite codes

- **Add-ons (EAN/UPC + 2/5-digit):** enable the main symbology and `two-digit-add-on` / `five-digit-add-on`, allow at least 2 codes/locations per frame, and combine main + add-on from the session. An add-on alone is never returned.
- **Composite codes (GS1 1D + 2D part):** enable the 1D symbology plus PDF417/MicroPDF417, allow 2 codes per frame, and concatenate. `sc_barcode_get_composite_flag`: NONE 0, UNKNOWN 1 (EAN/UPC), LINKED 2 (DataBar/GS1-128), GS1_A 3, GS1_B 4 (MicroPDF417), GS1_C 5 (PDF417).- **GS1:** check `sc_barcode_is_gs1_data_carrier`. Read the raw data and use the parser (§10). Typical encoding mistakes: a leading GS in Data Matrix byte mode, or human-readable "(01)…" text in a plain Data Matrix.- **Structured append** (split codes; e.g. DotCode since 8.6): `sc_barcode_get_file_id`, `get_segment_index`, `get_segment_count` (7.6; Python fields 8.6). The app has to reassemble the segments.

## 7. Session and results

- `sc_barcode_scanner_get_session(scanner)` (owned by the scanner).
- `get_newly_recognized_codes`, `get_all_recognized_codes` (grows until `sc_barcode_scanner_session_clear`), **`get_newly_localized_codes`** (codes found but not decoded: symbology UNKNOWN, no data; the key diagnostic for "there is a code but it doesn't read"), `get_last_processed_frame_id`.
- **ScBarcode:** `get_data`, `get_data_encoding` (free with `sc_encoding_array_free`), `get_symbology`, `is_recognized`, `get_location` (`ScQuadrilateral`, pixel corners), `get_symbol_count`, `is_color_inverted`, `get_composite_flag`, `get_frame_id`, segment fields.
- **`sc_barcode_get_module_counts` (7.5)** returns an `ScPoint`:
  - 1D: x = modules along the code, y = -1
  - 2D: x, y = modules per side
  - stacked (PDF417, DataBar stacked): x = modules per row, y = rows
  - Python: not in the 8.6 bindings.  - **PPM of a decoded code = edge length of `get_location` in px ÷ module count.** Use it to measure the PPM margin of codes that do scan (code-readability §2.2).

## 8. Images

- `ScImageDescription` (`sc_image_description_new`, all zero + `SC_IMAGE_LAYOUT_UNKNOWN`): set width, height and layout (always required) and the row bytes per plane (`set_plane_row_bytes`). Bi-planar layouts (NV12, NV21) also need **both** plane offsets (`set_plane_offset`; plane API 7.0). `get_planes_count` tells you how many planes a layout has. Padded rows (row bytes > width × bytes per pixel) are common with camera buffers; set the real stride.
- Layouts: GRAY_8U 0x1, RGB_8U 0x2, RGBA_8U 0x4, YPCBCR_8U 0x8 (NV12), YPCRCB_8U 0x10 (NV21), YUYV_8U 0x20, UYVY_8U 0x40, I420_8U 0x80, ARGB_8U 0x100, BGR_8U 0x200, NV16_8U 0x800.- **Prefer GRAY_8U or a YUV layout**; RGB is converted to grey by the SDK.
- Docs' recommendations for **single images**: 800×600 to 1920×1080 (1280×720 recommended for speed), FullHD or 4K with HIGH_EFFORT for small codes; a restricted area of at least **320×160 px**; no pre-cropping, filtering, blurring or binarizing; uncompressed input (JPEG block artifacts hurt); `start_new_frame_sequence` / `process_frame` / `end_frame_sequence` per image; duplicate filter off; HIGH_EFFORT. A single image is never as robust as a video stream.
- **Video:** FullHD (4K for range). Restart the frame sequence only when the stream is discontinuous. The SDK does no exposure/focus control for you.

## 9. Camera (`ScCamera`, V4L2 only)

The camera API is a thin V4L2 wrapper (on non-V4L2 platforms it returns a dummy object). Most camera problems come from **what the driver reports** and **which resolution/layout gets requested**, so read the capabilities first.
**Create and release:** `sc_camera_new()`, `sc_camera_new_with_buffer_count(n)`, `sc_camera_new_from_path("/dev/video0", 4)`. They return NULL on error. Too many buffers can make the allocation fail; 4 is the documented example. `sc_camera_release` / `retain`.

**Capabilities: two modes (`ScCameraMode`)**, separately for resolution and framerate:

| Mode | Meaning | Query with |
| --- | --- | --- |
| `SC_CAMERA_MODE_DISCRETE` (1) | Fixed list of resolutions / framerates | `sc_camera_query_supported_resolutions(cam, ScSize *array, len)` → count written (0 if not discrete); `sc_camera_query_supported_framerates(cam, resolution, ScFramerate *array, len)` |
| `SC_CAMERA_MODE_STEPWISE` (2) | Any value from min to max in steps | `sc_camera_query_supported_resolutions_stepwise(cam, &ScStepwiseResolution)` → SC_FALSE if not stepwise; `sc_camera_query_supported_framerates_stepwise(cam, resolution, &ScStepwiseFramerate)` |
| `SC_CAMERA_MODE_UNKNOWN` (0) | Driver didn't say | — |

- Get the mode with `sc_camera_get_resolution_mode` / `sc_camera_get_framerate_mode`, then call the matching query. Calling the wrong one returns 0 / SC_FALSE, which looks like "the camera supports nothing".
- `ScStepwiseResolution { min_width, max_width, step_width, min_height, max_height, step_height }` (uint32).
- `ScFramerate { numerator, denominator }` is a fraction. Don't interpret it by hand: use `sc_framerate_get_fps(&f)` and `sc_framerate_get_frame_interval(&f)` (seconds). `ScStepwiseFramerate { min, max, step }` holds three `ScFramerate`.
- Framerates are queried **per resolution**: a camera can do 30 fps at 1080p but only 10 fps at full sensor resolution.
- **Why stepwise matters:** some drivers (e.g. the Raspberry Pi Camera Module 3) report a stepwise range with an unrealistic maximum such as 16376×16376. Requesting the maximum then fails with `Could not request buffers: Cannot allocate memory`. Request a real sensor mode inside the range and aligned to the step instead.

**Request settings** (all return SC_TRUE/SC_FALSE: check them):
- `sc_camera_request_resolution(cam, (ScSize){w, h})`, then confirm with `sc_camera_get_resolution`.
- `sc_camera_request_framerate(cam, ScFramerate)` (5.15).
- `sc_camera_query_supported_image_layouts(cam, ScImageLayout *array, len)` (7.2.1) → count; `sc_camera_request_image_layout(cam, layout)` (7.2.1) forces a buffer re-initialization, so **don't call it while streaming**; confirm with `sc_camera_get_image_layout`. Prefer GRAY_8U or a YUV layout.
- Focus: `sc_camera_set_focus_mode(cam, ScCameraFocusMode)` and `sc_camera_set_manual_auto_focus_distance(cam, int32 distance)` (only with autofocus off; the value is device-specific). These camera calls still exist in 8.x; only the *scanner-settings* focus API was removed in 8.0 (§11). Many embedded cameras ignore them.

**Streaming loop:** `sc_camera_start_stream` → per frame `sc_camera_get_frame(cam, desc)` (fills `desc` for exactly that frame; NULL if none) → `sc_recognition_context_process_frame(ctx, desc, data)` → `sc_camera_enqueue_frame_data(cam, data)` → `sc_camera_stop_stream`. The complete loop is in the bundled `samples/CommandLineBarcodeScannerCameraSample.c`.

- `get_frame` fills the `ScImageDescription` (width, height, layout, planes, row bytes) for exactly that frame. Pass it straight to `process_frame` rather than building your own.
- **Forgetting `sc_camera_enqueue_frame_data` drains the buffer pool** and the stream stalls after a few frames (as many as the buffer count).
- Fixes: **8.5** falls back to single-plane when a multi-planar request fails. **8.6** `get_frame` no longer hangs when the camera disconnects. **7.2.1** ignored `request_image_layout` (fixed in 7.3.1).

## 10. Object tracker, parser, generator, info

- **Object tracker** (7.0; needs "tracking"): `sc_object_tracker_new(ctx)`, `set_enabled`, `apply_scanner_settings`, `get_session` → `sc_object_tracker_session_get_tracked_objects` (release the map with `sc_tracked_object_map_release`; iterate with `sc_tracked_object_map_get_size` / `_get_ids` / `_get_item_at`). Tracked objects: id (can be reused), location, `sc_tracked_object_get_barcode` (release with `sc_barcode_release`). `sc_object_tracker_release` is the one call that may happen from any thread. Guide: matrixscan.md.
- **Parser:** `sc_parser_new_with_context(ctx, type, &status)` returns NULL if the license lacks the parser. Types: GS1_AI 1, HIBC 2, DLID 3 (AAMVA driver's license), MRTD 4, SWISSQR 5, VIN 6, US_USID 7. `sc_parser_parse_string(parser, data, len, &result)`, `sc_parser_set_options`; fields via `sc_parser_result_*` / `sc_field_*`; every returned `ScByteArray` freed with `sc_byte_array_free`; `sc_parser_result_free`, `sc_parser_free` before the context. Guide: parser.md.
- **Barcode generator** (5.8; license feature): `sc_barcode_generator_new(ctx, symbology, &err)` / `sc_barcode_generator_new_with_options(ctx, symbology, json, &err)`, `sc_barcode_generator_set_options`, `sc_barcode_generator_generate(gen, data, len, encoding, &err)` (`ScEncodingArray` by value) → RGBA `ScImageBuffer` (`sc_image_buffer_free`); free the generator with `sc_barcode_generator_free`. Guide: barcode-generator.md. Symbologies: Code 39, Code 128, EAN-13, UPC-A, ITF, QR, Data Matrix, PDF417 (8.2). Options: foreground/background `[r,g,b,a]`; QR `errorCorrectionLevel` L/M/Q/H (default M), `versionNumber` 1–40; PDF417 `errorCorrectionLevel` 0–8, `compact`, `compaction`, `dimensions`. Useful to create clean reference codes for a repro or a PPM test series.
- **Version string:** `sc_get_information_string(SC_INFORMATION_KEY_SDK_VERSION)` (also `SDK_BUILD`, `SOFTWARE_LICENSES`). Log it at startup and include it in support requests.
- `sc_symbology_to_string` / `sc_symbology_from_string`; `SC_ALL_SYMBOLOGIES`.
### Python bindings coverage (8.6 `scanditsdk.py`)

| Area | Python | Not in the 8.6 bindings |
| --- | --- | --- |
| Context, frames | `RecognitionContext(key, path[, device_name])`, `start_new_frame_sequence()` → `FrameSequence.process_frame(descr, data_ptr)` / `.end()`, `set_camera_properties` | — |
| Settings | `BarcodeScannerSettings(preset=…)`, `from_json`, `as_json(settings)`, `enable_symbology`, `symbologies[sym]` (`enabled`, `color_inverted_enabled`, `active_symbol_counts`, `set_extension_enabled`), `multi_scan_enabled`, `max_num_locations_to_process_per_frame`, `code_duplicate_filter`, `code_direction_hint`, `search_area`, `code_location_area_1d/2d`, `code_location_constraint_1d/2d`, `properties` | checksums, OCR-fallback regex, circle of interest, ArUco dictionary (use `from_json` where a JSON key exists) |
| Scanner, results | `BarcodeScanner(context)`, `apply_settings` → status (`is_success()`, `flag`, `message`), `wait_for_setup_completed`, `session.newly_recognized_codes` / `newly_localized_codes` / `all_recognized_codes` / `clear()`; `Barcode.data`, `raw_data`, `data_encoding`, `symbology`, `symbology_string`, `location`, `is_gs1_data_carrier`, `composite_flag`, `symbol_count`, `file_id`, `segment_index`, `segment_count` | `module_counts`, `is_color_inverted` |
| Images | `ImageDescription` (`width`, `height`, `layout`, `planes_count`, `set_plane_row_bytes` / `get_…`, `set_plane_offset` / `get_…`) | no `memory_size`, no `first_plane_row_bytes` (assigning them silently does nothing) |
| Camera | `Camera(path=None, buffer_count=4)`, `resolution`, `supported_resolutions` (`discrete_resolutions` / `stepwise_resolutions`), `image_layout`, `supported_image_layouts`, `start_streaming()`, `with camera.frame as f:` (`f.data`, `f.description`) | framerate and focus control |
| MatrixScan | `ObjectTracker(context, settings)`, `session.tracked_objects` (`items()`, `keys()`, `[id]`), `TrackedObject.id`, `location`, `get_barcode()` | — |
| Generator | `BarcodeGenerator(context, symbology)`, `set_options(dict)`, `generate(ascii_text)` → `ImageBuffer` (`description`, `numpy_array`) | non-ASCII input |
| Parser | — | the whole parser |

## 11. Migrating to 8.0 (breaking changes)

Step-by-step guide including 5.x → 7.0 and the behaviour changes per version: migration.md.

| Before 8.0 | 8.0 and later |
| --- | --- |
| `sc_barcode_scanner_new_with_settings(ctx, settings)` | `sc_barcode_scanner_new(ctx)` + `sc_barcode_scanner_apply_settings(scanner, settings)` |
| `apply_settings` returned nothing useful | returns `ScContextStatus` (check + `sc_context_status_free`) |
| `set_max_number_of_codes_per_frame` | `set_multi_scan_enabled` + `set_max_num_locations_to_process_per_frame` (≠ 0) |
| `process_frame` result | extended `ScProcessFrameResult` + `sc_process_frame_result_free` |
| `SC_SYMBOLOGY_RM4SCC`, JSON `rm4scc` | `royal-mail-4state` |
| scanner-settings focus mode APIs, JSON `focusMode` | removed (use `SC_CODE_DIRECTION_NONE` for fixed-focus devices). `sc_camera_set_focus_mode` on `ScCamera` still exists |
| `sc_context_status_flag_get_message` | removed; use `status.message` |
| `sc_parser_new_with_context(ctx, type)` | takes `ScContextStatus*` |
| unscanned default locations in the session | no longer reported |

Code written for 7.x uses the removed calls in the left column; replace them with the 8.x calls above.
## 12. Release notes: what changed when

Source: [Linux release notes](https://docs.scandit.com/sdks/linux/release-notes/).
| Version | Date | What changed |
| --- | --- | --- |
| 8.0.0 | 2025-11-04 | Breaking API changes (§11) |
| 8.0.1 / 8.1.0 | | EAN-13 out-of-bounds crash fixed |
| 8.1.0 | | Mirrored Aztec; OCR fallback without resources → error 28 |
| 8.2.0 | | PDF417 generation |
| 8.3.0 | | `SINGLE_CODE_HAND_HELD` smart scan intention fixed |
| 8.4.0 | | Code 128 with uneven blur (not on ARM without FP16); ITF checksum-dependent scoring; Abseil removed; k-out-of-n crash fix (also 8.1.4) |
| 8.4.2 | | Data Matrix DPM (direct part marking) fix for 8.4.0 |
| 8.5.0 | 2026-07-09 | Low-resolution QR (versions 1–3); Code 128 minimum symbol count 4; tighter Code 39 (`relaxed` restores old behavior); camera single-plane fallback |
| 8.5.3 | | Low-res QR disabled for multi-code tracking |
| 8.6.0 | 2026-08-31 | DotCode ECI and structured append; fewer EAN/UPC false positives; ITF +20 %; MicroQR +40 %; mirrored MaxiCode by default; Python segment fields; camera disconnect hang fixed |
| 8.6.1 | 2026-10-01 | QR with degraded finder patterns (regression in 8.6.0) fixed; Data Matrix unlatch/pad; 1D on colored backgrounds (regression since 5.19) fixed; Data Matrix DPM fix |
| 8.6.2 | 2026-10-26 | MicroQR improvements for rotated codes and cluttered backgrounds now active; faster scanning with many codes in the frame when only QR or Data Matrix is enabled (tracking modes) |
| 8.5.5 | 2026-10-29 | Data Matrix `direct_part_marking_mode` accuracy fix (regression from 8.4.0) |

**If results got worse after upgrading, check this table first**: tightened validation (8.5 Code 39) can look like a regression but is intentional; real regressions (8.4.0 DPM, 8.6.0 QR) are fixed in later patches.

