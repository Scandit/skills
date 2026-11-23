# Scanning Against a List (BarcodeCountCaptureList)

> **This is the canonical way to validate scans against a picklist, packing slip, or backend order.**
> Do NOT compare scanned data against a plain JavaScript array. `BarcodeCountCaptureList` is the only
> mechanism that produces correct `correctBarcodes` / `wrongBarcodes` / `missingBarcodes` session data
> and drives the built-in progress bar. A JS array comparison will miss quantity tracking, will not
> drive the view's visual states, and will not trigger `didCompleteCaptureList`.

For a new React Native screen, follow the [integration setup](integration.md) for packages, permissions and camera lifecycle.

---

### 9a — Modeling the target list

A typical packing slip or picklist arrives from a backend API as a JSON array:

```json
[
  { "symbology": "ean13Upca", "data": "4006381333931", "quantity": 2 },
  { "symbology": "ean13Upca", "data": "4006381333948", "quantity": 1 },
  { "symbology": "code128",   "data": "ITEM-ABC-001",  "quantity": 3 }
]
```

Convert each entry to a `TargetBarcode` using `TargetBarcode.create(data, quantity)`. The `data` field
is a plain string (the barcode's decoded value). Symbology is not stored on `TargetBarcode` — it is
enforced by enabling the correct symbologies in `BarcodeCountSettings` (see step 9c).

```typescript
import {
  BarcodeCountCaptureList,
  BarcodeCountCaptureListListener,
  BarcodeCountCaptureListSession,
  TargetBarcode,
} from 'scandit-react-native-datacapture-barcode';
import { useMemo, useRef } from 'react';

// Shape of a picklist item from your backend
interface PicklistItem {
  symbology: string;
  data: string;
  quantity: number;
}

// Example picklist — in practice this comes from navigation params or a React context
const PICKLIST: PicklistItem[] = [
  { symbology: 'ean13Upca', data: '4006381333931', quantity: 2 },
  { symbology: 'ean13Upca', data: '4006381333948', quantity: 1 },
  { symbology: 'code128',   data: 'ITEM-ABC-001',  quantity: 3 },
];

export const ScanPage = () => {
  // Build TargetBarcode[] once — useMemo prevents rebuild on every render
  const targetBarcodes = useMemo<TargetBarcode[]>(
    () => PICKLIST.map(item => TargetBarcode.create(item.data, item.quantity)),
    [] // static list; add PICKLIST to deps if it changes at runtime
  );

  // ...rest of component (see below)
};
```

`TargetBarcode` API:

```typescript
const target = TargetBarcode.create('4006381333931', 2);
console.log(target.data);     // '4006381333931'
console.log(target.quantity); // 2  — must be >= 1
```

---

### 9b — Wiring the list to the mode

Construct `BarcodeCountCaptureList` with `BarcodeCountCaptureList.create(listener, targetBarcodes)`,
then call `barcodeCount.setBarcodeCountCaptureList(captureList)` **immediately after** constructing
the `BarcodeCount` mode.

> **Critical**: If you skip `setBarcodeCountCaptureList`, the view renders in "free count" mode —
> no matched/not-in-list distinction, no progress bar, no `didCompleteCaptureList` callback.

```typescript
import {
  BarcodeCount,
  BarcodeCountCaptureList,
  BarcodeCountCaptureListListener,
  BarcodeCountCaptureListSession,
  BarcodeCountSettings,
  Symbology,
  TargetBarcode,
} from 'scandit-react-native-datacapture-barcode';
import dataCaptureContext from './CaptureContext';

// Inside your function component, after targetBarcodes is built with useMemo:

const barcodeCountRef = useRef<BarcodeCount>(null!);
const captureListRef = useRef<BarcodeCountCaptureList>(null!);

if (!barcodeCountRef.current) {
  const settings = new BarcodeCountSettings();
  // Enable every symbology that appears in your picklist
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.UPCE,
    Symbology.Code128,
  ]);

  const barcodeCount = new BarcodeCount(settings);

  // BarcodeCountListener — fires once per shutter tap
  barcodeCount.addListener({
    didScan: async (_: BarcodeCount, session) => {
      // session.recognizedBarcodes: Barcode[] — all barcodes seen so far
      console.log('Total recognized:', session.recognizedBarcodes.length);
    },
  });

  // Build the capture list listener (see section 9d for full implementation)
  const captureListListener: BarcodeCountCaptureListListener = {
    didUpdateSession: (list: BarcodeCountCaptureList, session: BarcodeCountCaptureListSession) => {
      console.log('Correct:', session.correctBarcodes.length);
      console.log('Wrong (not in list):', session.wrongBarcodes.length);
      console.log('Missing:', session.missingBarcodes.length);
    },
  };

  const captureList = BarcodeCountCaptureList.create(captureListListener, targetBarcodes);

  // REQUIRED: attach the list to the mode
  barcodeCount.setBarcodeCountCaptureList(captureList);

  barcodeCountRef.current = barcodeCount;
  captureListRef.current = captureList;
}
```

---

### 9c — Handling matched / not-in-list visualization

When `viewStyle` is `BarcodeCountViewStyle.Dot`, the three visual states are driven by three brush
properties on `BarcodeCountView`:

| State | Session source | Brush property | Recommended color |
|-------|---------------|----------------|-------------------|
| Scanned and in list (`correctBarcodes`) | `session.correctBarcodes` | `view.recognizedBrush` | Green `#4CAF50` |
| Scanned but not in list (`wrongBarcodes`) | `session.wrongBarcodes` | `view.notInListBrush` | Red `#F44336` |
| Accepted by user (via not-in-list popup) | `session.acceptedBarcodes` | `view.acceptedBrush` | Blue `#2196F3` |

Set global brushes in the `ref` callback:

```tsx
import { Brush, Color } from 'scandit-react-native-datacapture-core';
import { BarcodeCountViewStyle } from 'scandit-react-native-datacapture-barcode';

<BarcodeCountView
  style={{ flex: 1 }}
  barcodeCount={barcodeCountRef.current}
  context={dataCaptureContext}
  viewStyle={BarcodeCountViewStyle.Dot}
  ref={view => {
    if (view) {
      // Matched-on-list = green
      view.recognizedBrush = new Brush(
        Color.fromHex('#4CAF50'),
        Color.fromHex('#4CAF50'),
        1,
      );
      // Not-in-list = red
      view.notInListBrush = new Brush(
        Color.fromHex('#F44336'),
        Color.fromHex('#F44336'),
        1,
      );
      // Accepted via the not-in-list popup = blue (RN 7.1+)
      view.acceptedBrush = new Brush(
        Color.fromHex('#2196F3'),
        Color.fromHex('#2196F3'),
        1,
      );

      // Show the built-in progress bar
      view.shouldShowListProgressBar = true;

      view.listener = viewListenerRef.current;
      view.uiListener = viewUiListenerRef.current;
    }
  }}
/>
```

For dynamic per-barcode colors (e.g. to shade items by how close they are to their target quantity),
call `setBrushForRecognizedBarcodeNotInList` imperatively from inside `BarcodeCountViewListener`:

```typescript
const viewListener: BarcodeCountViewListener = {
  brushForRecognizedBarcodeNotInList: (view, trackedBarcode) => {
    // Return a custom brush based on the barcode's data
    const isKnownExtra = myExtraItemSet.has(trackedBarcode.barcode.data ?? '');
    return isKnownExtra
      ? new Brush(Color.fromHex('#FF9800'), Color.fromHex('#FF9800'), 1)  // orange: known extra
      : new Brush(Color.fromHex('#F44336'), Color.fromHex('#F44336'), 1); // red: unexpected
  },
};
```

---

### 9d — Wiring BarcodeCountCaptureListListener

`BarcodeCountCaptureListListener` is the primary hook for reacting to list progress. It fires
alongside (not instead of) `BarcodeCountListener.didScan` — both listeners co-exist on the same
`BarcodeCount` instance.

The JavaScript method name on `BarcodeCountCaptureListListener` is **`didUpdateSession`**
(`:available: react-native=6.17`). On RN 8.3+, `didCompleteCaptureList` is also available on the
listener (in addition to `BarcodeCountViewListener.didCompleteCaptureList`).

```typescript
import {
  BarcodeCountCaptureList,
  BarcodeCountCaptureListListener,
  BarcodeCountCaptureListSession,
  TargetBarcode,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';

// Hold derived state in a ref so it is available when navigating to results
const listSessionRef = useRef<{
  correct: TrackedBarcode[];
  wrong: TrackedBarcode[];
  missing: TargetBarcode[];
}>({ correct: [], wrong: [], missing: [] });

const captureListListener: BarcodeCountCaptureListListener = {
  /**
   * Called after each frame that changes the list state.
   *
   * session.correctBarcodes  — TrackedBarcode[] matched to a TargetBarcode
   * session.wrongBarcodes    — TrackedBarcode[] scanned but NOT in the target list
   * session.missingBarcodes  — TargetBarcode[]  not yet scanned
   */
  didUpdateSession: (
    _list: BarcodeCountCaptureList,
    session: BarcodeCountCaptureListSession,
  ) => {
    const correct = session.correctBarcodes;
    const wrong   = session.wrongBarcodes;
    const missing = session.missingBarcodes;

    // Cache for the results screen
    listSessionRef.current = { correct, wrong, missing };

    // Compute progress: how many distinct target items have been fulfilled
    const fulfilledCount = targetBarcodes.length - missing.length;
    const total = targetBarcodes.length;
    console.log(`Progress: ${fulfilledCount}/${total} items, ${wrong.length} extras`);
  },

  // RN 8.3+: fires when ALL target barcodes have been scanned at the required quantity
  didCompleteCaptureList: (_list: BarcodeCountCaptureList, _session: BarcodeCountCaptureListSession) => {
    console.log('All items scanned — capture list complete');
  },
};
```

---

### 9e — Progress UI

Surface progress to the user in two complementary ways:

**Built-in progress bar** — turn on `shouldShowListProgressBar` on the view (already shown in 9c).
The SDK drives it automatically from the capture list session.

**Custom progress text** — derive counts from the `listSessionRef` kept in 9d and display them
in your own UI:

```tsx
import React, { useState } from 'react';
import { Text, View } from 'react-native';

// State driven from the listSessionRef inside didUpdateSession:
const [progress, setProgress] = useState({ fulfilled: 0, total: 0, extras: 0 });

// Inside didUpdateSession, after computing counts:
const captureListListener: BarcodeCountCaptureListListener = {
  didUpdateSession: (_list, session) => {
    listSessionRef.current = {
      correct: session.correctBarcodes,
      wrong:   session.wrongBarcodes,
      missing: session.missingBarcodes,
    };

    const fulfilled = targetBarcodes.length - session.missingBarcodes.length;
    setProgress({
      fulfilled,
      total:  targetBarcodes.length,
      extras: session.wrongBarcodes.length,
    });
  },
};

// In JSX:
<View style={{ padding: 8 }}>
  <Text>{progress.fulfilled} of {progress.total} items scanned</Text>
  {progress.extras > 0 && (
    <Text style={{ color: '#F44336' }}>{progress.extras} unexpected item(s) detected</Text>
  )}
</View>
```

To sum quantities rather than count distinct target items, reduce over the original `targetBarcodes`
array and subtract quantities still present in `session.missingBarcodes`:

```typescript
const totalQty = targetBarcodes.reduce((sum, t) => sum + t.quantity, 0);
const missingQty = session.missingBarcodes.reduce((sum, t) => sum + t.quantity, 0);
const scannedQty = totalQty - missingQty;
// => "X of Y units scanned"
```

---

### 9f — Results screen

When the user taps the list button or the exit button, navigate to a results screen. Derive the
three lists from `listSessionRef.current`:

```tsx
// ResultsPage.tsx
import React from 'react';
import { FlatList, SectionList, Text, View } from 'react-native';
import { TargetBarcode, TrackedBarcode } from 'scandit-react-native-datacapture-barcode';

interface ResultsPageProps {
  correct: TrackedBarcode[];    // matched to target — show with checkmark
  wrong: TrackedBarcode[];      // not in list — show as unexpected
  missing: TargetBarcode[];     // never scanned — show as missing
}

export const ResultsPage = ({ correct, wrong, missing }: ResultsPageProps) => {
  const sections = [
    {
      title: `Matched (${correct.length})`,
      data: correct.map(tb => ({
        key: tb.barcode.data ?? '',
        label: `✓ ${tb.barcode.data}`,
        color: '#4CAF50',
      })),
    },
    {
      title: `Missing (${missing.length})`,
      data: missing.map(tb => ({
        key: tb.data + tb.quantity,
        label: `✗ ${tb.data}  ×${tb.quantity}`,
        color: '#9E9E9E',
      })),
    },
    {
      title: `Unexpected (${wrong.length})`,
      data: wrong.map(tb => ({
        key: tb.barcode.data ?? '',
        label: `! ${tb.barcode.data}`,
        color: '#F44336',
      })),
    },
  ];

  return (
    <SectionList
      sections={sections}
      keyExtractor={item => item.key}
      renderSectionHeader={({ section }) => (
        <Text style={{ fontWeight: 'bold', padding: 8 }}>{section.title}</Text>
      )}
      renderItem={({ item }) => (
        <Text style={{ color: item.color, paddingLeft: 16, paddingVertical: 4 }}>
          {item.label}
        </Text>
      )}
    />
  );
};
```

Wire it from `BarcodeCountViewUiListener`:

```typescript
const viewUiListener: BarcodeCountViewUiListener = {
  didTapListButton: (_: BarcodeCountView) => {
    navigation.navigate('Results', {
      correct: listSessionRef.current.correct,
      wrong:   listSessionRef.current.wrong,
      missing: listSessionRef.current.missing,
    });
  },
  didTapExitButton: (_: BarcodeCountView) => {
    camera.switchToDesiredState(FrameSourceState.Off);
    navigation.navigate('Results', {
      correct: listSessionRef.current.correct,
      wrong:   listSessionRef.current.wrong,
      missing: listSessionRef.current.missing,
    });
  },
};
```

---

### 9g — Exit / re-entry behavior

The capture list **persists across scanning phases** — navigating to a results screen and returning
does not reset it. This is intentional: the user can scan more items and the already-matched barcodes
remain matched.

To resume scanning when the user navigates back:

```typescript
useFocusEffect(
  useCallback(() => {
    // Camera was off while on the results screen — turn it back on
    cameraRef.current.switchToDesiredState(FrameSourceState.On);
    barcodeCountRef.current.isEnabled = true;
  }, [])
);
```

To **swap to a new picklist** (e.g. the user moves to the next order):

```typescript
async function loadNewPicklist(newItems: PicklistItem[]) {
  const newTargetBarcodes = newItems.map(item =>
    TargetBarcode.create(item.data, item.quantity)
  );

  // 1. Build and attach the new list
  const newList = BarcodeCountCaptureList.create(captureListListener, newTargetBarcodes);
  barcodeCountRef.current.setBarcodeCountCaptureList(newList);
  captureListRef.current = newList;

  // 2. Clear all visual highlights so the previous order's dots disappear
  await viewRef.current?.clearHighlights();

  // 3. Reset the BarcodeCount session (clears recognizedBarcodes history)
  await barcodeCountRef.current.reset();

  // 4. Reset local progress state
  listSessionRef.current = { correct: [], wrong: [], missing: [] };
}
```

> **Note**: Calling `barcodeCount.setBarcodeCountCaptureList(newList)` alone does NOT clear the
> visual highlights from the previous list — always follow it with `view.clearHighlights()` when
> switching lists mid-session.

---

### 9h — Common pitfalls

- **Do NOT compare scanned data against a plain JS array.** Only `BarcodeCountCaptureList` produces
  correct `correctBarcodes` / `wrongBarcodes` / `missingBarcodes` session data, drives the progress
  bar, and fires `didCompleteCaptureList`. A JS array comparison cannot replicate this behavior.

- **`TargetBarcode.create(data, quantity)` requires quantity ≥ 1.** Passing `0` produces
  undefined behavior. Guard against zero-quantity items in your picklist before creating
  `TargetBarcode` objects.

- **`BarcodeCountCaptureList` is symbology-agnostic.** Symbology filtering is enforced
  by `BarcodeCountSettings.enableSymbology`. If your picklist contains EAN-13 items but
  EAN-13 is not enabled in settings, those barcodes will never be recognized and will
  always appear in `missingBarcodes`. Ensure every symbology present in your picklist
  is enabled in settings.

- **`BarcodeCountCaptureListListener.didUpdateSession` fires alongside
  `BarcodeCountListener.didScan`, not instead of it.** Both listeners co-exist on the same
  `BarcodeCount` instance. Use `didScan` for the raw recognized-barcodes array and
  `didUpdateSession` for list-aware progress.

- **`setBarcodeCountCaptureList` must be called before the view mounts (or immediately
  after mode construction).** Calling it after the view is already scanning works but may
  produce a single frame with incorrect visual state.

- **The `didCompleteCaptureList` callback on `BarcodeCountCaptureListListener` requires
  react-native=8.3+.** On earlier versions, listen to `BarcodeCountViewListener.didCompleteCaptureList`
  instead (available from react-native=6.17 on the view listener).

---

### TargetBarcode quick reference

```typescript
// TargetBarcode.create(data, quantity)
// :available: react-native=6.17
const target = TargetBarcode.create('4006381333931', 2);
console.log(target.data);     // '4006381333931'
console.log(target.quantity); // 2
```

### BarcodeCountCaptureListSession property reference

| Property | Type | Description | Available |
|----------|------|-------------|-----------|
| `correctBarcodes` | `TrackedBarcode[]` | Scanned barcodes that matched a TargetBarcode in the list. | react-native=6.17 |
| `wrongBarcodes` | `TrackedBarcode[]` | Scanned barcodes that did NOT match any TargetBarcode. | react-native=6.17 |
| `missingBarcodes` | `TargetBarcode[]` | Target barcodes not yet scanned at the required quantity. | react-native=6.17 |
| `acceptedBarcodes` | `TrackedBarcode[]` | Barcodes accepted via the not-in-list action popup. | react-native=7.1 |
| `rejectedBarcodes` | `TrackedBarcode[]` | Barcodes rejected via the not-in-list action popup. | react-native=7.1 |
| `additionalBarcodes` | `Barcode[]` | Barcodes injected with `setAdditionalBarcodes`. | react-native=6.17 |
