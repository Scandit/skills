# Why doesn't my code scan? Code readability and PPM guide for the Scandit Linux SDK

This guide explains, with numbers, why a barcode doesn't scan with the **Scandit Linux SDK** and how to fix it. It is based on our experience with Linux SDK customers (fixed industrial cameras, conveyors, vehicle-mounted cameras, static images). It applies to the Linux SDK only; other Scandit SDKs may behave differently.

---

## 1. The short answer

A camera-based scanner can only decode what the image shows. Nearly every "it doesn't scan" case comes down to one of these, in this order of likelihood:

1. **Too few pixels per module (PPM).** The narrowest bar or cell is only about 1 pixel wide in the image.
2. **Blur.** Focus, motion or exposure smear the module edges.
3. **Low contrast.** Bars and background are too close in brightness, or there is glare.
4. **Geometry.** The angle, perspective, curvature or lens distortion shrinks or bends the modules.
5. **The image pipeline.** Screenshots, resizing, compression, re-scanning or downscaled debug images change bar widths.
6. **The code itself.** Misprints, damage, a missing quiet zone, or a code that isn't to spec.
7. **Settings.** The symbology isn't enabled, the length is outside the allowed range, inverted codes aren't enabled, or multi-scan is off.
8. **One image instead of a video.** A single frame gets one chance. A video stream gets 30 per second.

If a code scans **sometimes**, it is almost always **borderline**: it sits right at the edge of the requirements, and small variations decide the result. That is expected behavior, not randomness in the SDK.

---

## 2. Pixels per module (PPM)

### 2.1 What it is

A **module** is the narrowest element of a barcode: the thinnest bar or space in a 1D code, or one cell in a 2D code. Its printed size is called the **X-dimension** (e.g. 0.33 mm or 13 mil). **PPM** is how many image pixels that module covers.

| PPM | What to expect |
| --- | --- |
| **≥ 3** | Robust, with margin for blur, angle and print variation. Recommended for production. |
| **2–3** | Robust range under good conditions. |
| **~1–2** | Borderline. Expect intermittent results. A different frame, SDK version or angle can flip the result. |
| **< 1** | Too little signal. Reads are unlikely and not reliable. |

- **2–4 PPM is the requirement for robust scanning, for all symbologies, 1D and 2D** (Code 128, Code 39, EAN/UPC, ITF, Data Matrix, QR, PDF417…).
- This range **already allows for typical motion blur**. It is not a "perfect conditions" number.
- More PPM than needed doesn't hurt decoding. 12–17 PPM is fine. Very large codes mainly cost processing time and field of view.

### 2.2 How to measure PPM in an image

**PPM = width of the code in pixels ÷ number of modules across it**

For 2D codes, use one side: **PPM = side length in pixels ÷ modules per side**.

Steps:

1. **Use the exact image the SDK processed.** Use the raw frame or buffer at full resolution, not a preview, a screenshot, a thumbnail or a resized debug PNG. A preview saved at 50% size halves the PPM you measure.
2. **Measure from the first bar to the last bar.** Don't include the white quiet zone. Tools:
   - **GIMP:** use the Measure tool and drag from the start of the first bar to the end of the last bar. Read "Distance" in pixels.
   - **macOS Preview:** draw a rectangular selection around the bars only. The size is shown in pixels.
   - **Python:** crop and inspect the array, or plot one row of pixel values across the code.
3. **Get the module count** from the table in 2.3.
4. **Divide.** If the code is rotated, measure along the code's own axis, not the image axis.
5. **Shortcut for long or variable codes:** measure a known section, such as a few characters or codewords, and divide by the modules in that section. Example: 2 PDF417 codewords = 2 × 17 = 34 modules spanning 340 px, so **10 PPM**.

To view raw camera buffers, convert them first. Example for a 1920×1080 UYVY frame:

```bash
ffmpeg -f rawvideo -pixel_format uyvy422 -video_size 1920x1080 -i frame.bin frame.png
# 8-bit grey: -pixel_format gray ; 16-bit grey: -pixel_format gray16le (save as .tiff)
```

**Let the SDK measure it (codes that do scan).** For every decoded code, the SDK reports where it is and how many modules it has. Together they give the PPM directly, which shows how much margin a code has before it starts to fail:

- `sc_barcode_get_location(barcode)` returns the four corners in pixels (Python: `barcode.location`).
- `sc_barcode_get_module_counts(barcode)` (C, since 7.5) returns:
  - 1D codes: x = modules along the code, y = -1
  - 2D codes: x and y = modules per side
  - stacked codes (PDF417, stacked DataBar): x = modules per row, y = number of rows
- **PPM ≈ length of the top (or bottom) edge in pixels ÷ x.**

```c
ScQuadrilateral q = sc_barcode_get_location(barcode);
ScPoint mc = sc_barcode_get_module_counts(barcode);
float top = hypotf(q.top_right.x - q.top_left.x, q.top_right.y - q.top_left.y);
printf("approx. PPM: %.2f\n", top / (float)mc.x);
```

Check the field names against the header of your SDK version. The location is approximate, so treat the result as an estimate. Logging it for every scan in a pilot shows quickly whether the setup runs at a comfortable 3+ PPM or close to the edge.

**Codes that are found but not decoded** have no module count. `sc_barcode_scanner_session_get_newly_localized_codes(session)` (Python: `session.newly_localized_codes`) returns their location, which tells you where to measure by hand. Expect some false localizations in this list.

**If the code isn't in the localized list either,** the SDK didn't find it at all. That usually means a severe problem in that area of the image: very low PPM, strong blur, very low contrast or glare, a code cut off at the frame edge, or a code outside the search area or circle of interest (check the settings in 3.6). Measure it by hand on the original frame:

1. **Find the code** in the original full-resolution frame and zoom to 400–800%.
2. **Measure along the code's own axis.** In GIMP, the Measure tool shows the distance and the angle, so rotated codes are fine. Measure from the start of the first bar to the end of the last bar, without the quiet zone.
3. **Get the module count.** As nothing decoded, you don't have the data from the SDK. Use one of these:
   - the human-readable text printed under the code, or the data the label should contain, with the table in 2.3
   - **a fixed pattern of known width**, which doesn't depend on the data:

| Symbology | Pattern | Modules |
| --- | --- | --- |
| EAN-13 / UPC-A | start guard (bar, space, bar) | 3 |
| EAN-13 / UPC-A | center guard (space, bar, space, bar, space) | 5 |
| EAN-13 / UPC-A | whole symbol, first to last guard bar | 95 |
| Code 128 / GS1-128 | stop pattern at the right end, including the final bar | 13 |
| Code 128 / GS1-128 | any single character (3 bars + 3 spaces) | 11 |
| PDF417 | start pattern at the left edge | 17 |
| QR | one finder square (corner pattern), outer edge to outer edge | 7 |
| Data Matrix | the alternating "clock" edge: count the cells | 1 per cell |

4. **Divide** the measured pixels by the modules of what you measured. For small patterns (3–13 modules), measure several and average, because one pixel of error changes the result a lot.
5. **Last resort: measure the narrowest bar directly.** Its width in pixels is roughly the PPM. This is coarse: at low PPM it snaps to whole pixels, and blur widens or merges thin bars.

The result is approximate, but it is enough to tell "about 1 PPM" from "about 3 PPM". That difference is what decides whether the image or the code itself needs to change.

### 2.3 Module counts per symbology

These counts follow the symbology standards and **exclude quiet zones**. `N` is the number of characters, `R` is the wide-to-narrow ratio (typically 2–3; 2.5 is a good default when unknown).

