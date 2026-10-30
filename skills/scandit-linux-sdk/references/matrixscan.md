# MatrixScan on Linux: tracking many barcodes per frame (object tracker)

*Based on the [Linux overview](https://docs.scandit.com/sdks/linux/overview/#multi-barcode-scanning-and-tracking), the [C API reference](https://docs.scandit.com/stable/c_api/annotated.html) and the bundled `CommandLineMatrixScanCameraSample.c` / `opencv_py_demo/OpenCvPyTrackingSample.py`.*

## When to use what

| Need | Use |
| --- | --- |
| One code at a time, or the first code in view | `ScBarcodeScanner` (integration.md) |
| Several codes in **one** image or frame, results per frame | `ScBarcodeScanner` with multi-scan (`sc_barcode_scanner_settings_set_multi_scan_enabled` + `sc_barcode_scanner_settings_set_max_num_locations_to_process_per_frame`) |
| Many codes in a **video stream**, each with a stable ID and position from frame to frame (counting, AR overlays, "has this box been read yet?") | `ScObjectTracker` (this guide) |

Both multi-scan and the object tracker need a license key with the **"tracking"** (MatrixScan) feature. Without it, `process_frame` returns a status in the unlicensed-feature range (255–512) whose message names the missing feature.

## Integration flow

Ask the user only what isn't clear: language (C or Python), input (V4L2 camera or their own frames: see capture-pipelines.md), the symbologies, and which file to integrate into. Then write the code into that file, following the bundled sample named under "Starting points" below, and show the setup checklist from integration.md, adding: "**the license key needs the tracking (MatrixScan) feature**".

## How the tracker works

- `sc_object_tracker_new(context)` creates a tracker (enabled by default; `sc_object_tracker_set_enabled` pauses it). It needs **no `ScBarcodeScanner`**: pass the scanner settings with `sc_object_tracker_apply_scanner_settings(tracker, settings)`.
- For tracking, set the code location constraints to `SC_CODE_LOCATION_IGNORE` (codes are everywhere in the frame, not only in the default center strip), and keep the duplicate filter off.
- Process frames exactly as for scanning: one frame sequence for the stream, `sc_recognition_context_process_frame` per frame.
- After each frame, `sc_object_tracker_session_get_tracked_objects(sc_object_tracker_get_session(tracker))` returns an `ScTrackedObjectMap` of everything currently tracked. Release the map with `sc_tracked_object_map_release` after each frame.
- Iterate with `sc_tracked_object_map_get_size` and `sc_tracked_object_map_get_ids`, look objects up with `sc_tracked_object_map_get_item_at(map, id)`.
- Per object: `sc_tracked_object_get_id`, `sc_tracked_object_get_location` (an `ScQuadrilateral` in image pixels, follows the code as it moves) and `sc_tracked_object_get_barcode` (NULL if the object isn't a barcode; otherwise **release it with `sc_barcode_release`**).
- **IDs** are stable while an object stays tracked. Once an object is lost, its ID may be reused for another object; if you count items, key them by data (and position) as well as ID.
- The session belongs to the tracker. Release the tracker before the context; `sc_object_tracker_release` is the one call that may happen from any thread.
- Python: `sc.ObjectTracker(context, settings)`, then `tracker.session.tracked_objects` (a map: `.items()`, `.keys()`, `len()`, `[id]`), and per object `obj.id`, `obj.location`, `obj.get_barcode()`.

## Starting points

- **C, V4L2 camera:** the bundled `samples/CommandLineMatrixScanCameraSample.c` (run: `./CommandLineMatrixScanCameraSample /dev/video0 1920 1080`). It shows the whole loop: tracker creation, `apply_scanner_settings`, the frame sequence, reading and releasing the tracked-object map per frame, and the teardown order.
- **Python, OpenCV frames with drawn outlines:** the bundled `samples/opencv_py_demo/OpenCvPyTrackingSample.py`. Set the image stride with `descr.set_plane_row_bytes(0, frame.strides[0])` (the 8.x bindings have no `first_plane_row_bytes` property).
- **Your own frames** (GStreamer, libcamera, a vendor SDK): describe the buffer as in [capture-pipelines.md](capture-pipelines.md) and process it with the tracker exactly as the sample does; the tracker needs no `ScBarcodeScanner`.

When integrating into the user's file, keep the sample's call order and the settings from "How the tracker works" above.

## Tips

- Resolution: FullHD is the usual starting point; small codes far away need more pixels per module (code-readability.md), not a different tracker setting.
- Enable only the symbologies on your labels; each extra symbology costs time in every frame.
- Low-resolution QR enhancements (8.5) are disabled for MatrixScan modes since 8.5.3 / 8.6.0.
- To overlay results, draw the location quadrilaterals onto the same frame you passed to `process_frame` (same coordinates, origin top-left).
