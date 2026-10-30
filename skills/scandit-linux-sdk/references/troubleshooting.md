# Scandit Linux SDK: troubleshooting

*Symptom → cause → fix tables for the Scandit Linux SDK. Exact API names and the full status-code table are in the API reference. If a code is visible but not decoded, use the readability guide (pixels per module, blur, contrast, print quality).*

**Start here:** print the SDK version (`sc_get_information_string(SC_INFORMATION_KEY_SDK_VERSION)`), print every status as **code + message** (`sc_byte_array_get_string(status.message)`), and dump the effective settings (`sc_barcode_scanner_settings_as_json`). Most problems are obvious from those three lines.

**Contents:** 1 Install and startup · 2 License status codes · 3 Nothing or the wrong thing scans · 4 Multiple codes · 5 Camera · 6 Image buffers · 6a Python bindings · 7 Performance · 8 Crashes, hangs, threads · 9 Worse after an upgrade · 10 What to send to support

---

## 1. Install and startup

| Symptom | Cause and fix |
| --- | --- |
| `undefined reference to log@GLIBC_2.29` (or another `GLIBC_2.xx`) when linking or starting | The system glibc is older than the SDK needs. Since 7.0 the SDK requires glibc 2.31 or newer (Ubuntu 20.04, Debian 11 or newer); on older systems the package can install but fails at link or load time. Check with `ldd --version` and upgrade the OS or firmware image. |
| Status **28** `MISSING_RESOURCE_ERROR` ("could not access a required resource") | The SDK can't find or parse its resources (ML models). Usually an incomplete install or modified resource files: reinstall the `.deb` without changes. Since 8.1, enabling OCR fallback without its resources also gives 28. |
| `error while loading shared libraries: libscanditsdk.so` | The library isn't on the loader path: install the `.deb`, or set `LD_LIBRARY_PATH` to the folder with `libscanditsdk.so` (needed for the Python/OpenCV samples when not installed system-wide). |
| `ModuleNotFoundError: scanditsdk` (Python) | Put the folder with `scanditsdk.py` on `PYTHONPATH` and use `import scanditsdk as sc`. |
| *"OpenGLES GPU acceleration failed … falling back to CPU"* | Harmless. The CPU path (NEON/SSE) is used. |
| `sc_barcode_scanner_new` returns NULL | The context already has a scanner (one scanner per context since 8.0). |
| Context is created, but `apply_settings` or `process_frame` returns a license status | Expected: a wrong or missing key does not make context creation fail. Read the status code and message (§2). |
| `implicit declaration of function 'sc_barcode_scanner_new_with_settings'` (or `..._max_number_of_codes_per_frame`, `sc_context_status_flag_get_message`, `sp_parser_*`) | Code written for an older SDK version: see migration.md. |
| Build dependencies for the samples missing | Packages: `libv4l-dev`, `libsdl2-dev`, `libsdl2-image-dev`, `python3-sdl2`, `libpng-dev`. Other dependencies (package README): GCC ≥ 4.9, pthread, dbus ≥ 1.6.8, zlib ≥ 1.2.8, OpenGL ES ≥ 2.0 (optional), Python 3 for the bindings. |

**Isolate first:** run the bundled image-file sample on the same machine and image. If the sample works, the problem is in your code or environment.

## 2. License status codes

Print the code **and** `status.message`; the message often names the missing feature. Full table in the API reference (§4).