| Symbology | Modules across the symbol | Notes |
| --- | --- | --- |
| EAN-13 / UPC-A | **95** | Fixed |
| EAN-8 | **67** | Fixed |
| UPC-E | **51** | Fixed |
| Code 128 / GS1-128 | **11 × (N + 2) + 13** | N = symbol characters, including code-set switches and FNC1. In code set C, 2 digits = 1 character. Start, check and data are 11 modules each; stop is 13. |
| Code 39 | **(N + 2) × (3R + 6) + (N + 1) × gap** | N data characters plus the start and stop `*`. Each character has 3 wide and 6 narrow elements. Use a **1X** gap between characters (the standard minimum and the most common). Some printers use wider gaps, which adds a few modules (e.g. 2X). You can check it in the image: a 1X gap is as wide as a narrow bar. Add check characters to N if used. |
| Code 93 | **9 × (N + 4) + 1** | Start, stop and 2 check characters are 9 modules each, plus a 1-module termination bar |
| ITF / ITF-14 | **N × (2R + 3) + R + 6** | N digits (even). ITF-14 at R = 3 gives 135 |
| MSI Plessey | **12 × (N + checks) + 7** | 12 modules per digit; start 3, stop 4 |
| Codabar | **S × (2R + 5) + L × (3R + 4) + (S + L − 1) × gap** | Character widths differ. S = "standard" characters (0–9, `-`, `$`), L = "wide" characters (`:` `/` `.` `+` and the start/stop letters A–D, so at least 2). At R = 2.5 and a 1X gap that is 10 per standard and 11.5 per wide character, plus the gaps: `A12345B` = 79 modules. |
| Code 11 | **≈ 7 × N + 15** (lower bound) | N includes the check digit(s) C (and K). `0`, `9` and `-` have one wide element, all other digits two, so the exact width depends on the content: at R = 2, each `0`/`9`/`-` adds 7 modules and every other digit 8, plus 15 for start/stop. `12345` = 55 modules (the approximation gives 50). |
| PDF417 | **17 × columns + 69** per row | Each codeword is 17 modules; start 17, stop 18, plus 2 row indicators. A section measurement is often easier. |
| QR | **21 + 4 × (version − 1)** per side | Version 1 = 21, version 2 = 25, version 10 = 57 |
| Micro QR | **11 + 2 × (version − 1)** per side | M1 = 11 … M4 = 17 |
| Data Matrix | the symbol size, e.g. 10, 12, 14, … 144 per side | Count along the solid "L" finder edge, or take it from the generator |

**Check your counting with these examples** (R = 2.5, 1X gap, no quiet zone): Code 39 `HELLO` = 100.5 · Code 93 `TEST` = 73 · ITF `123456` = 56.5 · MSI Plessey `12345` = 67 · Code 128 `Hello` (code set B, 8 symbol characters incl. start, check and stop) = 90 · Codabar `A12345B` = 79. Half modules are normal: they come from the 2.5 wide-to-narrow ratio.

### 2.4 Worked examples (illustrative)

These examples use round, illustrative numbers. They show the patterns we see most often.

**A. Borderline PPM: "it scans sometimes, but not reliably".** A Code 39 label with 16 characters has 18 symbols including start and stop. At R = 2.5 with the standard 1X gap, that is (18 × 13.5) + 17 = **260 modules**. In the full-resolution 1280×720 frame, the bars span 400 px: 400 ÷ 260 = **about 1.5 PPM**, which is borderline. That explains the intermittent reads. To reach 3 PPM, the code must span about 780 px. **Fix:** about 2× larger print, about 2× camera resolution or a closer camera, or a Data Matrix code, which fits the same data into larger modules.

*Check what you measure:* if the same frame had been saved as a half-size preview, the measurement would show about 0.77 PPM. Always measure on the frame that is passed to the SDK.

**B. "PPM is fine, but it doesn't scan": a print defect.** A GS1-128 label measures 600 px ÷ 255 modules = **about 2.4 PPM**, which is in range. At 400–800% zoom, some bars are split or merged, so the printed code is invalid. Overlaying a freshly generated code with the same data on the photo shows the difference clearly. A phone streaming video can sometimes get past one damaged bar across many frames. A single noisy, low-contrast image can't. **Fix:** maintain or adjust the printer, and improve contrast and noise in the capture.

**C. Fixed camera over a conveyor, mounted to see far more than the codes.** The camera covers the whole belt and its surroundings, so the 1D codes only reach **about 2 PPM**, right at the edge, while most of the frame is background. **Fix:** move the camera closer or use a longer lens so the field of view matches the area where codes appear. The same camera then delivers more PPM.

**D. Small crops from an upstream detector.** Some systems detect codes with their own model and pass only small crops at **1–1.5 PPM** to the SDK. These are at or below the edge. Upscaling such crops 2× before passing them can noticeably improve read rates, but it doesn't add real detail. Passing the full frame, or a generous crop at full resolution, is better: tight crops also cost localization accuracy.

### 2.5 Planning a setup: from camera and distance to PPM

