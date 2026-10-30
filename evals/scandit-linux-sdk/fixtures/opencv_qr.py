"""opencv_qr.py - reads QR codes from a webcam with OpenCV's QRCodeDetector."""
import cv2


def main():
    capture = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        ok, texts, points, _ = detector.detectAndDecodeMulti(frame)
        if ok:
            for text in texts:
                if text:
                    print("QR:", text)
    capture.release()


if __name__ == "__main__":
    main()
