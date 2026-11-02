/* zbar_scanner.c - reads EAN-13 and Code 128 from greyscale frames of a fixed camera (ZBar).
 * Build: gcc -O2 -o zbar_scanner zbar_scanner.c -lzbar
 */
#include <stdio.h>
#include <stdint.h>
#include <zbar.h>

static zbar_image_scanner_t *scanner;

void init_scanner(void) {
    scanner = zbar_image_scanner_create();
    zbar_image_scanner_set_config(scanner, ZBAR_NONE, ZBAR_CFG_ENABLE, 0);
    zbar_image_scanner_set_config(scanner, ZBAR_EAN13, ZBAR_CFG_ENABLE, 1);
    zbar_image_scanner_set_config(scanner, ZBAR_CODE128, ZBAR_CFG_ENABLE, 1);
}

/* Called for every camera frame (8-bit grey, width*height bytes). */
int scan_frame(const uint8_t *gray, unsigned width, unsigned height) {
    zbar_image_t *image = zbar_image_create();
    zbar_image_set_format(image, zbar_fourcc('Y', '8', '0', '0'));
    zbar_image_set_size(image, width, height);
    zbar_image_set_data(image, gray, (unsigned long)width * height, NULL);
    int n = zbar_scan_image(scanner, image);
    for (const zbar_symbol_t *s = zbar_image_first_symbol(image); s; s = zbar_symbol_next(s))
        printf("%s: %s\n", zbar_get_symbol_name(zbar_symbol_get_type(s)), zbar_symbol_get_data(s));
    zbar_image_destroy(image);
    return n;
}

void shutdown_scanner(void) {
    zbar_image_scanner_destroy(scanner);
}
