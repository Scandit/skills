# Flutter State-Management & Route-Lifecycle Recipes

The base `integration.md` uses **StatefulWidget + `WidgetsBindingObserver`** because the official `IdCaptureSimpleSample` is written that way. Real Flutter apps usually pick one of: **BLoC** (the official extended sample), **Riverpod**, or **Provider**. They also tend to use a real router (Navigator 2.0, `RouteAware` + `RouteObserver`, or `GoRouter`) where *another* screen can sit on top of the scan screen — and the camera needs to pause for that, not just for OS background. This file covers each.

The **Scandit APIs themselves are identical** across all of these — the settings, listener, scanner, overlay, and `CapturedId` access in `references/integration.md` do not change. What differs is the **state-management harness** and the **route-aware lifecycle**.

## 1. BLoC pattern (matches `IdCaptureExtendedSample`)

The official `IdCaptureExtendedSample` uses a plain-Dart BLoC (StreamControllers, no `flutter_bloc` package). Owning the SDK handles in a BLoC keeps them out of the widget tree and makes per-screen disposal easy.

```dart
import 'dart:async';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
import 'package:scandit_flutter_datacapture_id/scandit_flutter_datacapture_id.dart';

class CapturedIdResult {
  final CapturedId captured;
  CapturedIdResult(this.captured);
}

class IdCaptureBloc implements IdCaptureListener {
  late final DataCaptureContext _context;
  late final IdCapture _idCapture;
  late final DataCaptureView _captureView;
  Camera? _camera = Camera.defaultCamera;

  final _capturedController = StreamController<CapturedIdResult>.broadcast();
  Stream<CapturedIdResult> get onCaptured => _capturedController.stream;

  final _rejectedController = StreamController<RejectionReason>.broadcast();
  Stream<RejectionReason> get onRejected => _rejectedController.stream;

  DataCaptureView get view => _captureView;

  IdCaptureBloc(String licenseKey) {
    _context = DataCaptureContext.forLicenseKey(licenseKey);

    // ... settings, scanner from integration.md ...
    final settings = IdCaptureSettings()
      ..acceptedDocuments.add(DriverLicense(IdCaptureRegion.any))
      ..scanner = IdCaptureScanner(physicalDocumentScanner: FullDocumentScanner());

    _idCapture = IdCapture(settings)..addListener(this);
    _captureView = DataCaptureView.forContext(_context);
    _captureView.addOverlay(IdCaptureOverlay(_idCapture));
    _context.setMode(_idCapture);

    _camera?.applySettings(IdCapture.createRecommendedCameraSettings());
    if (_camera != null) _context.setFrameSource(_camera!);
  }

  Future<void> enable() async {
    await _camera?.switchToDesiredState(FrameSourceState.on);
    _idCapture.isEnabled = true;
  }

  Future<void> disable() async {
    _idCapture.isEnabled = false;
    await _camera?.switchToDesiredState(FrameSourceState.off);
  }

  @override
  Future<void> didCaptureId(IdCapture idCapture, CapturedId capturedId) async {
    _idCapture.isEnabled = false; // pause while UI consumes the event
    _capturedController.sink.add(CapturedIdResult(capturedId));
  }

  @override
  Future<void> didRejectId(
      IdCapture idCapture, CapturedId? rejectedId, RejectionReason reason) async {
    _idCapture.isEnabled = false;
    _rejectedController.sink.add(reason);
  }

  void dispose() {
    _idCapture.removeListener(this);
    _idCapture.isEnabled = false;
    _camera?.switchToDesiredState(FrameSourceState.off);
    _context.removeAllModes();
    _capturedController.close();
    _rejectedController.close();
  }
}
```

The screen widget then just renders `bloc.view`, subscribes to `bloc.onCaptured` / `bloc.onRejected`, and calls `bloc.dispose()` in its `State.dispose()`. For `flutter_bloc`'s `Cubit`/`Bloc`, the same structure fits — the SDK lives as private fields on the cubit, `emit(...)` replaces `sink.add(...)`, and the override `close()` replaces `dispose()`.

