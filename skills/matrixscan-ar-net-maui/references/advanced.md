# MatrixScan AR .NET MAUI — Advanced AR Topics

This file covers AR features beyond a basic rectangle highlight + info annotation: popover annotations with action buttons, the listener interfaces on info and popover annotations (so taps on header / footer / body icons / buttons are routed back into your view model), and custom `BarcodeArFeedback` compositions (mixing default and silent sound / vibration). It is meant to be read **after** `references/integration.md` — it assumes a working integration is already in place.

> All of the APIs covered here live in the **cross-platform** Scandit packages (`Scandit.DataCapture.Barcode` and `Scandit.DataCapture.Core`), not in the MAUI-only `Scandit.DataCapture.Barcode.Maui` assembly. The MAUI integration only changes how the `BarcodeArView` is hosted — the annotation, feedback, and listener types are the same as in the per-TFM skills.

## Table of contents

1. [Popover annotations with action buttons](#1-popover-annotations-with-action-buttons)
2. [Tap routing on `BarcodeArInfoAnnotation`](#2-tap-routing-on-barcodearinfoannotation)
3. [Custom `BarcodeArFeedback` compositions](#3-custom-barcodearfeedback-compositions)
4. [Putting it together — a richer `AnnotationProvider`](#4-putting-it-together--a-richer-annotationprovider)
5. [Responsive annotations (close-up vs far-away)](#5-responsive-annotations-close-up-vs-far-away)

---

## 1. Popover annotations with action buttons

`BarcodeArPopoverAnnotation` shows a row of icon + text buttons attached to a tracked barcode. The user taps a button (or the popover background) and your `IBarcodeArPopoverAnnotationListener` fires with the tap.

**Constructor:** `new BarcodeArPopoverAnnotation(Barcode barcode, IList<BarcodeArPopoverAnnotationButton> buttons)` — note `IList<…>`, not `IReadOnlyList<…>`. Pass a `List<BarcodeArPopoverAnnotationButton>` (or any other `IList`).

**Button constructor:** `new BarcodeArPopoverAnnotationButton(ScanditIcon icon, string text)`. Build the `ScanditIcon` with `ScanditIconBuilder`.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Annotations;
using Scandit.DataCapture.Barcode.Ar.UI.Annotations.Popover;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.UI.Icon;
using Microsoft.Maui.Graphics;

public sealed class PopoverAnnotationProvider : IBarcodeArAnnotationProvider, IBarcodeArPopoverAnnotationListener
{
    public Task<IBarcodeArAnnotation?> AnnotationForBarcodeAsync(Barcode barcode)
    {
        var infoIcon  = new ScanditIconBuilder().WithIcon(ScanditIconType.InspectItem).Build();
        var checkIcon = new ScanditIconBuilder().WithIcon(ScanditIconType.Checkmark).Build();
        var cartIcon  = new ScanditIconBuilder().WithIcon(ScanditIconType.ToPick).Build();

        var buttons = new List<BarcodeArPopoverAnnotationButton>
        {
            new(infoIcon,  "Info")  { TextColor = Colors.White },
            new(checkIcon, "Pick")  { TextColor = Colors.White },
            new(cartIcon,  "Cart")  { TextColor = Colors.White },
        };

        var popover = new BarcodeArPopoverAnnotation(barcode, buttons)
        {
            // Default trigger is HighlightTapAndBarcodeScan — pop the annotation as soon
            // as the barcode is tracked. Switch to HighlightTap to require an explicit
            // tap on the highlight first.
            AnnotationTrigger = BarcodeArAnnotationTrigger.HighlightTap,
            EntirePopoverTappable = false,    // tapping the background fires OnPopoverTapped only when true
            Listener = this,
        };

        return Task.FromResult<IBarcodeArAnnotation?>(popover);
    }

    public void OnPopoverButtonTapped(
        BarcodeArPopoverAnnotation popover,
        BarcodeArPopoverAnnotationButton button,
        int buttonIndex)
    {
        // Called on the main thread on both Android and iOS.
        var barcodeData = popover.Barcode.Data;
        switch (buttonIndex)
        {
            case 0: /* Info  */ break;
            case 1: /* Pick  */ break;
            case 2: /* Cart  */ break;
        }
    }

    public void OnPopoverTapped(BarcodeArPopoverAnnotation popover)
    {
        // Fires only when EntirePopoverTappable = true.
    }
}
```

Assign in code-behind (typical):

```csharp
this.BarcodeArView.AnnotationProvider = new PopoverAnnotationProvider();
```

### `BarcodeArPopoverAnnotation` properties

| Property | Type | Description |
|----------|------|-------------|
| `Barcode` | `Barcode` (get) | The barcode this annotation is bound to. |
| `Buttons` | `IReadOnlyCollection<BarcodeArPopoverAnnotationButton>` (get) | The buttons passed to the constructor. |
| `EntirePopoverTappable` | `bool` (get/set) | If `true`, taps anywhere on the popover background fire `OnPopoverTapped`. |
| `AnnotationTrigger` | `BarcodeArAnnotationTrigger` (get/set) | `HighlightTapAndBarcodeScan` (default) or `HighlightTap`. |
| `Listener` | `IBarcodeArPopoverAnnotationListener?` (get/set) | Receives `OnPopoverButtonTapped` and `OnPopoverTapped`. |

### `BarcodeArPopoverAnnotationButton` properties

| Property | Type | Description |
|----------|------|-------------|
| `Text` | `string` (get) | The label passed to the constructor. |
| `TextColor` | `Color` (get/set) | Label color. |
| `Enabled` | `bool` (get/set) | Disable the button (greyed out, no tap routing). |
| `Icon` | `ScanditIcon` (get) | The icon passed to the constructor. |
| `TextSize` | `float` (get/set, Android-only — `#if __ANDROID__`) | Label font size. Not visible from cross-platform MAUI code; for cross-platform sizing, leave at default and adjust via the `ScanditIcon` styling. |
| `Typeface` | `Android.Graphics.Typeface` (get/set, Android-only — `#if __ANDROID__`) | Label typeface. Per-platform helper required for cross-platform code. |
| `Font` | `UIKit.UIFont` (get/set, iOS-only — `#if __IOS__`) | Label font. Per-platform helper required for cross-platform code. |

> **Cross-platform MAUI code can only set `Text`, `TextColor`, `Enabled`, and `Icon` on `BarcodeArPopoverAnnotationButton`.** Typography (`TextSize` / `Typeface` / `Font`) is gated by `#if __ANDROID__` / `#if __IOS__` and is not visible to cross-platform code. If you need per-platform font tweaks, write a `partial`-class helper under `Platforms/Android/` and `Platforms/iOS/` and call into it from the cross-platform code. For most apps the defaults look fine.

### `IBarcodeArPopoverAnnotationListener`

| Method | When it fires |
|--------|---------------|
| `OnPopoverButtonTapped(BarcodeArPopoverAnnotation popover, BarcodeArPopoverAnnotationButton button, int buttonIndex)` | The user tapped one of the buttons. `buttonIndex` is the zero-based index of `button` in the `Buttons` collection. |
| `OnPopoverTapped(BarcodeArPopoverAnnotation popover)` | The user tapped the popover background (only when `EntirePopoverTappable = true`). |

Both methods are called on the main thread on both Android and iOS, so you can update MAUI bindings directly inside the handler without `MainThread.BeginInvokeOnMainThread`.

---

## 2. Tap routing on `BarcodeArInfoAnnotation`

`BarcodeArInfoAnnotation` supports finer-grained tap routing than the simple `EntireAnnotationTappable` flag: you can react to taps on the header, footer, body row left/right icons, and the body as a whole, all separately. Implement `IBarcodeArInfoAnnotationListener` and assign it to the annotation's `Listener` property.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Annotations;
using Scandit.DataCapture.Barcode.Ar.UI.Annotations.Info;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.UI.Icon;

public sealed class StockInfoAnnotationProvider : IBarcodeArAnnotationProvider, IBarcodeArInfoAnnotationListener
{
    public Task<IBarcodeArAnnotation?> AnnotationForBarcodeAsync(Barcode barcode)
    {
        var infoIcon = new ScanditIconBuilder().WithIcon(ScanditIconType.InspectItem).Build();

        var annotation = new BarcodeArInfoAnnotation(barcode)
        {
            Width = BarcodeArInfoAnnotationWidthPreset.Medium,
            Anchor = BarcodeArInfoAnnotationAnchor.Bottom,
            HasTip = true,
            EntireAnnotationTappable = false,
            AnnotationTrigger = BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan,

            Header = new BarcodeArInfoAnnotationHeader
            {
                Text = barcode.Data ?? string.Empty,
            },

            Body = new List<BarcodeArInfoAnnotationBodyComponent>
            {
                new() { Text = "In stock: 42", LeftIcon = infoIcon, LeftIconTappable = true },
                new() { Text = "Aisle 7, Bay 3" },
            },

            Footer = new BarcodeArInfoAnnotationFooter
            {
                Text = "Tap for details",
            },

            Listener = this,
        };

        return Task.FromResult<IBarcodeArAnnotation?>(annotation);
    }

    #region IBarcodeArInfoAnnotationListener
    public void OnInfoAnnotationTapped(BarcodeArInfoAnnotation annotation)
    {
        // Fires only when EntireAnnotationTappable = true.
        var data = annotation.Barcode.Data;
    }

    public void OnInfoAnnotationHeaderTapped(BarcodeArInfoAnnotation annotation)
    {
        var data = annotation.Barcode.Data;
    }

    public void OnInfoAnnotationFooterTapped(BarcodeArInfoAnnotation annotation)
    {
        var data = annotation.Barcode.Data;
    }

    public void OnInfoAnnotationLeftIconTapped(
        BarcodeArInfoAnnotation annotation,
        BarcodeArInfoAnnotationBodyComponent component,
        int componentIndex)
    {
        // `component` is the body row whose left icon was tapped (component.LeftIconTappable must be true).
        // `componentIndex` is its zero-based position in annotation.Body.
        var rowText = component.Text;
    }

    public void OnInfoAnnotationRightIconTapped(
        BarcodeArInfoAnnotation annotation,
        BarcodeArInfoAnnotationBodyComponent component,
        int componentIndex)
    {
        // Symmetric to the left-icon callback (component.RightIconTappable must be true).
    }
    #endregion
}

// Assign:
this.BarcodeArView.AnnotationProvider = new StockInfoAnnotationProvider();
```

### `IBarcodeArInfoAnnotationListener`

| Method | When it fires |
|--------|---------------|
| `OnInfoAnnotationTapped(annotation)` | The annotation background was tapped. Only fires when `annotation.EntireAnnotationTappable = true`. |
| `OnInfoAnnotationHeaderTapped(annotation)` | The header was tapped. Only fires if the annotation has a `Header`. |
| `OnInfoAnnotationFooterTapped(annotation)` | The footer was tapped. Only fires if the annotation has a `Footer`. |
| `OnInfoAnnotationLeftIconTapped(annotation, component, componentIndex)` | A body row's left icon was tapped. Only fires when that row has `LeftIcon` set and `LeftIconTappable = true`. |
| `OnInfoAnnotationRightIconTapped(annotation, component, componentIndex)` | Symmetric to the left-icon callback. Only fires when `RightIcon` is set and `RightIconTappable = true`. |

All callbacks run on the main thread on both Android and iOS.

> **`EntireAnnotationTappable` is a coarse switch, not a free-tap surface.** Setting it to `true` enables `OnInfoAnnotationTapped` but **suppresses** the more specific header / footer / icon tap callbacks for the *same* tap (the system picks the most specific tap target). Use `false` if you want the granular callbacks and add an explicit "Tap me" footer if you need a clear hit area.

### `BarcodeArInfoAnnotationBodyComponent` quick reference

The body of a `BarcodeArInfoAnnotation` is an `IReadOnlyCollection<BarcodeArInfoAnnotationBodyComponent>`. Each component supports:

| Property | Type | Description |
|----------|------|-------------|
| `Text` | `string` (get/set) | The row's text. |
| `TextColor` | `Color` (get/set) | Text color. |
| `TextSize` | `float` (get/set) | Text size in dp. |
| `Typeface` | per-platform | `Android.Graphics.Typeface` (Android-only) or `UIKit.UIFont` (iOS-only). For cross-platform code, leave at default or set via a partial-class helper. |
| `StyledTextFormatted` | `Java.Lang.ICharSequence?` (Android) / `Foundation.NSAttributedString?` (iOS) | Pre-styled text (use for inline color / bold / italic). Per-platform. |
| `LeftIcon` | `ScanditIcon?` (get/set) | Optional left icon. |
| `RightIcon` | `ScanditIcon?` (get/set) | Optional right icon. |
| `LeftIconTappable` | `bool` (get/set) | Allow tap routing to `OnInfoAnnotationLeftIconTapped`. |
| `RightIconTappable` | `bool` (get/set) | Allow tap routing to `OnInfoAnnotationRightIconTapped`. |
| `TextAlignment` | platform-specific | Text alignment within the row. |

`BarcodeArInfoAnnotationHeader` and `BarcodeArInfoAnnotationFooter` share the same `Text` / `TextSize` / `Typeface` / `TextColor` / `Icon` / `BackgroundColor` surface — see the integration guide for the full list.

---

## 3. Custom `BarcodeArFeedback` compositions

`barcodeAr.Feedback` is a single property whose value is a `BarcodeArFeedback`. The class exposes two slots:

| Property | Type | Played when |
|----------|------|-------------|
| `Scanned` | `Scandit.DataCapture.Core.Common.Feedback.Feedback` | A barcode enters tracking. |
| `Tapped`  | `Scandit.DataCapture.Core.Common.Feedback.Feedback` | A highlight is tapped. |

The two extremes:

```csharp
using Scandit.DataCapture.Barcode.Ar.Feedback;

// Silent — both Scanned and Tapped are silent feedback instances:
this.BarcodeAr.Feedback = new BarcodeArFeedback();

// Defaults — beep + vibration on both:
this.BarcodeAr.Feedback = BarcodeArFeedback.DefaultFeedback;
```

For asymmetric compositions, instantiate a `BarcodeArFeedback` and assign the two slots independently. The `Feedback` constructor takes nullable `Vibration?` and nullable `Sound?` — passing `null` for one disables that channel.

```csharp
using Scandit.DataCapture.Barcode.Ar.Feedback;
using Scandit.DataCapture.Core.Common.Feedback;

// Silent on scan, default beep + vibrate on tap:
this.BarcodeAr.Feedback = new BarcodeArFeedback
{
    Scanned = new Feedback(vibration: null, sound: null),  // explicit silence
    Tapped  = new Feedback(Vibration.DefaultVibration, Sound.DefaultSound),
};

// Vibration-only feedback on both events (silent beep):
this.BarcodeAr.Feedback = new BarcodeArFeedback
{
    Scanned = new Feedback(Vibration.DefaultVibration),    // (Vibration?) overload — sound = null
    Tapped  = new Feedback(Vibration.DefaultVibration),
};

// Sound-only on scan, nothing on tap:
this.BarcodeAr.Feedback = new BarcodeArFeedback
{
    Scanned = new Feedback(Sound.DefaultSound),            // (Sound?) overload — vibration = null
    Tapped  = new Feedback(vibration: null, sound: null),
};
```

### `Feedback` constructors

| Overload | Result |
|----------|--------|
| `new Feedback(Vibration? vibration, Sound? sound)` | Custom composition; `null` disables that channel. |
| `new Feedback(Vibration? vibration)` | Vibration-only (sound = null). |
| `new Feedback(Sound? sound)` | Sound-only (vibration = null). |
| `Feedback.DefaultFeedback` | Static property — default vibration + default sound. |

### What's cross-platform-safe in MAUI

For MAUI code that compiles on both Android and iOS, only these `Vibration` / `Sound` constants are visible:

| Constant | Available in MAUI cross-platform code? |
|----------|----------------------------------------|
| `Vibration.DefaultVibration` | ✅ Yes |
| `Vibration.SelectionHapticFeedback` | ❌ iOS-only (`#if __IOS__`) |
| `Vibration.SuccessHapticFeedback` | ❌ iOS-only (`#if __IOS__`) |
| `Sound.DefaultSound` | ✅ Yes |
| `new Sound(NSUrl url)` | ❌ iOS-only (`#if __IOS__`) |
| `new Sound(string assetName)` | ❌ Android-only (`#if __ANDROID__`) |
| `new Sound(int resourceId)` | ❌ Android-only (`#if __ANDROID__`) |

> For **custom sounds**, the `Sound` constructors are per-platform — the iOS overload takes an `NSUrl`, the Android overload takes a resource id or asset name. There is no cross-platform `new Sound(string path)` overload that works on both. If you need a custom scan sound in MAUI, write a `partial`-class helper under `Platforms/Android/` and `Platforms/iOS/` that returns the right `Sound` instance, and call it from the cross-platform code. For most apps, `Sound.DefaultSound` is the right choice and there is no need to customize.

> `Vibration.SelectionHapticFeedback` / `SuccessHapticFeedback` exist only on iOS. They produce the system-level iOS selection and success haptics respectively, which behave slightly differently from `Vibration.DefaultVibration`. They are not visible from cross-platform MAUI code; reach them only from `Platforms/iOS/` helpers.

### Restoring the default after customization

```csharp
// Restore both channels to defaults — single property assignment:
this.BarcodeAr.Feedback = BarcodeArFeedback.DefaultFeedback;
```

> `BarcodeArFeedback.DefaultFeedback` is a **static property** in .NET, not a method. Calling it with parentheses (`BarcodeArFeedback.DefaultFeedback()`) is a compile error.

---

## 4. Putting it together — a richer `AnnotationProvider`

A full provider that returns different annotation kinds for different symbologies — popovers for QR codes (linkable URLs), info annotations for 1D codes (product info), and status icons for everything else — and routes taps through a single class.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Annotations;
using Scandit.DataCapture.Barcode.Ar.UI.Annotations.Info;
using Scandit.DataCapture.Barcode.Ar.UI.Annotations.Popover;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.UI.Icon;
using Microsoft.Maui.Graphics;

namespace MyApp.Scanning;

public sealed class StockAnnotationProvider :
    IBarcodeArAnnotationProvider,
    IBarcodeArInfoAnnotationListener,
    IBarcodeArPopoverAnnotationListener
{
    private readonly ScanditIcon infoIcon  = new ScanditIconBuilder().WithIcon(ScanditIconType.InspectItem).Build();
    private readonly ScanditIcon checkIcon = new ScanditIconBuilder().WithIcon(ScanditIconType.Checkmark).Build();
    private readonly ScanditIcon cartIcon  = new ScanditIconBuilder().WithIcon(ScanditIconType.ToPick).Build();

    public Task<IBarcodeArAnnotation?> AnnotationForBarcodeAsync(Barcode barcode)
    {
        return Task.FromResult<IBarcodeArAnnotation?>(barcode.Symbology switch
        {
            Symbology.Qr        => this.BuildPopover(barcode),
            Symbology.Ean13Upca => this.BuildInfo(barcode),
            Symbology.Code128   => this.BuildInfo(barcode),
            _                   => this.BuildStatusIcon(barcode),
        });
    }

    private BarcodeArPopoverAnnotation BuildPopover(Barcode barcode)
    {
        var buttons = new List<BarcodeArPopoverAnnotationButton>
        {
            new(this.infoIcon,  "Open") { TextColor = Colors.White },
            new(this.checkIcon, "Save") { TextColor = Colors.White },
        };
        return new BarcodeArPopoverAnnotation(barcode, buttons)
        {
            AnnotationTrigger = BarcodeArAnnotationTrigger.HighlightTap,
            EntirePopoverTappable = false,
            Listener = this,
        };
    }

    private BarcodeArInfoAnnotation BuildInfo(Barcode barcode)
    {
        return new BarcodeArInfoAnnotation(barcode)
        {
            Width = BarcodeArInfoAnnotationWidthPreset.Medium,
            Anchor = BarcodeArInfoAnnotationAnchor.Bottom,
            HasTip = true,
            Header = new BarcodeArInfoAnnotationHeader { Text = barcode.Data ?? string.Empty },
            Body = new List<BarcodeArInfoAnnotationBodyComponent>
            {
                new() { Text = "Tap row for details", LeftIcon = this.infoIcon, LeftIconTappable = true },
            },
            Listener = this,
        };
    }

    private BarcodeArStatusIconAnnotation BuildStatusIcon(Barcode barcode)
    {
        return new BarcodeArStatusIconAnnotation(barcode)
        {
            Icon = this.infoIcon,
            Text = barcode.Data,
            HasTip = true,
        };
    }

    public void OnPopoverButtonTapped(
        BarcodeArPopoverAnnotation popover,
        BarcodeArPopoverAnnotationButton button,
        int buttonIndex)
    {
        // Main-thread callback. Update MAUI bindings or invoke commands directly.
    }

    public void OnPopoverTapped(BarcodeArPopoverAnnotation popover) { }

    public void OnInfoAnnotationTapped(BarcodeArInfoAnnotation annotation) { }
    public void OnInfoAnnotationHeaderTapped(BarcodeArInfoAnnotation annotation) { }
    public void OnInfoAnnotationFooterTapped(BarcodeArInfoAnnotation annotation) { }

    public void OnInfoAnnotationLeftIconTapped(
        BarcodeArInfoAnnotation annotation,
        BarcodeArInfoAnnotationBodyComponent component,
        int componentIndex) { }

    public void OnInfoAnnotationRightIconTapped(
        BarcodeArInfoAnnotation annotation,
        BarcodeArInfoAnnotationBodyComponent component,
        int componentIndex) { }
}
```

Assign once:

```csharp
this.BarcodeArView.AnnotationProvider = new StockAnnotationProvider();
```

> The provider is invoked on a background recognition thread (via `AnnotationForBarcodeAsync`), but the tap callbacks (`OnInfoAnnotation*Tapped`, `OnPopover*Tapped`) fire on the main thread. There is no need for `MainThread.BeginInvokeOnMainThread` inside the tap handlers, but there **is** a need to keep the `AnnotationForBarcodeAsync` body cheap — it runs on every newly-tracked barcode, and blocking it stalls the recognition pipeline.

## 5. Responsive annotations (close-up vs far-away)

`BarcodeArResponsiveAnnotation` wraps **two** `BarcodeArInfoAnnotation` variations and switches between them automatically based on how large the barcode appears on screen. When the barcode area (as a percentage of the screen area) exceeds the threshold, the **close-up** annotation is shown; otherwise the **far-away** annotation is shown. Either variation may be `null` to show nothing for that case.

Available on MAUI since `dotnet.android=8.0` / `dotnet.ios=8.0`. It lives in the `Scandit.DataCapture.Barcode.Ar.UI.Annotations` namespace, like the other annotation types.

**Constructor:** `new BarcodeArResponsiveAnnotation(Barcode barcode, BarcodeArInfoAnnotation? closeUpAnnotation, BarcodeArInfoAnnotation? farAwayAnnotation)`.

```csharp
using Scandit.DataCapture.Barcode.Ar.UI.Annotations;
using Scandit.DataCapture.Barcode.Ar.UI.Annotations.Info;
using Scandit.DataCapture.Barcode.Data;

public sealed class ResponsiveAnnotationProvider : IBarcodeArAnnotationProvider
{
    public Task<IBarcodeArAnnotation?> AnnotationForBarcodeAsync(Barcode barcode)
    {
        // Detailed annotation when the barcode is close to the camera.
        var closeUp = new BarcodeArInfoAnnotation(barcode)
        {
            Width = BarcodeArInfoAnnotationWidthPreset.Large,
            Header = new BarcodeArInfoAnnotationHeader { Text = "In stock" },
            Body = new List<BarcodeArInfoAnnotationBodyComponent>
            {
                new() { Text = barcode.Data ?? string.Empty },
            },
        };

        // Compact annotation when the barcode is far away.
        var farAway = new BarcodeArInfoAnnotation(barcode)
        {
            Width = BarcodeArInfoAnnotationWidthPreset.Small,
            Body = new List<BarcodeArInfoAnnotationBodyComponent>
            {
                new() { Text = barcode.Data ?? string.Empty },
            },
        };

        var annotation = new BarcodeArResponsiveAnnotation(barcode, closeUp, farAway);
        return Task.FromResult<IBarcodeArAnnotation?>(annotation);
    }
}

// The switch point is a CLASS-LEVEL static property — it applies to every instance.
// 0.1 means the barcode covers 10% of the screen area. Default is 0.05.
BarcodeArResponsiveAnnotation.Threshold = 0.1f;
```

| Member | Type | Description |
|--------|------|-------------|
| `BarcodeArResponsiveAnnotation(Barcode, BarcodeArInfoAnnotation?, BarcodeArInfoAnnotation?)` | constructor | `closeUpAnnotation` then `farAwayAnnotation`. Either may be `null`. |
| `Threshold` | `static float` (get/set) | **Static** — applies to all instances. Barcode-area / screen-area ratio (0.0–1.0). Default `0.05`. |
| `CloseUpAnnotation` | `BarcodeArInfoAnnotation?` (get) | Shown when the barcode area exceeds `Threshold`. |
| `FarAwayAnnotation` | `BarcodeArInfoAnnotation?` (get) | Shown when the barcode area is below or equal to `Threshold`. |
| `AnnotationTrigger` | `BarcodeArAnnotationTrigger` (get/set) | Default `HighlightTapAndBarcodeScan`. |
| `Barcode` | `Barcode` (get) | |

> `Threshold` is a **static** property — assign it once (`BarcodeArResponsiveAnnotation.Threshold = …`), not per-annotation. The close-up and far-away variations are themselves ordinary `BarcodeArInfoAnnotation` instances, so everything you can do to an info annotation (header, body rows, footer, width preset) applies to each variation independently.

---

## Key rules

1. **`BarcodeArPopoverAnnotation` takes `IList<…>` buttons** — `IList<BarcodeArPopoverAnnotationButton>`, not `IReadOnlyList<…>`. A plain `List<…>` is the natural argument.
2. **`BarcodeArPopoverAnnotationButton` is `ScanditIcon + string` in the constructor** — no `Color`, no `TextSize`. Build the icon with `ScanditIconBuilder`. Set per-button `TextColor` / `Enabled` via property setters.
3. **Per-platform-only properties on `BarcodeArPopoverAnnotationButton`:** `TextSize` and `Typeface` are Android-only (`#if __ANDROID__`); `Font` is iOS-only (`#if __IOS__`). Not visible from cross-platform MAUI code. For cross-platform fonts, use a `partial`-class helper or leave the defaults.
4. **`IBarcodeArInfoAnnotationListener` fires granular callbacks** for header / footer / left icon / right icon / annotation-as-a-whole. The icon callbacks include the body `component` and its `componentIndex`. **All callbacks run on the main thread.**
5. **`EntireAnnotationTappable = true` suppresses the granular tap callbacks** for the same tap. Use `false` when you want the granular routing.
6. **`BarcodeArFeedback` has two slots: `Scanned` and `Tapped`.** Both are `Scandit.DataCapture.Core.Common.Feedback.Feedback` instances. Construct with `new Feedback(vibration, sound)` (both nullable), `new Feedback(vibration)`, `new Feedback(sound)`, or use the static `Feedback.DefaultFeedback`.
7. **Custom sound files are per-platform** — `new Sound(NSUrl)` on iOS, `new Sound(string assetName)` / `new Sound(int resourceId)` on Android. There is no cross-platform constructor. For MAUI cross-platform code, stick to `Sound.DefaultSound` unless you split into `Platforms/Android/` / `Platforms/iOS/` helpers.
8. **`BarcodeArFeedback.DefaultFeedback` is a static property**, not a method. No parentheses.
