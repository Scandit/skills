# Label Capture — Overlay Customization & Advanced Topics (.NET for iOS)

This guide covers, for a **non-MAUI .NET for iOS** Label Capture integration:

- Customizing the **Basic Overlay** appearance (per-field / per-label brushes, tap handling).
- The **Advanced Overlay** for arbitrary native `UIView`s over labels/fields (AR-style annotations).
- **Adaptive Recognition** cloud fallback (**beta**).
- **Receipt Scanning** (**beta**).

Read `references/integration.md` first — these topics build on the mode/view/overlay setup described there. Every API below is verified against the `dotnet.ios` documentation; do not invent brush, listener, or overlay shapes. If you need a symbol not shown here, fetch the [Advanced Configurations](https://docs.scandit.com/sdks/net/ios/label-capture/advanced/) page before responding.

## Customizing the Basic Overlay

For appearance that does **not** depend on the field's name or content, set the overlay's default brushes directly (no listener needed):

```csharp
using Scandit.DataCapture.Core.UI.Style;
using Scandit.DataCapture.Label.UI.Overlay;

this.overlay = LabelCaptureBasicOverlay.Create(this.labelCapture);
this.dataCaptureView.AddOverlay(this.overlay);

this.overlay.CapturedFieldBrush  = LabelCaptureBasicOverlay.DefaultCapturedFieldBrush;
this.overlay.PredictedFieldBrush = LabelCaptureBasicOverlay.DefaultPredictedFieldBrush;
// Hide the whole-label outline by giving it a transparent brush:
this.overlay.LabelBrush = Brush.TransparentBrush;
```

To vary the brush **per field or per label** (e.g. tint the barcode one color and the expiry date another), implement `ILabelCaptureBasicOverlayListener` and assign it to `overlay.Listener`. `BrushForField` is called for each field of a captured label, `BrushForLabel` for the label as a whole, and `OnLabelTapped` when the user taps a label. Return `null` to fall back to the overlay's default brush.

```csharp
using Scandit.DataCapture.Core.UI.Style;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay;
using UIKit;

public class BasicOverlayListener : ILabelCaptureBasicOverlayListener
{
    private readonly Brush barcodeBrush = new Brush(
        fillColor: UIColor.FromRGB(46, 193, 206),
        strokeColor: UIColor.FromRGB(46, 193, 206),
        strokeWidth: 1f);
    private readonly Brush expiryDateBrush = new Brush(
        fillColor: UIColor.FromRGB(250, 68, 70),
        strokeColor: UIColor.FromRGB(250, 68, 70),
        strokeWidth: 1f);

    public Brush? BrushForField(
        LabelCaptureBasicOverlay overlay, LabelField field, CapturedLabel label) =>
        field.Name switch
        {
            "Barcode" => this.barcodeBrush,
            "Expiry Date" => this.expiryDateBrush,
            _ => null
        };

    public Brush? BrushForLabel(
        LabelCaptureBasicOverlay overlay, CapturedLabel label) =>
        Brush.TransparentBrush;

    public void OnLabelTapped(
        LabelCaptureBasicOverlay overlay, CapturedLabel label)
    {
        // Handle the tap (e.g. open a detail screen for this label).
    }
}

// Wire it up:
this.overlay.Listener = new BasicOverlayListener();
```

> `Brush` lives in `Scandit.DataCapture.Core.UI.Style`. The constructor is `new Brush(UIColor fillColor, UIColor strokeColor, nfloat strokeWidth)`. `Brush.TransparentBrush` is a static property for "draw nothing". The listener callbacks match fields by the exact `Name` you passed to `.Build("...")`.

## Advanced Overlay (custom native views over labels)

For AR-style annotations — arbitrary `UIView`s anchored to a label or an individual field — use `LabelCaptureAdvancedOverlay` instead of (or alongside) the basic overlay. You provide the views and their anchoring through an `ILabelCaptureAdvancedOverlayListener`.

```csharp
using Scandit.DataCapture.Core.UI.Style;
using Scandit.DataCapture.Label.Data;
using Scandit.DataCapture.Label.UI.Overlay;
using UIKit;

var advancedOverlay = LabelCaptureAdvancedOverlay.Create(this.labelCapture);
this.dataCaptureView.AddOverlay(advancedOverlay);
advancedOverlay.Listener = new AdvancedOverlayListener();

public class AdvancedOverlayListener : ILabelCaptureAdvancedOverlayListener
{
    // View anchored to the whole label (return null to add nothing).
    public UIView? ViewForCapturedLabel(
        LabelCaptureAdvancedOverlay overlay, CapturedLabel capturedLabel) => null;

    public Anchor AnchorForCapturedLabel(
        LabelCaptureAdvancedOverlay overlay, CapturedLabel capturedLabel) => Anchor.Center;

    public PointWithUnit OffsetForCapturedLabel(
        LabelCaptureAdvancedOverlay overlay, CapturedLabel capturedLabel, UIView view) =>
        new PointWithUnit(0f, 0f, MeasureUnit.Pixel);

    // View anchored to an individual field — e.g. a warning under an expiry date.
    public UIView? ViewForCapturedLabelField(
        LabelCaptureAdvancedOverlay overlay, LabelField labelField)
    {
        if (labelField.Name == "Expiry Date" && labelField.Type == LabelFieldType.Text)
        {
            var badge = new UILabel
            {
                Text = "Expires soon!",
                Font = UIFont.SystemFontOfSize(14f),
                TextColor = UIColor.White,
                BackgroundColor = UIColor.Red
            };
            badge.SizeToFit();
            return badge;
        }
        return null;
    }

    public Anchor AnchorForCapturedLabelField(
        LabelCaptureAdvancedOverlay overlay, LabelField labelField) => Anchor.BottomCenter;

    public PointWithUnit OffsetForCapturedLabelField(
        LabelCaptureAdvancedOverlay overlay, LabelField labelField, UIView view) =>
        new PointWithUnit(0f, 22f, MeasureUnit.Dip);
}
```

> `LabelCaptureAdvancedOverlay.Create(labelCapture)` mirrors the basic overlay factory; add it with `dataCaptureView.AddOverlay(...)`. The view factory methods return `UIView?` — return `null` to skip a label/field. `Anchor`, `PointWithUnit`, `MeasureUnit` live in `Scandit.DataCapture.Core.*`. The native init factory `LabelCaptureAdvancedOverlay.NewInstance(...)` is **not** available on .NET — always use `Create`.

## Adaptive Recognition — cloud fallback (BETA)

:::warning Beta
Adaptive Recognition (the Adaptive Recognition Engine) is **beta** and may change in future SDK versions. It must be enabled on your Scandit subscription — contact support@scandit.com.
:::

Adaptive Recognition adds a larger cloud-hosted model as a fallback: when the on-device model fails to extract a field, the SDK can fall back to the cloud automatically. Enable it **per label definition** by setting `AdaptiveRecognitionMode.Auto` on the definition — a single extra line on top of an otherwise normal definition. No overlay change is required for the cloud fallback itself.

```csharp
using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.Data;

var labelDefinition = LabelDefinition.Create("Retail Item", fields);
labelDefinition.AdaptiveRecognitionMode = AdaptiveRecognitionMode.Auto; // off by default

var settings = LabelCaptureSettings.Create(new List<LabelDefinition> { labelDefinition });
```

> `AdaptiveRecognitionMode` is an enum (`Off` is the default; `Auto` enables the cloud fallback) and is a get/set property on `LabelDefinition`. See [AdaptiveRecognitionMode](https://docs.scandit.com/sdks/net/ios/label-capture/advanced/) for the available options before suggesting any value other than `Auto`/`Off`.

## Receipt Scanning (BETA)

:::warning Beta
Receipt Scanning requires the Adaptive Recognition Engine, which is **beta** and may change. It must be enabled on your subscription — contact support@scandit.com.
:::

Receipt Scanning extracts structured data from receipts **in the cloud** (store info, payment details, line items) and uses a **different integration pattern** from standard label capture:

- Use `LabelCaptureAdaptiveRecognitionOverlay` instead of the basic overlay.
- Receive results via `LabelCaptureAdaptiveRecognitionListener` (its recognized callback returns a `ReceiptScanningResult`).

`ReceiptScanningResult` exposes store fields (`StoreName`, `StoreAddress`, `StoreCity`), transaction fields (`Date`, `Time`), payment totals (`PaymentPreTaxTotal`, `PaymentTax`, `PaymentTotal`, `LoyaltyNumber`), and `LineItems` — each `ReceiptScanningLineItem` carrying `Name`, `UnitPrice`, `Discount`, `Quantity`, and `TotalPrice`.

Because Receipt Scanning is beta and its result shapes may change, **fetch the [Advanced Configurations](https://docs.scandit.com/sdks/net/ios/label-capture/advanced/) page** for the exact overlay/listener wiring before writing a full integration, rather than guessing method signatures.

## Key rules

1. **Basic overlay**: default brushes via `CapturedFieldBrush` / `PredictedFieldBrush` / `LabelBrush`; name/content-dependent brushes via `ILabelCaptureBasicOverlayListener` (`BrushForField` / `BrushForLabel` / `OnLabelTapped`), assigned to `overlay.Listener`. Return `null` from a brush callback to use the default. `Brush.TransparentBrush` hides an element.
2. **Advanced overlay**: `LabelCaptureAdvancedOverlay.Create(labelCapture)` + `dataCaptureView.AddOverlay(...)` + `ILabelCaptureAdvancedOverlayListener`. View factories return `UIView?`; anchor with `Anchor` + `PointWithUnit`. Use `Create`, never the native `NewInstance`.
3. **Adaptive Recognition is per-definition**: `labelDefinition.AdaptiveRecognitionMode = AdaptiveRecognitionMode.Auto`. It is **beta** and subscription-gated — always flag this to the user.
4. **Receipt Scanning is a separate pattern** (`LabelCaptureAdaptiveRecognitionOverlay` + `LabelCaptureAdaptiveRecognitionListener` → `ReceiptScanningResult`) and is **beta** — flag it and fetch the docs for exact shapes.

## Where to go next

- [Advanced Configurations](https://docs.scandit.com/sdks/net/ios/label-capture/advanced/) — overlay customization, Validation Flow (see `references/validation-flow.md`), Adaptive Recognition, Receipt Scanning.
- [Label Definitions](https://docs.scandit.com/sdks/net/ios/label-capture/label-definitions/) — pre-built and custom field catalogue.
