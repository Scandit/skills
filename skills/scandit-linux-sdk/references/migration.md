# Migrating a Scandit Linux SDK integration between SDK versions

*Based on the [Linux release notes](https://docs.scandit.com/sdks/linux/release-notes/) (8.x), the [version 7 release notes](https://docs.scandit.com/7.6.15/sdks/linux/release-notes/) (7.0 to 7.6; Linux has no 6.x versions: it went from 5.x to 7.0) and the [C API reference](https://docs.scandit.com/stable/c_api/annotated.html).*

## Migration principles

- **Authority.** When this guide and the headers of the target version disagree, trust the headers (`/usr/include/Scandit/` of the installed package) and a build against them, then the C API reference, over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a behaviour change (a new default, stricter validation, a changed scan rate or result order) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm, and suggest testing it on their own images.
- **Compatibility layer.** When the Scandit calls sit behind the user's own scanner module or wrapper that other code calls, keep that module's public API frozen (same functions, types, callbacks) and change only the Scandit calls underneath.
- **Dual-version code.** C code that names a function removed in the target version does not compile against it, so the code path cannot be chosen at run time. Select it at build time with the version macros from `<Scandit/ScConfig.h>` (`SC_VERSION_MAJOR`, `SC_VERSION_MINOR`, `SC_VERSION_INT`) or a build option, never on the presence of a new function. In Python, choose the path from the SDK version you deploy with (the `scanditsdk.py` must come from the same package as the library), not by probing for attributes.

## Step 1: Detect the installed and the target version

Check in this order and tell the user what you found:

1. **The package:** `dpkg -s libscandit-barcodescanner | grep Version`, or the `.deb` file names (`libscandit-barcodescanner-<version>-<arch>.deb`).
2. **The headers:** `grep -E 'define SC_VERSION_(MAJOR|MINOR|PATCH)' /usr/include/Scandit/ScConfig.h`.
3. **At run time:** `sc_get_information_string(SC_INFORMATION_KEY_SDK_VERSION)`.
4. **The code itself** when the SDK isn't installed where you are:

| The code uses | It was written for |
| --- | --- |
| `sp_parser_*`, `SpParser`, `#include <Scandit/Parser/...>`, `SC_SYMBOLOGY_EAN13` / `SC_SYMBOLOGY_UPCA`, `ScData`, `sc_data_free`, `sc_barcode_scanner_settings_set_property`, `ScObjectTrackerCallbacks`, `sc_image_description_set_memory_size` | 5.x (before 7.0) |
| `sc_barcode_scanner_new_with_settings`, `sc_barcode_scanner_settings_set_max_number_of_codes_per_frame`, `sc_context_status_flag_get_message`, `ScContextStatusFlag` as the return of `apply_settings`, `SC_SYMBOLOGY_RM4SCC` | 7.x (or older) |
| `sc_barcode_scanner_new` + `sc_barcode_scanner_apply_settings` returning `ScContextStatus`, `sc_process_frame_result_free` | 8.x |

| Installed | Target | Apply |
| --- | --- | --- |
| 5.x | 7.x | **5.x → 7.0** |
| 7.x | 8.x | **7 → 8** |
| 5.x | 8.x | **5.x → 7.0**, then **7 → 8** |
| 8.x | later 8.x | no API changes; check the **behaviour changes** (Step 5) |

If you can't determine the version, ask the user which version they are migrating from.

## Step 2: Update the package

1. Install the new `.deb` for every architecture you ship (amd64, arm64): `sudo dpkg -i libscandit-barcodescanner-<new>-<arch>.deb`. Check glibc on the target devices: 7.0 and later need glibc 2.31 or newer.
2. Python: replace `scanditsdk.py` with the one from the **same** package. Mixing bindings and library versions gives wrong results or crashes.
3. Rebuild everything that includes the headers (`-Werror=implicit-function-declaration` makes removed C functions fail the build instead of becoming implicit declarations).
4. The license key: an older key may not cover the new version (status 17 `INVALID_SDK_VERSION` or 26 `INVALID_LICENSE_KEY_VERSION`); create a new key in the dashboard if needed.

## Step 3: 5.x → 7.0 (Linux skipped 6.x)

| 5.x | 7.0 and later |
| --- | --- |
| glibc 2.27 (Ubuntu 18.04, Debian 10) | newer glibc (release notes: 2.31; Ubuntu 18.04 and Debian 10 are no longer supported) |
| `SC_SYMBOLOGY_EAN13`, `SC_SYMBOLOGY_UPCA` | `SC_SYMBOLOGY_EAN13_UPCA` |
| UPC-A extension `remove_leading_zero` | `remove_leading_upca_zero` |
| code caching: `sc_barcode_scanner_settings_set_code_caching_duration`, JSON `codeCachingDuration` | removed: read `sc_barcode_scanner_session_get_newly_recognized_codes` after **every** frame |
| presets `SC_PRESET_ENABLE_RETAIL_SYMBOLOGIES`, `SC_PRESET_ENABLE_VIN_DECODING`, `SC_PRESET_ENABLE_SSCC_DECODING`, `SC_PRESET_ENABLE_SINGLE_FRAME_MODE` | removed: enable symbologies explicitly; for single images use `SC_PRESET_HIGH_EFFORT` (7.1+) |
| `sc_barcode_scanner_settings_get_property` / `_set_property` | removed: configure scanning with the documented setters or JSON settings (advanced.md) |
| status flags `..._LICENSE_FILE_EXPIRED`, `..._LICENSE_FILE_IO_ERROR`, `..._LICENSE_VALIDATION_FAILED`, `..._LICENSE_VALIDATION_FAILED_400`; `sc_recognition_context_set_geographical_location` | removed |
| Parser: `#include <Scandit/Parser/SpParser.h>`, `SpParser`, `SpParserType`, `SP_PARSER_TYPE_*`, `sp_parser_*`, `SpParserResult`, `SpField`, `sp_parser_result_*`, `SpBool`, `SpData`, `sp_data_free` | `#include <Scandit/ScParser.h>`, `ScParser`, `ScParserType`, `SC_PARSER_TYPE_*`, `sc_parser_*`, `ScParserResult`, `ScField`, `sc_parser_result_*`, `ScBool`, `ScByteArray`, `sc_byte_array_free` |
| `ScByteArray` fields `data`, `c_str`, `length`; `ScData`, `sc_data_free` | `sc_byte_array_get_data`, `sc_byte_array_get_string`, `sc_byte_array_get_size` (size no longer counts the terminating NUL); `sc_byte_array_free` |
| `sc_image_description_get_first_plane_offset` / `_row_bytes`, `_second_plane_…`, `sc_image_description_set_memory_size` / `_get_memory_size` | `sc_image_description_get_plane_offset(desc, i)`, `sc_image_description_get_plane_row_bytes(desc, i)`, `sc_image_description_get_planes_count`; no memory size |
| Object tracker with a barcode scanner and `ScObjectTrackerCallbacks` | `sc_object_tracker_apply_scanner_settings` (no scanner needed) and the session `ScObjectTrackerSession` (matrixscan.md) |
| Barcode generator: 12-digit UPC-A input for `SC_SYMBOLOGY_EAN13_UPCA` | pass 13 digits (UPC-A with its leading zero); 12 digits are read as EAN-13 without check digit |
| Python: `SC_CODE_DIRECTION_*`, `SC_IMAGE_LAYOUT_*`, `SC_CAMERA_*`, `SC_CODE_LOCATION_*` aliases; `sc.IMAGE_LAYOUT_NV16` | `sc.CODE_DIRECTION_*`, `sc.IMAGE_LAYOUT_*`, `sc.CAMERA_*`, `sc.CODE_LOCATION_*`; `sc.IMAGE_LAYOUT_NV16_U8` |

Also: calling any `sc_*_free` function twice is undefined behaviour since 7.0.

## Step 4: 7 → 8

| 7.x | 8.0 and later |
| --- | --- |
| `sc_barcode_scanner_new_with_settings(ctx, settings)` | `sc_barcode_scanner_new(ctx)` + `sc_barcode_scanner_apply_settings(scanner, settings)`; `sc_barcode_scanner_new` returns NULL if the context already has a scanner |
| `sc_barcode_scanner_apply_settings` without a useful result | returns `ScContextStatus`: check `.flag`, log `.message`, then `sc_context_status_free(status)` (by value) |
| `sc_barcode_scanner_settings_set_max_number_of_codes_per_frame(settings, n)` / `_get_…`; JSON `maxNumberOfCodesPerFrame` | `sc_barcode_scanner_settings_set_multi_scan_enabled(settings, SC_TRUE)` + `sc_barcode_scanner_settings_set_max_num_locations_to_process_per_frame(settings, n)` (n > 0); JSON `multiScanEnabled` + `maxNumLocationsToProcessPerFrame`. **The old JSON key is silently ignored in 8.x** |
| `ScProcessFrameResult` with a status flag | `ScProcessFrameResult {status, frame_id}` with `status.flag` and `status.message`; free with `sc_process_frame_result_free(result)` (by value) |
| `sc_context_status_flag_get_message(flag)` | removed: use `status.message` (`sc_byte_array_get_string`) |
| `sc_parser_new_with_context(ctx, type, ScContextStatusFlag *)` | last parameter is `ScContextStatus *` (free it with `sc_context_status_free`) |
| `sc_barcode_scanner_settings_set_focus_mode` / `_get_focus_mode`, JSON `focusMode` | removed: for cameras without autofocus set `SC_CODE_DIRECTION_NONE`. `sc_camera_set_focus_mode` on `ScCamera` still exists |
| `SC_SYMBOLOGY_RM4SCC`, JSON `rm4scc` | `SC_SYMBOLOGY_ROYAL_MAIL_4STATE`, JSON `royal-mail-4state` |
| `*_retain` / `*_release` take non-const pointers | they accept const pointers (no change needed) |
| unscanned default locations appear in the session | no longer reported |

Before (7.x):

```c
/* 7.x - does not compile against 8.x */
ScBarcodeScannerSettings *settings = sc_barcode_scanner_settings_new_with_preset(SC_PRESET_NONE);
sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_CODE128, SC_TRUE);
sc_barcode_scanner_settings_set_max_number_of_codes_per_frame(settings, 4);
ScBarcodeScanner *scanner = sc_barcode_scanner_new_with_settings(ctx, settings);
/* ... */
ScProcessFrameResult result = sc_recognition_context_process_frame(ctx, desc, pixels);
if (result.status != SC_RECOGNITION_CONTEXT_STATUS_SUCCESS)
    printf("error: %s\n", sc_context_status_flag_get_message(result.status));
```

After (8.x):

```c
ScBarcodeScannerSettings *settings = sc_barcode_scanner_settings_new_with_preset(SC_PRESET_NONE);
sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_CODE128, SC_TRUE);
sc_barcode_scanner_settings_set_multi_scan_enabled(settings, SC_TRUE);   /* needs the "tracking" feature */
sc_barcode_scanner_settings_set_max_num_locations_to_process_per_frame(settings, 4);
ScBarcodeScanner *scanner = sc_barcode_scanner_new(ctx);
ScContextStatus status = sc_barcode_scanner_apply_settings(scanner, settings);
if (status.flag != SC_RECOGNITION_CONTEXT_STATUS_SUCCESS)
    printf("apply_settings: %d %s\n", (int)status.flag, sc_byte_array_get_string(status.message));
sc_context_status_free(status);
/* ... */
ScProcessFrameResult result = sc_recognition_context_process_frame(ctx, desc, pixels);
if (result.status.flag != SC_RECOGNITION_CONTEXT_STATUS_SUCCESS)
    printf("error %d: %s\n", (int)result.status.flag, sc_byte_array_get_string(result.status.message));
sc_process_frame_result_free(result);
```

Python 7 → 8: `scanner.apply_settings(settings)` returns a status object (`status.is_success()`, `status.flag`, `status.message`); `frame_seq.process_frame(...)` returns a result with `is_success()`, `flag`, `message`, `frame_id`; multi-scan is `settings.multi_scan_enabled = True` + `settings.max_num_locations_to_process_per_frame = n`. Compare the user's code with the Python samples of the new package, and only use names that exist in its `scanditsdk.py`.

### Code that must build against 7.x and 8.x

```c
#include <Scandit/ScConfig.h>
#include <Scandit/ScBarcodeScanner.h>
#include <Scandit/ScBarcodeScannerSettings.h>

/* Returns the scanner, or NULL if it couldn't be created or configured. */
static ScBarcodeScanner *make_scanner(ScRecognitionContext *ctx, ScBarcodeScannerSettings *settings) {
#if SC_VERSION_MAJOR >= 8
    ScBarcodeScanner *scanner = sc_barcode_scanner_new(ctx);
    if (!scanner) return NULL;
    ScContextStatus status = sc_barcode_scanner_apply_settings(scanner, settings);
    int ok = status.flag == SC_RECOGNITION_CONTEXT_STATUS_SUCCESS;
    sc_context_status_free(status);
    if (!ok) { sc_barcode_scanner_release(scanner); return NULL; }
    return scanner;
#else
    return sc_barcode_scanner_new_with_settings(ctx, settings);   /* 7.x */
#endif
}
```

Build and test the 7.x branch against the 7.x headers.

## Step 5: Behaviour changes to confirm with the user

These need no code change but can change results. List the ones between the installed and the target version as judgment calls:

| Version | Change | What to do |
| --- | --- | --- |
| 7.1 | Resources (models) load from `/usr/share/scanditsdk/resources` instead of being embedded; missing resources give status 28 | Ship the full package contents; don't copy only the `.so` |
| 7.1 | `SC_DUPLICATE_FILTER_DEFAULT` (-2) became the default (behaves like 0, off); color-inverted QR and MicroQR scan without a setting | none |
| 7.2.1 | Default camera image layout favors low latency | Request a layout explicitly if you depend on one |
| 7.3 | EAN-8 / EAN-13 relaxed quiet-zone checks became the default (`relaxed_sharp_quiet_zone_check` removed for them) | none |
| 7.4 | Camera device paths: symbolic links in the basename are no longer followed | Use the real `/dev/videoN` path |
| 8.4 | ITF checksum-dependent scoring (`no_checksum_dependent_validation` disables it); smart scan intention adapts between single scan and selection | Test ITF without check digits |
| 8.5 | Code 128 minimum symbol count 6 → 4; tighter Code 39 filter (`relaxed` extension restores it) | Restrict symbol counts if short Code 128 false reads appear; test Code 39 |
| 8.6 | Mirrored MaxiCode read by default (`mirrored` extension removed); DotCode GS1 flag only for real GS1 data | Remove the extension from settings |

If results get worse after an upgrade, first compare the same original frames with both versions and check this table; tightened validation is intentional, real regressions are fixed in later patch releases (api-reference.md, release notes table).

## Step 6: Verify and summarize

1. Build with warnings enabled; no implicit declarations, no removed names.
2. Create the context and scanner **once** and reuse them for every image or frame (one scanner per context in 8.x); if the old code created them per image, change that and mention it in the summary.
3. Log the SDK version and `sc_barcode_scanner_settings_as_json` once at startup and compare the settings with the old version (renamed JSON keys are silently ignored).
4. Run a set of the user's original frames through old and new versions and compare (scan rate, data, false reads).
5. Summarize for the user: the version path applied, every API change made (old → new), the behaviour changes from Step 5 that apply to them as judgment calls, and anything you couldn't verify (e.g. a 7.x branch that wasn't built).