| Code | Meaning | Fix |
| --- | --- | --- |
| 6 | Network access required by this key (e.g. test keys) | Connect the device, restart. Ask for a key type that fits offline use if needed. |
| 11 | Validation failed (403) | Check the key and the available device activations in the dashboard. |
| 12 | Key missing | The key string is empty (check the license-key constant or wherever your application stores the key). |
| 13 | Key expired | Get a new key from the dashboard. |
| 14 | Wrong platform | The key wasn't created for Linux. |
| **15** | **App ID mismatch** | On Linux the app ID is the **executable name**: the first element of the process command line. `python3 app.py` → `python3`, not `app.py`; in embedded runtimes it is the host binary. Shell aliases don't change it. Create a key with the right executable name, or one without an executable name. |
| 16 | Wrong device | The key is bound to other devices. |
| 17 | Key doesn't cover this SDK version | Get a key for this version. |
| 18 | Key invalid | Malformed or truncated: check for copy/paste errors, quotes, line breaks, whitespace. |
| 19 | Device activation failed | Connect to the internet and restart. |
| 20 / 21 | Time / scan limit reached | Limited key used up; get a new key. |
| 24 / 27 | Unlicensed symbology / extension enabled | Disable it, or get it added to the key. |
| 28 | Missing resource | See §1. |
| 29 | Text recognizer not licensed | OCR fallback is enabled but not on the key. |
| 255–512 | Unlicensed feature | Read `status.message`. Common: multi-scan / tracking without the "tracking" feature. |

- Trial and production keys use the same engine: the key doesn't change accuracy.
- Never post a key in a public place; when asking for help, share only its first few characters.

## 3. Nothing (or the wrong thing) scans

Check in this order:

1. **Status OK?** `apply_settings` and every `process_frame` return a status: anything but 1 (SUCCESS) explains the problem.
2. **Symbology enabled?** All symbologies are **disabled by default**. Enable each one you need, then call `sc_barcode_scanner_apply_settings` (settings do nothing until applied).
3. **JSON settings typo or outdated key?** Unknown JSON keys are silently ignored (e.g. `maxNumberOfCodesPerFrame`, removed in 8.0). A symbology's `extensions` list in JSON **replaces** its default extensions (Code 128 and Data Matrix then lose `strip_leading_fnc1`). Compare your JSON with the `as_json` output. Write float values with a decimal point (`1.0`).
4. **Code length outside the active symbol counts?** Codes outside the range are not returned (e.g. very short or long Code 128/39, ITF, Codabar). Set `activeSymbolCounts` / `sc_symbology_settings_set_active_symbol_counts` (count = number of elements, not bytes).
5. **Light-on-dark code?** Enable color inversion for that symbology (`colorInvertedEnabled`); only QR and MicroQR have it on by default.
6. **Search area / RESTRICT too tight?** `SC_CODE_LOCATION_RESTRICT` decodes only inside the area and turns localization off. With a portrait-mounted camera, the code direction hint is in **image** coordinates (horizontal codes become BOTTOM_TO_TOP).
7. **Duplicate filter** hides repeats: turn it off (`SC_DUPLICATE_FILTER_OFF`) for single-image tests.
8. **Frame sequence:** `process_frame` without `start_new_frame_sequence` returns status 3. For unrelated single images start a new sequence per image.
9. **Is the code found at all?** `sc_barcode_scanner_session_get_newly_localized_codes`: if the code is localized but not decoded, it is usually image quality (go to the readability guide: pixels per module, blur, contrast, glare, print quality). If not even localized, check size, area, and that the code is in the frame you pass.
10. **Checksums:** a code passes if any enabled checksum matches; optional check digits are always included in the data.
11. **Code 32 vs Code 39** can't be told apart: enable only the one you use.
12. **Add-ons / composites** are never returned alone: enable the main symbology plus the add-on (or PDF417/MicroPDF417 for composites) and allow at least 2 codes per frame.
13. **Wrong characters / binary data truncated:** data can contain NUL bytes; use `sc_byte_array_get_size`, not `strlen`. Check `sc_barcode_get_data_encoding` for the encoding.

**"A phone app reads it but the Linux SDK doesn't"** (single image): a phone scans a video stream at close range with autofocus and many attempts; a single image gets one try at whatever resolution and sharpness it has. Compare pixels per module and sharpness first (readability guide).

## 4. Multiple codes

