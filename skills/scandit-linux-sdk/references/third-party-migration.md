# Replacing an open-source barcode library with the Scandit Linux SDK

*For code that uses ZBar / pyzbar, ZXing / zxing-cpp, libdmtx / pylibdmtx or OpenCV's QR and barcode detectors. The Scandit side is based on the [C API reference](https://docs.scandit.com/stable/c_api/annotated.html); the other libraries are described at the concept level (check their names in their own documentation).*

## Migration principles

- **Authority.** When this guide and the headers of the installed SDK (`/usr/include/Scandit/`, `scanditsdk.py`) disagree, trust the headers and a build against them, then the C API reference, over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a behaviour difference as a 1:1 replacement: Scandit enables no symbology by default, returns one code per frame unless multi-scan is on, filters codes by symbol counts, and reports positions as quadrilaterals. List each difference that affects the user's results (other codes found or not found, order, data format such as GS1 separators or add-ons) as a judgment call the user must confirm.
- **Compatibility layer.** When the old library sits behind the user's own scanner module or function that other code calls (e.g. a `decode(image)` helper), keep that module's public API frozen (same function names, arguments, result types and fields) and replace only the library calls underneath. The rest of the application should not change.

## Migration flow

1. **Find the old library and every call site:** `#include <zbar.h>`, `zbar_*` / `zbar::ImageScanner`, `from pyzbar.pyzbar import decode`, `ZXing::ReadBarcodes` / `zxingcpp.read_barcodes`, `dmtxDecode*` / `pylibdmtx.decode`, `cv2.QRCodeDetector` / `cv2.barcode` / `cv::QRCodeDetector`. Note which symbologies it is configured for (or that it uses its defaults, often "all"), whether it decodes video or single images, how many codes per image the callers expect, and the result fields they read.
2. **Ask the user only what the code doesn't show:** the symbologies they actually scan (Scandit enables none by default, and enabling only the needed ones makes scanning faster and more reliable), unusual code lengths, light-on-dark codes, and whether several codes per image are needed (multi-scan needs the "tracking" license feature).
3. **Write the replacement into the user's files:** keep the wrapper or function signature (compatibility layer), create the Scandit context and scanner **once** (not per call), map the image to an `ScImageDescription` (see the table below and capture-pipelines.md), choose the settings for single images or video (integration.md), and map the results back to the fields the callers use. Remove the old includes, imports, link flags and package dependencies.
4. **Show the setup checklist** from integration.md (package, build flags or `PYTHONPATH`, license key, writable data path), plus: remove the old library from the build (`-lzbar`, `requirements.txt`, …).
5. **Summarize:** what was replaced, which result fields map to what, and the behaviour differences as judgment calls. Suggest comparing both libraries on the same set of original frames, including the hard cases.

## Concepts side by side

| Concept | Typical open-source library | Scandit Linux SDK |
| --- | --- | --- |
| Setup | Create a reader/scanner object, often no license | **License key** + `sc_recognition_context_new(key, writable_path, NULL)`, then `sc_barcode_scanner_new(ctx)`; one scanner per context, one context per process |
| Which symbologies | Often **all enabled** by default (ZBar, ZXing) | **All disabled** by default: enable each one (`sc_barcode_scanner_settings_set_symbology_enabled`) and call `sc_barcode_scanner_apply_settings` |
| Decode call | `decode(image)` returns results directly | `start_new_frame_sequence` → `process_frame(ctx, desc, pixels)` → read the **session** (`get_newly_recognized_codes`) → `end_frame_sequence` |
| Video | Each frame decoded independently | One **frame sequence** for a continuous stream: the SDK uses information across frames. Start a new sequence only for unrelated images |
| Image input | Library-specific image object, often greyscale | `ScImageDescription`: width, height, layout (`SC_IMAGE_LAYOUT_GRAY_8U`, NV12, YUYV, RGB, …), row bytes per plane (and plane offsets for NV12/NV21). Pass the raw buffer, no copy into an image object |
| Several codes per image | Usually returned by default | **Multi-scan off by default**: `set_multi_scan_enabled` + `set_max_num_locations_to_process_per_frame`; needs the "tracking" license feature |
| Result data | Bytes or string | `sc_barcode_get_data` → `ScByteArray` (may contain NUL bytes), plus `get_data_encoding` |
| Symbology name | String or enum | `ScSymbology` enum, `sc_symbology_to_string` |
| Position | Rectangle and/or polygon | `ScQuadrilateral` (4 corners, image pixels, origin top-left) |
| Code length limits | Usually none | **Active symbol counts** per symbology: codes outside the range aren't returned (set them for unusually short or long 1D codes) |
| Inverted (light-on-dark) codes | Library option or preprocessing (invert the image) | `colorInvertedEnabled` per symbology (on by default only for QR/MicroQR); don't invert the image yourself |
| Region of interest | Crop the image yourself | `set_search_area`, code location areas, circle of interest; or crop (keep ≥ 320×160 px) |
| Duplicates in video | Your own logic | `set_code_duplicate_filter` (ms, OFF, or INFINITE until `session_clear`) |
| Errors | Return value / exception | `ScContextStatus {flag, message}` from `apply_settings` and `process_frame`; check and free (by value) |
| Threads | Varies | Not thread-safe: all calls for one context on one thread; more throughput with more processes |
| Memory | Garbage-collected or RAII | Explicit `*_release` / `*_free`; release everything before the context |

