# Advanced barcode scanning configuration (Linux)

*Based on [Configure with JSON](https://docs.scandit.com/sdks/linux/barcode-capture/configure-with-json/), [Add-on codes](https://docs.scandit.com/sdks/linux/barcode-capture/add-on-codes/), [Composite codes](https://docs.scandit.com/sdks/linux/barcode-capture/composite-codes/) and the [C API reference](https://docs.scandit.com/stable/c_api/annotated.html). Full tables of presets, extensions, checksums and symbol counts: api-reference.md (sections 5 and 6).*

When the user asks for one of these, add the recipe to the settings code of their existing integration (integration.md) rather than starting a new program, and say which license feature it needs, if any.

## Settings as JSON

Configuration can live in a JSON file instead of code: `sc_barcode_scanner_settings_new_from_json(json, &error)` (Python: `sc.BarcodeScannerSettings.from_json(text)`). The top level must be an object; `{}` gives default settings with every symbology disabled. Missing keys keep their defaults.

```c
/* Settings from JSON; unknown keys are ignored, so log what was actually applied. */
ScBarcodeScannerSettings *settings_from_json(const char *json) {
    ScError error = {0};
    ScBarcodeScannerSettings *settings = sc_barcode_scanner_settings_new_from_json(json, &error);
    if (!settings) {                                   /* invalid JSON or wrong types */
        fprintf(stderr, "settings JSON: %s\n", error.message);
        sc_error_free(&error);
        return NULL;
    }
    char *applied = sc_barcode_scanner_settings_as_json(settings);
    fprintf(stderr, "applied settings: %s\n", applied);
    sc_free(applied);
    return settings;
}
```

**Unknown keys are ignored without an error**, so a typo or an outdated key is a silent no-op. Always compare against the `as_json` output, which shows what was applied.

```json
{
  "symbologies": {
    "ean13upca": true,
    "code128": { "activeSymbolCounts": [18, 19, 20, 21, 22, 23, 24] },
    "data-matrix": { "colorInvertedEnabled": true, "extensions": ["direct_part_marking_mode", "strip_leading_fnc1"] },
    "itf": { "checksums": ["mod10"] }
  },
  "multiScanEnabled": true,
  "maxNumLocationsToProcessPerFrame": 4,
  "codeDuplicateFilter": 1000,
  "codeLocation1d": { "area": { "x": 0.0, "y": 0.45, "width": 1.0, "height": 0.1 }, "constraint": "restrict" },
  "codeDirectionHint": "horizontal",
  "searchArea": { "x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0 }
}
```

| Key | Values | C equivalent |
| --- | --- | --- |
| `symbologies` | array of names (`["ean13upca", "code128"]`) or object of name → `true` / options | `sc_barcode_scanner_settings_set_symbology_enabled` |
| per symbology `enabled`, `colorInvertedEnabled` | booleans | `sc_symbology_settings_set_enabled`, `_set_color_inverted_enabled` |
| per symbology `activeSymbolCounts` | array of integers | `sc_symbology_settings_set_active_symbol_counts` |
| per symbology `extensions` | array of names. **Replaces the symbology's default extensions**: list the defaults you want to keep (e.g. `strip_leading_fnc1` for Code 128 and Data Matrix) | `sc_symbology_settings_set_extension_enabled` (adds to the defaults) |
| per symbology `checksums` | e.g. `["mod10"]` | `sc_symbology_settings_set_checksums` |
| per symbology `ocrFallbackRegex` | regular expression string | `sc_symbology_settings_set_ocr_fallback_regex` |
| `multiScanEnabled`, `maxNumLocationsToProcessPerFrame` | boolean, integer > 0 (default 5) | `_set_multi_scan_enabled`, `_set_max_num_locations_to_process_per_frame` |
| `codeDuplicateFilter` | ms; `0` off, `-1` until the session is cleared | `_set_code_duplicate_filter` |
| `searchArea` | `{x, y, width, height}`, relative 0–1 | `_set_search_area` |
| `codeLocation1d`, `codeLocation2d` | `{"area": {…}, "constraint": "restrict" | "hint" | "ignore"}` | `_set_code_location_area_1d/2d`, `_set_code_location_constraint_1d/2d` |
| `codeDirectionHint` | `left-to-right`, `right-to-left`, `top-to-bottom`, `bottom-to-top`, `vertical`, `horizontal`, `none` | `_set_code_direction_hint` |
| `arucoDictionaryPreset` | ArUco dictionary preset | `sc_barcode_scanner_settings_set_aruco_dictionary` |

Symbology names (case-insensitive; `sc_symbology_to_string` / `sc_symbology_from_string` convert): `ean13upca`, `ean8`, `upce`, `two-digit-add-on`, `five-digit-add-on`, `code128`, `code39`, `code93`, `code11`, `code25`, `code32`, `itf`, `iata2of5`, `matrix2of5`, `codabar`, `msi-plessey`, `databar`, `databar-expanded`, `databar-limited`, `qr`, `microqr`, `data-matrix`, `pdf417`, `micropdf417`, `aztec`, `maxicode`, `dotcode`, `aruco`, `royal-mail-4state` (`rm4scc` is still accepted as input), `kix`, `lapa4sc`, `usps-intelligent-mail`, `upu-4state`, `australian-post-4state`, `french-post`.

**Outdated keys:** `maxNumberOfCodesPerFrame` (removed in 8.0) is ignored, so multi-scan silently stays off; use `multiScanEnabled` + `maxNumLocationsToProcessPerFrame`. `codeCachingDuration` and `focusMode` were removed in 7.0 and 8.0. Write float values with a decimal point (`1.0`, not `1`).

## Add-on codes (EAN-2 / EAN-5)

Add-ons are separate small codes next to EAN-13/UPC-A, EAN-8 or UPC-E (price, issue number). The main code and its add-on are **two results** that you combine; an add-on is never returned on its own.

```c
#include <Scandit/ScBarcodeArray.h>
#include <Scandit/ScBarcode.h>
/* EAN-13/UPC-A with 2- and 5-digit add-ons: the main code and the add-on are separate results. */
void enable_add_ons(ScBarcodeScannerSettings *settings) {
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_EAN13_UPCA, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_TWO_DIGIT_ADD_ON, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_FIVE_DIGIT_ADD_ON, SC_TRUE);
    sc_barcode_scanner_settings_set_multi_scan_enabled(settings, SC_TRUE);          /* "tracking" feature */
    sc_barcode_scanner_settings_set_max_num_locations_to_process_per_frame(settings, 2);
}

/* After each frame: print main code + add-on as one result. An add-on is never returned alone. */
void print_with_add_on(const ScBarcodeArray *codes) {
    const ScBarcode *main_code = NULL, *add_on = NULL;
    for (uint32_t i = 0; i < sc_barcode_array_get_size(codes); i++) {
        const ScBarcode *c = sc_barcode_array_get_item_at(codes, i);
        ScSymbology s = sc_barcode_get_symbology(c);
        if (s == SC_SYMBOLOGY_TWO_DIGIT_ADD_ON || s == SC_SYMBOLOGY_FIVE_DIGIT_ADD_ON) add_on = c;
        else if (s == SC_SYMBOLOGY_EAN13_UPCA) main_code = c;
    }
    if (main_code)
        printf("%s%s%s\n", sc_byte_array_get_string(sc_barcode_get_data(main_code)), add_on ? " + " : "",
               add_on ? sc_byte_array_get_string(sc_barcode_get_data(add_on)) : "");
}
```

Call `print_with_add_on` with the array from `sc_barcode_scanner_session_get_newly_recognized_codes` after each frame. A frame can contain only the main code (the add-on not yet readable); if every product has an add-on, wait for both before accepting a result. The older add-on page uses `sc_barcode_scanner_settings_set_max_number_of_codes_per_frame`, which no longer exists in 8.x: use the multi-scan calls above.

## Composite codes (GS1 CC-A, CC-B, CC-C)

| Type | 1D part | 2D part |
| --- | --- | --- |
| CC-A, CC-B | EAN/UPC, GS1-128 (Code 128) or GS1 DataBar family | MicroPDF417 |
| CC-C | GS1-128 (Code 128) | PDF417 |

```c
#include <Scandit/ScBarcode.h>
/* GS1 composite codes (CC-A/CC-B: EAN/UPC, GS1-128 or DataBar + MicroPDF417; CC-C: GS1-128 + PDF417). */
void enable_composites(ScBarcodeScannerSettings *settings) {
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_EAN13_UPCA, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_CODE128, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_GS1_DATABAR, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_GS1_DATABAR_EXPANDED, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_GS1_DATABAR_LIMITED, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_MICRO_PDF417, SC_TRUE);
    sc_barcode_scanner_settings_set_symbology_enabled(settings, SC_SYMBOLOGY_PDF417, SC_TRUE);
    sc_barcode_scanner_settings_set_multi_scan_enabled(settings, SC_TRUE);          /* "tracking" feature */
    sc_barcode_scanner_settings_set_max_num_locations_to_process_per_frame(settings, 2);
}

/* A 1D part flagged UNKNOWN/LINKED and a 2D part flagged GS1_A/B/C belong together:
   concatenate 1D data + 2D data into one GS1 element string. */
int is_composite_1d(const ScBarcode *c) {
    ScCompositeFlag f = sc_barcode_get_composite_flag(c);
    return f == SC_COMPOSITE_FLAG_UNKNOWN || f == SC_COMPOSITE_FLAG_LINKED;
}
int is_composite_2d(const ScBarcode *c) {
    ScCompositeFlag f = sc_barcode_get_composite_flag(c);
    return f == SC_COMPOSITE_FLAG_GS1_A || f == SC_COMPOSITE_FLAG_GS1_B || f == SC_COMPOSITE_FLAG_GS1_C;
}
```

Accumulate results until you have a 1D part (EAN/UPC or GS1-128 flagged UNKNOWN or LINKED, or DataBar flagged LINKED) and a 2D part (PDF417/MicroPDF417 flagged GS1_A, GS1_B or GS1_C), then concatenate the 1D data and the 2D data into one GS1 element string (parse it with parser.md).

## Where to look: areas, laser line, circle of interest

- **Search area** (`sc_barcode_scanner_settings_set_search_area`): only this part of the image is searched (1D and 2D).
- **Code location areas** per 1D/2D with a constraint: `SC_CODE_LOCATION_RESTRICT` (decode only there), `SC_CODE_LOCATION_HINT` (look there first; default) or `SC_CODE_LOCATION_IGNORE` (no preferred area: codes anywhere). Default 1D area: a centered horizontal strip (x 0, y 0.375, width 1, height 0.25); default 2D area: the whole image.
- **Direction hint** is in image coordinates: a camera mounted in portrait needs `SC_CODE_DIRECTION_BOTTOM_TO_TOP` (or `VERTICAL`) for horizontal codes. Use `SC_CODE_DIRECTION_NONE` for unknown orientation and for fixed-focus cameras.

```c
/* "Laser line": decode 1D codes only in a horizontal strip through the middle of the image,
   and keep 2D codes on the whole image. Coordinates are relative (0..1), origin top-left. */
void laser_line(ScBarcodeScannerSettings *settings) {
    sc_barcode_scanner_settings_set_code_location_area_1d(settings, sc_rectangle_f_make(0.0f, 0.45f, 1.0f, 0.1f));
    sc_barcode_scanner_settings_set_code_location_constraint_1d(settings, SC_CODE_LOCATION_RESTRICT);
    sc_barcode_scanner_settings_set_code_direction_hint(settings, SC_CODE_DIRECTION_HORIZONTAL);
    sc_barcode_scanner_settings_set_code_location_area_2d(settings, sc_rectangle_f_make(0.0f, 0.0f, 1.0f, 1.0f));
    sc_barcode_scanner_settings_set_code_location_constraint_2d(settings, SC_CODE_LOCATION_HINT);
}

/* Only codes that touch a circle around the image center (radius relative to the image),
   closest to the center first. A negative radius or SC_CIRCLE_RADIUS_INFINITE makes it a hint only. */
void center_circle(ScBarcodeScannerSettings *settings) {
    sc_barcode_scanner_settings_set_circle_of_interest(settings, sc_point_f_make(0.5f, 0.5f), 0.2f);
}
```

## Symbol counts, inverted codes, extensions, checksums

```c
void symbology_options(ScBarcodeScannerSettings *settings) {
    /* Code 128 with 18 to 24 symbols only (symbol count = characters + start + check + stop). */
    ScSymbologySettings *code128 = sc_barcode_scanner_settings_get_symbology_settings(settings, SC_SYMBOLOGY_CODE128);
    sc_symbology_settings_set_enabled(code128, SC_TRUE);
    uint16_t counts[] = {18, 19, 20, 21, 22, 23, 24};
    sc_symbology_settings_set_active_symbol_counts(code128, counts, sizeof counts / sizeof counts[0]); /* elements, not bytes */

    /* Light-on-dark Data Matrix as well as dark-on-light, plus direct part marks. */
    ScSymbologySettings *dm = sc_barcode_scanner_settings_get_symbology_settings(settings, SC_SYMBOLOGY_DATA_MATRIX);
    sc_symbology_settings_set_enabled(dm, SC_TRUE);
    sc_symbology_settings_set_color_inverted_enabled(dm, SC_TRUE);
    sc_symbology_settings_set_extension_enabled(dm, "direct_part_marking_mode", SC_TRUE);

    /* ITF with a mandatory mod-10 check digit. */
    ScSymbologySettings *itf = sc_barcode_scanner_settings_get_symbology_settings(settings, SC_SYMBOLOGY_INTERLEAVED_2_OF_5);
    sc_symbology_settings_set_enabled(itf, SC_TRUE);
    sc_symbology_settings_set_checksums(itf, SC_CHECKSUM_MOD_10);
}
```

- Symbol counts are ignored for EAN/UPC and 2D codes; codes outside the active range are **not returned** (a common reason for "short or long codes don't scan"). Pass the number of elements, not bytes. How to count per symbology: api-reference.md, section 6.
- Since 8.5 Code 128 accepts 4 symbols and more by default (before: 6); restrict the counts if very short codes cause false reads.
- Color inversion covers light-on-dark codes; enable it in addition to the normal polarity when both occur. It is on by default only for QR and MicroQR, and not supported for every symbology (api-reference.md).
- Python: `sym = settings.symbologies[sc.SYMBOLOGY_CODE128]`, then `sym.enabled = True`, `sym.active_symbol_counts = [18, 19, 20]`, `sym.color_inverted_enabled = True`, `sym.set_extension_enabled("direct_part_marking_mode", True)`. Checksums and the OCR-fallback regex aren't in the 8.6 Python bindings: use JSON (`sc.BarcodeScannerSettings.from_json`) for those.

## OCR fallback

Reads the printed human-readable text when the bars can't be decoded (EAN-13/UPC-A, Code 128, Code 39, Codabar).

```c
/* OCR fallback: read the human-readable text when the bars of a Code 128 can't be decoded.
   Needs the SINGLE_CODE_HAND_HELD preset, the OCR resources from the package and the license feature. */
ScBarcodeScannerSettings *ocr_fallback_settings(void) {
    ScBarcodeScannerSettings *settings = sc_barcode_scanner_settings_new_with_preset(SC_PRESET_SINGLE_CODE_HAND_HELD);
    ScSymbologySettings *code128 = sc_barcode_scanner_settings_get_symbology_settings(settings, SC_SYMBOLOGY_CODE128);
    sc_symbology_settings_set_enabled(code128, SC_TRUE);
    sc_symbology_settings_set_extension_enabled(code128, "ocr_fallback", SC_TRUE);
    sc_symbology_settings_set_ocr_fallback_regex(code128, "^[A-Z]{2}[0-9]{9}$");   /* must match the whole text */
    return settings;
}
```

Requirements: `SC_PRESET_SINGLE_CODE_HAND_HELD` (smart scan intention), the OCR models in `/usr/share/scanditsdk/resources` (missing models give status 28), and the license feature (status 29 otherwise). It triggers after a code has been stationary for about a second. Without a regex, Code 128/39 OCR results are limited to alphanumeric text.

## GS1 data

Check `sc_barcode_is_gs1_data_carrier`, read the raw data (`sc_barcode_get_data`) and split it with the GS1 parser (parser.md). Don't strip the GS separators. Typical encoding mistakes on labels: a leading GS in a Data Matrix encoded in byte mode, or the human-readable "(01)…" text encoded in a plain Data Matrix.

## Split codes (structured append)

Some symbologies can spread a message over several codes (DotCode since 8.6). Each part reports its segment:

```c
/* Structured append (a message split over several codes): collect segments by file id. */
void print_segment(const ScBarcode *c) {
    int32_t count = sc_barcode_get_segment_count(c);   /* -1 if the code isn't part of a split message */
    if (count <= 1) return;
    printf("file %s: segment %d of %d: %s\n", sc_barcode_get_file_id(c),   /* owned by the barcode */
           sc_barcode_get_segment_index(c) + 1, count, sc_byte_array_get_string(sc_barcode_get_data(c)));
}
```

Collect all parts with the same file id, order them by segment index and concatenate the data once all `count` segments are there.

