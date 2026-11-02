# Barcode generator on Linux

*Based on the [Barcode Generator guide](https://docs.scandit.com/sdks/linux/barcode-generator/), the [C API reference](https://docs.scandit.com/stable/c_api/annotated.html) (`ScBarcodeGenerator`) and the bundled `CommandLineBarcodeGeneratorSample.c` / `.py`.*

The generator renders data as a barcode image (RGBA). It is a license feature: without it, creating the generator fails with "Your license does not include the barcode generator".

**Symbologies:** Code 39, Code 128, EAN-13, UPC-A, ITF, QR, Data Matrix, and PDF417 (8.2+).

## Integration flow

Ask for the symbology, the data, the output (file format, size) and which file to add the generator to; then write the code into that file starting from the example below, and remind the user that the key needs the barcode generator feature.

## API

- `sc_barcode_generator_new(ctx, symbology, &error)` or `sc_barcode_generator_new_with_options(ctx, symbology, json_options, &error)`; change options later with `sc_barcode_generator_set_options(gen, json, &error)`. On failure the `ScError` holds a message: free it with `sc_error_free`.
- `ScImageBuffer *sc_barcode_generator_generate(gen, data, data_length, encoding, &error)`. `encoding` is an `ScEncodingArray` passed **by value** that says which bytes use which character encoding: `sc_encoding_array_new(1)` + `sc_encoding_array_assign(&enc, 0, "US-ASCII", 0, length)`, freed with `sc_encoding_array_free`.
- The result is RGBA (4 bytes per pixel): `image->data`, `image->description` (width, height, row bytes via `sc_image_description_get_plane_row_bytes`), `image->data_size`. Free it with `sc_image_buffer_free`.
- Free the generator with `sc_barcode_generator_free` before releasing the context.
- **The image has one pixel per module** plus a one-module margin (e.g. 23×23 px for a version-1 QR code with 21×21 modules). Scale it up by an integer factor with nearest-neighbour interpolation (no smoothing) before printing or displaying it, and add the quiet zone your print layout needs.
- **EAN-13 / UPC-A** (`SC_SYMBOLOGY_EAN13_UPCA`): pass 13 digits for EAN-13; 12 digits are read as EAN-13 data without the check digit (a UPC-A needs its leading zero).
- Python: `sc.BarcodeGenerator(context, symbology)`, `generator.set_options(dict)`, `generator.generate(text)` (ASCII text only) → `ImageBuffer` with `.description`, `.numpy_array`. Errors raise `RuntimeError`.

## Options (JSON)

| Symbology | Option | Values |
| --- | --- | --- |
| all | `foregroundColor`, `backgroundColor` | `[r, g, b, a]`, 0–255 |
| QR | `errorCorrectionLevel` | `"L"` (7 %), `"M"` (15 %, default), `"Q"` (25 %), `"H"` (30 %) |
| QR | `versionNumber` | 1–40; chosen automatically if not set (generation fails if too small for the data) |
| PDF417 | `errorCorrectionLevel` | 0–8 |
| PDF417 | `compact` | `true` / `false` |
| PDF417 | `compaction` | `"TEXT"`, `"BYTE"`, `"NUMERIC"`, `"AUTO"` |
| PDF417 | `dimensions` | `{"minCols": n, "maxCols": n, "minRows": n, "maxRows": n}`; incompatible values make encoding fail |

```json
{
    "errorCorrectionLevel": 3,
    "compact": true,
    "dimensions": { "minCols": 1, "maxCols": 3, "minRows": 2, "maxRows": 10 }
}
```

## Complete example (C)

Writes a binary PPM so no image library is needed (the bundled sample uses libpng instead).

```c
/* generate_code.c - render a barcode image with the Scandit barcode generator (8.x) and save it as PPM.
 * Needs a license key with the barcode generator feature.
 * Build: gcc -O2 -std=c99 -o generate_code generate_code.c -lscanditsdk
 * Run:   ./generate_code "Hello World" qr.ppm
 */
#include <stdio.h>
#include <string.h>
#include <Scandit/ScRecognitionContext.h>
#include <Scandit/ScBarcodeGenerator.h>
#include <Scandit/ScEncodingArray.h>
#include <Scandit/ScImageDescription.h>
#include <Scandit/ScCommon.h>

#ifndef SCANDIT_SDK_LICENSE_KEY
#define SCANDIT_SDK_LICENSE_KEY "-- INSERT YOUR LICENSE KEY HERE --"
#endif
#define SCANDIT_WRITABLE_DATA_PATH "/tmp"

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: %s data out.ppm\n", argv[0]); return 2; }
    const uint8_t *data = (const uint8_t *)argv[1];
    size_t length = strlen(argv[1]);

    ScRecognitionContext *ctx =
            sc_recognition_context_new(SCANDIT_SDK_LICENSE_KEY, SCANDIT_WRITABLE_DATA_PATH, NULL);
    if (!ctx) { fprintf(stderr, "context creation failed\n"); return 1; }

    /* Options are JSON; see the barcode generator guide for what each symbology accepts. */
    const char *options = "{\"foregroundColor\":[0,0,0,255],\"backgroundColor\":[255,255,255,255],"
                          "\"errorCorrectionLevel\":\"M\"}";
    ScError error = {0};
    ScBarcodeGenerator *gen = sc_barcode_generator_new_with_options(ctx, SC_SYMBOLOGY_QR, options, &error);
    if (!gen) {
        fprintf(stderr, "generator: %s\n", error.message);
        sc_error_free(&error);
        sc_recognition_context_release(ctx);
        return 1;
    }

    /* Which bytes use which character encoding: here all of it is ASCII. */
    ScEncodingArray encoding = sc_encoding_array_new(1);
    sc_encoding_array_assign(&encoding, 0, "US-ASCII", 0, length);
    ScImageBuffer *image = sc_barcode_generator_generate(gen, data, length, encoding, &error);
    int ok = image != NULL;
    if (!ok) {
        fprintf(stderr, "generate: %s\n", error.message);
        sc_error_free(&error);
    } else {
        /* The result is RGBA (4 bytes per pixel); rows can be padded, so use the row bytes. */
        uint32_t w = sc_image_description_get_width(image->description);
        uint32_t h = sc_image_description_get_height(image->description);
        uint32_t stride = sc_image_description_get_plane_row_bytes(image->description, 0);
        FILE *f = fopen(argv[2], "wb");
        ok = f != NULL;
        if (ok) {
            fprintf(f, "P6 %u %u 255\n", w, h);
            for (uint32_t y = 0; y < h; y++)                    /* binary PPM: RGB, alpha dropped */
                for (uint32_t x = 0; x < w; x++) fwrite(&image->data[(size_t)y * stride + x * 4], 1, 3, f);
            fclose(f);
            printf("wrote %s (%ux%u)\n", argv[2], w, h);
        }
        sc_image_buffer_free(image);
    }

    sc_encoding_array_free(encoding);
    sc_barcode_generator_free(gen);
    sc_recognition_context_release(ctx);
    return ok ? 0 : 1;
}
```

## Complete example (Python)

```python
"""generate_code.py - render a barcode image with the Scandit barcode generator (Python bindings, 8.x).

Needs a license key with the barcode generator feature.
Setup: pip install pillow numpy
Run:   python3 generate_code.py "Hello World" qr.png
"""
import sys

import scanditsdk as sc
from PIL import Image

LICENSE_KEY = "-- INSERT YOUR LICENSE KEY HERE --"
WRITABLE_DATA_PATH = "/tmp"


def main(data: str, out_path: str) -> int:
    context = sc.RecognitionContext(LICENSE_KEY, WRITABLE_DATA_PATH)
    try:
        generator = sc.BarcodeGenerator(context, sc.SYMBOLOGY_QR)  # RuntimeError if not licensed
        generator.set_options({
            "foregroundColor": [0, 0, 0, 255],
            "backgroundColor": [255, 255, 255, 255],
            "errorCorrectionLevel": "M",
        })
        image = generator.generate(data)  # ASCII input only in the Python bindings
    except RuntimeError as error:
        print(f"barcode generator: {error}")
        return 1

    width = image.description.width
    height = image.description.height
    stride = image.description.get_plane_row_bytes(0)
    # RGBA rows of `stride` bytes: reshape as (height, row bytes), then crop the padding.
    rows = image.numpy_array[: stride * height].reshape(height, stride)
    rgba = rows[:, : width * 4].reshape(height, width, 4)
    Image.fromarray(rgba.copy(), "RGBA").save(out_path)
    print(f"wrote {out_path} ({width}x{height})")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: python3 generate_code.py data out.png")
    sys.exit(main(sys.argv[1], sys.argv[2]))
```

Reshape the RGBA data as `(height, row bytes)`, not `(width, height)`: the two only coincide for square codes such as QR.

## Uses

- Clean reference codes for tests: generate a code, print or display it at a known size, and compare scan results across settings, distances and SDK versions.
- A pixels-per-module test series: generate a code once, scale it by integer factors (nearest neighbour), and display or print it at decreasing sizes to find the smallest size that scans reliably on your setup (code-readability.md).