## Habits to drop when switching

- **Preprocessing.** Thresholding, sharpening, binarizing, inverting or upscaling helps some open-source decoders but hurts the Scandit SDK. Pass the original greyscale frame. Cropping is fine if the crop stays large enough.
- **Decoding a frame "fresh" each time.** In video, keep one frame sequence open; restarting it per frame throws away information.
- **"Enable everything".** Enabling all symbologies slows scanning and adds false positives. Enable what you actually scan.
- **Retrying with rotations or scales.** Don't rotate or rescale and retry; set the code direction hint to the orientation you expect (or NONE) instead.
- **Comparing on screenshots or JPEGs.** Compare libraries on the same original frames (uncompressed, full resolution), and on a representative set that includes the hard cases.

## Library-specific notes

### ZBar / pyzbar
- ZBar's per-symbology config (enable/disable) maps to `set_symbology_enabled`; remember that Scandit starts with everything off.
- pyzbar's result fields (data, type, rect, polygon) map to `get_data`, `get_symbology`/`sc_symbology_to_string`, and `get_location`.
- ZBar doesn't read Data Matrix; the Scandit SDK reads 1D and 2D (QR, Data Matrix, PDF417, Aztec, MaxiCode, DotCode, …) in one call.

### ZXing / zxing-cpp
- "Formats" in the reader options map to enabled symbologies; "try harder" is roughly what `SC_PRESET_HIGH_EFFORT` does for single images (more time, more accuracy).
- "Try rotate / try invert / try downscale" options have no direct equivalent: use the code direction hint instead of rotating, inversion is a per-symbology setting, and the resolution is your choice (see pixels per module).
- GS1 / FNC1 handling: check `sc_barcode_is_gs1_data_carrier` and the raw data; the Scandit parser (GS1 AI, HIBC, …, license feature) can split element strings.

### libdmtx / pylibdmtx
- Data Matrix only, often with long timeouts on large images. In Scandit enable `SC_SYMBOLOGY_DATA_MATRIX` (plus color inversion for light-on-dark marks). For dot-peen / laser-etched direct part marks there is the `direct_part_marking_mode` extension (slower: restrict the search area).

### OpenCV QR / barcode detectors
- Keep OpenCV for capture and display if you like, and pass the `cv::Mat` buffer to `process_frame`: greyscale `CV_8UC1` → `SC_IMAGE_LAYOUT_GRAY_8U`, BGR `CV_8UC3` → `SC_IMAGE_LAYOUT_BGR_8U`, with `step` as the row bytes. The bundled OpenCV samples (`samples/opencv_py_demo`) show this.
- OpenCV's separate detect/decode steps map to localized (`get_newly_localized_codes`) and recognized codes.

## Example: a pyzbar-compatible `decode()` (Python)

Callers that did `from pyzbar.pyzbar import decode` switch to `from scandit_decode import decode` and keep reading `.data`, `.type`, `.rect` and `.polygon`. The `type` values become Scandit symbology names (`ean13upca`, `code128`, `qr`, …): map them if callers compare against pyzbar's names (`EAN13`, `CODE128`, `QRCODE`).

