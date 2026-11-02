# Fixtures for the scandit-linux-sdk evals

| File | Used by | Builds against SDK 8.x? |
| --- | --- | --- |
| `EmptyScanner.c` | integration (C single image), licence key | yes (no Scandit calls yet) |
| `empty_scanner.py` | integration (Python camera), MatrixScan Python | yes (py_compile) |
| `opencv_app.cpp` | integration (C++ OpenCV) | yes, with OpenCV 4 |
| `gst_pipeline.c` | integration (GStreamer NV12) | yes, with GStreamer 1.x |
| `ScannerV7.c` | migration 7 → 8 | **no, on purpose**: 7.x API |
| `ScannerV5.c` | migration 5.x → 8 | **no, on purpose**: 5.x API |
| `ScannerWrapper.h` / `ScannerWrapper.c` | migration with a frozen wrapper API | header yes; `.c` **no, on purpose** (7.x API) |
| `settings_v7.json` | migration of JSON settings | loads, but outdated keys are ignored (that's the point) |
| `pyzbar_scanner.py`, `zbar_scanner.c`, `zxing_scanner.cpp`, `opencv_qr.py` | third-party migration | inputs for other libraries; not built here |
| `broken_descr.py` | troubleshooting (Python silent attributes) | runs, but sets non-existent properties (that's the point) |

All fixtures use the placeholder `-- INSERT YOUR LICENSE KEY HERE --`; never put a real key here.