Use this before buying hardware, or to explain why reads fail at a distance or an angle:

```text
FOV width (mm)   = 2 × distance × tan(HFOV / 2)        or   sensor width × distance / focal length
pixels per mm    = horizontal pixels of the frame given to the SDK ÷ FOV width
PPM              = pixels per mm × X-dimension (mm) × cos(tilt angle)
max distance     = pixels × X × cos(angle) ÷ (2 × tan(HFOV / 2) × target PPM)
```

- Use the resolution **actually passed to the SDK**. If a 12 MP sensor is downscaled to 1080p before scanning, use 1920, not 4000.
- **Tilt foreshortens the modules** by about cos(angle): 20° costs 6%, 40° costs 23%, 60° costs 50%.
- 1 mil = 0.0254 mm. Typical X-dimensions: retail EAN about 0.33 mm (13 mil); logistics Code 128 often 0.5 mm (20 mil) or more.

**Worked example (camera approaching a label):** 4K camera (3840 px wide), 60° HFOV, Code 128 with X = 0.5 mm:

| Distance | FOV width | px/mm | PPM square-on | at 20° | at 40° |
| --- | --- | --- | --- | --- | --- |
| 0.5 m | 0.58 m | 6.7 | **3.3** | 3.1 | 2.6 |
| 0.75 m | 0.87 m | 4.4 | **2.2** | 2.1 | 1.7 |
| 1.0 m | 1.15 m | 3.3 | **1.7** | 1.6 | 1.3 |
| 1.5 m | 1.73 m | 2.2 | **1.1** | 1.0 | 0.9 |

This is the typical pattern behind "reads fail when far away and at an angle, and succeed as we get closer and straighter". In this setup, 2 PPM square-on is reached at about 83 cm. Options are a narrower lens (more PPM at the same distance), larger labels, or scanning in the closer part of the approach.

**Worked example (fixed-focus camera with a lens):** a 5 MP camera with 2592 px across a 5.6 mm wide sensor and a 16 mm lens. EAN codes with X = 0.33 mm reach 3 PPM up to about **80 cm**, with a field of view about 29 cm wide.

**Reading distance for small QR codes** depends on the same numbers: the module size (code size ÷ modules per side) and the camera's pixels per mm at that distance. A dense QR code (high version or high error correction) has smaller modules than a simple one of the same printed size. The fastest answer is to test the real code on the real device. Alternatively, take the code at true size (PDF or image) and calculate.

### 2.6 How to get more PPM (most effective first)

1. **Move the camera closer**, or use a **longer focal length or zoom lens** with the same camera.
2. **Use more resolution**, and make sure the full resolution actually reaches the SDK (no downscaling in the pipeline).
3. **Print larger modules.** Bigger X-dimension, or less data per code.
4. **Pick a denser symbology or a smaller version.** Data Matrix or QR often give larger modules than a long 1D code in the same area. For QR, use the **lowest acceptable error-correction level and the smallest version** that fits the data.
5. **Crop the field of view** to the area of interest instead of capturing a wide scene.
6. **Upscaling small crops** (e.g. 2×) can help when the source is already small, but it doesn't add real detail. It is a workaround, not a fix.

---

## 3. Other reasons a code doesn't scan

For each cause: how to recognize it, why it happens, and how to improve it.

### 3.1 Blur: focus, motion, exposure

- **How to recognize it:** module edges are soft or smeared. Zoom to 400–800% and look at the bar edges. Narrow bars merge with neighboring spaces.
- **Why it happens:** Blur spreads each bar over its neighbors. At borderline PPM even a little blur removes the information the decoder needs.
- **How to improve it:**
  - Make sure the code is inside the depth of field (fixed-focus lenses only have a limited sharp range).
  - Shorten the exposure time to reduce motion blur, and add light to keep contrast up. **Diffuse lighting** avoids glare on glossy or plastic-wrapped labels.
  - Rolling-shutter sensors also skew fast-moving codes. Shorter exposures help here too.

### 3.2 Contrast, exposure and glare

