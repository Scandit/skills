# MatrixScan Count iOS — Clustering (Grouping Barcodes)

This guide covers **clustering** — grouping several scanned barcodes that belong together into a single
unit, either automatically from their visual context or manually by the user. It assumes the basic
integration is already in place (see `integration.md`);
here we only add clustering on top — do not re-create the context, mode, view, camera, or lifecycle.

> **Clustering vs. group scanning.** Clustering groups barcodes that physically belong together (e.g. a
> multi-pack) into one highlight within a single count. If instead you want to split one counting session
> into separate batches the user advances through (e.g. one per pallet), that is **group scanning** — see
> `group-scanning.md`.

> **Not compatible with scan preview.** Clustering cannot be combined with scan preview
> (`BarcodeCountSettings(scanPreviewEnabled:)`). If the user asks for both, do **not** write code enabling
> them together — say the combination isn't supported and ask which one they want.

> If a clustering API doesn't resolve, verify the symbol against the
> [BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html)
> before guessing.

## Enable clustering

Clustering is off by default. Turn it on by setting `clusteringMode` on `BarcodeCountSettings` **before**
constructing the `BarcodeCount` mode:

```swift
let settings = BarcodeCountSettings()
settings.set(symbology: .ean13UPCA, enabled: true)
settings.clusteringMode = .auto

let barcodeCount = BarcodeCount(context: context, settings: settings)
```

`ClusteringMode` has four cases:

| Mode | Behavior |
|------|----------|
| `.disabled` | No clustering (the default). |
| `.manual` | The user groups barcodes themselves using the built-in on-screen gesture UI. |
| `.auto` | Clusters are formed automatically and **cannot** be manually changed. |
| `.autoWithManualCorrection` | Clusters are formed automatically, but the user can also form or dissolve them via the UI. |

When clustering is enabled, the barcodes that form a cluster share a single **rectangular highlight**.
Clustered codes still appear individually in `session.recognizedBarcodes` (and the clusters in
`session.recognizedClusters`).

Optionally tell the SDK how many barcodes you expect in each cluster — this drives each cluster's
`expectationStatus` (below). It is `Int?` (Swift); leave it `nil` (the default) if you have no expectation:

```swift
settings.expectedNumberOfBarcodesPerCluster = 4
```

## Reading the recognized clusters

Clusters are exposed on the session as `recognizedClusters`. As with `recognizedBarcodes`, the
`BarcodeCountSession` is **only valid inside the listener callback** — copy what you need out and hop to
the main queue before touching UIKit:

```swift
extension CountViewController: BarcodeCountListener {
    func barcodeCount(_ barcodeCount: BarcodeCount,
                      didScanIn session: BarcodeCountSession,
                      frameData: FrameData) {
        let clusters = session.recognizedClusters
        DispatchQueue.main.async {
            for cluster in clusters {
                // cluster.barcodes is [Barcode]; cluster.expectationStatus is a ClusterExpectationStatus
                // enum — switch over it rather than printing it (it has no human-readable description).
                let status: String
                switch cluster.expectationStatus {
                case .matches:      status = "matches the expected count"
                case .deviates:     status = "deviates from the expected count"
                case .notEvaluated: status = "no expectation set"
                @unknown default:   status = "unknown"
                }
                print("cluster of \(cluster.barcodes.count) barcodes — \(status)")
            }
        }
    }
}
```

Each `Cluster` exposes:
- `barcodes` (`[Barcode]`) — the barcodes grouped into this cluster.
- `expectationStatus` (`ClusterExpectationStatus`) — how the cluster's size compares to
  `expectedNumberOfBarcodesPerCluster`: `.notEvaluated` (no expectation set, or not yet evaluated),
  `.matches` (size matches the expected count), or `.deviates` (size differs).

`BarcodeCountSessionSnapshot` (from the List/Exit UI-delegate callbacks) also exposes `recognizedClusters`.

## Manual clustering (the user gesture UI)

In `.manual` and `.autoWithManualCorrection`, the user forms clusters with the built-in gesture UI: they
swipe or circle (draw a shape around) the barcodes they want to group, and when the gesture completes,
every barcode inside the drawn area is grouped into one cluster. Tapping the **×** on a cluster's
highlight bursts (dissolves) it.

Customize the on-screen hint that tells the user how to cluster:

```swift
barcodeCountView.setTextForClusteringGestureHint("Swipe across barcodes to group them")
```

