"""empty_scanner.py - shelf-camera kiosk: should print every barcode seen by the USB camera."""
import sys


def main(device: str) -> int:
    # TODO: open the camera and scan barcodes with the Scandit SDK
    print(f"would scan from {device}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/dev/video0"))