```python
"""scandit_decode.py - a pyzbar-style decode() on top of the Scandit Linux SDK Python bindings (8.x).

Callers keep `for r in decode(image): r.data, r.type, r.rect, r.polygon`; only this module talks to Scandit.
Create one Decoder per process and reuse it: creating the context and scanner is expensive.
"""
import ctypes
from typing import List, NamedTuple, Tuple

import numpy as np
import scanditsdk as sc

LICENSE_KEY = "-- INSERT YOUR LICENSE KEY HERE --"
WRITABLE_DATA_PATH = "/tmp"  # use a directory that survives reboots


class Rect(NamedTuple):
    left: int
    top: int
    width: int
    height: int


class Decoded(NamedTuple):
    data: bytes                         # as in pyzbar: bytes
    type: str                           # Scandit symbology name, e.g. "ean13upca", "code128", "qr"
    rect: Rect
    polygon: List[Tuple[int, int]]


class Decoder:
    def __init__(self, symbologies=(sc.SYMBOLOGY_EAN13_UPCA, sc.SYMBOLOGY_CODE128, sc.SYMBOLOGY_QR)):
        self._context = sc.RecognitionContext(LICENSE_KEY, WRITABLE_DATA_PATH)
        settings = sc.BarcodeScannerSettings(preset=sc.PRESET_HIGH_EFFORT)
        for symbology in symbologies:  # Scandit starts with everything disabled
            settings.enable_symbology(symbology, True)
        settings.code_duplicate_filter = sc.DUPLICATE_FILTER_OFF
        settings.code_location_constraint_1d = sc.CODE_LOCATION_IGNORE
        settings.code_location_constraint_2d = sc.CODE_LOCATION_IGNORE
        settings.code_direction_hint = sc.CODE_DIRECTION_NONE
        # pyzbar returns every code in the image; with Scandit that needs multi-scan
        # and the "tracking" license feature.
        settings.multi_scan_enabled = True
        settings.max_num_locations_to_process_per_frame = 10
        self._scanner = sc.BarcodeScanner(self._context)
        status = self._scanner.apply_settings(settings)
        if not status.is_success():
            raise RuntimeError(f"Scandit settings: status {status.flag}: {status.message}")
        self._scanner.wait_for_setup_completed()
        self._descr = sc.ImageDescription()

    def decode(self, image) -> List[Decoded]:
        """image: a PIL image or a numpy array (greyscale HxW or BGR HxWx3, uint8)."""
        pixels = np.asarray(image.convert("L")) if hasattr(image, "convert") else np.asarray(image)
        pixels = np.ascontiguousarray(pixels, dtype=np.uint8)
        self._descr.width = pixels.shape[1]
        self._descr.height = pixels.shape[0]
        self._descr.layout = sc.IMAGE_LAYOUT_GRAY_8U if pixels.ndim == 2 else sc.IMAGE_LAYOUT_BGR_8U
        self._descr.set_plane_row_bytes(0, pixels.strides[0])

        frame_seq = self._context.start_new_frame_sequence()  # unrelated images: one sequence each
        result = frame_seq.process_frame(self._descr, pixels.ctypes.data)
        frame_seq.end()
        if not result.is_success():
            raise RuntimeError(f"Scandit process_frame: status {result.flag}: {result.message}")

        decoded = []
        for code in self._scanner.session.newly_recognized_codes:
            polygon = [(p.x, p.y) for p in code.location.all_corners]
            xs, ys = [x for x, _ in polygon], [y for _, y in polygon]
            rect = Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            raw = code.raw_data  # the exact bytes, also for binary codes
            data = ctypes.string_at(raw.bytes, raw.size) if raw.size else b""
            decoded.append(Decoded(data, code.symbology_string, rect, polygon))
        return decoded


_decoder = None


def decode(image) -> List[Decoded]:
    """Drop-in for `pyzbar.pyzbar.decode(image)`."""
    global _decoder
    if _decoder is None:
        _decoder = Decoder()
    return _decoder.decode(image)
```

For C code using ZBar's `zbar_scan_image`, the same pattern applies: keep your function, and inside it describe the greyscale buffer, start a frame sequence, process the frame and copy the results out of the session (complete program: integration.md, single image).

## Result field mapping

| Field | ZBar / pyzbar | ZXing / zxing-cpp | Scandit C | Scandit Python |
| --- | --- | --- | --- | --- |
| Data | `zbar_symbol_get_data` / `.data` (bytes) | `text()` / `bytes()` | `sc_barcode_get_data` → `ScByteArray` | `code.data` (text), `code.raw_data` (bytes) |
| Type | `zbar_symbol_get_type` / `.type` | `format()` | `sc_barcode_get_symbology` + `sc_symbology_to_string` | `code.symbology`, `code.symbology_string` |
| Position | `.rect`, `.polygon` | `position()` | `sc_barcode_get_location` (4 corners, pixels) | `code.location` |
| GS1 | — | `contentType()` / symbology identifier | `sc_barcode_is_gs1_data_carrier` | `code.is_gs1_data_carrier` |

## Checklist

- [ ] Trial key from https://www.scandit.com/trial/ or a Linux key from the dashboard (right executable name or none; see **Licence key** in SKILL.md)
- [ ] The symbologies and code lengths you scan are enabled; symbol counts set for unusual lengths
- [ ] Image source mapped to an `ScImageDescription` (layout + stride); preprocessing removed
- [ ] Video: one frame sequence per stream. Single images: HIGH_EFFORT, new sequence per image, duplicate filter off, codes anywhere
- [ ] Several codes per image: multi-scan enabled and the "tracking" feature on the key
- [ ] Context and scanner created once and reused; every status checked; teardown order respected; all calls on one thread
- [ ] Old library removed from includes, imports, link flags and dependencies
- [ ] Both libraries compared on the same original frames; failures analysed with code-readability.md (pixels per module) before tuning settings
- [ ] Links: [overview](https://docs.scandit.com/sdks/linux/overview/) · [installation](https://docs.scandit.com/sdks/linux/add-sdk/) · [samples](https://docs.scandit.com/sdks/linux/samples/) · [C API](https://docs.scandit.com/stable/c_api/annotated.html)