## 2. Riverpod (`AsyncNotifier`)

If the app uses Riverpod, model the scan screen as an `AsyncNotifier` that owns the SDK handles in its `build` and cleans them up via `ref.onDispose`. Share a single `DataCaptureContext` across screens with a separate `Provider`.

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
import 'package:scandit_flutter_datacapture_id/scandit_flutter_datacapture_id.dart';

// Long-lived: one context per app run, shared across scan screens.
final dataCaptureContextProvider = Provider<DataCaptureContext>((ref) {
  final context = DataCaptureContext.forLicenseKey(
    '-- ENTER YOUR SCANDIT LICENSE KEY HERE --',
  );
  ref.onDispose(() => context.dispose());
  return context;
});

class IdScanState {
  final DataCaptureView view;
  final IdCapture idCapture;
  IdScanState(this.view, this.idCapture);
}

class IdScanNotifier extends AsyncNotifier<IdScanState> implements IdCaptureListener {
  Camera? _camera;

  @override
  Future<IdScanState> build() async {
    final context = ref.read(dataCaptureContextProvider);

    final settings = IdCaptureSettings()
      ..acceptedDocuments.add(Passport(IdCaptureRegion.any))
      ..scanner = IdCaptureScanner(physicalDocumentScanner: FullDocumentScanner());

    final idCapture = IdCapture(settings)..addListener(this);
    final view = DataCaptureView.forContext(context);
    view.addOverlay(IdCaptureOverlay(idCapture));
    await context.setMode(idCapture);

    _camera = Camera.defaultCamera;
    _camera?.applySettings(IdCapture.createRecommendedCameraSettings());
    if (_camera != null) await context.setFrameSource(_camera!);
    await _camera?.switchToDesiredState(FrameSourceState.on);
    idCapture.isEnabled = true;

    ref.onDispose(() {
      idCapture.removeListener(this);
      idCapture.isEnabled = false;
      _camera?.switchToDesiredState(FrameSourceState.off);
      context.removeMode(idCapture);
    });

    return IdScanState(view, idCapture);
  }

  @override
  Future<void> didCaptureId(IdCapture idCapture, CapturedId capturedId) async {
    idCapture.isEnabled = false;
    // Update state, navigate, etc.
  }

  @override
  Future<void> didRejectId(
      IdCapture idCapture, CapturedId? rejectedId, RejectionReason reason) async {
    idCapture.isEnabled = false;
  }
}

final idScanProvider = AsyncNotifierProvider<IdScanNotifier, IdScanState>(
  IdScanNotifier.new,
);
```

In the widget, `ref.watch(idScanProvider).when(...)` resolves to the `IdScanState` and renders `state.view`. When the screen is `pop`-ped *and* the provider has no other listeners, Riverpod auto-disposes — running the cleanup above. If you want to keep the context alive across navigations, the `dataCaptureContextProvider` stays bound to its parent scope (e.g. a `ProviderScope` near the app root).

## 3. Route-aware lifecycle (`RouteAware` + `RouteObserver`)

`WidgetsBindingObserver.didChangeAppLifecycleState` fires on **OS-level** transitions only. When the user pushes another route on top of the scan screen (modal, details page, settings), the scan screen stays mounted and the camera stays on. Use `RouteAware` + a `RouteObserver` to pause for in-app navigation.

### Wire the observer at app root

```dart
import 'package:flutter/material.dart';

