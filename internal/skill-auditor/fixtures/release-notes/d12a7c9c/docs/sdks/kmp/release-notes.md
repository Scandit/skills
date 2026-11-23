---
description: "Release notes for the Scandit Data Capture SDK for Kotlin Multiplatform: new features, changes, and fixes by version."
toc_max_heading_level: 3
displayed_sidebar: kmpSidebar
hide_title: true
title: Release Notes
pagination_prev: null
framework: kmp
keywords:
  - kmp
product: platform
topic_type: release-notes
canonical_id: scandit.platform.release-notes
---

## 8.7.0

**Released**: November 5, 2026

### New Features

#### Barcode

* Added support for the Han Xin Code symbology (`SC_SYMBOLOGY_HAN_XIN`)
* Added structured append support to MaxiCode. The "m of n" sequencing metadata is now no longer part of the barcode data.
* Extended BarcodeArResponsiveAnnotation to accept an annotationsByThreshold map, so an annotation can switch between any number of distance-based states instead of only close-up and far-away
* Added Barcode Sequence mode support to the Kotlin Multiplatform SDK, mirroring the existing Android and iOS Barcode Sequence functionality for shared Kotlin Multiplatform apps

#### Id

* Extended the ID rejection API to reject documents based on passport type with rejectPassportTypes, and added a new PassportType, EmergencyTravelDocument
* Added [`PassportType.EMERGENCY_TRAVEL_DOCUMENT`](https://docs.scandit.com/data-capture-sdk/kmp/id-capture/api/passport-type.html#value-scandit.datacapture.id.PassportType.EmergencyTravelDocument) and split PU-prefixed passport MRZs out of Emergency. The same change is now exposed on the frameworks
* Added VIZ support for the front of the 2026 Alberta driver's license and of the 2026 Nebraska driver's license and ID card, including the versions for minors.
* Added VIZ support for the front of the 2026 Hawaii driver's license and ID card, including the under-21 driver's license.
* ID Capture now offers [`IdCaptureSettings.notifyOnSideCapture`](https://docs.scandit.com/data-capture-sdk/kmp/id-capture/api/id-capture-settings.html#property-scandit.datacapture.id.IdCaptureSettings.NotifyOnSideCapture) and [`CapturedId.isCapturingComplete`](https://docs.scandit.com/data-capture-sdk/kmp/id-capture/api/captured-id.html#property-scandit.datacapture.id.CapturedId.IsCapturingComplete), the visa fields on `MrzResult, CapturedId.visaNumber`, `passportNumber` and `sex`, [`MobileDocumentResult.signature`](https://docs.scandit.com/data-capture-sdk/kmp/id-capture/api/mobile-document-result.html#property-scandit.datacapture.id.MobileDocumentResult.Signature), and [`IdCaptureSettings.rejectPassportTypes`](https://docs.scandit.com/data-capture-sdk/kmp/id-capture/api/id-capture-settings.html#property-scandit.datacapture.id.IdCaptureSettings.RejectPassportTypes).
* ID Validate now verifies the digital signature in the barcode of California driver's licenses and ID cards issued since October 2025. A valid signature confirms the barcode as authentic; a missing or invalid signature is reported as forged.

#### Core

* Optimized rendering so that idle viewfinders (target aimer and laserline) no longer force a continuous render loop when nothing is animating

### Performance Improvements

#### Barcode

* Improved scanning of blurry, far-away and deformed Data Matrix codes. Enabled by default on devices with FP16 support
* Improved MaxiCode detection robustness for digitally generated and screen-displayed codes.
* Improved PDF417 recognition of codes at low resolution and with poor print quality.
* Improved the error correction capacity available to QR Model 1 codes. Damaged Model 1 codes now read more reliably.
* Improved decoding accuracy on blurry and otherwise hard-to-read EAN-13 and UPC-A codes.

#### Id

* Improved VIZ scanning of the Swiss passport (2022 design).
* Improved VIZ scanning of ID cards and driver's licenses, so that more card designs are read correctly. Passports and visas are unchanged.

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
* Aligned which Data Matrix symbols are reported as GS1 with the Data Matrix specification: an FNC1 in any other position is a field separator and no longer sets the flag, so a symbol carrying GS1 Application Identifier data without a leading FNC1 is no longer reported as GS1; with leading-FNC1 stripping enabled the data follows the flag in both directions, so such a symbol now keeps its first FNC1 while a Structured Append symbol with an FNC1 in the fifth position now loses it.
* Changed DotCode, MaxiCode and Aztec to assemble structured append sequences without a file ID (DotCode, MaxiCode modes 4 and 5, and Aztec without a message ID) into a complete buffered barcode. Their segments are grouped by symbology and segment count, so segments of two such sequences of the same length scanned within 30 seconds of each other cannot be told apart.
* Changed MaxiCode modes 2 and 3 structured append segments to report their primary message fields as the file ID, and the assembled buffered barcode now holds the primary message once instead of once per segment.

#### Id

* Spanish residence permits now return the NIE in both [`VizResult.personalIdNumber`](https://docs.scandit.com/data-capture-sdk/kmp/id-capture/api/viz-result.html#property-scandit.datacapture.id.VizResult.PersonalIdNumber) and [`VizResult.documentAdditionalNumber`](https://docs.scandit.com/data-capture-sdk/kmp/id-capture/api/viz-result.html#property-scandit.datacapture.id.VizResult.DocumentAdditionalNumber). Previously only one of the two carried it.
* [`MrzResult.passportType`](https://docs.scandit.com/data-capture-sdk/kmp/id-capture/api/mrz-result.html#property-scandit.datacapture.id.MrzResult.PassportType) now uses the ICAO meaning of the second letter of the MRZ document code only where it is reliable, and reports the new [`PassportType.UNKNOWN`](https://docs.scandit.com/data-capture-sdk/kmp/id-capture/api/passport-type.html#value-scandit.datacapture.id.PassportType.Unknown) otherwise. Older passports from countries that used these letters differently no longer get a special type. For example, older Swiss passports with `PM` are now `National` instead of `Military`. Letters without an ICAO meaning now report `Unknown` instead of `National`. When the type is `National` or `Unknown`, nationality `XXA` gives `Stateless`, and `XXB` or `XXC` give `Refugee`. `Unknown` is only rejected if `rejectPassportTypes` lists it.

### Bug Fixes

#### Barcode

* Fixed several MaxiCode decoding and character encoding defects:
  - Fixed the reading of symbols where the relative size of finder pattern and module rows is slightly off relative to the specification.
  - Fixed corrupted characters in the data of damaged symbols that end in a truncated Numeric Shift or ECI sequence.
  - Fixed a crash on mode 2 and 3 symbols whose secondary message is cut off inside the `[)>RS01GS` format header. Such symbols now decode to the postal code, country code and service class followed by the truncated message.
  - Fixed character encoding reporting issues in `sc_barcode_get_data_encoding` for ECI and MaxiCode mode 2 and 3 symbols.
* Fixed several Data Matrix decoding and character encoding defects:
  - Fixed the GS1 flag reported by `sc_barcode_is_gs1_data_carrier`, which is now set by an FNC1 in the first symbol character position, or the fifth of a Structured Append symbol, as the specification defines.
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
  - Fixed the file ID of an Aztec structured append symbol whose optional message ID field is absent. `sc_barcode_get_file_id` returned the placeholder `DEFAULT`.
  - Fixed the character encoding reported for Aztec byte shift data that follows an ECI.
* Fixed a scan regression from SDK 5.19 for 1D codes with colored backgrounds, such as dark print on a saturated label.
* Fixed a rare out-of-bounds image read while detecting a code that touches the right or bottom image border.
* Fixed the missing error report when a symbology's `ocr_fallback` extension is enabled without the ScanditLabelCaptureText module: the data capture context now reports a Missing Resource error naming the resources that could not be loaded, and barcode scanning continues without OCR fallback.
* Fixed the camera view temporarily rotating incorrectly in SparkScan Target mode when using hold-to-scan.
* Fixed a UI glitch when switching Selection Mode from On to Auto in BarcodeCapture.
* Fixed [`BarcodeArViewSettings.soundEnabled`](https://docs.scandit.com/data-capture-sdk/kmp/barcode-capture/api/ui/barcode-ar-view-settings.html#property-scandit.datacapture.barcode.ar.ui.BarcodeArViewSettings.SoundEnabled) and hapticEnabled being ignored when the view settings were updated after the BarcodeAr view was created.
* Fixed the redo-group delete icon in BarcodeCountView being drawn at the bottom of the screen when idle, where it overlapped the system navigation bar on Android 15 and later.
* Fixed a camera freeze when an app alternates MatrixScan Count's scan preview with another camera-backed mode. Returning to the scan preview could leave the camera unresponsive for 10-15 seconds.
* Fixed MatrixScan Count losing its counted barcodes when recognition is interrupted, for example by opening Control Center. Scanning a retained barcode again counts it again.
* Fixed an issue that could increase the time to scan when only QR or Data Matrix is enabled and there are more than 8 codes in the frame while using Barcode Tracking, Barcode AR, Barcode Pick, Barcode Find and Label Capture.

#### Id

* Fixed the 2026 Oklahoma driver's license not returning `issuingJurisdiction` and `issuingJurisdictionIso`
* Updated the bundled ID Validate model to `8.0.20260626`, which fixes valid Ohio driver's licenses (OH0901DL format) being reported as forged by ID Validate. This model was previously delivered over the air; it is now included in the SDK, so new installs use it from the first scan.
* Fixed iOS reporting error 3072 instead of 33805 when the license key does not include VIZ scanning, matching Android
* Fixed a crash when tapping the view after the ID Capture mode was removed from the data capture context.
* Fixed South African driving licenses failing to scan when the barcode contains a vehicle restriction issue date without a day.
* Fixed FullDocumentScanner returning no MRZ result for the US Border Crossing Card. The result now combines the VIZ and the MRZ.
* Fixed [`IdCapture.externalTransactionId`](https://docs.scandit.com/data-capture-sdk/kmp/id-capture/api/id-capture.html#property-scandit.datacapture.id.IdCapture.ExternalTransactionId) being cleared when new settings were applied. Scans after the settings change were reported without the ID.

#### Smart Label Capture

* Fixed expiry and packing date fields accepting a numeric date that does not exist, such as `BEST BEFORE 32/13/2027`. Such a date is now rejected instead of being returned as the field value.
* Changed the month of a captured date field to be reported with the month name as it was read from the label, in its original language and letter case, rather than a normalized lowercase English abbreviation. `10 Ene 2026` yields the month text `Ene` instead of `jan`, and the field text `10.Ene.2026` instead of `10.jan.2026`. A zero read in place of the letter `o` is still corrected, so `N0V` yields `NOV`. The numeric month is unaffected—compare against it instead of the text to branch on a month.
* Fixed the LabelCapture validation flow staying idle when returning to a screen that keeps the mode enabled; a paused or finished flow now survives the navigation round trip, and validation flow listener removal takes effect
* Fixed a crash that could occur when the adaptive recognition result type was changed while a scan was still being processed
* Fixed expiry and packing date fields missing a date written day first with a space before the month name, such as `BEST BEFORE 25 MAR 2027`.

#### Core

* Fixed a bug in Camera API 1 that might cause a camera to show as STANDBY instead of OFF when another application takes over the device camera
* Fixed camera preview failures during a live settings change (for example, resolution): a rejected parameter update or a failed preview restart could leave the camera stopped or streaming mismatched frames; it now recovers or reports a consistent state
* Fixed the recovery from a failed camera wake-up in Camera API 1, which now restarts the camera reliably, including when the camera was started via standby
* Fixed a crash when starting the camera on devices whose camera reports zoom support without providing zoom ratios
* Fixed rapid torch toggles being dropped or applied twice when issued before the previous toggle was confirmed by the camera
* Fixed a memory leak where cleared weak references to torch and zoom listeners accumulated indefinitely in the camera's listener sets
* Fixed a crash that terminated the app when a camera frame used a pixel layout the SDK cannot convert, for example frames produced by the camera image-injection features of automated testing services. Such frames are now skipped with a warning instead
* Fixed an error thrown on iOS when passing an empty byte array to [`ArucoMarker.create()`](https://docs.scandit.com/data-capture-sdk/kmp/barcode-capture/api/aruco-marker.html#method-scandit.datacapture.barcode.ArucoMarker.Create) or [`Parser.parseRawData()`](https://docs.scandit.com/data-capture-sdk/kmp/parser/api/parser.html#method-scandit.datacapture.parser.Parser.ParseRawData), which now matches the existing Android behavior
* Fixed the camera and torch switch controls not updating their accessibility labels on the main thread, so TalkBack announcements no longer misfire when the camera or torch state changes

## 8.6.2

**Released**: October 26, 2026

### Bug Fixes

#### Barcode

* Fixed an issue with MicroQR that prevented improvements for rotated codes and codes with cluttered backgrounds from being available in production builds.
* Fixed an issue in SparkScan where, with hold-to-scan disabled, pressing and holding the collapsed trigger button and then releasing it started scanning.
* Fixed an issue that could increase the time to scan when only QR or Data Matrix is enabled and there are more than 8 codes in the frame while using Barcode Tracking, Barcode AR, Barcode Pick, Barcode Find and Label Capture.

#### Core

* Adjusted SDK views and the scan area for devices with horizontal safe-area insets, such as the iPhone Duo cover display. The scan area now excludes the left and right safe-area insets.

## 8.6.1

**Released**: October 1, 2026

### New Features

#### Id

* Visa VIZ results for Canadian visa stickers now report the full 10-character number in [`VizResult.visaNumber`](https://docs.scandit.com/data-capture-sdk/kmp/id-capture/api/viz-result.html#property-scandit.datacapture.id.VizResult.VisaNumber) (the MRZ result remains truncated).

### Bug Fixes

#### Barcode

* Fixed a QR scanning accuracy regression introduced in 8.6 for codes with degraded finder patterns (round, dotted, curved, bent, damaged) in single-barcode scanning.
* Rectangular Micro QR: Fixed a rare crash during detection of codes whose finder pattern covers a large part of the frame, such as when scanning at very close range.
* Fixed a Data Matrix scanning accuracy regression introduced in 8.4.0 for codes scanned with the `direct_part_marking_mode` symbology extension.
* Fixed Data Matrix codes not being read when their encoder ends the data with an Unlatch codeword followed by more than one pad codeword.
* Fixed a 1D symbology scan regression from SDK 5.19 for codes with colored backgrounds, such as dark print on a saturated label.
* Fixed the barcode duplicate filter explicitly set to -2 under SelectionMode On not being respected and being incorrectly relaxed to 0.

#### Id

* Fixed the 2026 Oklahoma driver's license not returning the Jurisdiction and JurisdictionIso fields.
* Fixed a crash in the IdCapture overlay when it was tapped.
* Updated the bundled ID Validate model to `8.0.20260626`, which fixes valid Ohio driver's licenses (OH0901DL format) being reported as forged by ID Validate. This model was previously delivered over the air; it is now included in the SDK, so new installs use it from the first scan.

#### Smart Label Capture

* Fixed a bug where the camera preview could remain black or frozen when opening a scanning screen after leaving a LabelCapture validation flow screen.

#### Core

* Fixed a crash that terminated the app when a camera frame used a pixel layout the SDK cannot convert, for example frames produced by the camera image-injection features of automated testing services. Such frames are now skipped with a warning instead.
* Fixed customer archives for Capacitor, Cordova and React Native shipping unresolvable `workspace:*` dependency specifiers, so `npm install` now succeeds in the bundled samples.

## 8.6.0

**Released**: August 31, 2026

### New Features

The Scandit Data Capture SDK is now available for Kotlin Multiplatform, letting you write one Kotlin codebase that scans on both Android and iOS. The KMP SDK covers SparkScan, Barcode Capture, Barcode Selection, MatrixScan (Batch, AR, Count, Find, Pick), Barcode Generator, ID Capture, Smart Label Capture, and the Parser, with Compose Multiplatform UI companions for the view-based modules.

Android and shared code resolve from Maven Central (com.scandit.datacapture.kmp). On iOS you integrate through Swift Package Manager: add the datacapture-kmp-spm package and pick the prebuilt umbrella product matching the Scandit modules you use (barcode, ID, label and/or parser). The required native Scandit frameworks are resolved automatically as transitive dependencies. Apps that already ship their own shared KMP module can instead pin datacapture-spm directly.

Get started by understanding the [system requirements](/sdks/kmp/system-requirements.mdx) and [how to add the SDK to your project](/sdks/kmp/add-sdk.mdx).

To start the implementation of the different features you can follow the relevant guides for [single barcode scanning](/sdks/kmp/single-scanning.md) ([SparkScan](/sdks/kmp/sparkscan/intro.md), [Barcode Capture](/sdks/kmp/barcode-capture/get-started.md)), [multiple barcode scanning](/sdks/kmp/batch-scanning.md) ([MatrixScan Batch](/sdks/kmp/matrixscan/intro.md), [MatrixScan AR](/sdks/kmp/matrixscan-ar/intro.md), [MatrixScan Count](/sdks/kmp/matrixscan-count/intro.md), [MatrixScan Find](/sdks/kmp/matrixscan-find/intro.md), [MatrixScan Pick](/sdks/kmp/matrixscan-pick/intro.md)), [ID scanning](/sdks/kmp/id-capture/intro.md), or [label scanning](/sdks/kmp/label-capture/intro.md).
