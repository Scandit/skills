---
name: scandit-linux-sdk
description: Scandit Linux SDK (C/C++ API and Python bindings, x86_64/arm64): barcode scanning from images, V4L2 cameras or your own frames (OpenCV, GStreamer), MatrixScan tracking, parser, barcode generator. Use for integration, settings and JSON, troubleshooting status codes, SDK upgrades (7→8), replacing ZBar/pyzbar, ZXing, libdmtx or OpenCV, and why a code doesn't scan (pixels per module, camera/lens/distance, blur, print quality). Linux only.
license: Apache-2.0
metadata:
  author: scandit
  version: "1.0.0"
---

# Scandit Linux SDK Skill

The Linux SDK is a low-level C API (usable from C++) with Python bindings (`scanditsdk.py`). There is no UI and no stream management: the app passes image buffers in and reads decoded codes from a session. Debian packages for amd64 and arm64 (Jetson, Raspberry Pi 4/5). This skill covers the **Linux SDK only**; for iOS, Android, Web or cross-platform frameworks, say it doesn't apply and point to https://docs.scandit.com.

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The C API changed significantly in **7.0** and **8.0**: functions were removed, renamed or changed signature, and old names don't compile.

**Always verify APIs against the references in this skill before writing or suggesting code.** Do not rely on memorized function signatures, parameters, enum values, JSON keys or Python property names. If you cannot find an API in the provided references, fetch the C API reference before responding.

Linux gotchas worth flagging:
1. **All symbologies are disabled by default.** Settings only take effect after `sc_barcode_scanner_apply_settings`, which returns an `ScContextStatus` to check and free.
2. **Multi-scan is off by default** (`sc_barcode_scanner_settings_set_multi_scan_enabled`, JSON `multiScanEnabled`) and needs the "tracking" license feature. The old JSON key `maxNumberOfCodesPerFrame` is **silently ignored** in 8.x.
3. `sc_context_status_free` and `sc_process_frame_result_free` take the struct **by value**. `status.message` is an `ScByteArray`: print it with `sc_byte_array_get_string`.
4. **One scanner per context** (`sc_barcode_scanner_new` returns NULL for a second one) and one context per process. Not thread-safe: all calls for a context on one thread.
5. **Release everything created from a context before the context.** Session getters transfer ownership (`sc_barcode_array_release`); `sc_tracked_object_get_barcode` needs `sc_barcode_release`.
6. **License status 15 (app ID):** on Linux the app ID is the executable name, so `python3` for Python scripts. A bad key doesn't fail context creation; it shows up as a status from `apply_settings` or `process_frame`.
7. **Single images:** `SC_PRESET_HIGH_EFFORT`, a new frame sequence per image, duplicate filter off, codes anywhere (`SC_CODE_LOCATION_IGNORE`, direction hint NONE). **Video:** one frame sequence for the whole stream.
8. **Camera:** check discrete vs stepwise resolution mode, request a real sensor mode, and call `sc_camera_enqueue_frame_data` for every frame.
9. **Python bindings are plain classes:** assigning a misspelled property (e.g. `descr.memory_size`, `descr.first_plane_row_bytes`) silently creates an attribute and does nothing. Use `set_plane_row_bytes`. The 8.6 bindings have no parser class.
10. **glibc:** since 7.0 the SDK requires glibc 2.31 or newer (Ubuntu 20.04, Debian 11 or newer). On older systems it fails at link or load time (e.g. `undefined reference to ...@GLIBC_2.29`); check with `ldd --version`.

## Intent Routing

Based on the user's request, load the matching reference before responding:

- **Integrating barcode scanning from scratch** in C, C++ or Python: single images or files, a V4L2 camera, or frames from your own capture code; "add Scandit to my Linux app", "write a scanner", "scan from /dev/video0" → read [references/integration.md](references/integration.md) and follow its integration flow.
- **Frames from OpenCV, GStreamer, libcamera, a vendor camera SDK, NV12/YUYV buffers, or a C++ wrapper** → [references/capture-pipelines.md](references/capture-pipelines.md) (together with integration.md).
- **Scanning and tracking many codes per frame (MatrixScan, object tracker, IDs across frames)** → [references/matrixscan.md](references/matrixscan.md).
- **Parsing GS1, HIBC, AAMVA driver's license (DLID), MRTD, Swiss QR, VIN or US USID data** → [references/parser.md](references/parser.md).
- **Generating barcode images** → [references/barcode-generator.md](references/barcode-generator.md).
- **Configuring scanning:** JSON settings, add-on and composite codes, GS1, search area / "laser line", circle of interest, inverted codes, symbol counts, extensions, OCR fallback, structured append → [references/advanced.md](references/advanced.md); exact names and values in [references/api-reference.md](references/api-reference.md).
- **Upgrading or migrating an existing Scandit integration** ("upgrade to 8.x", "sc_barcode_scanner_new_with_settings doesn't exist", "what changed between versions") → read [references/migration.md](references/migration.md) and follow it.
- **Replacing ZBar/pyzbar, ZXing/zxing-cpp, libdmtx/pylibdmtx or OpenCV's detectors** → read [references/third-party-migration.md](references/third-party-migration.md) and follow it.
- **Something fails:** install, status codes, nothing or the wrong thing scans, camera, buffers, performance, crashes, worse after an upgrade → [references/troubleshooting.md](references/troubleshooting.md), then the workflow below.
- **Why a visible code doesn't scan:** pixels per module (PPM), camera/lens/distance planning, blur, contrast, geometry, print quality → [references/code-readability.md](references/code-readability.md) and the readability workflow below.
- **Exact API lookups:** status codes, presets, setters, JSON keys, symbology settings, image layouts, camera functions, release notes → [references/api-reference.md](references/api-reference.md). Grep for the section instead of loading the whole file.

## API Usage Policy

Only use APIs that are explicitly documented in this skill's references or the C API reference. Do not invent or guess function signatures, parameters, enum values, JSON keys or Python names. If unsure whether an API exists, or if a build fails, fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant documentation link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific API page:
1. First check whether a page you already fetched links to it directly. Always request links alongside content in your fetch prompt.
2. Otherwise fetch the C API index (https://docs.scandit.com/stable/c_api/annotated.html), extract the real link from it, and follow that.

Version notes: the references describe SDK **8.6**. The C API reference can describe a newer (pre-release) version, so an API listed there may not exist in the user's version. When the user's SDK is installed, the headers in `/usr/include/Scandit/` and the `scanditsdk.py` from their package are the final authority.

Python: the bindings wrap the C API, so concepts, call order, settings and status codes are the same. Use only Python names shown in the references or present in the user's `scanditsdk.py`.

## Licence key

Scanning needs a Scandit license key created for the **Linux** platform. The Scandit MCP server does not provision Linux keys, so:

1. The user creates the key in the Scandit dashboard at <https://ssl.scandit.com> (no account yet: <https://ssl.scandit.com/dashboard/sign-up?p=test> for a trial) and pastes it in.
   - On Linux the key's app ID is the **executable name** (the first element of the process command line: the binary's name, or `python3` for a Python script). A key with the wrong executable name gives status 15; a key without an executable name avoids that.
   - MatrixScan needs the "tracking" feature, the parser and the barcode generator need their features on the key.
2. **Then put the key into the code:** write it into the license-key constant in place of the placeholder (`SCANDIT_SDK_LICENSE_KEY` in C/C++, `LICENSE_KEY` in Python; placeholder `-- INSERT YOUR LICENSE KEY HERE --`, as in the bundled samples). Show at most a masked preview in chat (first and last few characters); never print a full key. Do not search the project, its files or the environment for a key. The key ends up as a literal in the source, so remind the user to keep non-trial keys out of version control.

## Workflow: something fails

