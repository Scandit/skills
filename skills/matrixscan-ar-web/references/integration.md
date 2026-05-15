# MatrixScan AR Web Integration Guide

MatrixScan AR (API name: `BarcodeAr*`) is a multi-barcode AR mode that tracks all barcodes in view simultaneously and overlays highlights and annotations on each one in real time. On web it renders through `BarcodeArView`, which is itself a custom HTML element — no `DataCaptureView` is needed.

> **Language note**: Examples below use TypeScript (v8 API). For plain JavaScript projects, remove the type annotations and keep the same imports and structure.

> **Multithreading note**: BarcodeAr requires browser multithreading. Before writing any code, confirm that the server sends the correct cross-origin isolation headers — see the [COOP/COEP section](#cross-origin-isolation-coop--coep) below.

## Starting from zero? Use the pre-built sample

If the user has no existing app yet, always offer the official sample as the fastest path to a working integration.

- **MatrixScan AR Simple Sample:** <https://github.com/Scandit/datacapture-web-samples/tree/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanARSimpleSample>

Tell the user to clone the repo and open the sample folder. Once they have it open, help them:

1. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with their key from <https://ssl.scandit.com>
2. Adjust the enabled symbologies to match their use case
3. Run `npm install` and start the app

Only proceed to the manual integration steps below if the user already has an existing project.

---

## Prerequisites

- Scandit Data Capture SDK for web via npm, pnpm, or yarn:
  - `@scandit/web-datacapture-core`: <https://www.npmjs.com/package/@scandit/web-datacapture-core>
  - `@scandit/web-datacapture-barcode`: <https://www.npmjs.com/package/@scandit/web-datacapture-barcode>
- A valid Scandit license key — sign in at <https://ssl.scandit.com> (no account? sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>)
- Cross-origin isolation headers configured on the server (required — see below)

### Cross-origin isolation (COOP / COEP)

**BarcodeAr requires browser multithreading via `SharedArrayBuffer`.** Without these headers the SDK degrades to single-threaded mode, which is too slow for AR tracking.

Always set:
```
Cross-Origin-Opener-Policy: same-origin
```

For `Cross-Origin-Embedder-Policy`, the value depends on how you host the SDK:

| Hosting | COEP value |
|---------|-----------|
| Self-hosted SDK files | `require-corp` |
| CDN (`cdn.jsdelivr.net`) | `credentialless` (Chrome/Edge 96+) |

> **Heads up:** COEP blocks cross-origin resources (images, fonts, iframes, third-party scripts) that do not include `Cross-Origin-Resource-Policy` or `Access-Control-Allow-Origin`. Audit your page's cross-origin dependencies before enabling COEP in production.

For the complete Vite setup — COOP/COEP middleware, `library/engine` self-hosting with `vite-plugin-static-copy`, and license key injection — use the official sample `vite.config.ts` as the source of truth:
<https://github.com/Scandit/datacapture-web-samples/blob/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanARSimpleSample/vite.config.ts>

## Integration flow

Ask the user which barcode symbologies they need to scan. Only enable the symbologies actually required — each extra symbology adds processing time.

Once the user responds, ask which file or component they'd like to integrate MatrixScan AR into. Then write the integration code directly into that file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install @scandit/web-datacapture-core @scandit/web-datacapture-barcode`
2. Set cross-origin headers (`COOP: same-origin` + `COEP: require-corp` or `credentialless`) on the server
3. Configure `libraryLocation` to point to the SDK engine files (self-hosted) or set to the CDN path `https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8/sdc-lib/`
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key from <https://ssl.scandit.com>
5. Add a container element to your HTML (e.g. `<div id="barcode-ar-view" style="position:fixed;inset:0">`) with defined dimensions

## Step 1 — Initialize DataCaptureContext

```typescript
import { DataCaptureContext } from "@scandit/web-datacapture-core";
import { barcodeCaptureLoader } from "@scandit/web-datacapture-barcode";

await DataCaptureContext.forLicenseKey(
  "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
  {
    libraryLocation: new URL("library/engine/", document.baseURI).toString(),
    moduleLoaders: [barcodeCaptureLoader()],
  }
);
// After forLicenseKey() resolves, DataCaptureContext.sharedInstance is ready to use.
```

- `forLicenseKey()` configures `DataCaptureContext.sharedInstance` as a side effect — no need to save the return value. Access the context anywhere via `DataCaptureContext.sharedInstance`.
- `libraryLocation` points to the folder containing the SDK engine WASM/JS files. For the sample this is `library/engine/` relative to the document base URI; adjust to match your asset layout.
- `barcodeCaptureLoader()` is the single module loader for all barcode modes — BarcodeCapture, BarcodeBatch, and BarcodeAr all use it. There is no separate BarcodeAr loader.
- **No `DataCaptureView` is needed.** `BarcodeArView.create()` serves as the camera + AR view and replaces it entirely.

## Step 2 — Configure BarcodeArSettings

```typescript
import {
  BarcodeArSettings,
  Symbology,
} from "@scandit/web-datacapture-barcode";

const settings = new BarcodeArSettings();
settings.enableSymbologies([
  Symbology.EAN13UPCA,
  Symbology.EAN8,
  Symbology.UPCE,
  Symbology.Code39,
  Symbology.Code128,
]);

// Optional: adjust active symbol counts for variable-length symbologies
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
```

### BarcodeArSettings Members

| Member | Description |
|--------|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | Get per-symbology settings (e.g. `activeSymbolCounts`). |
| `enabledSymbologies` | Read-only array of currently enabled symbologies. |

## Step 3 — Create BarcodeAr

```typescript
import { BarcodeAr } from "@scandit/web-datacapture-barcode";
import { DataCaptureContext } from "@scandit/web-datacapture-core";

const barcodeAr = await BarcodeAr.forContext(DataCaptureContext.sharedInstance, settings);
```

- `BarcodeAr.forContext()` is **async** — always `await` it.
- Do NOT use `new BarcodeAr(settings)` — that is the React Native constructor, not the web API.

### Optional: BarcodeArListener

Register a session listener to observe tracked barcodes on every frame:

```typescript
barcodeAr.addListener({
  didUpdateSession: (_barcodeAr, session) => {
    // session.addedTrackedBarcodes — Record<string, TrackedBarcode> newly tracked this frame
    for (const tracked of Object.values(session.addedTrackedBarcodes)) {
      console.log("New barcode:", tracked.barcode.data, tracked.barcode.symbology);
    }
    // session.removedTrackedBarcodes — string[] of IDs that left the frame
    // session.allTrackedBarcodes — { [id: string]: TrackedBarcode } all current barcodes
  },
});
```

### BarcodeArSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `addedTrackedBarcodes` | `Record<string, TrackedBarcode>` | Barcodes newly tracked this frame. Use `Object.values(session.addedTrackedBarcodes)` to iterate. |
| `removedTrackedBarcodes` | `string[]` | IDs (as strings) of barcodes that left the camera view. |
| `allTrackedBarcodes` | `Record<string, TrackedBarcode>` | All currently tracked barcodes. |

## Step 4 — Create BarcodeArView

```typescript
import { BarcodeArView } from "@scandit/web-datacapture-barcode";
import { DataCaptureContext } from "@scandit/web-datacapture-core";

const container = document.getElementById("barcode-ar-view")!;
const barcodeArView = await BarcodeArView.create(container, DataCaptureContext.sharedInstance, barcodeAr);
```

- `BarcodeArView.create()` is **async** — always `await` it.
- The `container` element must have defined dimensions and a CSS `position` value (`fixed` or `absolute`). A zero-sized or statically positioned container will not render.
- `BarcodeArView` **is an HTML element** (it extends `ScanditHTMLElement`) — it attaches itself to the provided container automatically.
- **BarcodeArView manages the camera internally.** Do NOT manually create a `Camera`, call `context.setFrameSource()`, or call `switchToDesiredState()` — those belong to BarcodeBatch, not BarcodeAr.

### BarcodeArView Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `shouldShowTorchControl` | `boolean` | `false` | Show/hide torch (flashlight) button. |
| `torchControlPosition` | `Anchor` | `TopLeft` | Position of the torch button. |
| `shouldShowZoomControl` | `boolean` | `false` | Show/hide zoom button. |
| `shouldShowCameraSwitchControl` | `boolean` | `false` | Show/hide camera switch button. |
| `highlightProvider` | `BarcodeArHighlightProvider \| null` | `null` | Provider that delivers a highlight for each barcode (callback pattern). |
| `annotationProvider` | `BarcodeArAnnotationProvider \| null` | `null` | Provider that delivers an annotation for each barcode (callback pattern). |
| `listener` | `BarcodeArViewUiListener \| null` | `null` | Receives tap events on barcode highlights: `didTapHighlightForBarcode(view, barcode)`. |

### BarcodeArView Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `BarcodeArView.create(element, context, barcodeAr)` | `Promise<BarcodeArView>` | Creates and attaches the AR view to the container. |
| `start()` | `Promise<void>` | Starts scanning. Must be called explicitly after `create()`. |
| `stop()` | `Promise<void>` | Stops scanning and releases the camera. |
| `pause()` | `Promise<void>` | Pauses scanning (keeps camera warm for faster resume). |
| `reset()` | `void` | Clears all highlights and annotations; re-queries providers. |
| `remove()` | `void` | Removes the view element from the DOM. Call during cleanup. |

## Step 5 — Highlight Provider

Highlights are colored shapes that appear directly over each tracked barcode. Assign a `highlightProvider` object to the `BarcodeArView`.

> **Critical web difference:** On web, providers use a **callback pattern** — deliver results via `callback(highlight)`. Do NOT return the value. This is different from React Native where providers are async functions that return a Promise.

```typescript
import {
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
} from "@scandit/web-datacapture-barcode";

barcodeArView.highlightProvider = {
  async highlightForBarcode(barcode, callback) {
    const highlight = BarcodeArCircleHighlight.create(barcode, BarcodeArCircleHighlightPreset.Dot);
    callback(highlight);
    // To show no highlight for a barcode: callback(null)
  },
};
```

### BarcodeArCircleHighlight

Draws a circle over the barcode. Use static factory `BarcodeArCircleHighlight.create(barcode, preset)`.

| Preset | Description |
|--------|-------------|
| `BarcodeArCircleHighlightPreset.Dot` | Small circle, good for dense barcode grids. |
| `BarcodeArCircleHighlightPreset.Icon` | Larger circle, suitable for showing an icon inside. |

Key properties:

| Property | Type | Description |
|----------|------|-------------|
| `brush` | `Brush` | Fill color, stroke color, stroke width. |
| `icon` | `ScanditIcon \| null` | Optional icon rendered inside the circle. |

### BarcodeArRectangleHighlight

Draws a rectangle matching the barcode bounding box. Use static factory `BarcodeArRectangleHighlight.create(barcode)`.

```typescript
import { BarcodeArRectangleHighlight } from "@scandit/web-datacapture-barcode";

barcodeArView.highlightProvider = {
  async highlightForBarcode(barcode, callback) {
    const highlight = BarcodeArRectangleHighlight.create(barcode);
    callback(highlight);
  },
};
```

Key properties:

| Property | Type | Description |
|----------|------|-------------|
| `brush` | `Brush` | Fill color, stroke color, stroke width. |
| `icon` | `ScanditIcon \| null` | Optional icon. |

### ScanditIcon (async on web)

`ScanditIconBuilder.build()` returns `Promise<ScanditIcon>` on web — icon construction is async. Construct via `new ScanditIconBuilder()`, chain methods, then `await .build()`:

```typescript
import { ScanditIconBuilder, ScanditIconType, ScanditIconShape } from "@scandit/web-datacapture-core";
import { Color } from "@scandit/web-datacapture-core";

// Simple icon — just a glyph, no background
const icon = await new ScanditIconBuilder()
  .withIcon(ScanditIconType.Checkmark)
  .build();

// Icon with colored circular background
const iconWithBg = await new ScanditIconBuilder()
  .withIcon(ScanditIconType.ExclamationMark)
  .withBackgroundShape(ScanditIconShape.Circle)
  .withBackgroundColor(Color.fromHex("#FF4444"))
  .withIconColor(Color.fromHex("#FFFFFF"))
  .build();

highlight.icon = icon;
```

### ScanditIconBuilder Methods (all return `ScanditIconBuilder` for chaining)

| Method | Parameter | Description |
|--------|-----------|-------------|
| `withIcon(icon)` | `ScanditIconType` | Sets the icon glyph. |
| `withIconColor(color)` | `Color` | Sets the icon glyph color. |
| `withIconSize(size)` | `number` | Sets the glyph size within the background. |
| `withBackgroundShape(shape)` | `ScanditIconShape \| null` | Sets background: `Circle`, `Square`, or `null` for no background. |
| `withBackgroundColor(color)` | `Color` | Sets background fill color. |
| `withBackgroundStrokeColor(color)` | `Color` | Sets background stroke color. |
| `withBackgroundStrokeWidth(width)` | `number` | Sets background stroke width. |
| `withWidth(width)` | `number` | Sets the background shape width. |
| `withHeight(height)` | `number` | Sets the background shape height. |
| `build()` | `Promise<ScanditIcon>` | Builds the icon asynchronously. |

### ScanditIconType Values

All 31 values — there is **no** `Info` value:

| Value | Since | Value | Since |
|-------|-------|-------|-------|
| `ChevronUp` | 7.1 | `ChevronDown` | 7.1 |
| `ChevronLeft` | 7.1 | `ChevronRight` | 7.1 |
| `ArrowUp` | 7.1 | `ArrowDown` | 7.1 |
| `ArrowLeft` | 7.1 | `ArrowRight` | 7.1 |
| `ToPick` | 7.1 | `Checkmark` | 7.1 |
| `XMark` | 7.1 | `QuestionMark` | 7.1 |
| `ExclamationMark` | 7.1 | `LowStock` | 7.1 |
| `InspectItem` | 7.1 | `ExpiredItem` | 7.1 |
| `WrongItem` | 7.1 | `FragileItem` | 7.1 |
| `StarOutlined` | 7.1 | `StarFilled` | 7.1 |
| `StarHalfFilled` | 7.1 | `Print` | 7.1 |
| `CameraSwitch` | 7.1 | `DotFiveX` | 7.1 |
| `OneX` | 7.1 | `TwoX` | 7.1 |
| `Restart` | 7.3 | `Keyboard` | 7.3 |
| `Delete` | 8.1 | `Slash` | 8.1 |
| `Pause` | 8.2 | | |

### Custom HTML Element Highlight (Web Components)

For complete control over the highlight's appearance and interaction, implement `BarcodeArHighlight` as a custom HTML element. The SDK calls `updatePosition` on every frame to keep the element positioned over the barcode.

```typescript
import type { Barcode, BarcodeArHighlight } from "@scandit/web-datacapture-barcode";
import type { Point, ScanditIcon } from "@scandit/web-datacapture-core";
import { Brush } from "@scandit/web-datacapture-core";

const tag = "custom-highlight-view";

export class CustomHighlightView extends HTMLElement implements BarcodeArHighlight {
  public barcode!: Barcode;
  public brush: Brush = new Brush();
  public icon: ScanditIcon | null = null;

  public static create(barcode: Barcode): CustomHighlightView {
    const element = document.createElement(tag) as CustomHighlightView;
    element.barcode = barcode;
    return element;
  }

  public connectedCallback(): void {
    this.innerHTML = `
      <style>
        custom-highlight-view {
          position: absolute;
          will-change: transform;
          width: 50px;
          height: 50px;
          background-color: green;
          border-radius: 50%;
        }
        custom-highlight-view[hidden] { display: none; }
      </style>
      <div>Custom Highlight</div>
    `;
  }

  public updatePosition(point: Point, transformOrigin: Point, rotationAngle: number): void {
    this.style.transform =
      `translate3d(calc(${Math.round(point.x)}px + ${transformOrigin.x}%), ` +
      `calc(${Math.round(point.y)}px + ${transformOrigin.y}%), 0px) ` +
      `rotate(${rotationAngle}deg)`;
  }
}

if (!customElements.get(tag)) {
  customElements.define(tag, CustomHighlightView);
}
```

Use it in a highlight provider:

```typescript
barcodeArView.highlightProvider = {
  async highlightForBarcode(barcode, callback) {
    callback(CustomHighlightView.create(barcode));
  },
};
```

**Requirements for a custom highlight element:**

| Member | Type | Description |
|--------|------|-------------|
| `barcode` | `Barcode` | Set by your factory; identifies which barcode this highlight belongs to. |
| `brush` | `Brush` | Required by the interface (can be a default `new Brush()`). |
| `icon` | `ScanditIcon \| null` | Required by the interface (can be `null`). |
| `updatePosition(point, transformOrigin, rotationAngle)` | `void` | Called every frame to position the element. Apply as `transform: translate3d(...)`. |

CSS rules that **must** be present on the element: `position: absolute` and `will-change: transform`. Add `[hidden] { display: none }` to respect the SDK's visibility management.

## Step 6 — Annotation Provider

Annotations display additional information anchored to a barcode. Assign an `annotationProvider` object to the `BarcodeArView`.

The same callback pattern applies: deliver results via `callback(annotation)`, not return.

```typescript
import {
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArAnnotationTrigger,
} from "@scandit/web-datacapture-barcode";

barcodeArView.annotationProvider = {
  async annotationForBarcode(barcode, callback) {
    const body = BarcodeArInfoAnnotationBodyComponent.create(); // static factory, not `new`
    body.text = barcode.data ?? "";

    const annotation = BarcodeArInfoAnnotation.create(barcode);
    annotation.body = [body];
    annotation.annotationTrigger = BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan;
    callback(annotation);
    // To show no annotation: callback(null)
  },
};
```

### BarcodeArInfoAnnotation

The primary annotation type. Use static factory `BarcodeArInfoAnnotation.create(barcode)`.

Key properties:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `body` | `BarcodeArInfoAnnotationBodyComponent[]` | `[]` | Array of body rows. |
| `header` | `BarcodeArInfoAnnotationHeader \| null` | `null` | Optional header section. |
| `footer` | `BarcodeArInfoAnnotationFooter \| null` | `null` | Optional footer section. |
| `widthPreset` | `BarcodeArInfoAnnotationWidthPreset` | `Small` | `Small`, `Medium`, or `Large`. |
| `anchor` | `BarcodeArInfoAnnotationAnchor` | `Bottom` | `Top`, `Bottom`, `Left`, `Right`. |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | `HighlightTapAndBarcodeScan` | When to show the annotation. |
| `isEntireAnnotationTappable` | `boolean` | `false` | If `true`, tapping anywhere fires the tap listener. |
| `backgroundColor` | `Color` | `#CCFFFFFF` | Background color of the annotation card. |
| `hasTip` | `boolean` | `true` | Whether to show the pointer tip toward the barcode. |

### BarcodeArAnnotationTrigger Values

| Value | Description |
|-------|-------------|
| `BarcodeScan` | Show immediately whenever a barcode is scanned, regardless of tap. |
| `HighlightTap` | Show only when user taps the highlight. |
| `HighlightTapAndBarcodeScan` | Show immediately on scan; hide/show on highlight tap. |

### BarcodeArPopoverAnnotation

Displays a row of icon+text buttons when the user taps a barcode highlight. Add buttons via DOM `append()`:

```typescript
import {
  BarcodeArPopoverAnnotation,
  BarcodeArPopoverAnnotationButton,
} from "@scandit/web-datacapture-barcode";
import { ScanditIconBuilder, ScanditIconType } from "@scandit/web-datacapture-core";

barcodeArView.annotationProvider = {
  async annotationForBarcode(barcode, callback) {
    const annotation = BarcodeArPopoverAnnotation.create(barcode);

    // create(icon, text?) — icon is required; text is optional second arg
    const infoIcon = await new ScanditIconBuilder().withIcon(ScanditIconType.InspectItem).build();
    const detailsButton = BarcodeArPopoverAnnotationButton.create(infoIcon, "Details");
    detailsButton.addEventListener("click", () => {
      console.log("Details clicked for:", barcode.data);
    });

    const checkIcon = await new ScanditIconBuilder().withIcon(ScanditIconType.Checkmark).build();
    const addButton = BarcodeArPopoverAnnotationButton.create(checkIcon, "Add");
    addButton.addEventListener("click", () => {
      console.log("Add clicked for:", barcode.data);
    });

    annotation.append(detailsButton, addButton);
    callback(annotation);
  },
};
```

### BarcodeArStatusIconAnnotation

A compact icon that expands to show text when tapped. Use static factory `BarcodeArStatusIconAnnotation.create(barcode)`.

```typescript
import { BarcodeArStatusIconAnnotation } from "@scandit/web-datacapture-barcode";
import { ScanditIconBuilder, ScanditIconType } from "@scandit/web-datacapture-core";

barcodeArView.annotationProvider = {
  async annotationForBarcode(barcode, callback) {
    const annotation = BarcodeArStatusIconAnnotation.create(barcode);
    annotation.icon = await new ScanditIconBuilder().withIcon(ScanditIconType.ExclamationMark).build();
    annotation.text = "Low stock";
    callback(annotation);
  },
};
```

### BarcodeArResponsiveAnnotation

Switches between two `BarcodeArInfoAnnotation` variants based on barcode size relative to the screen.

> **Important**: `BarcodeArResponsiveAnnotation.threshold` is a **static property** — set it BEFORE calling `BarcodeArResponsiveAnnotation.create()`.

```typescript
import {
  BarcodeArResponsiveAnnotation,
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationWidthPreset,
} from "@scandit/web-datacapture-barcode";

barcodeArView.annotationProvider = {
  async annotationForBarcode(barcode, callback) {
    const closeBody = BarcodeArInfoAnnotationBodyComponent.create();
    closeBody.text = `${barcode.data} — full details`;
    const closeUpAnnotation = BarcodeArInfoAnnotation.create(barcode);
    closeUpAnnotation.body = [closeBody];
    closeUpAnnotation.widthPreset = BarcodeArInfoAnnotationWidthPreset.Large;

    const farBody = BarcodeArInfoAnnotationBodyComponent.create();
    farBody.text = "Get closer";
    const farAnnotation = BarcodeArInfoAnnotation.create(barcode);
    farAnnotation.body = [farBody];
    farAnnotation.widthPreset = BarcodeArInfoAnnotationWidthPreset.Small;

    BarcodeArResponsiveAnnotation.threshold = 0.05; // 5% of screen = close-up threshold
    const annotation = BarcodeArResponsiveAnnotation.create(barcode, closeUpAnnotation, farAnnotation);
    callback(annotation);
  },
};
```

### Custom HTML Element Annotation (Web Components)

For complete control over annotation appearance, implement `BarcodeArAnnotation` as a custom HTML element. The same `updatePosition` contract applies as for custom highlights.

```typescript
import type { Barcode, BarcodeArAnnotation, BarcodeArInfoAnnotationAnchor } from "@scandit/web-datacapture-barcode";
import { BarcodeArAnnotationTrigger } from "@scandit/web-datacapture-barcode";
import type { Point, ScanditIcon } from "@scandit/web-datacapture-core";
import { Brush } from "@scandit/web-datacapture-core";

const tag = "custom-annotation-view";

export class CustomAnnotationView extends HTMLElement implements BarcodeArAnnotation {
  public barcode!: Barcode;
  public brush: Brush = new Brush();
  public icon: ScanditIcon | null = null;
  public annotationTrigger: BarcodeArAnnotationTrigger = BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan;
  public anchor: BarcodeArInfoAnnotationAnchor | undefined = undefined;

  public static create(barcode: Barcode): CustomAnnotationView {
    const element = document.createElement(tag) as CustomAnnotationView;
    element.barcode = barcode;
    return element;
  }

  public connectedCallback(): void {
    this.innerHTML = `
      <style>
        custom-annotation-view {
          position: absolute;
          will-change: transform;
          width: 100px;
          height: 100px;
          background-color: yellow;
        }
        custom-annotation-view[hidden] { display: none; }
      </style>
      <div>Custom Annotation</div>
    `;
  }

  public updatePosition(point: Point, transformOrigin: Point, rotationAngle: number): void {
    this.style.transform =
      `translate3d(calc(${Math.round(point.x)}px + ${transformOrigin.x}%), ` +
      `calc(${Math.round(point.y)}px + ${transformOrigin.y}%), 0px) ` +
      `rotate(${rotationAngle}deg)`;
  }
}

if (!customElements.get(tag)) {
  customElements.define(tag, CustomAnnotationView);
}
```

Use it in an annotation provider:

```typescript
barcodeArView.annotationProvider = {
  async annotationForBarcode(barcode, callback) {
    callback(CustomAnnotationView.create(barcode));
  },
};
```

**Requirements for a custom annotation element:**

| Member | Type | Description |
|--------|------|-------------|
| `barcode` | `Barcode` | Set by your factory. |
| `brush` | `Brush` | Required by the interface (can be a default `new Brush()`). |
| `icon` | `ScanditIcon \| null` | Required by the interface (can be `null`). |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | Controls when the annotation is shown. Default: `HighlightTapAndBarcodeScan`. |
| `anchor` | `BarcodeArInfoAnnotationAnchor \| undefined` | Controls the attachment point relative to the barcode. |
| `updatePosition(point, transformOrigin, rotationAngle)` | `void` | Called every frame to position the element. Apply as `transform: translate3d(...)`. |

CSS rules that **must** be present: `position: absolute` and `will-change: transform`. Add `[hidden] { display: none }` to respect SDK visibility management.

> **Note**: Custom element highlights and annotations are registered once via `customElements.define`. Guard the call with `if (!customElements.get(tag))` to avoid re-registration errors when the module is imported multiple times.

## Step 7 — Start Scanning

```typescript
await barcodeArView.start();
```

`start()` is required — the view does NOT start automatically after `create()`.

## Step 8 — Lifecycle and Cleanup

### Freeze / resume (e.g. navigating away and back)

```typescript
// Freeze — pauses scanning, keeps camera warm for faster resume
await barcodeArView.pause();

// Resume
await barcodeArView.start();
```

### Full cleanup (e.g. page unmount)

```typescript
await barcodeArView.stop();     // stops scanning, releases camera
barcodeArView.remove();         // removes the element from the DOM
await context.dispose();        // releases all SDK resources
```

## Complete Example

```typescript
import {
  BarcodeAr,
  BarcodeArSettings,
  BarcodeArView,
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArAnnotationTrigger,
  barcodeCaptureLoader,
  Symbology,
} from "@scandit/web-datacapture-barcode";
import { DataCaptureContext } from "@scandit/web-datacapture-core";

async function run(): Promise<void> {
  // Step 1: Initialize context — forLicenseKey() sets DataCaptureContext.sharedInstance
  await DataCaptureContext.forLicenseKey(
    "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
    {
      libraryLocation: new URL("library/engine/", document.baseURI).toString(),
      moduleLoaders: [barcodeCaptureLoader()],
    }
  );

  // Step 2: Configure settings
  const settings = new BarcodeArSettings();
  settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.EAN8, Symbology.Code128]);

  // Step 3: Create BarcodeAr mode
  const barcodeAr = await BarcodeAr.forContext(DataCaptureContext.sharedInstance, settings);

  // Optional: session listener
  barcodeAr.addListener({
    didUpdateSession: (_barcodeAr, session) => {
      for (const tracked of Object.values(session.addedTrackedBarcodes)) {
        console.log("Tracked:", tracked.barcode.data);
      }
    },
  });

  // Step 4: Create BarcodeArView
  const container = document.getElementById("barcode-ar-view")!;
  const barcodeArView = await BarcodeArView.create(container, DataCaptureContext.sharedInstance, barcodeAr);
  barcodeArView.shouldShowTorchControl = true;

  // Step 5: Highlight provider (callback pattern — do NOT return the value)
  barcodeArView.highlightProvider = {
    async highlightForBarcode(barcode, callback) {
      const highlight = BarcodeArCircleHighlight.create(barcode, BarcodeArCircleHighlightPreset.Dot);
      callback(highlight);
    },
  };

  // Step 6: Annotation provider (callback pattern)
  barcodeArView.annotationProvider = {
    async annotationForBarcode(barcode, callback) {
      const body = BarcodeArInfoAnnotationBodyComponent.create(); // static factory, not `new`
      body.text = barcode.data ?? "";

      const annotation = BarcodeArInfoAnnotation.create(barcode);
      annotation.body = [body];
      annotation.annotationTrigger = BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan;
      callback(annotation);
    },
  };

  // Step 7: Start
  await barcodeArView.start();
}

run();
```

## Key Rules

1. **`BarcodeAr.forContext()` and `BarcodeArView.create()` are both async** — always `await` them.
2. **Providers use callback pattern** — `callback(highlight)` / `callback(annotation)`. Never return the value. `callback(null)` to show nothing.
3. **`start()` is required** — the view does not start automatically.
4. **BarcodeArView manages camera** — do NOT set up `Camera`, `setFrameSource`, or `switchToDesiredState` manually.
5. **No `DataCaptureView`** — `BarcodeArView.create()` replaces it entirely.
6. **Cleanup order**: `stop()` → `remove()` → `context.dispose()`.
7. **COOP/COEP headers are mandatory** — without them the SDK runs single-threaded and AR tracking is too slow.
8. **`barcodeCaptureLoader()`** is the module loader for all barcode modes including BarcodeAr.

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Barcodes tracked but no highlights/annotations appear | Forgot to call `barcodeArView.start()`, or provider never calls `callback()`. |
| Provider returns a value instead of calling callback | On web, providers use callback pattern: `callback(highlight)` — do not `return` the value. |
| Camera black screen or view not rendering | Container has no dimensions or `position: static`. Add `position: fixed; inset: 0` or explicit width/height. |
| `BarcodeAr.forContext` undefined | Imported from wrong package, or `barcodeCaptureLoader()` was not passed to `DataCaptureContext.forLicenseKey`. |
| AR too slow / not keeping up with motion | COOP/COEP headers missing. Check browser devtools for SharedArrayBuffer availability. |
| Icon is `undefined` | `ScanditIconBuilder.build()` is async on web — `await` it before assigning to `highlight.icon`. |
