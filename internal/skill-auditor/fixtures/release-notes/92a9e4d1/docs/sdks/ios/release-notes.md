---
description: "Release notes and updates for the Scandit iOS SDK."
toc_max_heading_level: 3
displayed_sidebar: iosSidebar
hide_title: true
title: Release Notes
pagination_prev: null
framework: ios
keywords:
  - ios
product: platform
topic_type: release-notes
canonical_id: scandit.platform.release-notes
---

## 8.7.0-beta.1

**Released**: October 22, 2026

### New Features

#### Barcode

* Added support for the Han Xin Code symbology (`SC_SYMBOLOGY_HAN_XIN`)
* Added structured append support to MaxiCode. The "m of n" sequencing metadata is now no longer part of the barcode data.
* Added an AdaptiveRecognitionServiceListener that can be attached to the BarcodeCapture and BarcodeCount modes to be notified of adaptive recognition responses and errors. Each callback carries the originating frame's AdaptiveRecognitionFrameMetadata (frame ID and recognized barcodes), so an asynchronously delivered outcome can be correlated back to its frame. On the Web SDK the listener is available on BarcodeCapture only
* Extended BarcodeArResponsiveAnnotation to accept any BarcodeArAnnotation (info, popover, status icon, or custom) per distance state, not just BarcodeArInfoAnnotation
* Changed the BarcodeCount Scan Preview so that highlights for barcodes that are no longer present are removed promptly instead of persisting while engine results are being dropped
* Added BarcodeSequenceScanAreaRestrictionSettings to restrict MatrixScan Sequence scanning to an adjustable horizontal band of the camera preview
* Changed MatrixScan Sequence so that the area outside the scan area restriction band is dimmed with the dimming color instead of blurred, so content outside the band stays visible
* Added BarcodeSequenceView.highlightProvider to MatrixScan Sequence, which lets you supply your own view for the highlight drawn over each sequenced barcode, replacing the built-in circle
* Added the possibility to verify a sequenced shelf module using BarcodeSequence

#### Id

* Extended the ID rejection API to reject documents based on passport type with rejectPassportTypes, and added a new PassportType, EmergencyTravelDocument
* Added PassportType.EmergencyTravelDocument and split PU-prefixed passport MRZs out of Emergency. The same change is now exposed on the frameworks
* Added VIZ support for the front of the 2026 Alberta driver's license and of the 2026 Nebraska driver's license and ID card, including the versions for minors.
* Added VIZ support for the front of the 2026 Hawaii driver's license and ID card, including the under-21 driver's license.
* Added a convenience conversion from IdCaptureRegion to ISO code as public API
* ID Validate now verifies the digital signature in the barcode of California driver's licenses and ID cards issued since October 2025. A valid signature confirms the barcode as authentic; a missing or invalid signature is reported as forged.

#### Smart Label Capture

* Added LabelCaptureSettings languages and the LabelCaptureLanguage enum (English, Spanish) to restrict prebuilt field recognition to the labels' languages. Spanish labels now also recognize full month names such as "15 de enero de 2026"
* Changed date fields to report the month text as it was read from the label, in its original language and letter case, instead of a normalized English abbreviation

#### Core

* Added the parser C API (`sc_parser_new_with_context`, `sc_parser_parse_string`, `sc_parser_set_options`, `sc_parser_free` and the `ScParserResult` accessors) to the Android and iOS low-level SDKs, which previously built it for Linux only although its headers shipped on every platform. The Data Capture SDK is unaffected: it exposes its own parser API.
* Added a ProductionMetrics object that can be created from the DataCaptureContext and allows the registration of a MetricsSink for tracking usage metrics along with custom app events. For example, a CameraConfigMetrics payload for the CameraConfig metric group, with the preferred VideoResolution, the focus strategy and the desired and current camera settings.
* Added Camera.isTorchLevelAvailable to check whether the camera can adjust its torch intensity while running
* Optimized rendering so that idle viewfinders (target aimer and laserline) no longer force a continuous render loop when nothing is animating

### Performance Improvements

#### Barcode

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

#### Id

* Spanish residence permits now return the NIE in both `VizResult.personalIdNumber` and `VizResult.documentAdditionalNumber`. Previously only one of the two carried it.

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
  - Fixed the file ID of an Aztec structured append symbol whose optional message ID field is absent. `sc_barcode_get_file_id` returned the placeholder `DEFAULT` and merged unrelated sequences; it now returns an empty string, and such segments are no longer automatically grouped.
  - Fixed the character encoding reported for Aztec byte shift data that follows an ECI.
