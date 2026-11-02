"""pyzbar_scanner.py - document intake: finds the barcodes on scanned delivery notes.
Other modules call find_codes(path) and use .data, .type and .rect of each result.
"""
from PIL import Image
from pyzbar.pyzbar import ZBarSymbol, decode


def find_codes(path):
    image = Image.open(path).convert("L")
    image = image.point(lambda p: 255 if p > 128 else 0)  # binarize, helps pyzbar on faint prints
    return decode(image, symbols=[ZBarSymbol.CODE128, ZBarSymbol.EAN13, ZBarSymbol.QRCODE])


if __name__ == "__main__":
    import sys
    for result in find_codes(sys.argv[1]):
        print(result.type, result.data.decode(), result.rect)
