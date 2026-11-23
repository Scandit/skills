---
description: "Release notes for the Scandit Data Capture SDK on Linux: new features, changes, and fixes by version."
toc_max_heading_level: 3
displayed_sidebar: linuxSidebar
hide_title: true
title: Release Notes
pagination_prev: null
framework: linux
keywords:
  - linux
product: platform
topic_type: release-notes
canonical_id: scandit.platform.release-notes
---

## 8.7.1

**Released**: November 12, 2026

No updates for this framework in this release.

## 8.7.0

**Released**: November 5, 2026

### New Features

#### Barcode

* Added support for the Han Xin Code symbology ([`SC_SYMBOLOGY_HAN_XIN`](https://docs.scandit.com/stable/c_api/_sc_barcode_8h.html#a8f7838b7a7660e4f3fdfa5a45c07181da9b978b952ca908121d4915e068bd9398))
* Added structured append support to MaxiCode. The "m of n" sequencing metadata is now no longer part of the barcode data.
* Added `const` to read-only opaque pointer parameters in [`sc_symbology_settings_get_enabled_extensions()`](https://docs.scandit.com/stable/c_api/struct_sc_symbology_settings.html#a29328a8d98ea31ddfd7ebcb51dceb772) and [`sc_symbology_settings_get_active_symbol_counts()`](https://docs.scandit.com/stable/c_api/struct_sc_symbology_settings.html#aaf777968ea0544b3c6ea71cef90c2c16).

#### Core

* Added support for BGRA image layouts via [`SC_IMAGE_LAYOUT_BGRA_8U`](https://docs.scandit.com/stable/c_api/_sc_image_description_8h.html#afc93520991c77ea85ec774cba4f7a30da9723e7374df1b0a644d75a0165448865).
* Added libcurl 8.22.0, built from source with mbedTLS as its TLS backend, as a dependency of the Linux library. The Debian package now also depends on `ca-certificates`, which provides the CA trust store read at runtime.

### Performance Improvements

#### Barcode

* Improved scanning of blurry, far-away and deformed Data Matrix codes. Enabled by default on devices with FP16 support
* Improved MaxiCode detection robustness for digitally generated and screen-displayed codes.
* Improved PDF417 recognition of codes at low resolution and with poor print quality.
* Improved the error correction capacity available to QR Model 1 codes. Damaged Model 1 codes now read more reliably.
* Improved decoding accuracy on blurry and otherwise hard-to-read EAN-13 and UPC-A codes.

#### Core

* Improved the speed of camera frame downscaling by a factor of 4/3 on ARM CPUs, most noticeably on low-end Android devices.

### Behavioral Changes

#### Barcode

* Changed 1D symbology decoding to reduce false scans, at the cost of a lower scan rate on hard-to-read codes:
  - Reduced false scans of EAN-13/UPC-A and Code 93, and of EAN-8 and UPC-E reads inside an EAN-13/UPC-A code, in normal and strict mode.
  - Reduced false scans in strict mode, which now requires at least 0.75 pixels per module and decodes EAN-13/UPC-A more conservatively.
  - Lowered the scan rate of hard-to-read UPC-E and Code 93 codes in normal and strict mode, and of EAN-13/UPC-A, Code 128, ITF and Codabar codes in strict mode, as a cost of the false-scan reductions.
* Changed GS1 decoding to reject codes that previously produced unreliable data:
  - Changed the GS1 DataBar Expanded reader to reject codes whose compressed item identification, weight, date or currency field holds a value the specification does not define, or whose AI 392x or 393x price has no digits, as damaged instead of producing malformed element strings.
  - Changed GS1 Composite decoding to reject composite codes with a damaged 2D component instead of producing a GS1 barcode with empty or malformed data.
* Data Matrix: Malformed codes with invalid shift values or unhandled Upper Shift sequences are now correctly rejected as damaged rather than decoding incorrectly.
* Improved QR code validation to reject improperly formatted or non-standard codes, reducing false positives and unreliable data.
* Changed the Aztec reader to no longer accept a structured append header whose sequencing field is not two upper-case letters. Such symbols previously reported an invented segment index and count, for example a negative index or the third of three segments, and could be grouped into a sequence they do not belong to; their content is now decoded as ordinary message data.
* Extended the Python API to expose optional symbology checksums (via SymbologySettings.checksums, CHECKSUM_*, [`sc_symbology_settings_get_checksums()`](https://docs.scandit.com/stable/c_api/struct_sc_symbology_settings.html#ae78fd9b4234dd1a36e9e9fc185f9f4b6), and [`sc_symbology_settings_set_checksums()`](https://docs.scandit.com/stable/c_api/struct_sc_symbology_settings.html#ae43e2c9d1fdc0341438678d45f14df71)) alongside the remaining barcode-area C API functions and generator options: SymbologySettings.symbology, SymbologySettings.ocr_fallback_regex, SymbologySettings.enabled_extensions, Barcode.is_recognized, Barcode.is_color_inverted, Barcode.frame_id, Barcode.module_counts, BarcodeScannerSettings.circle_of_interest (with CIRCLE_RADIUS_INFINITE), BarcodeScannerSettings.clone(), BarcodeScannerSettings.set_aruco_dictionary() (with ArucoDictionary and ARUCO_DICTIONARY_PRESET_*), BarcodeScanner.is_setup_complete, BarcodeScannerSession.last_processed_frame_id, and the BarcodeGenerator constructor options.
* Aligned which Data Matrix symbols are reported as GS1 with the Data Matrix specification: an FNC1 in any other position is a field separator and no longer sets the flag, so a symbol carrying GS1 Application Identifier data without a leading FNC1 is no longer reported as GS1; with leading-FNC1 stripping enabled the data follows the flag in both directions, so such a symbol now keeps its first FNC1 while a Structured Append symbol with an FNC1 in the fifth position now loses it.
* Changed DotCode, MaxiCode and Aztec to assemble structured append sequences without a file ID (DotCode, MaxiCode modes 4 and 5, and Aztec without a message ID) into a complete buffered barcode. Their segments are grouped by symbology and segment count, so segments of two such sequences of the same length scanned within 30 seconds of each other cannot be told apart.
* Changed MaxiCode modes 2 and 3 structured append segments to report their primary message fields as the file ID, and the assembled buffered barcode now holds the primary message once instead of once per segment.

#### Core

* Changed recognition contexts alive at the same time to require the same `writable_data_path`, reversing the earlier advice to give each one its own. Behavior change: [`sc_recognition_context_new()`](https://docs.scandit.com/stable/c_api/struct_sc_recognition_context.html#adda6daac2623c54c3421cadf6dfa1261) returns NULL, and the Python `RecognitionContext` raises `RuntimeError`, while a context created with another path, or an object created from one such as a parser, is still alive.
* Documented that every object created from a recognition context, such as a barcode scanner or a parser created with [`sc_parser_new_with_context()`](https://docs.scandit.com/stable/c_api/struct_sc_parser.html#abc713c64bc17313e641880f618d34713), must be released before the context's last reference is released with [`sc_recognition_context_release()`](https://docs.scandit.com/stable/c_api/struct_sc_recognition_context.html#a4ed5ac309db47c4eec096af4ab80ee07).

### Bug Fixes

#### Barcode

* Fixed several MaxiCode decoding and character encoding defects:
  - Fixed the reading of symbols where the relative size of finder pattern and module rows is slightly off relative to the specification.
  - Fixed corrupted characters in the data of damaged symbols that end in a truncated Numeric Shift or ECI sequence.
  - Fixed a crash on mode 2 and 3 symbols whose secondary message is cut off inside the `[)>RS01GS` format header. Such symbols now decode to the postal code, country code and service class followed by the truncated message.
  - Fixed character encoding reporting issues in [`sc_barcode_get_data_encoding()`](https://docs.scandit.com/stable/c_api/struct_sc_barcode.html#aeba86835957d7c81e128c280068c4142) for ECI and MaxiCode mode 2 and 3 symbols.
* Fixed several Data Matrix decoding and character encoding defects:
  - Fixed the GS1 flag reported by [`sc_barcode_is_gs1_data_carrier()`](https://docs.scandit.com/stable/c_api/struct_sc_barcode.html#ac39cea56730df343e21a8f33bdf501c1), which is now set by an FNC1 in the first symbol character position, or the fifth of a Structured Append symbol, as the specification defines.
  - Fixed the decoded value of a backtick encoded in the Text encodation scheme, which was read as an apostrophe.
  - Fixed several Data Matrix decoding defects related to character encoding, end-of-data handling, and shift formatting.
  - Fixed a Data Matrix scanning accuracy regression introduced in 8.4.0 for codes scanned with the `direct_part_marking_mode` symbology extension.
* Fixed several QR decoding defects:
  - Fixed the reading of Model 1 codes that use data mask pattern 111. The reader accepted only seven of the eight mask patterns the standard defines for Model 1, so such codes went unrecognized.
  - Fixed false Structured Append results from damaged codes: a Structured Append header that is not at the start of the code, or a second one, now makes the code fail to decode instead of reporting arbitrary sequence and parity information.
  - Fixed decoding and flag reporting for QR codes carrying AIM Application Indicators and GS1 headers.
  - Fixed a QR scanning accuracy regression introduced in 8.6 for codes with degraded finder patterns (round, dotted, curved, bent, damaged) in single-barcode scanning.
* Fixed several Micro QR and rectangular Micro QR (rMQR) defects:
  - MicroQR: Fixed an issue that prevented improvements for rotated codes and codes with cluttered backgrounds from being available in production builds.
  - Fixed decoding and truncation issues in Micro QR codes with invalid character counts or fully filled codewords.
  - Fixed the AIM Application Indicator (FNC1 in second position) of rectangular Micro QR (rMQR) codes, which is now transmitted as the two digits or the letter the specification defines instead of three digits. Codes with a reserved Application Indicator, or with an FNC1 mode indicator that is not placed right before the first data mode indicator, are now rejected, and FNC1 mode now stays in effect across later ECI headers.
  - Fixed a rare crash during detection of rectangular Micro QR codes whose finder pattern covers a large part of the frame, such as when scanning at very close range.
* Fixed several GS1 Composite and GS1 DataBar Expanded decoding defects:
  - Fixed decoding errors in GS1 composite codes, such as misread lot number flag bits and dropped digits when fields are followed by additional element strings.
  - Removed extraneous group separators and trailing characters incorrectly appended to the decoded data of composite codes.
  - Fixed decoding errors in GS1 DataBar Expanded codes with AI 392x or 393x prices followed by additional element strings, such as dropped element strings or lost digits.
* Fixed a false ArUco result where the inner shape of a marker was read as a second, color-inverted marker.
* Fixed several Aztec decoding defects:
  - Fixed the file ID of an Aztec structured append symbol whose optional message ID field is absent. [`sc_barcode_get_file_id()`](https://docs.scandit.com/stable/c_api/struct_sc_barcode.html#a046b34b96820b58e13a3e495f404eaab) returned the placeholder `DEFAULT`.
  - Fixed the character encoding reported for Aztec byte shift data that follows an ECI.
* Fixed a scan regression from SDK 5.19 for 1D codes with colored backgrounds, such as dark print on a saturated label.
* Fixed a rare out-of-bounds image read while detecting a code that touches the right or bottom image border.
* Fixed [`sc_barcode_scanner_settings_new_from_json()`](https://docs.scandit.com/stable/c_api/struct_sc_barcode_scanner_settings.html#a12865e80efbcf01cac8bc8c749032663) rejecting a `float`/`double`-typed setting whose value was written as a whole number (for example, `1` instead of `1.0`). Such values are now accepted.
* Fixed an issue that could increase the time to scan when only QR or Data Matrix is enabled and there are more than 8 codes in the frame while using Barcode Tracking, Barcode AR, Barcode Pick, Barcode Find and Label Capture.

## 8.6.3

**Released**: November 19, 2026

No updates for this framework in this release.

## 8.6.2

**Released**: October 26, 2026

### Bug Fixes

#### Barcode

* Fixed an issue with MicroQR that prevented improvements for rotated codes and codes with cluttered backgrounds from being available in production builds.
* Fixed an issue that could increase the time to scan when only QR or Data Matrix is enabled and there are more than 8 codes in the frame while using Barcode Tracking, Barcode AR, Barcode Pick, Barcode Find and Label Capture.

## 8.6.1

**Released**: October 1, 2026

### Bug Fixes

#### Barcode

* Fixed a QR scanning accuracy regression introduced in 8.6 for codes with degraded finder patterns (round, dotted, curved, bent, damaged) in single-barcode scanning.
* Fixed a Data Matrix scanning accuracy regression introduced in 8.4.0 for codes scanned with the `direct_part_marking_mode` symbology extension.
* Fixed Data Matrix codes not being read when their encoder ends the data with an Unlatch codeword followed by more than one pad codeword.
* Fixed a 1D symbology scan regression from SDK 5.19 for codes with colored backgrounds, such as dark print on a saturated label.

## 8.6.0

**Released**: August 31, 2026

### New Features

#### Barcode

* Extended the support for DotCode features by adding support for:
  - Extended Channel Interpretation (ECI). Symbols that switch character sets (for example to Cyrillic or another code page) now report the correct per-segment encoding. As part of this, the default character set for DotCode is now reported as ISO 8859-1 instead of ASCII.
  - Message envelopes as defined in ISO/IEC 15434.
  - Structured append. DotCode has no file ID, so segments are not automatically grouped by the buffered barcode session.

### Performance Improvements

#### Barcode

* Reduced the false positive rate for EAN13, UPCA, EAN8, and UPC-E.
* Improved ITF decoding robustness, reducing the number of unscanned codes. On our internal datasets, we measured an improvement of more than 20% true positives.
* Improved MicroQR decoding for rotated codes and cluttered backgrounds. On our internal datasets, we measured an improvement of more than 40% true positives.

#### Id

* Improved PDF417 scanning on Quebec, Alaska, and Oklahoma driver’s licenses.

### Behavioral Changes

#### Barcode

* Enabled detection and decoding of mirrored MaxiCodes by default. Previously this required enabling the symbology extension `mirrored`, which has been removed.
* Limited the GS1 format flag for DotCode to genuine GS1 openings (a leading digit pair without FNC1) per AIM DotCode v3.0, instead of defaulting all symbols to GS1.
* Disabled enhanced low-resolution scanning of QR codes (introduced in 8.5.0) for MatrixScan modes. Customers who need this feature should contact Scandit support.

#### Core

* Exposed the structured append segment fields on `Barcode` (`segment_index`, `segment_count`, `file_id`) via the Python API, matching the C API's [`sc_barcode_get_segment_index()`](https://docs.scandit.com/stable/c_api/struct_sc_barcode.html#aa52f8d15230b7dcc62bd1280c753186b), [`sc_barcode_get_segment_count()`](https://docs.scandit.com/stable/c_api/struct_sc_barcode.html#a48707b292ef1788d9bf881dbf3ee7659), and [`sc_barcode_get_file_id()`](https://docs.scandit.com/stable/c_api/struct_sc_barcode.html#a046b34b96820b58e13a3e495f404eaab).

### Bug Fixes

#### Barcode

* Fixed rare cases where DotCode Code Set C symbols using the date/lot macro decoded to incorrect data due to a dropped leading zero in a digit pair.
* Fixed a regression where short ITF codes with low wide/narrow ratio were not decoded.

#### Core

* Fixed [`sc_camera_get_frame()`](https://docs.scandit.com/stable/c_api/struct_sc_camera.html#acfe352f7ca3a084b86a0c3d3116aba8e) hanging indefinitely when the camera is disconnected while streaming. It now returns promptly instead of blocking.
* Fixed the Python camera sample (`CommandLineBarcodeScannerCameraSample.py`) crashing at startup.