## Forming and dissolving clusters programmatically

You can also form and dissolve clusters from code (e.g. a "group all" / "ungroup" button) — get a
`BarcodeClusterEditor` from the mode, make your edits, and call `endEditing()`:

```swift
// Group the currently recognized barcodes into one cluster:
let editor = barcodeCount.beginClusterEditing()
editor?.formCluster(session.recognizedBarcodes)
editor?.endEditing()

// Dissolve every existing cluster:
let editor = barcodeCount.beginClusterEditing()
session.recognizedClusters.forEach { editor?.dissolveCluster($0) }
editor?.endEditing()
```

- `beginClusterEditing()` returns a `BarcodeClusterEditor?` (nullable — handle the `nil` case).
- `formCluster(_:)` takes `[Barcode]`; `dissolveCluster(_:)` takes a `Cluster`.
- Always finish with `endEditing()` to commit the edits.
- `beginClusterEditing()` returns `nil` unless the mode allows **manual** editing — you get an editor
  only in **`.manual`** and **`.autoWithManualCorrection`**; in `.disabled` and `.auto` it returns `nil`
  (that's why the call is optional). `formCluster(_:)` also **fails if a barcode is already in a cluster**,
  so forming your own groups is most predictable in **`.manual`** (nothing is auto-clustered).

## Customizing the cluster highlight and taps

Set the view's `delegate` (`BarcodeCountViewDelegate` — the same delegate used for per-barcode brushes/
icons) to color clusters and react to taps:

```swift
barcodeCountView.delegate = self

extension CountViewController: BarcodeCountViewDelegate {
    func barcodeCountView(_ view: BarcodeCountView,
                          brushForCluster cluster: Cluster) -> Brush? {
        // For clusters only the fill COLOR is used — pass a solid color.
        switch cluster.expectationStatus {
        case .matches:      return Brush(fill: .systemGreen, stroke: .clear, strokeWidth: 0)
        case .deviates:     return Brush(fill: .systemRed,   stroke: .clear, strokeWidth: 0)
        case .notEvaluated: return Brush(fill: .systemGray,  stroke: .clear, strokeWidth: 0)
        @unknown default:   return nil
        }
    }

    func barcodeCountView(_ view: BarcodeCountView,
                          didTap cluster: Cluster) {
        // e.g. show what's in the tapped cluster (cluster.barcodes)
    }
}
```

- When barcodes are grouped, the members' individual highlights are **not** drawn — the whole cluster is
  represented by a **single highlight at its center** (one icon, plus the background you set). You do
  **not** customize each member; you customize the one cluster highlight.
- **Background color** — set it with `barcodeCountView(_:brushForCluster:)`. For clusters, only the
  brush's fill **color** is applied (the SDK supplies the cluster's transparency and border itself), so
  just return a solid color — the fill's alpha, the stroke color, and the stroke width are ignored. It
  works in the default Icon style (no need to switch to Dot). Return `nil` to keep the SDK default.
  `Brush` is `Brush(fill:stroke:strokeWidth:)` — **not** `fillColor:`/`strokeColor:` (see `highlights.md`).
- **The single center icon** follows a precedence (you don't pick it directly):
  1. if any member is **not-in-list / rejected**, that state's icon is used;
  2. otherwise, if the cluster's count **deviates** from `expectedNumberOfBarcodesPerCluster`, the SDK's
     default deviation icon is shown (your custom icon is **not** used in this case);
  3. otherwise the cluster shows a **representative member's** icon — i.e. whatever your
     `iconForRecognizedBarcode` returns for that member.
  There is **no** per-cluster icon callback, so to control the icon, return the **same** icon for every
  barcode from `iconForRecognizedBarcode` (then whichever member represents the cluster looks the same).
- `barcodeCountView(_:didTap:)` (with a `Cluster` parameter) fires when the user taps a cluster
  highlight. Note the Swift name is `didTap:`, **not** `didTapCluster:` — the SDK shortens it because the
  parameter type is already `Cluster`.

> If you also use **status mode** with clustering on, the per-barcode status icons are organized on the
> cluster highlight (not per individual barcode) — see `status-mode.md`.

## After wiring up

Build the project. If a clustering API doesn't resolve or a delegate method isn't called, fetch the
[Advanced Configurations](https://docs.scandit.com/sdks/ios/matrixscan-count/advanced/) page (Clustering
section) and the
[BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html)
to confirm the current signatures before guessing. Always include the docs link in your answer.
