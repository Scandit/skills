# MatrixScan Count Android — Clustering (Grouping Barcodes)

This guide covers **clustering** — grouping several scanned barcodes that belong together into a single
unit, either automatically from their visual context or manually by the user. It assumes the basic
integration is already in place (see `integration.md`); here we only add clustering on top — do not
re-create the context, mode, view, camera, or lifecycle.

> If a clustering API doesn't resolve, verify the symbol against the
> [BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html)
> before guessing.

## Enable clustering

Clustering is off by default. Turn it on by setting `clusteringMode` on `BarcodeCountSettings` **before**
constructing the `BarcodeCount` mode:

```kotlin
val settings = BarcodeCountSettings()
settings.setSymbologyEnabled(Symbology.EAN13_UPCA, true)
settings.clusteringMode = ClusteringMode.AUTO

val barcodeCount = BarcodeCount.forDataCaptureContext(dataCaptureContext, settings)
```

`ClusteringMode` (from `com.scandit.datacapture.core.data`) has four values:

| Mode | Behavior |
|------|----------|
| `DISABLED` | No clustering (the default). |
| `MANUAL` | The user groups barcodes themselves using the built-in on-screen gesture UI. |
| `AUTO` | Clusters are formed automatically and **cannot** be manually changed. |
| `AUTO_WITH_MANUAL_CORRECTION` | Clusters are formed automatically, but the user can also form or dissolve them via the UI. |

When clustering is enabled, the barcodes that form a cluster share a single **rectangular highlight**.
Clustered codes still appear individually in `session.recognizedBarcodes` (and the clusters in
`session.recognizedClusters`).

Optionally tell the SDK how many barcodes you expect in each cluster — this drives each cluster's
`expectationStatus` (below). It is a nullable `Integer`; leave it `null` (the default) if you have no
expectation:

```kotlin
settings.expectedNumberOfBarcodesPerCluster = 4
```

## Reading the recognized clusters

Clusters are exposed on the session as `recognizedClusters`. As with `recognizedBarcodes`, the
`BarcodeCountSession` is **only valid inside the listener callback** — copy what you need out and hop to
the main thread before touching UI:

```kotlin
override fun onScan(
    barcodeCount: BarcodeCount,
    session: BarcodeCountSession,
    data: FrameData
) {
    val clusters: List<Cluster> = session.recognizedClusters
    runOnUiThread {
        for (cluster in clusters) {
            val count = cluster.barcodes.size   // cluster.barcodes is List<Barcode>
            when (cluster.expectationStatus) {
                ClusterExpectationStatus.MATCHES -> { /* size matches the expected count */ }
                ClusterExpectationStatus.DEVIATES -> { /* size differs from the expected count */ }
                ClusterExpectationStatus.NOT_EVALUATED -> { /* no expectation set / not yet evaluated */ }
            }
        }
    }
}
```

Each `Cluster` exposes:
- `barcodes` (`List<Barcode>`) — the barcodes grouped into this cluster.
- `expectationStatus` (`ClusterExpectationStatus`, from `com.scandit.datacapture.core.data`) — how the
  cluster's size compares to `expectedNumberOfBarcodesPerCluster`: `NOT_EVALUATED` (no expectation set,
  or not yet evaluated), `MATCHES` (size matches), or `DEVIATES` (size differs).

## Manual clustering (the user gesture UI)

In `MANUAL` and `AUTO_WITH_MANUAL_CORRECTION`, the user forms clusters with the built-in gesture UI: they
swipe or circle (draw a shape around) the barcodes they want to group, and when the gesture completes,
every barcode inside the drawn area is grouped into one cluster. Tapping the **×** on a cluster's
highlight bursts (dissolves) it.

Customize the on-screen hint that tells the user how to cluster:

```kotlin
barcodeCountView.textForClusteringGestureHint = "Swipe across barcodes to group them"
```

## Forming and dissolving clusters programmatically

You can also form and dissolve clusters from code (e.g. a "group all" / "ungroup" button) — get a
`BarcodeClusterEditor` from the mode, make your edits, and call `endEditing()`:

```kotlin
// Group the currently recognized barcodes into one cluster:
val editor = barcodeCount.beginClusterEditing()
editor?.formCluster(session.recognizedBarcodes)
editor?.endEditing()

// Dissolve every existing cluster:
val editor = barcodeCount.beginClusterEditing()
session.recognizedClusters.forEach { editor?.dissolveCluster(it) }
editor?.endEditing()
```

- `beginClusterEditing()` returns a **nullable** `BarcodeClusterEditor?` — use `?.` / handle the `null`
  case. It returns `null` unless the mode allows **manual** editing, i.e. only in `MANUAL` and
  `AUTO_WITH_MANUAL_CORRECTION`; in `DISABLED` and `AUTO` it returns `null`.
- `formCluster(barcodes)` takes `List<Barcode>`; `dissolveCluster(cluster)` takes a `Cluster`.
- Always finish with `endEditing()` to commit the edits.
- `formCluster(...)` fails if a barcode is already in a cluster, so forming your own groups is most
  predictable in `MANUAL` (nothing is auto-clustered).

## Coloring clusters and reacting to taps

Set the view's `listener` (`BarcodeCountViewListener` — the same listener used for per-barcode brushes
and taps, see `highlights.md`) to color clusters via `brushForCluster` and react to taps via
`onClusterTapped`:

```kotlin
barcodeCountView.listener = object : BarcodeCountViewListener {
    override fun brushForCluster(view: BarcodeCountView, cluster: Cluster): Brush {
        // Color the cluster highlight by how its size compares to the expected count.
        return when (cluster.expectationStatus) {
            ClusterExpectationStatus.MATCHES -> Brush(Color.GREEN, Color.GREEN, 0f)
            ClusterExpectationStatus.DEVIATES -> Brush(Color.RED, Color.RED, 0f)
            ClusterExpectationStatus.NOT_EVALUATED -> Brush(Color.GRAY, Color.GRAY, 0f)
        }
    }

    override fun onClusterTapped(view: BarcodeCountView, cluster: Cluster) {
        // e.g. show what's in the tapped cluster (cluster.barcodes)
    }
}
```

`brushForCluster` returns a `Brush?` — return `null` to keep the SDK default, or a concrete `Brush`
(Android color ints) as above; for clusters the fill color is what the SDK applies.

## After wiring up

Build the project. If a clustering API doesn't resolve or a listener method isn't called, fetch the
[Advanced Configurations](https://docs.scandit.com/sdks/android/matrixscan-count/advanced/) page (Clustering
section) and the
[BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html)
to confirm the current signatures before guessing. Always include the docs link in your answer.
