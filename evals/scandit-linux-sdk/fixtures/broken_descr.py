"""broken_descr.py - adapted from the OpenCV Python sample; processing fails or finds nothing."""
import tempfile

import cv2
import scanditsdk as sc

frame = cv2.imread("label.png")  # BGR
descr = sc.ImageDescription()
descr.width = frame.shape[1]
descr.height = frame.shape[0]
descr.first_plane_row_bytes = 3 * frame.shape[1]
descr.layout = sc.IMAGE_LAYOUT_BGR_8U
descr.memory_size = 3 * frame.shape[0] * frame.shape[1]

context = sc.RecognitionContext("-- INSERT YOUR LICENSE KEY HERE --", tempfile.gettempdir())
settings = sc.BarcodeScannerSettings(preset=sc.PRESET_HIGH_EFFORT)
settings.enable_symbology(sc.SYMBOLOGY_CODE128, True)
scanner = sc.BarcodeScanner(context)
scanner.apply_settings(settings)
seq = context.start_new_frame_sequence()
result = seq.process_frame(descr, frame.__array_interface__["data"][0])
seq.end()
print(result.flag, result.message, len(scanner.session.newly_recognized_codes))
