# Parser on Linux: GS1, HIBC, AAMVA, MRTD, Swiss QR, VIN, US USID

*Based on the [C API reference](https://docs.scandit.com/stable/c_api/annotated.html) (`ScParser`, `ScParserResult`) and the bundled `ParsingLibrarySample.c`.*

The parser turns the raw data of a decoded code into named fields. It is a separate license feature: `sc_parser_new_with_context` returns NULL (and fills the status) when the key doesn't include it.

## Parser types (`ScParserType`)

| Type | Value | Data |
| --- | --- | --- |
| `SC_PARSER_TYPE_GS1_AI` | 1 | GS1 application identifiers (GS1-128, GS1 DataMatrix, GS1 QR, DataBar, composite codes) |
| `SC_PARSER_TYPE_HIBC` | 2 | Health Industry Bar Code |
| `SC_PARSER_TYPE_DLID` | 3 | AAMVA driver's license / ID (PDF417 on North American IDs) |
| `SC_PARSER_TYPE_MRTD` | 4 | Machine-readable zone of travel documents (from OCR or another source) |
| `SC_PARSER_TYPE_SWISSQR` | 5 | Swiss QR bill |
| `SC_PARSER_TYPE_VIN` | 6 | Vehicle identification number |
| `SC_PARSER_TYPE_US_USID` | 7 | US Uniformed Services ID |

## Integration flow

Ask which data format the user needs to parse (and where the data comes from: a code scanned with the SDK, or a string from elsewhere), then add the parser to the file that handles the scan results, following the example below. The parser is created once from the same context as the scanner and reused for every code. Remind the user that the license key needs the parser feature.

## API

- `ScParser *sc_parser_new_with_context(ScRecognitionContext *ctx, ScParserType type, ScContextStatus *status)`: `status` may be NULL; if you pass one, free it with `sc_context_status_free` (by value).
- `ScBool sc_parser_parse_string(parser, const char *data, size_t length, ScParserResult **result)`: returns `SC_FALSE` if the data couldn't be parsed; the reason is in `sc_parser_result_get_error_message(result)`. Free the result with `sc_parser_result_free` in both cases.
- Fields: `sc_parser_result_get_fields_count`, `sc_parser_result_get_field_by_index`, `sc_parser_result_get_field_by_name(result, "01")`. Per field: `sc_field_get_name`, `sc_field_get_string_value`, `sc_field_get_json_values` (structured value), `sc_field_get_issues_count` / `sc_field_get_issue` (problems found in that field). The whole result as JSON: `sc_parser_result_get_json_values`.
- **Every `ScByteArray` the parser returns must be freed with `sc_byte_array_free`** (names, values, JSON, error messages).
- `sc_parser_set_options(parser, json, length)` returns an `ScByteArray` with an error message, or a NULL string if there was no error; free it with `sc_byte_array_free`.
- Free the parser with `sc_parser_free` before releasing the context.
- Pass the **raw** barcode data: `sc_barcode_get_data(code)` with `sc_byte_array_get_data` / `sc_byte_array_get_size`. In GS1 data, variable-length fields end with the group separator GS (0x1D); don't strip it, and don't feed the human-readable "(01)…" text.
- The 8.6 Python bindings have no parser class; parse in C, or pass the data to a GS1 library of your choice.

## Complete example (C)

```c
/* parse_gs1.c - split GS1 element strings into application identifiers with the Scandit parser (8.x).
 * Needs a license key with the parser feature.
 * Build: gcc -O2 -std=c99 -o parse_gs1 parse_gs1.c -lscanditsdk
 * Run:   ./parse_gs1
 */
#include <stdio.h>
#include <string.h>
#include <Scandit/ScRecognitionContext.h>
#include <Scandit/ScParser.h>
#include <Scandit/ScParserResult.h>
#include <Scandit/ScByteArray.h>

#ifndef SCANDIT_SDK_LICENSE_KEY
#define SCANDIT_SDK_LICENSE_KEY "-- INSERT YOUR LICENSE KEY HERE --"
#endif
#define SCANDIT_WRITABLE_DATA_PATH "/tmp"

int main(void) {
    ScRecognitionContext *ctx =
            sc_recognition_context_new(SCANDIT_SDK_LICENSE_KEY, SCANDIT_WRITABLE_DATA_PATH, NULL);
    if (!ctx) { fprintf(stderr, "context creation failed\n"); return 1; }

    /* NULL if the license doesn't include the parser; the status says why. */
    ScContextStatus status;
    ScParser *parser = sc_parser_new_with_context(ctx, SC_PARSER_TYPE_GS1_AI, &status);
    if (!parser) {
        fprintf(stderr, "parser: status %d: %s\n", (int)status.flag, sc_byte_array_get_string(status.message));
        sc_context_status_free(status);
        sc_recognition_context_release(ctx);
        return 1;
    }
    sc_context_status_free(status);

    /* Raw barcode data: variable-length AIs end with the GS separator (0x1D, "\035"). */
    const char *data = "010031234567890621123456789012\035300144";
    ScParserResult *result = NULL;
    int ok = sc_parser_parse_string(parser, data, strlen(data), &result) == SC_TRUE;
    if (!ok) {
        ScByteArray msg = sc_parser_result_get_error_message(result);
        fprintf(stderr, "parsing failed: %s\n", sc_byte_array_get_string(msg));
        sc_byte_array_free(msg);
    } else {
        size_t n = sc_parser_result_get_fields_count(result);
        for (size_t i = 0; i < n; i++) {
            const ScField *field = sc_parser_result_get_field_by_index(result, i);
            ScByteArray name = sc_field_get_name(field);
            ScByteArray value = sc_field_get_string_value(field);
            printf("AI %s = %s\n", sc_byte_array_get_string(name), sc_byte_array_get_string(value));
            sc_byte_array_free(name);                 /* every ScByteArray from the parser is freed */
            sc_byte_array_free(value);
        }
        ScByteArray json = sc_parser_result_get_json_values(result);   /* all fields as JSON */
        printf("%s\n", sc_byte_array_get_string(json));
        sc_byte_array_free(json);
    }

    sc_parser_result_free(result);
    sc_parser_free(parser);                           /* before the context */
    sc_recognition_context_release(ctx);
    return ok ? 0 : 1;
}
```

Expected output for the sample data: AI `01` = `00312345678906`, AI `21` = `123456789012`, AI `30` = `0144`, followed by the JSON form.

To parse what the scanner decoded, use the code's data directly:

```c
ScByteArray raw = sc_barcode_get_data(code);
if (sc_barcode_is_gs1_data_carrier(code)) {
    ScParserResult *parsed = NULL;
    if (sc_parser_parse_string(parser, (const char *)sc_byte_array_get_data(raw),
                               sc_byte_array_get_size(raw), &parsed)) {
        /* read fields as above */
    }
    sc_parser_result_free(parsed);
}
```