- **Multi-scan is off by default.** Enable it with `sc_barcode_scanner_settings_set_multi_scan_enabled(settings, SC_TRUE)` and set `sc_barcode_scanner_settings_set_max_num_locations_to_process_per_frame` (≥ 1; higher costs time).
- It needs the **"tracking"** license feature; without it you get a status in 255–512.
- `SC_PRESET_SINGLE_CODE_HAND_HELD` returns at most one code (or group) per frame by design.
- Before 8.0 this was `set_max_number_of_codes_per_frame` (removed). In JSON, `maxNumberOfCodesPerFrame` is silently ignored in 8.x: use `multiScanEnabled` and `maxNumLocationsToProcessPerFrame`.

## 5. Camera (`ScCamera`, V4L2)

| Symptom | Cause and fix |
| --- | --- |
| "No camera available", `Could not request buffers: Cannot allocate memory` | The driver reports an unrealistic stepwise maximum (e.g. 16376×16376) and that size was requested. Request a real sensor mode (datasheet or `v4l2-ctl --list-formats-ext -d /dev/video0`) and check the return value of `sc_camera_request_resolution`. Too many buffers can also make the allocation fail (4 is the documented example). |
| The camera "supports no resolutions / framerates" | Wrong query for the mode. Check `sc_camera_get_resolution_mode` / `get_framerate_mode`: DISCRETE → `query_supported_resolutions`, STEPWISE → `query_supported_resolutions_stepwise`. |
| Low or unexpected fps | Framerates depend on the resolution; query them for the resolution you use. Use `sc_framerate_get_fps`. |
| Stream stalls after a few frames | `sc_camera_enqueue_frame_data` isn't called for every frame from `sc_camera_get_frame`. |
| Garbled, shifted or striped image | Layout or row stride doesn't match the buffer. Pass the `ScImageDescription` filled by `get_frame` instead of building one; camera buffers often have padded rows. |
| `Device or resource busy` / wrong format | Request the layout explicitly with `sc_camera_request_image_layout` before `start_stream` (not while streaming), confirm with `sc_camera_get_image_layout`. (7.2.1 ignored the request; fixed in 7.3.1.) |
| Focus calls do nothing | `sc_camera_set_focus_mode` only works if the V4L2 driver exposes focus controls; many fixed-focus modules don't. Only the scanner-settings focus API was removed in 8.0. |
| `get_frame` hangs when the camera is unplugged | Fixed in 8.6. |
| Raspberry Pi camera not found | Install `v4l-utils`, add `bcm2835-v4l2` to `/etc/modules-load.d/modules.conf`, reboot. |

- FourCC numbers in logs are little-endian ASCII: `842094158` = NV12, `1448695129` = YUYV.
- To separate camera from decoding problems, save raw frames and run them through the image-file sample.

## 6. Image buffers (your own capture stack)

| Status / symptom | Fix |
| --- | --- |
| 4 `UNSUPPORTED_IMAGE_DATA` | Layout not supported or not set: use a valid `SC_IMAGE_LAYOUT_*` (GRAY_8U preferred). |
| 5 `INCONSISTENT_IMAGE_DATA` | Buffer smaller than width × height × layout: check row bytes (stride) per plane and, for NV12/NV21, **both** plane offsets. |
| Codes found in the wrong place / image looks sheared | Wrong stride. Set `sc_image_description_set_plane_row_bytes` to the real bytes per row. |
| Worse results with JPEG/PNG from disk than live | Re-encoding, resizing, sharpening or screenshots destroy thin bars. Pass the original frame, uncompressed, greyscale or YUV, without preprocessing. |

## 6a. Python bindings