final RouteObserver<PageRoute<dynamic>> routeObserver = RouteObserver<PageRoute<dynamic>>();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ScanditFlutterDataCaptureId.initialize();
  runApp(MaterialApp(
    home: const HomePage(),
    navigatorObservers: [routeObserver],
  ));
}
```

### Make the scan screen `RouteAware`

```dart
class _ScanPageState extends State<ScanPage>
    with WidgetsBindingObserver, RouteAware {
  late IdCaptureBloc _bloc;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _bloc = IdCaptureBloc('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final route = ModalRoute.of(context);
    if (route is PageRoute) routeObserver.subscribe(this, route);
  }

  // RouteAware: another route pushed on top.
  @override void didPushNext() { _bloc.disable(); }
  // RouteAware: returned to this route from above.
  @override void didPopNext()  { _bloc.enable(); }

  // WidgetsBindingObserver: OS state.
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && ModalRoute.of(context)?.isCurrent == true) {
      _bloc.enable();
    } else {
      _bloc.disable();
    }
  }

  @override
  void dispose() {
    routeObserver.unsubscribe(this);
    WidgetsBinding.instance.removeObserver(this);
    _bloc.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => _bloc.view;
}
```

The two observers don't fight: `RouteAware` handles **in-app** transitions; `WidgetsBindingObserver` handles **OS** transitions; the `isCurrent` check in `didChangeAppLifecycleState` prevents the OS `resumed` from starting the camera on a route the user has navigated away from.

### GoRouter

Pass the same observer into `GoRouter`'s `observers` parameter instead of `MaterialApp.navigatorObservers`:

```dart
final router = GoRouter(
  routes: [/* … */],
  observers: [routeObserver],
);

void main() {
  runApp(MaterialApp.router(routerConfig: router));
}
```

`RouteAware` then works the same — GoRouter pushes / pops use the underlying Navigator, so the observer's notifications fire as usual.

## 4. Where to keep the SDK handles

`DataCaptureContext`, `IdCapture`, `Camera`, and `DataCaptureView` are **native bridge handles** — not serializable Dart values. Keep them inside a long-lived owner (BLoC, Riverpod notifier, plain field on the `State`) and call `dispose()` / `removeMode` / `removeListener` when that owner dies. Specifically:

- **Don't** put them in a `ChangeNotifier` you broadcast to multiple screens without coordinating teardown; double-`dispose` on the native side is a bug.
- **Don't** persist them with `shared_preferences` / `hive` / route arguments — they don't round-trip.
- **Do** stash *serializable* values (license key, last `capturedId.rejectionDiagnosticJSON`, selected fields the UI needs) in your state manager.
- **Do** create exactly one `DataCaptureContext` per app session — either at app bootstrap or via a single `Provider`/`InheritedWidget`/Riverpod `Provider`. Creating one per screen works but wastes the cold-start cost.

## Cross-pattern rules that don't change

- `IdCaptureListener` callbacks (`didCaptureId`, `didRejectId`) are the same shape regardless of state-management library — implement on the BLoC / notifier / state object that owns the `IdCapture` instance.
- Always `disable()` (set `isEnabled = false` and switch camera off) before showing a modal / navigating away; always `enable()` again on return.
- Always `removeListener` and `removeMode` (or `removeAllModes`) on full teardown — once per `IdCapture` instance. Don't rely on garbage collection.
- `WidgetsBindingObserver` covers OS state; `RouteAware` covers in-app navigation. Use both for any screen that lives below other routes.
- `ScanditFlutterDataCaptureId.initialize()` is an **app-startup** call. Call it once in `main()` before `runApp`, not per BLoC / notifier.

## Reference links

- Skill: `references/integration.md` (the unchanged Scandit code: settings, listener, scanner, overlay, reading `CapturedId`).
- Skill: `references/supplementary-modules.md` (voided / Europe-DL / AAMVA add-on packages).
- [Flutter `RouteAware`](https://api.flutter.dev/flutter/widgets/RouteAware-class.html) · [`RouteObserver`](https://api.flutter.dev/flutter/widgets/RouteObserver-class.html)
- [Riverpod `AsyncNotifier`](https://riverpod.dev/docs/providers/notifier_provider)
- [GoRouter `observers`](https://pub.dev/documentation/go_router/latest/go_router/GoRouter/observers.html)
- [`IdCaptureExtendedSample` (BLoC reference)](https://github.com/Scandit/datacapture-flutter-samples/tree/master/02_ID_Scanning_Samples/IdCaptureExtendedSample)
