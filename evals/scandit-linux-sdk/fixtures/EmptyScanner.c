/* EmptyScanner.c - inspection station: reads one greyscale PGM image per run and should print
 * the barcodes in it. Build: gcc -O2 -std=c99 -o scanner EmptyScanner.c -lscanditsdk
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

/* Minimal reader for binary PGM (P5, maxval <= 255, no comment lines). */
static uint8_t *read_pgm(const char *path, uint32_t *w, uint32_t *h) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    int maxval = 0;
    if (fscanf(f, "P5 %u %u %d", w, h, &maxval) != 3 || maxval > 255) { fclose(f); return NULL; }
    fgetc(f);
    size_t n = (size_t)(*w) * (*h);
    uint8_t *px = malloc(n);
    if (px && fread(px, 1, n, f) != n) { free(px); px = NULL; }
    fclose(f);
    return px;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s image.pgm\n", argv[0]); return 2; }
    uint32_t w = 0, h = 0;
    uint8_t *pixels = read_pgm(argv[1], &w, &h);
    if (!pixels) { fprintf(stderr, "cannot read %s\n", argv[1]); return 2; }

    /* TODO: scan the image with the Scandit SDK and print each code */

    free(pixels);
    return 0;
}