| Symptom | Cause and fix |
| --- | --- |
| Status 5 or garbage results although width, height and layout look right | The stride was never set: `descr.memory_size` and `descr.first_plane_row_bytes` are not properties of the 8.x `ImageDescription`, and Python silently creates a new attribute. Use `descr.set_plane_row_bytes(0, array.strides[0])`. |
| A setting has no effect | Same cause: check the property name against `scanditsdk.py` (e.g. `settings.multi_scan_enabled`, `settings.code_duplicate_filter`). |
| Crash or wrong data in `process_frame` | Pass the address of a contiguous uint8 buffer (`np.ascontiguousarray(a).ctypes.data`) and keep the array alive during the call. |
| `AttributeError` for `module_counts`, checksums, circle of interest, parser | Not in the 8.6 bindings; use the C API, or JSON settings for checksums. |
| Status 15 in Python only | The executable name is `python3`, not the script name. |
| Generated barcode image looks distorted | Reshape the generator's RGBA data as `(height, row bytes)`, not `(width, height)`. |

## 7. Performance

- **Disable symbologies you don't need**: the cheapest gain in speed and false positives.
- **Pass greyscale (GRAY_8U) or YUV**, not RGB: the SDK converts to grey anyway.
- **Restrict the search area** (`set_search_area`, circle of interest) when codes appear in a known region; keep it at least 320×160 px.
- **Right resolution:** 1280×720 is the docs' recommendation for speed; go higher only if the codes need it (pixels per module). If there are plenty of pixels per module, downscaling the frame speeds things up without losing reads.
- **Preset:** `SC_PRESET_HIGH_EFFORT` is slower by design (best accuracy, single images/servers); use `SC_PRESET_NONE` for real-time video. `SC_PRESET_SINGLE_CODE_HAND_HELD` targets hand-held devices, not low-power fixed installations.
- **Reuse** the context and scanner; creating them per image is expensive.
- **Parallelism:** one context per process; for more throughput run several processes.
- The SDK uses SIMD (NEON on ARM, SSE on x86). No GPU setup is needed.

## 8. Crashes, hangs, threads

- The API is **not thread-safe**: make all calls for a context and its scanner from one thread (`sc_object_tracker_release` is the documented exception).
- **Release order:** release scanner, settings, parser, tracker and arrays before the last release of the context.
- Free every `ScContextStatus` / `ScProcessFrameResult` (by value) and every returned array; release only arrays, not their items.
- Slow first frames or slow release right after creating the scanner: setup is still running. `sc_barcode_scanner_is_setup_complete` / `sc_barcode_scanner_wait_for_setup_completed` let you wait for it.
- For a reproducible crash: SDK version, architecture, a backtrace (`gdb`), and the smallest program and image that trigger it.

## 9. Worse after an upgrade

Check the release notes table in the API reference (§12) before assuming a regression:
- **8.0** changed the API (`sc_barcode_scanner_new` + `apply_settings`, multi-scan setters, status structs, `royal-mail-4state`). Migration table in the API reference (§11).
- Multi-scan has been **off by default** since 7.x: re-enable it after upgrading old code.
- Some versions **tighten validation on purpose** (fewer false positives, sometimes a lower scan rate on hard codes): e.g. 8.5 Code 39 (the `relaxed` extension restores the old filter).
- Known regressions are fixed in later patches (e.g. Data Matrix DPM 8.4.0 → 8.4.2; QR with degraded finder patterns 8.6.0 → 8.6.1): update to the latest patch release.
- **Compare before you report:** run the same set of original frames through the old and the new version and compare scan rate, data and false reads. If an image scans with the older version and not with the newer one, send that image and both version numbers to Scandit support (§10).

## 10. What to send to Scandit support

To support@scandit.com or through your support channel (not public forums if the images contain personal data):

- SDK version and build, architecture (x86_64/arm64), OS and glibc version, device/camera model
- The status code **and** message
- The settings JSON (`sc_barcode_scanner_settings_as_json`)
- **Original frames** as passed to the SDK (not screenshots or resized copies), ideally several that scan and several that don't
- A minimal program (or the bundled sample) that reproduces the problem, and what you expected
- For regressions: the last version that worked
- Never the full license key; its first few characters are enough
