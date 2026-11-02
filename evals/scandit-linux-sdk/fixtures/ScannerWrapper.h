/* ScannerWrapper.h - our team's scanner API. Used by 14 call sites in the warehouse app; must not change. */
#ifndef SCANNER_WRAPPER_H
#define SCANNER_WRAPPER_H
#include <stdint.h>

typedef struct scanner scanner_t;

typedef struct {
    char text[256];
    char symbology[32];
} scan_result_t;

/* Returns NULL on error and writes a message into err (size err_len). */
scanner_t *scanner_create(const char *data_dir, char *err, int err_len);
/* Scans one greyscale image; returns the number of results written (max max_results), -1 on error. */
int scanner_scan_gray(scanner_t *s, const uint8_t *pixels, uint32_t width, uint32_t height, uint32_t stride,
                      scan_result_t *results, int max_results);
void scanner_destroy(scanner_t *s);
#endif