1. Ask only for what's missing: SDK version (`sc_get_information_string(SC_INFORMATION_KEY_SDK_VERSION)`), architecture, language, the status code **and** message, the effective settings (`sc_barcode_scanner_settings_as_json`), and what changed.
2. Go through the matching section of [references/troubleshooting.md](references/troubleshooting.md). For "worse after upgrading", check the release notes table in [references/api-reference.md](references/api-reference.md) first.
3. If a code is visible but doesn't decode, switch to the readability workflow.

## Workflow: why doesn't this code scan (readability)

1. **Collect the facts** in one message, only what is missing: symbology and data (or number of characters); the original full-resolution frame as passed to the SDK (not a screenshot or resized image), or its resolution; printed size or X-dimension; camera resolution, lens/field of view, distance, angle (for setups); single images or video, SDK version, architecture.
2. **Calculate PPM** with `scripts/ppm_calc.py`:
   - From an image: `python3 scripts/ppm_calc.py ppm <symbology> --chars N --pixels P` (also `qr --version V`, `datamatrix --size S`, `section --section-modules M`; for Codabar and Code 11 use `--data <content>`). P = width from first to last bar, without the quiet zone, on the original frame.
   - From what the SDK reports for a decoded code: `python3 scripts/ppm_calc.py location --corners x1,y1 x2,y2 x3,y3 x4,y4 --modules-x N [--modules-y M] [--stacked]` (see `### 2.2` of code-readability.md).
   - Code not decoded: check whether it is at least localized (`### 2.2`); if not, measure by hand with the fixed patterns in `### 2.2`. For 1D also `python3 scripts/ppm_calc.py profile <frame.png> --from X,Y --to X,Y [--modules N]`.
   - From a setup: `python3 scripts/ppm_calc.py plan --res-px W --hfov DEG --distance-mm D --x-mm X [--angle A]`, or `--target-ppm T` for the maximum distance; `--sensor-mm` and `--focal-mm` instead of `--hfov` when the lens is known.
   - Without code execution, apply the formulas in `### 2.2`, `### 2.3`, `### 2.5`, show the steps, and check the counting against the examples under the table in `### 2.3`. Pixel widths estimated by viewing an image are estimates: say so.
3. **Check the other causes** in `## 3.` of code-readability.md that fit the symptoms.
4. **Answer:** the most likely cause with numbers (e.g. "about 1.5 pixels per module; 2–4 is needed"); the top 1–3 improvements with targets (e.g. "the code needs to span about 780 px"); "calculate it yourself" steps if useful; what to send next if facts are missing. Be honest about physical limits (optics, print, image quality).

## When to hand over to Scandit support

Recommend support@scandit.com with the original frames, settings JSON, SDK version and architecture (see the last section of troubleshooting.md) when: a code doesn't scan at ≥ 3 PPM, sharp, good contrast and correct settings; an image scanned with an earlier SDK version and not with a newer one; a crash reproduces with a minimal program; or a license or feature question needs the account. Don't ask users to post images that may contain personal data in public places, and never a full license key.

## References

| Topic | Resource |
|---|---|
| Overview, concepts (memory rules, coordinates, performance, threading) | [Linux overview](https://docs.scandit.com/sdks/linux/overview/) |
| Install and samples | [Installation](https://docs.scandit.com/sdks/linux/add-sdk/) · [Samples](https://docs.scandit.com/sdks/linux/samples/) |
| Barcode scanning configuration | [Configure with JSON](https://docs.scandit.com/sdks/linux/barcode-capture/configure-with-json/) · [Add-on codes](https://docs.scandit.com/sdks/linux/barcode-capture/add-on-codes/) · [Composite codes](https://docs.scandit.com/sdks/linux/barcode-capture/composite-codes/) · [Symbologies](https://docs.scandit.com/sdks/linux/barcode-symbologies/) |
| Barcode generation | [Barcode Generator](https://docs.scandit.com/sdks/linux/barcode-generator/) |
| Versions and changes | [Release notes](https://docs.scandit.com/sdks/linux/release-notes/) |
| Full API reference | [C API reference](https://docs.scandit.com/stable/c_api/annotated.html) |
| System requirements | [System requirements (Linux)](https://docs.scandit.com/sdks/web/system-requirements/#linux) |
