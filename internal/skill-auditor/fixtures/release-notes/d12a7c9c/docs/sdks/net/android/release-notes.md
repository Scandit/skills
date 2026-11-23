---
description: "Release notes for the Scandit Data Capture SDK on .NET Android: new features, changes, and fixes by version."
toc_max_heading_level: 3
displayed_sidebar: netAndroidSidebar
hide_title: true
title: Release Notes
pagination_prev: null
framework: net-android
keywords:
  - netAndroid
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
* Added an AdaptiveRecognitionServiceListener that can be attached to the BarcodeCapture and BarcodeCount modes to be notified of adaptive recognition responses and errors. Each callback carries the originating frame's AdaptiveRecognitionFrameMetadata (frame ID and recognized barcodes), so an asynchronously delivered outcome can be correlated back to its frame. On the Web SDK the listener is available on BarcodeCapture only
* Extended BarcodeArResponsiveAnnotation to accept an annotationsByThreshold map, so an annotation can switch between any number of distance-based states instead of only close-up and far-away
* Added the new types BarcodeInfo, StructuredAppendData, CompositeTypeDescription and Ean13UpcaClassification, and the new members [`Barcode.ModuleCountX`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode.html#property-scandit.datacapture.barcode.Barcode.ModuleCountX), [`Barcode.ModuleCountY`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode.html#property-scandit.datacapture.barcode.Barcode.ModuleCountY), [`Barcode.StructuredAppend`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode.html#property-scandit.datacapture.barcode.Barcode.IsStructuredAppend), Barcode.StructuredAppendData, [`Barcode.Create`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode.html#method-scandit.datacapture.barcode.Barcode.Create)(BarcodeInfo), [`BarcodeCaptureSettings.Create`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode-capture-settings.html#method-scandit.datacapture.barcode.BarcodeCaptureSettings.BarcodeCaptureSettings)(CapturePreset), [`BarcodeCaptureSettings.SetArucoDictionary()`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode-capture-settings.html#method-scandit.datacapture.barcode.BarcodeCaptureSettings.SetArucoDictionary), [`BarcodeCaptureOverlay.SelectionBrush`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-capture-overlay.html#property-scandit.datacapture.barcode.ui.BarcodeCaptureOverlay.SelectionBrush), [`SymbologyDescription.SupportedChecksums`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/symbology-description.html#property-scandit.datacapture.barcode.SymbologyDescription.SupportedChecksums) and [`SymbologySettings.OcrFallbackRegex`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/symbology-settings.html#property-scandit.datacapture.barcode.SymbologySettings.OcrFallbackRegex)
* Added [`SparkScanViewSettings.ScanningBehavior`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/spark-scan-view-settings.html#property-scandit.datacapture.barcode.spark.ui.SparkScanViewSettings.ScanningBehavior)/previewBehavior, SparkScanScanningMode.scanningBehavior/previewBehavior,SparkScanView.getScanningMode() and SparkScanViewUiListener.didChangeScanningMode

#### Id

* Extended the ID rejection API to reject documents based on passport type with rejectPassportTypes, and added a new PassportType, EmergencyTravelDocument
* Added [`PassportType.EmergencyTravelDocument`](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api/passport-type.html#value-scandit.datacapture.id.PassportType.EmergencyTravelDocument) and split PU-prefixed passport MRZs out of Emergency. The same change is now exposed on the frameworks
* Added VIZ support for the front of the 2026 Alberta driver's license and of the 2026 Nebraska driver's license and ID card, including the versions for minors.
* Added VIZ support for the front of the 2026 Hawaii driver's license and ID card, including the under-21 driver's license.
* Added the missing ID Capture APIs, so .NET for Android, .NET for iOS and MAUI now offer the same API as the native SDKs, including `RejectionTimeoutSeconds`, `NotifyOnSideCapture`, anonymized-field control, [`CapturedId.VisaNumber`](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api/captured-id.html#property-scandit.datacapture.id.CapturedId.VisaNumber) and `PassportNumber`, the visa fields and [`PassportType`](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api/passport-type.html#enum-scandit.datacapture.id.PassportType) on [`MrzResult`](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api/mrz-result.html#class-scandit.datacapture.id.MrzResult), more [`VizResult`](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api/viz-result.html#class-scandit.datacapture.id.VizResult) fields and the mDL signature image.
* ID Validate now verifies the digital signature in the barcode of California driver's licenses and ID cards issued since October 2025. A valid signature confirms the barcode as authentic; a missing or invalid signature is reported as forged.

#### Smart Label Capture

* Added [`LabelCaptureSettings.Builder()`](https://docs.scandit.com/data-capture-sdk/dotnet.android/label-capture/api/label-capture-settings.html#method-scandit.datacapture.label.LabelCaptureSettings.Builder) and LabelCaptureSettingsBuilder for fluent settings creation with AddLabel, SetHiddenProperty/SetHiddenProperties and SetLabelProperties, [`LabelDefinition.Builder()`](https://docs.scandit.com/data-capture-sdk/dotnet.android/label-capture/api/label-definition.html#method-scandit.datacapture.label.LabelDefinition.Builder) as the entry point to the existing LabelDefinitionBuilder, and ShippingLabelScanningResult (adaptive recognition), exposing barcodes, tracking ID, receiver address fields, and carrier, plus the Carrier enum and [`AdaptiveRecognitionResultType.ShippingLabel`](https://docs.scandit.com/data-capture-sdk/dotnet.android/label-capture/api/adaptive-recognition-result-type.html#value-scandit.datacapture.label.AdaptiveRecognitionResultType.ShippingLabel)

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

* Spanish residence permits now return the NIE in both [`VizResult.PersonalIdNumber`](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api/viz-result.html#property-scandit.datacapture.id.VizResult.PersonalIdNumber) and [`VizResult.DocumentAdditionalNumber`](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api/viz-result.html#property-scandit.datacapture.id.VizResult.DocumentAdditionalNumber). Previously only one of the two carried it.
* [`MrzResult.PassportType`](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api/mrz-result.html#property-scandit.datacapture.id.MrzResult.PassportType) now uses the ICAO meaning of the second letter of the MRZ document code only where it is reliable, and reports the new [`PassportType.Unknown`](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api/passport-type.html#value-scandit.datacapture.id.PassportType.Unknown) otherwise. Older passports from countries that used these letters differently no longer get a special type. For example, older Swiss passports with `PM` are now `National` instead of `Military`. Letters without an ICAO meaning now report `Unknown` instead of `National`. When the type is `National` or `Unknown`, nationality `XXA` gives `Stateless`, and `XXB` or `XXC` give `Refugee`. `Unknown` is only rejected if `rejectPassportTypes` lists it.

#### Core

* Removed the internal TinyIoC dependency. The TinyIoC MIT license text has been dropped from [`OpenSourceSoftwareLicenseInfo.LicenseText`](https://docs.scandit.com/data-capture-sdk/dotnet.android/core/api/open-source-software-license-info.html#property-scandit.datacapture.core.OpenSourceSoftwareLicenseInfo.LicenseText) accordingly

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
* Fixed MatrixScan Count losing its counted barcodes when recognition is interrupted, for example by opening Control Center. Scanning a retained barcode again counts it again.
* Fixed an issue that could increase the time to scan when only QR or Data Matrix is enabled and there are more than 8 codes in the frame while using Barcode Tracking, Barcode AR, Barcode Pick, Barcode Find and Label Capture.

#### Id

* Fixed the 2026 Oklahoma driver's license not returning `issuingJurisdiction` and `issuingJurisdictionIso`
* Updated the bundled ID Validate model to `8.0.20260626`, which fixes valid Ohio driver's licenses (OH0901DL format) being reported as forged by ID Validate. This model was previously delivered over the air; it is now included in the SDK, so new installs use it from the first scan.
* Fixed a crash when tapping the view after the ID Capture mode was removed from the data capture context.
* Fixed an error when selecting the UAE Esaad Card, UK Military ID, China Business Travel Permit (Hong Kong/Macau) or Irish Garda Age Card region-specific subtypes.
* Fixed South African driving licenses failing to scan when the barcode contains a vehicle restriction issue date without a day.
* Fixed FullDocumentScanner returning no MRZ result for the US Border Crossing Card. The result now combines the VIZ and the MRZ.
* Fixed [`IdCapture.ExternalTransactionId`](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api/id-capture.html#property-scandit.datacapture.id.IdCapture.ExternalTransactionId) being cleared when new settings were applied. Scans after the settings change were reported without the ID.

#### Smart Label Capture

* Fixed expiry and packing date fields accepting a numeric date that does not exist, such as `BEST BEFORE 32/13/2027`. Such a date is now rejected instead of being returned as the field value.
* Changed the month of a captured date field to be reported with the month name as it was read from the label, in its original language and letter case, rather than a normalized lowercase English abbreviation. `10 Ene 2026` yields the month text `Ene` instead of `jan`, and the field text `10.Ene.2026` instead of `10.jan.2026`. A zero read in place of the letter `o` is still corrected, so `N0V` yields `NOV`. The numeric month is unaffected—compare against it instead of the text to branch on a month.
* Fixed a crash that could occur when the adaptive recognition result type was changed while a scan was still being processed
* Fixed expiry and packing date fields missing a date written day first with a space before the month name, such as `BEST BEFORE 25 MAR 2027`.
* Fixed an issue where [`LabelCaptureSession.CapturedLabels`](https://docs.scandit.com/data-capture-sdk/dotnet.android/label-capture/api/label-capture-session.html#property-scandit.datacapture.label.LabelCaptureSession.CapturedLabels) kept returning the labels observed on the first read for the rest of the session, so listeners could see stale or empty results after a label was captured.

#### Core

* Fixed a bug in Camera API 1 that might cause a camera to show as STANDBY instead of OFF when another application takes over the device camera
* Fixed camera preview failures during a live settings change (for example, resolution): a rejected parameter update or a failed preview restart could leave the camera stopped or streaming mismatched frames; it now recovers or reports a consistent state
* Fixed the recovery from a failed camera wake-up in Camera API 1, which now restarts the camera reliably, including when the camera was started via standby
* Fixed a crash when starting the camera on devices whose camera reports zoom support without providing zoom ratios
* Fixed rapid torch toggles being dropped or applied twice when issued before the previous toggle was confirmed by the camera
* Fixed a memory leak where cleared weak references to torch and zoom listeners accumulated indefinitely in the camera's listener sets
* Fixed a crash that terminated the app when a camera frame used a pixel layout the SDK cannot convert, for example frames produced by the camera image-injection features of automated testing services. Such frames are now skipped with a warning instead
* Fixed several public API entry points that threw at runtime instead of working: Core.AimerViewfinder.DotColor (Android, StackOverflowException), Sound asset loading (Android), [`RectangularLocationSelection.CreateWithWidthAndAspectRatio`](https://docs.scandit.com/data-capture-sdk/dotnet.android/core/api/rectangular-location-selection.html#method-scandit.datacapture.core.RectangularLocationSelection.WithWidthAndAspectRatio)/CreateWithHeightAndAspectRatio (iOS and Android), and [`RectangularViewfinder.SetWidthAndAspectRatio`](https://docs.scandit.com/data-capture-sdk/dotnet.android/core/api/rectangular-viewfinder.html#method-scandit.datacapture.core.ui.RectangularViewfinder.SetWidthAndAspectRatio)/SetHeightAndAspectRatio (Android)
* Fixed an error thrown on iOS when passing an empty byte array to [`ArucoMarker.Create()`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/aruco-marker.html#method-scandit.datacapture.barcode.ArucoMarker.Create) or [`Parser.ParseRawData()`](https://docs.scandit.com/data-capture-sdk/dotnet.android/parser/api/parser.html#method-scandit.datacapture.parser.Parser.ParseRawData), which now matches the existing Android behavior
* Fixed the camera and torch switch controls not updating their accessibility labels on the main thread, so TalkBack announcements no longer misfire when the camera or torch state changes

## 8.6.2

**Released**: October 26, 2026

### Performance Improvements

#### Barcode

* Improved tracking for long trays in MatrixScan Sequence
* Improved stability of tray ordering in MatrixScan Sequence

### Bug Fixes

#### Barcode

* Fixed an issue with MicroQR that prevented improvements for rotated codes and codes with cluttered backgrounds from being available in production builds.
* Fixed an issue that could increase the time to scan when only QR or Data Matrix is enabled and there are more than 8 codes in the frame while using Barcode Tracking, Barcode AR, Barcode Pick, Barcode Find and Label Capture.

## 8.6.1

**Released**: October 1, 2026

### New Features

#### Id

* Visa VIZ results for Canadian visa stickers now report the full 10-character number in [`VizResult.VisaNumber`](https://docs.scandit.com/data-capture-sdk/dotnet.android/id-capture/api/viz-result.html#property-scandit.datacapture.id.VizResult.VisaNumber) (the MRZ result remains truncated).

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
* Updated the bundled ID Validate model to `8.0.20260626`, which fixes valid Ohio driver's licenses (OH0901DL format) being reported as forged by ID Validate. This model was previously delivered over the air; it is now included in the SDK, so new installs use it from the first scan.

#### Core

* Fixed a crash that terminated the app when a camera frame used a pixel layout the SDK cannot convert, for example frames produced by the camera image-injection features of automated testing services. Such frames are now skipped with a warning instead.
* Fixed customer archives for Capacitor, Cordova and React Native shipping unresolvable `workspace:*` dependency specifiers, so `npm install` now succeeds in the bundled samples.

## 8.6.0

**Released**: August 31, 2026

### New Features

#### Barcode

* MatrixScan Sequence: introduced several new configurations to adapt the sequencing flow.
  - `initialOrderOnShelf` and `initialOrderOnTray` resume scanning from a previous session.
  - `idleTimeout` sets the inactivity period in seconds before sequencing pauses automatically, defaulting to 10 seconds; 0 or less disables the automatic pause
* BarcodeArResponsiveAnnotation now takes a map of distance thresholds to annotations, so a barcode can show a different annotation at any number of distances instead of only close-up and far-away. The previous two-state API is deprecated, see Deprecations below.
* Added missing BarcodeAr .NET APIs: [`BarcodeArView.LogoAnchor`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-ar-view.html#property-scandit.datacapture.barcode.ar.ui.BarcodeArView.LogoAnchor) and [`BarcodeArView.LogoOffset`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-ar-view.html#property-scandit.datacapture.barcode.ar.ui.BarcodeArView.LogoOffset) to position the Scandit logo (iOS + Android); BarcodeArView.LogoStyle for minimal/extended logo style (iOS); BarcodeArView.ZoomControlOrientation for the zoom control's orientation (iOS); [`BarcodeArStatusIconAnnotation.Anchor`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-ar-status-icon-annotation.html#property-scandit.datacapture.barcode.ar.ui.BarcodeArStatusIconAnnotation.Anchor) plus the new BarcodeArStatusIconAnnotationAnchor enum (Top/Bottom/Left/Right) to anchor a status icon annotation (iOS + Android); and [`BarcodeArResponsiveAnnotation.CloseUpAnnotation`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-ar-responsive-annotation.html#property-scandit.datacapture.barcode.ar.ui.BarcodeArResponsiveAnnotation.CloseUpAnnotation) and [`BarcodeArResponsiveAnnotation.FarAwayAnnotation`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-ar-responsive-annotation.html#property-scandit.datacapture.barcode.ar.ui.BarcodeArResponsiveAnnotation.FarAwayAnnotation) to read the close-up/far-away annotation variations (iOS + Android).
* Added [`BarcodePickViewSettings.ZoomButtonPosition`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-pick-view-settings.html#property-scandit.datacapture.barcode.pick.ui.BarcodePickViewSettings.ZoomButtonPosition), ShowTorchButton, TorchButtonPosition, LogoAnchor, and LogoStyle (plus iOS TopLayoutAnchor and Android UiButtonsOffset); MinimumHighlightWidth and MinimumHighlightHeight on both Rectangular highlight styles; [`BarcodePickViewHighlightStyleRectangularWithIcons.StatusIconSettings`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-pick-view-highlight-style-rectangular-with-icons.html#property-scandit.datacapture.barcode.pick.ui.RectangularWithIcons.StatusIconSettings); and [`BarcodePickStatusIconStyle.WithIcon`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-pick-view-highlight-style-response.html#method-scandit.datacapture.barcode.pick.ui.BarcodePickStatusIconStyle.WithIcon)(ScanditIcon, string).
* Unified the .NET BarcodeCount API with native Android/iOS: added [`BarcodeCountStatus.ExpiringSoon`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode-count-status.html#value-scandit.datacapture.barcode.count.BarcodeCountStatus.ExpiringSoon), [`BarcodeCountView.ShouldShowStatusIconsOnScan`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-count-view.html#property-scandit.datacapture.barcode.count.ui.BarcodeCountView.ShouldShowStatusIconsOnScan)/LogoStyle/LogoAnchor, and a public BarcodeCountNotInListActionSettings() constructor.
* Added the missing BarcodeFind .NET APIs: BarcodeFindSession plus [`IBarcodeFindListener.OnSessionUpdated`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode-find-listener.html#method-scandit.datacapture.barcode.find.IBarcodeFindListener.OnSessionUpdated), the [`BarcodeFind.SessionUpdated`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode-find.html#property-scandit.datacapture.barcode.find.BarcodeFind.SessionUpdated) event, [`BarcodeFindView.LogoAnchor`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-find-view.html#property-scandit.datacapture.barcode.find.ui.BarcodeFindView.LogoAnchor)/LogoStyle, BarcodeFindItemSearchOptions raw-data and brush constructors/properties, and BarcodeFindViewSettings progress-bar color constructors and getters.
* Added missing BarcodeSelection .NET APIs: [`BarcodeSelectionSession.SelectUnselectedBarcodes()`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode-selection-session.html#method-scandit.datacapture.barcode.selection.BarcodeSelectionSession.SelectUnselectedBarcodes), [`BarcodeSelectionSettings.TapGestureForSelectionEnabled`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode-selection-settings.html#property-scandit.datacapture.barcode.selection.BarcodeSelectionSettings.TapGestureForSelectionEnabled) and SwipeGesturesEnabled, and the [`BarcodeSelectionSettings.Create`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode-selection-settings.html#method-scandit.datacapture.barcode.selection.BarcodeSelectionSettings.BarcodeSelectionSettings)(CapturePreset) factory.
* Added missing .NET BarcodeBatch and BarcodePick APIs: [`BarcodeBatchSettings.ExpectsOnlyUniqueBarcodes`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode-batch-settings.html#property-scandit.datacapture.barcode.batch.BarcodeBatchSettings.ExpectsOnlyUniqueBarcodes), [`BarcodeBatchSettings.SetArucoDictionary`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode-batch-settings.html#method-scandit.datacapture.barcode.batch.BarcodeBatchSettings.SetArucoDictionary)(ArucoDictionary), [`BarcodeBatchBasicOverlay.DotRadius`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-batch-basic-overlay.html#property-scandit.datacapture.barcode.batch.ui.BarcodeBatchBasicOverlay.DotRadius), the previously missing TrackedObject class (Location, Identifier, Data), and [`BarcodePickSession.TrackedObjects`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/barcode-pick-session.html#property-scandit.datacapture.barcode.pick.BarcodePickSession.TrackedObjects)/AddedObjects exposing the new TrackedObject.
* Added BarcodeSequence support to .NET, with MAUI consumption.
* Added BarcodeGenerator for .NET to generate barcode/2D-code images from text or byte[] at a configurable width, with foreground/background color customization. Supports Code 39, Code 128, EAN-13, UPC-A, Interleaved 2 of 5, QR Code, Data Matrix, Aztec, and PDF417.
* Added various Barcode AR APIs:
  - [`BarcodeArPopoverAnnotation.Anchor`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-ar-popover-annotation.html#property-scandit.datacapture.barcode.ar.ui.BarcodeArPopoverAnnotation.Anchor) and the [`BarcodeArPopoverAnnotationAnchor`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-ar-popover-annotation.html#enum-scandit.datacapture.barcode.ar.ui.BarcodeArPopoverAnnotationAnchor) enum (`Left`/`Right`/`Bottom`/`Top`, defaults to `Bottom`).
  - [`BarcodeArCircleHighlight.Pulsing`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-ar-highlight-circle.html#property-scandit.datacapture.barcode.ar.ui.BarcodeArCircleHighlight.IsPulsing) to enable/disable the pulsing highlight animation.
  - [`BarcodeArAnnotationTrigger.BarcodeScan`](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api/ui/barcode-ar-annotation.html#value-scandit.datacapture.barcode.ar.ui.BarcodeArAnnotationTrigger.BarcodeScan), showing AR annotations immediately on scan with no tap-to-toggle.
  - `IBarcodeArFilter` functionality.
* Extended BarcodeBatch on Android so that setting the overlay brush to null clears the highlights of tracked barcodes, matching iOS.
* Extended the support for DotCode features by adding support for:
  - Extended Channel Interpretation (ECI). Symbols that switch character sets (for example to Cyrillic or another code page) now report the correct per-segment encoding. As part of this, the default character set for DotCode is now reported as ISO 8859-1 instead of ASCII.
  - Message envelopes as defined in ISO/IEC 15434.
  - Structured append. DotCode has no file ID, so segments are not automatically grouped by the buffered barcode session.

#### Id

* Extended the VizDocumentScanner sanitizer restriction to run all sanitizers for front-and-back captures and only reject on front-only captures, so front-side VIZ field corrections are no longer lost in double-sided captures.

#### Smart Label Capture

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

* Improved PDF417 scanning on Quebec, Alaska, and Oklahoma driver’s licenses.

### Behavioral Changes

#### Barcode

* Changed the default highlight brush in SparkScan and Barcode Capture.
* Updated recommended camera settings for MatrixScan Batch, Find, Pick, Sequence, and AR, now using UHD4K resolution with a 16:9 aspect ratio.
* MatrixScan Count uses a new default colour for scanned (counted) barcodes, chosen to meet accessibility contrast requirements. It applies to single scanned barcodes, to the barcodes inside a cluster, and to the cluster highlight itself. To keep your previous appearance, set the colour through the existing icon customization.
* Enabled detection and decoding of mirrored MaxiCodes by default. Previously this required enabling the symbology extension `mirrored`, which has been removed.
* Limited the GS1 format flag for DotCode to genuine GS1 openings (a leading digit pair without FNC1) per AIM DotCode v3.0, instead of defaulting all symbols to GS1.
* Disabled enhanced low-resolution scanning of QR codes (introduced in 8.5.0) for MatrixScan modes. Customers who need this feature should contact Scandit support.

### Bug Fixes

#### Barcode

* Fixed a crash when clearing highlights or changing the scanning state on a MatrixScan Count mode that had been removed from its data capture context.
* Fixed a bug with the highlight colors of BarcodeCount clusters.
* Fixed the MatrixScan Count not-in-list accept/reject popover not reflecting a custom accepted/rejected ScanditIcon when configured.
* Fixed MatrixScan AR to adapt to the device UI scale.
* Fixed rare cases where DotCode Code Set C symbols using the date/lot macro decoded to incorrect data due to a dropped leading zero in a digit pair.
* Fixed a regression where short ITF codes with low wide/narrow ratio were not decoded.

#### Id

* Improved the DLID parser, fixing previously unparsable codes found in analytics.
* Hardened dependency resolution for Android native samples.
* Resolved a duplicate Objective-C class registration that could trigger spurious casting failures or crashes when an app links both ScanditCaptureCore and ScanditIdCapture.
* Fixed a crash (NoClassDefFoundError: kotlinx/serialization/json/JsonKt) when starting ID Capture in apps targeting net10.0-android, caused by the kotlinx-serialization-json dependency not being packed into the app. ID Capture now scans correctly on net10.0-android.

#### Smart Label Capture

* Fixed a bug where the receipt scanning overlay and validation flow overlay could not be used on the same mode instance.
* Fixed prebuilt date fields to recognize Spanish month abbreviations. The abbreviations `ene`, `abr`, `ago`, and `dic` are newly supported; the remaining Spanish abbreviations already resolved because they match their English form. The expiry-date anchor additionally recognizes common Spanish expiry terms such as `caducidad`, `vencimiento`, `consumir antes`, and `consumo preferente`.

#### Core

* Fixed a SequenceFrameSource occasionally delivering the same frame to its listeners twice.
* Fixed Nokia G11 and Nokia 8.3 5G devices not correctly getting the Camera2 path when API2-only features were requested.
* Fixed the Galaxy Note10 camera profile selection so the international Note10 family (SM-N970x/SM-N971x) gets its intended fixed-focus and Camera2 behaviors.
* Fixed the Galaxy S9+ (SM-G965x) camera profile selection so Camera2-based capture is enabled on those devices as intended.
* Fixed a race condition in SimplePropertyBehaviorSubject where mutating the subscriber list during a callback could cause crashes or missed notifications.
* Fixed an IllegalStateException in analytics HTTPS requests when the app is instrumented by APM tools such as Dynatrace.
* Fixed EventsResponse::getRetryTimeoutInSeconds to return a fallback instead of aborting on out-of-range header values.

### Deprecations

#### Barcode

* Removed the deprecated Barcode Sequence view settings API; configure the view's settings directly on the view.
* Deprecated the two-state BarcodeArResponsiveAnnotation API in favor of a new configurable annotationsByThreshold map that supports more than two distance states; the previous two-state API remains available.