* Fixed a scan regression from SDK 5.19 for 1D codes with colored backgrounds, such as dark print on a saturated label.
* Fixed a rare out-of-bounds image read while detecting a code that touches the right or bottom image border.
* Fixed the missing error report when a symbology's `ocr_fallback` extension is enabled without the ScanditLabelCaptureText module: the data capture context now reports a Missing Resource error naming the resources that could not be loaded, and barcode scanning continues without OCR fallback.
* Fixed a UI glitch when switching Selection Mode from On to Auto in BarcodeCapture.
* Fixed BarcodeArViewSettings.soundEnabled and hapticEnabled being ignored when the view settings were updated after the BarcodeAr view was created.
* Fixed a camera freeze when an app alternates MatrixScan Count's scan preview with another camera-backed mode. Returning to the scan preview could leave the camera unresponsive for 10-15 seconds.
* Fixed MatrixScan Count losing its counted barcodes when recognition is interrupted, for example by opening Control Center. Scanning a retained barcode again counts it again.

#### Id

* Fixed the 2026 Oklahoma driver's license not returning `issuingJurisdiction` and `issuingJurisdictionIso`
* Updated the bundled ID Validate model to `8.0.20260626`, which fixes valid Ohio driver's licenses (OH0901DL format) being reported as forged by ID Validate. This model was previously delivered over the air; it is now included in the SDK, so new installs use it from the first scan.
* Fixed iOS reporting error 3072 instead of 33805 when the license key does not include VIZ scanning, matching Android
* Fixed a crash when tapping the view after the ID Capture mode was removed from the data capture context.
* Fixed South African driving licenses failing to scan when the barcode contains a vehicle restriction issue date without a day.
* Fixed FullDocumentScanner returning no MRZ result for the US Border Crossing Card. The result now combines the VIZ and the MRZ.
* Fixed IdCapture.externalTransactionId being cleared when new settings were applied. Scans after the settings change were reported without the ID.
* Fixed a rare crash during text recognition

#### Smart Label Capture

* Fixed expiry and packing date fields accepting a numeric date that does not exist, such as `BEST BEFORE 32/13/2027`. Such a date is now rejected instead of being returned as the field value.
* Changed the month of a captured date field to be reported with the month name as it was read from the label, in its original language and letter case, rather than a normalized lowercase English abbreviation. `10 Ene 2026` yields the month text `Ene` instead of `jan`, and the field text `10.Ene.2026` instead of `10.jan.2026`. A zero read in place of the letter `o` is still corrected, so `N0V` yields `NOV`. The numeric month is unaffected—compare against it instead of the text to branch on a month.
* Fixed the LabelCapture validation flow staying idle when returning to a screen that keeps the mode enabled; a paused or finished flow now survives the navigation round trip, and validation flow listener removal takes effect
* Fixed LabelCaptureValidationFlowOverlay ignoring settings applied before the overlay was added to a DataCaptureView
* Fixed a crash that could occur when the adaptive recognition result type was changed while a scan was still being processed

#### Core

* Fixed a crash that terminated the app when a camera frame used a pixel layout the SDK cannot convert, for example frames produced by the camera image-injection features of automated testing services. Such frames are now skipped with a warning instead

## 8.6.2

**Released**: October 26, 2026

### Performance Improvements

#### Barcode

* Improved tracking for long trays in MatrixScan Sequence
* Improved stability of tray ordering in MatrixScan Sequence

### Behavioral Changes

#### Barcode

* Changed MatrixScan Sequence to dim the area outside the scan area restriction band with the dimming color instead of blurring it, so content outside the band stays visible.

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

#### Barcode

* Added BarcodeSequenceScanAreaRestrictionSettings to restrict MatrixScan Sequence scanning to an adjustable horizontal band of the camera preview, so only barcodes inside the band are sequenced.
* Added BarcodeSequenceView.highlightProvider to MatrixScan Sequence, letting you supply your own view for the highlight drawn over each sequenced barcode instead of the built-in circle.

#### Id

* Visa VIZ results for Canadian visa stickers now report the full 10-character number in `VizResult.visaNumber` (the MRZ result remains truncated).

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

## 8.6.0

**Released**: August 31, 2026

### New Features

#### Barcode