- **How to recognize it:** look at the histogram of the code area. If the bars and background only span a narrow range (e.g. 102–132 out of 255), less than half the dynamic range is used. Look for blown-out highlights or reflections across the bars.
- **Why it happens:** The decoder needs a clear difference between dark and light elements. Dark-on-light with strong contrast is ideal. The SDK supports a range of contrast, but very flat or glare-covered images lose bars.
- **How to improve it:**
  - Adjust exposure and gain, and add diffuse light.
  - Angle the light or the camera slightly to move reflections off the code.
  - When converting 10/12/16-bit images to 8-bit, map the useful range carefully. A naive min/max mapping can crush the code's contrast.
  - Remove alpha channels.
  - **Light-on-dark (inverted) codes** are supported, but they must be enabled in the symbology settings (see 3.6).

### 3.3 The image pipeline: screenshots, resizing, compression, re-scanning

- **How to recognize it:**
  - Bar widths that look uneven although the print is fine.
  - Blocky JPEG or video-compression artifacts.
  - Codes that come from a screenshot, a PDF render, a photocopy, or a "scanned document".
  - A capture that is fine on one device but has artifacts on an identical device.
- **Why it happens:** Resizing an image by a non-integer factor makes some bars one pixel wider and others one pixel narrower. At low PPM that changes the bar ratios and the checksum fails. The SDK correctly refuses to return a wrong result. Each copy step (print → scan → print → photo) compounds the loss.
- **How to improve it:**
  - Feed **raw camera frames** at full resolution, preferably as grey (`GRAY_8U`) or YUV. RGB works, but the SDK converts it to grey first.
  - Avoid lossy compression before scanning. JPEG block artifacts break thin bars; use uncompressed or lossless formats (PNG, BMP, raw buffers).
  - Don't pre-crop tightly, filter, sharpen, blur or binarize the image. The SDK expects the natural camera image.
  - For single images, the documentation recommends 800×600 to 1920×1080 (1280×720 is a good balance for speed), and FullHD or 4K with the `SC_PRESET_HIGH_EFFORT` preset when codes are small. If you restrict the search area, keep it at least 320×160 pixels.
  - For generated test images, render at **6–8 pixels per narrow bar, or as vector**, and never stretch a generated code to a different aspect ratio. The SDK's barcode generator (`sc_barcode_generator_new`, available when the generator is on your license) creates clean reference codes for Code 39, Code 128, EAN-13, UPC-A, ITF, QR, Data Matrix and PDF417.
  - Scan **original prints** rather than copies or re-scanned documents where possible.
  - Fix capture artifacts at the source (cabling, driver, sensor settings).

### 3.4 Geometry: angle, perspective, curvature, lens distortion

- **How to recognize it:** the code is tilted, viewed off-axis, wrapped around a bottle or cable, or near the edge of a wide-angle or fisheye image.
- **Why it happens:** Tilt shrinks the modules (by about cos(angle)) and makes them uneven in width. Curvature compresses the bars toward the edges of the code. Both reduce the effective PPM below what a flat, square-on code would have.
- **How to improve it:**
  - Mount the camera as square-on as possible, and place labels flat.
  - With tilt in one direction, **1D codes tolerate it better than QR**, because a line is easier to reconstruct than a grid.
  - For curved surfaces, use smaller codes relative to the curvature, or orient 1D codes so the bars run along the curve axis.
  - With fisheye or strong wide-angle lenses, pass **rectified (undistorted)** images. Rectified frames typically scan far more reliably than raw fisheye frames, especially near the image edges.
  - Don't apply aggressive undistortion or sharpening globally just because it made one sample scan. That is usually luck, and it can hurt other codes.

### 3.5 The code itself: print quality, damage, quiet zone, standards

- **How to recognize it:**
  - Split, merged or missing bars; smudges; low-ink or over-inked prints; torn labels.
  - Text or graphics touching the code.
  - Codes from free web generators that were stretched or squeezed.
- **Why it happens:**
  - The SDK only returns a result when the code decodes to a valid value, including its checksum, so it doesn't output a wrong number.
  - It can't return partial reads or per-character confidence.
  - It tolerates a fair amount of damage, but when the printed code itself is invalid, no camera-based reader can recover it from a single image.
