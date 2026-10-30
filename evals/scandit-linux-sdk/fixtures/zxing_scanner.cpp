// zxing_scanner.cpp - reads Data Matrix and QR codes from part photos with zxing-cpp 2.x.
#include <cstdio>
#include <string>
#include <vector>
#include "ZXing/ReadBarcode.h"

std::vector<std::string> read_codes(const unsigned char *gray, int width, int height, int stride) {
    ZXing::ImageView image(gray, width, height, ZXing::ImageFormat::Lum, stride);
    ZXing::ReaderOptions options;
    options.setFormats(ZXing::BarcodeFormat::DataMatrix | ZXing::BarcodeFormat::QRCode);
    options.setTryHarder(true);
    options.setTryRotate(true);
    options.setTryInvert(true);
    std::vector<std::string> texts;
    for (const auto &barcode : ZXing::ReadBarcodes(image, options))
        texts.push_back(barcode.text());
    return texts;
}