* The [MatrixScan Sequence simple sample](https://github.com/Scandit/datacapture-ios-samples/tree/master/03_Advanced_Batch_Scanning_Samples/06_Sequence/MatrixScanSequenceSimpleSample) is now publicly available, showing the minimum setup needed to run MatrixScan Sequence.
* MatrixScan Sequence: introduced several new configurations to adapt the sequencing flow.
  - `initialOrderOnShelf` and `initialOrderOnTray` resume scanning from a previous session (already available since 8.5.1).
  - `shelfSequencingOrientation` sets the accepted device orientation, defaulting to `.landscapeOnly`; set `.portraitOnly` or `.any` to enable portrait or any orientation, and the rotate-device prompt's default text follows the setting.
* [BETA] MatrixScan Count can now group barcodes by the physical label they share. Set barcodeCountSettings.AutomaticClusteringMethod to AutomaticClusteringMethod.Label to enable it: the barcodes within each label boundary get associated into a single cluster, so a product carrying several barcodes counts as one item.
* When highlights inside a MatrixScan Count cluster would overlap, the cluster now collapses into a single badge showing how many barcodes it contains, instead of drawing every highlight on top of the others. This also applies in Scan Preview mode.
* Scan Preview now supports two controls that were previously available only in the standard mode: the torch button, shown via `BarcodeCountView.shouldShowTorchControl`, and the accept/reject popover for barcodes not in the list, enabled via `BarcodeCountNotInListActionSettings.enabled`.
* Added an API to customize the text of the hint shown when a new scan group starts (`BarcodeCountView.setTextForNewGroupHint`).
* BarcodeArResponsiveAnnotation now takes a map of distance thresholds to annotations, so a barcode can show a different annotation at any number of distances instead of only close-up and far-away. The previous two-state API is deprecated, see Deprecations below.
* Extended BarcodeBatch on Android so that setting the overlay brush to null clears the highlights of tracked barcodes, matching iOS.
* Extended the support for DotCode features by adding support for:
  - Extended Channel Interpretation (ECI). Symbols that switch character sets (for example to Cyrillic or another code page) now report the correct per-segment encoding. As part of this, the default character set for DotCode is now reported as ISO 8859-1 instead of ASCII.
  - Message envelopes as defined in ISO/IEC 15434.
  - Structured append. DotCode has no file ID, so segments are not automatically grouped by the buffered barcode session.

#### Id

* Visa MRZ results now report country-specific additional details such as `MrzResult.visaNumber`, `MrzResult.visaNumberOfEntries`, `MrzResult.visaMultipleEntries` and `MrzResult.visaDurationInDays`.
* Added IdCaptureSettings.notifyOnSideCapture, which fires the capture callback after each side of a multi-sided document, and CapturedId.isCapturingComplete, which distinguishes a partial (single-side) result from a complete one.
* Added `setRepeatAsync` on `SDCImageFrameSource`. It determines whether the frame source keeps re-emitting its frames after all of them have been processed. Setting this to true makes a still image behave like a continuous camera feed, giving the recognizer the multiple passes over the image it generally needs.
* Added an [ID Capture image upload sample](https://github.com/Scandit/datacapture-ios-samples/tree/master/02_ID_Scanning_Samples/IdCaptureImageUploadSample) that demonstrates scanning ID documents from still images or PDF files on the device instead of using the live camera.
* Added MobileDocumentDataElement::SignatureUsualMark and MobileDocumentResult.signature to allow capture of signature images from ISO mDL documents.
* Extended the VizDocumentScanner sanitizer restriction to run all sanitizers for front-and-back captures and only reject on front-only captures, so front-side VIZ field corrections are no longer lost in double-sided captures.

#### Smart Label Capture

* [BETA] Added shipping-label support (`AdaptiveRecognitionResultType.shippingLabel`, `Carrier`, `ShippingLabelScanningResult`) to adaptive recognition.
* Added a new sample to quickly test and integrate Smart Label Capture to read and validate price shelf labels against a database - showing live AR overlays based on the match and mismatch of the content.
* Added support for label definitions that use the "semantics" feature on fields of both type "barcode" and "text" simultaneously; previously only one of the two types could use it at once.

#### Core

* Added support in the GS1 parser for the telecom Application Identifiers 8040 (IMEI), 8041 (IMEI2), 8042 (eSIM/EID), and 8043 (pSIM), so GS1 codes carrying them parse instead of being rejected as unrecognized.
* Added support for parsing the 2D-DOC (French 2D-Doc / ANTS) data format.
* Added more detailed error reporting when required resources are missing.
* Added LicenseInfo.allowedModes, exposing the set of capture modes a license key permits via the new CaptureMode enum.
* Added support for reading camera frames directly into a SharedArrayBuffer in supported environments (currently Chrome or Firefox, when pthread is enabled), avoiding an extra copy.

### Performance Improvements

#### Barcode

* Reduced the false positive rate for EAN13, UPCA, EAN8, and UPC-E.
* Improved ITF decoding robustness, reducing the number of unscanned codes. On our internal datasets, we measured an improvement of more than 20% true positives.
* Improved MicroQR decoding for rotated codes and cluttered backgrounds. On our internal datasets, we measured an improvement of more than 40% true positives.

#### Id

* Improved performance for the Irish Garda Age Card.
* Improved PDF417 scanning on Quebec, Alaska, and Oklahoma driver’s licenses.

### Behavioral Changes

#### Barcode

* Changed the default highlight brush in SparkScan and Barcode Capture.
* Updated recommended camera settings for MatrixScan Batch, Find, Pick, Sequence, and AR, now using UHD4K resolution with a 16:9 aspect ratio.
* MatrixScan Count uses a new default colour for scanned (counted) barcodes, chosen to meet accessibility contrast requirements. It applies to single scanned barcodes, to the barcodes inside a cluster, and to the cluster highlight itself. To keep your previous appearance, set the colour through the existing icon customization.
* MatrixScan Count now highlights each barcode inside a cluster individually and follows its live position.
* Enabled detection and decoding of mirrored MaxiCodes by default. Previously this required enabling the symbology extension `mirrored`, which has been removed.
* Limited the GS1 format flag for DotCode to genuine GS1 openings (a leading digit pair without FNC1) per AIM DotCode v3.0, instead of defaulting all symbols to GS1.
* Disabled enhanced low-resolution scanning of QR codes (introduced in 8.5.0) for MatrixScan modes. Customers who need this feature should contact Scandit support.

### Bug Fixes

#### Barcode

* Fixed a crash when clearing highlights or changing the scanning state on a MatrixScan Count mode that had been removed from its data capture context.
* Fixed an issue in MatrixScan Count Scan Preview where the not-in-list action popover overlapped the barcode instead of appearing next to it.
* Fixed an issue where navigating between capture modes that share a camera could leave the camera turned off. Camera-controlling scanner views now release the camera when they are dismissed, unless another mode is still using the shared camera.
* Fixed the MatrixScan Count not-in-list accept/reject popover not reflecting a custom accepted/rejected ScanditIcon when configured.
* Fixed logoStyle and logoAnchor having no effect in MatrixScan Count scan preview mode.
* Fixed MatrixScan Sequence losing the scanned data when the app was restored from the background while the sequence was paused.
* Fixed a visual artifact that could appear around the scan preview indicators in MatrixScan Count when using Scan Preview.
* Fixed rare cases where DotCode Code Set C symbols using the date/lot macro decoded to incorrect data due to a dropped leading zero in a digit pair.
* Fixed a regression where short ITF codes with low wide/narrow ratio were not decoded.

#### Id

* Fixed a crash that could occur when navigating away from a screen while a hint was displayed.
* Improved the DLID parser, fixing previously unparsable codes found in analytics.
* Fixed a crash caused by an edge case where XCTest called objc_copyClassList() while the ScanditIDC.xcframework was not linked.
* Resolved a duplicate Objective-C class registration that could trigger spurious casting failures or crashes when an app links both ScanditCaptureCore and ScanditIdCapture.
* Fixed an issue where the VLM scanning screen remained permanently displayed if IdCaptureSettings were applied mid-scan.

#### Smart Label Capture

* Fixed an issue where the software keyboard did not appear when editing fields in the LabelCapture validation flow.
* Fixed a bug where the receipt scanning overlay and validation flow overlay could not be used on the same mode instance.
* Fixed prebuilt date fields to recognize Spanish month abbreviations. The abbreviations `ene`, `abr`, `ago`, and `dic` are newly supported; the remaining Spanish abbreviations already resolved because they match their English form. The expiry-date anchor additionally recognizes common Spanish expiry terms such as `caducidad`, `vencimiento`, `consumir antes`, and `consumo preferente`.

#### Core

* Fixed a SequenceFrameSource occasionally delivering the same frame to its listeners twice.
* Fixed the camera preview appearing darker in single-scan modes after using a mode that applies its own exposure adjustment, such as SparkScan or MatrixScan Count.
* Fixed a race condition in SimplePropertyBehaviorSubject where mutating the subscriber list during a callback could cause crashes or missed notifications.
* Fixed EventsResponse::getRetryTimeoutInSeconds to return a fallback instead of aborting on out-of-range header values.

### Deprecations

#### Barcode

* Removed the deprecated Barcode Sequence view settings API; configure the view's settings directly on the view.
* Deprecated the alternative (accessible) color scheme for Barcode Count; it will be removed in a future release. The default color scheme now provides an accessible appearance, so you can remove the explicit setting.
* Deprecated the two-state BarcodeArResponsiveAnnotation API in favor of a new configurable annotationsByThreshold map that supports more than two distance states; the previous two-state API remains available.