- **How to improve it:**
  - Fix the printer (head cleaning, darkness, speed) and verify the codes.
  - Keep the **quiet zone** clear, as required by the symbology spec. For EAN-13, EAN-8, Code 39 and DataBar Limited printed with a too-narrow quiet zone, the `relaxed_sharp_quiet_zone_check` extension accepts tighter margins, at the cost of possible false reads. Fixing the print is the better solution.
  - Overlay a freshly generated code with the same data on the image to show print defects clearly.
  - Generate codes according to the symbology standard. Scandit implements against these specifications:

| Symbology | Specification |
| --- | --- |
| QR Code | ISO/IEC 18004:2024 |
| Data Matrix | ISO/IEC 16022:2024 |
| Code 128 | ISO/IEC 15417:2007 |
| Code 39 | ISO/IEC 16388:2023 |
| Code 93 | AIM BC5-2000 (Uniform Symbology Specification) |
| ITF (Interleaved 2 of 5) | ISO/IEC 16390:2007 |
| Codabar | AIM BC3-2000 / ANSI/AIM BC3-1995 |
| Code 11 | Original 1977 specification (no current standard) |
| MSI Plessey | No formal standard; implemented after the common Plessey description |

Scandit doesn't specify a minimum ISO/IEC 15416 (1D) or ISO/IEC 15415 (2D) print-quality grade. For quality control, codes printed to the specification above, and verified with a standard barcode verifier, are the right basis. The SDK's tolerance for damaged codes is a bonus, not a specification to design to.

### 3.6 Settings that look like image problems

Check these before blaming the image:
- The **symbology isn't enabled.** In the Linux SDK, all symbologies are disabled by default, and an empty JSON configuration enables nothing.
- The code's **length is outside the active symbol-count range** (common for Code 39, Code 128, ITF, Codabar and MSI). The count includes start/stop and check characters, for example:
  - Code 39: characters + 2 (a 17-character code has 19). Default 6–40.
  - Code 128: characters (or digit pairs in code set C) + start + stop + check. Default 4–40 since 8.5 (6–40 before).
  - Code 93: characters + 2 checks + 2 guards. ITF: number of digits. Codabar: digits + 2.
  - Set the range with `sc_symbology_settings_set_active_symbol_counts`; its last argument is the **number of entries**, not the size in bytes. Values outside the allowed range are ignored silently.
- **Inverted (light-on-dark) codes** aren't enabled. `set_enabled` covers dark-on-light only; also enable `sc_symbology_settings_set_color_inverted_enabled` (on by default only for QR and Micro QR). Inversion isn't supported for every symbology (e.g. not for PDF417, ITF, Codabar or DataBar); check the symbology properties page.
- A **JSON key is misspelled or outdated.** Unknown keys are ignored without an error. Print the effective settings with `sc_barcode_scanner_settings_as_json` and compare.
- **Settings weren't applied:** changes take effect only after `sc_barcode_scanner_apply_settings`; check the status it returns.
- **Checksum settings** don't match the printed code (e.g. Code 39 with or without mod43, MSI mod10/mod11).
- **The `strict` extension is enabled** on a low-resolution image. It trades scan rate for fewer false reads.- **Multi-scan is off.** In Linux SDK 7.x and 8.x, multi-scan is off by default: only one or a few codes per frame are returned, and the rest appear over the next frames. When several codes are in view, enable multi-scan (`sc_barcode_scanner_settings_set_multi_scan_enabled`; it needs the multi-code "tracking" feature on your license) and, from SDK 8.0, raise `sc_barcode_scanner_settings_set_max_num_locations_to_process_per_frame`.
- The **scan area or circle of interest** excludes the code, or the **duplicate filter** hides repeats.
- **Settings differ** between the test app and the integration. Compare like with like.

### 3.7 One image versus a video stream

- **Why it happens:** A phone app (for example a Scandit mobile demo app) sees about 30 frames per second with slightly different angle, focus and light, and only needs one good frame. A single still image gets one chance. This is why a code at the edge can scan in the app but not when a single image is passed to the Linux SDK.
- **How to improve it:** feed short frame sequences (e.g. 10–25 frames) into one scanning session instead of single images. Or improve the image until a single frame is comfortably above 2–4 PPM.
- **If you do process single images:** use the `SC_PRESET_HIGH_EFFORT` preset, start a new frame sequence for each image (`sc_recognition_context_start_new_frame_sequence` → `process_frame` → `end_frame_sequence`), and turn the duplicate filter off so a repeated code isn't suppressed.

