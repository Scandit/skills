---
description: "Release notes and updates for the Scandit Web SDK."
toc_max_heading_level: 3
displayed_sidebar: webSidebar
hide_title: true
title: Release Notes
pagination_prev: null
framework: web
keywords:
  - web
product: platform
topic_type: release-notes
canonical_id: scandit.platform.release-notes
---

## 8.7.1

**Released**: November 12, 2026

### Performance Improvements

#### Id

* Optimized the capture of AAMVA documents: when no [`IdImageType.CroppedDocument`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/id-image-type.html#value-scandit.datacapture.id.IdImageType.CroppedDocument) image is required, the back-side scans as fast as when only scanning the back with [`SingleSideScanner`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/physical-document-scanner.html#class-scandit.datacapture.id.SingleSideScanner).
* Improved the performance of the back-side VIZ capture.

## 8.7.0

**Released**: November 5, 2026

:::warning
Web SDK 8.7 is the last version that supports Safari versions earlier than 16.4, on both macOS and iOS. Starting with version 8.8, the Web SDK requires Safari 16.4 or later. See the [browser compatibility table](./system-requirements.mdx#browser-compatibility).
:::

### New Features

#### Barcode

* Added structured append support to MaxiCode. The "m of n" sequencing metadata is now no longer part of the barcode data.
* Changed SparkScan so that button taps no longer vibrate when haptic feedback is disabled in [`SparkScanViewSettings`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/spark-scan-view-settings.html#class-scandit.datacapture.barcode.spark.ui.SparkScanViewSettings)
* Added an AdaptiveRecognitionServiceListener that can be attached to the BarcodeCapture mode to be notified of adaptive recognition responses and errors. Each callback carries the originating frame's [`AdaptiveRecognitionFrameMetadata`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/adaptive-recognition-service-listener.html#interface-scandit.datacapture.barcode.AdaptiveRecognitionFrameMetadata) (frame ID and recognized barcodes), so an asynchronously delivered outcome can be correlated back to its frame.
* Added [`BarcodeArFilter`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/barcode-ar-filter.html#interface-scandit.datacapture.barcode.ar.BarcodeArFilter) to the web SDK, letting you choose which of the currently visible barcodes MatrixScan AR presents.
* Extended [`BarcodeArResponsiveAnnotation`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/barcode-ar-responsive-annotation.html#class-scandit.datacapture.barcode.ar.ui.BarcodeArResponsiveAnnotation) to accept any [`BarcodeArAnnotation`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/barcode-ar-annotation.html#interface-scandit.datacapture.barcode.ar.ui.BarcodeArAnnotation) (info, popover, status icon, or custom) per distance state, not just [`BarcodeArInfoAnnotation`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/barcode-ar-info-annotation.html#class-scandit.datacapture.barcode.ar.ui.BarcodeArInfoAnnotation)
* Added the [`expectsOnlyUniqueBarcodes`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/barcode-ar-settings.html#property-scandit.datacapture.barcode.ar.BarcodeArSettings.ExpectsOnlyUniqueBarcodes) property to [`BarcodeArSettings`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/barcode-ar-settings.html#class-scandit.datacapture.barcode.ar.BarcodeArSettings), matching other platforms

#### Id

* Extended the ID rejection API to reject documents based on passport type with [`rejectPassportTypes`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/id-capture-settings.html#property-scandit.datacapture.id.IdCaptureSettings.RejectPassportTypes), and added a new PassportType, EmergencyTravelDocument
* Added [`PassportType.EmergencyTravelDocument`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/passport-type.html#value-scandit.datacapture.id.PassportType.EmergencyTravelDocument) and split PU-prefixed passport MRZs out of Emergency. The same change is now exposed on the frameworks
* Added VIZ support for the front of the 2026 Alberta driver's license and of the 2026 Nebraska driver's license and ID card, including the versions for minors.
* Added VIZ support for the front of the 2026 Hawaii driver's license and ID card, including the under-21 driver's license.
* Added a convenience conversion from [`Region`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/id-capture-region.html#enum-scandit.datacapture.id.IdCaptureRegion) to ISO code as public API
* ID Validate now verifies the digital signature in the barcode of California driver's licenses and ID cards issued since October 2025. A valid signature confirms the barcode as authentic; a missing or invalid signature is reported as forged.

#### Smart Label Capture

* Added multi language support to the expiry date, packaging date, weight, unit price, total price fields. At the moment, English and Spanish are supported. New languages will follow in future releases (French and German in 8.8). You can now also select a single language for your label definition, while all languages will be supported by default.
* Added [`LabelCaptureSettings.settingsForSymbology()`](https://docs.scandit.com/data-capture-sdk/web/label-capture/api/label-capture-settings.html#method-scandit.datacapture.label.LabelCaptureSettings.GetSymbologySettings), so Smart Label Capture symbology settings (extensions, active symbol counts, OCR fallback regex) can be configured directly via the public API
* Added the [`LabelFieldLocationType`](https://docs.scandit.com/data-capture-sdk/web/label-capture/api/label-field-location-type.html#enum-scandit.datacapture.label.LabelFieldLocationType) enum to the public exports, so it can now be imported from @scandit/web-datacapture-label

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

* Spanish residence permits now return the NIE in both [`VIZResult.personalIdNumber`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/viz-result.html#property-scandit.datacapture.id.VizResult.PersonalIdNumber) and [`VIZResult.documentAdditionalNumber`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/viz-result.html#property-scandit.datacapture.id.VizResult.DocumentAdditionalNumber). Previously only one of the two carried it.
* [`MRZResult.passportType`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/mrz-result.html#property-scandit.datacapture.id.MrzResult.PassportType) now uses the ICAO meaning of the second letter of the MRZ document code only where it is reliable, and reports the new [`PassportType.Unknown`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/passport-type.html#value-scandit.datacapture.id.PassportType.Unknown) otherwise. Older passports from countries that used these letters differently no longer get a special type. For example, older Swiss passports with `PM` are now `National` instead of `Military`. Letters without an ICAO meaning now report `Unknown` instead of `National`. When the type is `National` or `Unknown`, nationality `XXA` gives `Stateless`, and `XXB` or `XXC` give `Refugee`. `Unknown` is only rejected if [`rejectPassportTypes`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/id-capture-settings.html#property-scandit.datacapture.id.IdCaptureSettings.RejectPassportTypes) lists it.

### Bug Fixes

#### Barcode

* Fixed several MaxiCode decoding and character encoding defects:
  - Fixed the reading of symbols where the relative size of finder pattern and module rows is slightly off relative to the specification.
  - Fixed corrupted characters in the data of damaged symbols that end in a truncated Numeric Shift or ECI sequence.
  - Fixed a crash on mode 2 and 3 symbols whose secondary message is cut off inside the `[)>RS01GS` format header. Such symbols now decode to the postal code, country code and service class followed by the truncated message.
  - Fixed character encoding reporting issues for ECI and MaxiCode mode 2 and 3 symbols.
* Fixed several Data Matrix decoding and character encoding defects:
  - Fixed the GS1 flag reported by [`Barcode.isGS1DataCarrier`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/barcode.html#property-scandit.datacapture.barcode.Barcode.IsGs1DataCarrier), which is now set by an FNC1 in the first symbol character position, or the fifth of a Structured Append symbol, as the specification defines.
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
  - Fixed the file ID of an Aztec structured append symbol whose optional message ID field is absent, which was reported as the placeholder `DEFAULT`.
  - Fixed the character encoding reported for Aztec byte shift data that follows an ECI.
* Fixed a scan regression from SDK 5.19 for 1D codes with colored backgrounds, such as dark print on a saturated label.
* Fixed a rare out-of-bounds image read while detecting a code that touches the right or bottom image border.
* Fixed the missing error report when a symbology's `ocr_fallback` extension is enabled without the ScanditLabelCaptureText module: the data capture context now reports a Missing Resource error naming the resources that could not be loaded, and barcode scanning continues without OCR fallback.
* Fixed a bug that caused SparkScan to crash when using SmartScanSelection.
* Fixed the SparkScan mini preview not being draggable.
* Fixed a UI glitch when switching Selection Mode from On to Auto in BarcodeCapture.
* Fixed a placement problem with [`BarcodeArStatusIconAnnotation`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/barcode-ar-status-icon-annotation.html#class-scandit.datacapture.barcode.ar.ui.BarcodeArStatusIconAnnotation) when the barcode rotates.
* Fixed BarcodeFind overwriting the zoom levels of the camera settings it was given: a [`BarcodeFindView`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/barcode-find-view.html#class-scandit.datacapture.barcode.find.ui.BarcodeFindView) created with custom CameraSettings now runs on the zoom levels it was configured with. BarcodeFind's recommended camera settings now report the .5x/1x levels, matching iOS and Android.
* Fixed an issue that could increase the time to scan when only QR or Data Matrix is enabled and there are more than 8 codes in the frame while using Barcode Tracking, Barcode AR, Barcode Pick, Barcode Find and Label Capture.

#### Id

* Fixed the 2026 Oklahoma driver's license not returning `issuingJurisdiction` and `issuingJurisdictionIso`
* Updated the bundled ID Validate model to `8.0.20260626`, which fixes valid Ohio driver's licenses (OH0901DL format) being reported as forged by ID Validate. This model was previously delivered over the air; it is now included in the SDK, so new installs use it from the first scan.
* Fixed a crash when tapping the view after the ID Capture mode was removed from the data capture context.
* Fixed South African driving licenses failing to scan when the barcode contains a vehicle restriction issue date without a day.
* Fixed [`FullDocumentScanner`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/physical-document-scanner.html#class-scandit.datacapture.id.FullDocumentScanner) returning no MRZ result for the US Border Crossing Card. The result now combines the VIZ and the MRZ.
* Fixed IdCapture.externalTransactionId being cleared when new settings were applied. Scans after the settings change were reported without the ID.

#### Smart Label Capture

* Fixed expiry and packing date fields accepting a numeric date that does not exist, such as `BEST BEFORE 32/13/2027`. Such a date is now rejected instead of being returned as the field value.
* Changed the month of a captured date field to be reported with the month name as it was read from the label, in its original language and letter case, rather than a normalized lowercase English abbreviation. `10 Ene 2026` yields the month text `Ene` instead of `jan`, and the field text `10.Ene.2026` instead of `10.jan.2026`. A zero read in place of the letter `o` is still corrected, so `N0V` yields `NOV`. The numeric month is unaffected—compare against it instead of the text to branch on a month.
* Fixed label capture with Data Matrix enabled stalling on the multithreaded build with the default settings.
* Fixed a crash that could occur when the adaptive recognition result type was changed while a scan was still being processed
* Fixed the built-in hint/notification banner (for example, the 'scanning paused' message) spanning edge-to-edge instead of staying centered when the device is in landscape orientation
* Fixed expiry and packing date fields missing a date written day first with a space before the month name, such as `BEST BEFORE 25 MAR 2027`.

#### Core

* Fixed the camera preview appearing shrunk with a large margin on Safari for iOS 27, caused by a WebKit regression
* Fixed a crash that terminated the app when a camera frame used a pixel layout the SDK cannot convert, for example frames produced by the camera image-injection features of automated testing services. Such frames are now skipped with a warning instead
* Fixed an issue where on iOS the sound was sometimes not correctly reproduced at the first scan
* Updated Emscripten from 5.0.3 to 5.0.7

## 8.6.3

**Released**: November 19, 2026

### Performance Improvements

#### Id

* Optimized the capture of AAMVA documents: when no [`IdImageType.CroppedDocument`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/id-image-type.html#value-scandit.datacapture.id.IdImageType.CroppedDocument) image is required, the back-side scans as fast as when only scanning the back with [`SingleSideScanner`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/physical-document-scanner.html#class-scandit.datacapture.id.SingleSideScanner).
* Improved the performance of the back-side VIZ capture.

### Bug Fixes

#### Id

* Fixed [`AamvaBarcodeVerifier.verify()`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/aamva-barcode-verifier.html#method-scandit.datacapture.id.AamvaBarcodeVerifier.VerifyCapturedIdAsync) never resolving for expired, non-US or barcode-less IDs; it now resolves with an error.

#### Core

* Fixed an issue on iOS 27 where the camera preview could appear shrunk, with a large margin around it, in every iPhone browser, including Chrome for iOS and in-app web views, and in Safari after the camera resumed (for example, after closing a result screen). The issue was caused by a WebKit regression: https://bugs.webkit.org/show_bug.cgi?id=324317.

## 8.6.2

**Released**: October 26, 2026

### Bug Fixes

#### Barcode

* Fixed an issue with MicroQR that prevented improvements for rotated codes and codes with cluttered backgrounds from being available in production builds.
* Fixed a visual bug where dragging the SparkScan trigger button or mini preview could leave stale shadow marks on screen in Safari on iOS.
* Fixed an issue that could increase the time to scan when only QR or Data Matrix is enabled and there are more than 8 codes in the frame while using Barcode Tracking, Barcode AR, Barcode Pick, Barcode Find and Label Capture.

#### Id

* Fixed an issue on Safari for iOS 27 where the camera preview could appear shrunk, with a large margin around it, after the camera resumed (for example after closing a result screen). The issue was caused by a WebKit regression.

#### Core

* Fixed the viewfinder becoming misaligned with the camera preview after changing the browser zoom level or resizing the window.
* Updated Emscripten from 5.0.3 to 5.0.7, which fixes a pthread syscall-proxying race that could cause crashes or hangs in threaded WebAssembly builds.

## 8.6.1

**Released**: October 1, 2026

### New Features

#### Id

* Visa VIZ results for Canadian visa stickers now report the full 10-character number in [`VIZResult.visaNumber`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/viz-result.html#property-scandit.datacapture.id.VizResult.VisaNumber) (the MRZ result remains truncated).

### Bug Fixes

#### Barcode

* Fixed a QR scanning accuracy regression introduced in 8.6 for codes with degraded finder patterns (round, dotted, curved, bent, damaged) in single-barcode scanning.
* Rectangular Micro QR: Fixed a rare crash during detection of codes whose finder pattern covers a large part of the frame, such as when scanning at very close range.
* Fixed a Data Matrix scanning accuracy regression introduced in 8.4.0 for codes scanned with the `direct_part_marking_mode` symbology extension.
* Fixed Data Matrix codes not being read when their encoder ends the data with an Unlatch codeword followed by more than one pad codeword.
* Fixed a 1D symbology scan regression from SDK 5.19 for codes with colored backgrounds, such as dark print on a saturated label.
* Fixed SparkScan selection highlight brushes not applying until the next selection cycle.
* Fixed a bug that caused SparkScan to crash when using SmartScanSelection.
* Fixed the SparkScan mini preview not being draggable.
* Fixed the barcode duplicate filter explicitly set to -2 under SelectionMode On not being respected and being incorrectly relaxed to 0.
* Fixed MatrixScan AR info annotations so that replacing a header, footer, icon or body replaces it instead of adding a second one, and setting it to null removes it. [`BarcodeArPopoverAnnotationButton.text`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/barcode-ar-popover-annotation.html#property-scandit.datacapture.barcode.ar.ui.BarcodeArPopoverAnnotationButton.Text) now returns the button's label instead of an empty string.
* Fixed a placement problem with [`BarcodeArStatusIconAnnotation`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/barcode-ar-status-icon-annotation.html#class-scandit.datacapture.barcode.ar.ui.BarcodeArStatusIconAnnotation) when the barcode rotates.
* Fixed [`BarcodeArAnnotationAnchor`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/barcode-ar-annotation.html#enum-scandit.datacapture.barcode.ar.ui.BarcodeArAnnotationAnchor) not being available at runtime, which made a custom BarcodeAr annotation ignore its anchor. The default placement now also matches native, above the tracked barcode instead of below it.
* Fixed BarcodeFind overwriting the zoom levels of the camera settings it was given: a [`BarcodeFindView`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/barcode-find-view.html#class-scandit.datacapture.barcode.find.ui.BarcodeFindView) created with custom CameraSettings now runs on the zoom levels it was configured with. BarcodeFind's recommended camera settings now report the .5x/1x levels, matching iOS and Android.

#### Id

* Fixed the 2026 Oklahoma driver's license not returning the Jurisdiction and JurisdictionIso fields.
* Updated the bundled ID Validate model to `8.0.20260626`, which fixes valid Ohio driver's licenses (OH0901DL format) being reported as forged by ID Validate. This model was previously delivered over the air; it is now included in the SDK, so new installs use it from the first scan.

#### Core

* Fixed scanning silently stopping after the browser released the page's WebGL context, while the camera preview kept rendering.
* Fixed a crash that terminated the app when a camera frame used a pixel layout the SDK cannot convert, for example frames produced by the camera image-injection features of automated testing services. Such frames are now skipped with a warning instead.
* Fixed ScanditIcon not rendering a background stroke by default when a background shape and stroke color were both configured, matching iOS and Android.

## 8.6.0

**Released**: August 31, 2026

### New Features

#### Barcode

* [`BarcodeArResponsiveAnnotation`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/barcode-ar-responsive-annotation.html#class-scandit.datacapture.barcode.ar.ui.BarcodeArResponsiveAnnotation) now takes a map of distance thresholds to annotations, so a barcode can show a different annotation at any number of distances instead of only close-up and far-away. The previous two-state API is deprecated, see Deprecations below.
* Extended BarcodeBatch on Android so that setting the overlay brush to null clears the highlights of tracked barcodes, matching iOS.
* Extended the support for DotCode features by adding support for:
  - Extended Channel Interpretation (ECI). Symbols that switch character sets (for example to Cyrillic or another code page) now report the correct per-segment encoding. As part of this, the default character set for DotCode is now reported as ISO 8859-1 instead of ASCII.
  - Message envelopes as defined in ISO/IEC 15434.
  - Structured append. DotCode has no file ID, so segments are not automatically grouped by the buffered barcode session.

#### Id

* Visa MRZ results now report country-specific additional details such as [`MRZResult.visaNumber`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/mrz-result.html#property-scandit.datacapture.id.MrzResult.VisaNumber), [`MRZResult.visaNumberOfEntries`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/mrz-result.html#property-scandit.datacapture.id.MrzResult.VisaNumberOfEntries), [`MRZResult.visaMultipleEntries`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/mrz-result.html#property-scandit.datacapture.id.MrzResult.VisaMultipleEntries) and [`MRZResult.visaDurationInDays`](https://docs.scandit.com/data-capture-sdk/web/id-capture/api/mrz-result.html#property-scandit.datacapture.id.MrzResult.VisaDurationInDays).
* Extended the VizDocumentScanner sanitizer restriction to run all sanitizers for front-and-back captures and only reject on front-only captures, so front-side VIZ field corrections are no longer lost in double-sided captures.

#### Smart Label Capture

* Restored SIMD support in WebAssembly for iOS 26, recovering performance across all capture modes, most noticeably Label Capture.
* [BETA] Added shipping-label support ([`AdaptiveRecognitionResultType.ShippingLabel`](https://docs.scandit.com/data-capture-sdk/web/label-capture/api/adaptive-recognition-result-type.html#value-scandit.datacapture.label.AdaptiveRecognitionResultType.ShippingLabel), [`Carrier`](https://docs.scandit.com/data-capture-sdk/web/label-capture/api/carrier.html#enum-scandit.datacapture.label.Carrier), [`ShippingLabelScanningResult`](https://docs.scandit.com/data-capture-sdk/web/label-capture/api/shipping-label-scanning-result.html#class-scandit.datacapture.label.ShippingLabelScanningResult)) to adaptive recognition.
* Added a new sample to quickly test and integrate Smart Label Capture to read and validate price shelf labels against a database - showing live AR overlays based on the match and mismatch of the content.
* Added support for label definitions that use the "semantics" feature on fields of both type "barcode" and "text" simultaneously; previously only one of the two types could use it at once.

#### Core

* Added support in the GS1 parser for the telecom Application Identifiers 8040 (IMEI), 8041 (IMEI2), 8042 (eSIM/EID), and 8043 (pSIM), so GS1 codes carrying them parse instead of being rejected as unrecognized.
* Added support for parsing the 2D-DOC (French 2D-Doc / ANTS) data format.
* Added more detailed error reporting when required resources are missing.
* Added HTTPS as the default protocol for SDK samples, so you can open and test a sample directly on a device without setting up an HTTPS tunnel.
* Added the [`DataCaptureView.setProperty`](https://docs.scandit.com/data-capture-sdk/web/core/api/ui/data-capture-view.html#method-scandit.datacapture.core.ui.DataCaptureView.SetProperty) method.
* Added [`CameraSwitchControl.behavior`](https://docs.scandit.com/data-capture-sdk/web/core/api/ui/camera-switch-control.html#property-scandit.datacapture.core.ui.CameraSwitchControl.Behavior) to choose between cycling through all cameras (Cycle) or flipping between front and back (Flip).
* Added a default camera frame rate cap of 30 fps, configurable via CameraSettings.maxFrameRate.
* Added LicenseInfo.allowedModes, exposing the set of capture modes a license key permits via the new CaptureMode enum.
* Added [`Camera.getAllWithPermissionState()`](https://docs.scandit.com/data-capture-sdk/web/core/api/camera.html#method-scandit.datacapture.core.Camera.GetAllWithPermissionState), which returns the available cameras together with the current camera PermissionState (granted, denied, or prompt). This lets you distinguish an empty camera list caused by the absence of cameras on the device from one caused by the user denying camera access.
* Added a UMD build alongside the ESM build.
* Added support for reading camera frames directly into a SharedArrayBuffer in supported environments (currently Chrome or Firefox, when pthread is enabled), avoiding an extra copy.

### Performance Improvements

#### Barcode

* Reduced the false positive rate for EAN13, UPCA, EAN8, and UPC-E.
* Improved ITF decoding robustness, reducing the number of unscanned codes. On our internal datasets, we measured an improvement of more than 20% true positives.
* Improved MicroQR decoding for rotated codes and cluttered backgrounds. On our internal datasets, we measured an improvement of more than 40% true positives.

#### Id

* Improved PDF417 scanning on Quebec, Alaska, and Oklahoma driver’s licenses.

### Behavioral Changes

#### Barcode

* Changed the default highlight brush in SparkScan and Barcode Capture.
* Updated recommended camera settings for MatrixScan Batch, Find, Pick, Sequence, and AR, now using UHD4K resolution with a 16:9 aspect ratio.
* Enabled detection and decoding of mirrored MaxiCodes by default. Previously this required enabling the symbology extension `mirrored`, which has been removed.
* Limited the GS1 format flag for DotCode to genuine GS1 openings (a leading digit pair without FNC1) per AIM DotCode v3.0, instead of defaulting all symbols to GS1.
* Disabled enhanced low-resolution scanning of QR codes (introduced in 8.5.0) for MatrixScan modes. Customers who need this feature should contact Scandit support.

### Bug Fixes

#### Barcode

* Fixed rare cases where DotCode Code Set C symbols using the date/lot macro decoded to incorrect data due to a dropped leading zero in a digit pair.
* Fixed a regression where short ITF codes with low wide/narrow ratio were not decoded.

#### Id

* Improved the DLID parser, fixing previously unparsable codes found in analytics.
* Resolved a duplicate Objective-C class registration that could trigger spurious casting failures or crashes when an app links both ScanditCaptureCore and ScanditIdCapture.

#### Smart Label Capture

* Fixed a bug where the receipt scanning overlay and validation flow overlay could not be used on the same mode instance.
* Fixed several LabelCapture debug-app scenarios (Point To Scan - Dates, EU Driver License Back Side, Mixed Semantics) that failed to scan.
* Fixed prebuilt date fields to recognize Spanish month abbreviations. The abbreviations `ene`, `abr`, `ago`, and `dic` are newly supported; the remaining Spanish abbreviations already resolved because they match their English form. The expiry-date anchor additionally recognizes common Spanish expiry terms such as `caducidad`, `vencimiento`, `consumir antes`, and `consumo preferente`.

#### Core

* Fixed a SequenceFrameSource occasionally delivering the same frame to its listeners twice.
* Fixed a race condition in SimplePropertyBehaviorSubject where mutating the subscriber list during a callback could cause crashes or missed notifications.
* Fixed a crash when the Scandit analytics server returned an out-of-range retry timeout.
* Fixed pinch-to-zoom and swipe-to-zoom becoming unresponsive after the browser interrupted a touch gesture, and duplicated tap and zoom handling after a data capture view was re-attached.
* Fixed a memory leak that could make the browser tab run out of memory and crash when the data capture context was disposed and created again repeatedly.

### Deprecations

#### Barcode

* Deprecated the two-state [`BarcodeArResponsiveAnnotation`](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/barcode-ar-responsive-annotation.html#class-scandit.datacapture.barcode.ar.ui.BarcodeArResponsiveAnnotation) API in favor of a new configurable annotationsByThreshold map that supports more than two distance states; the previous two-state API remains available.
