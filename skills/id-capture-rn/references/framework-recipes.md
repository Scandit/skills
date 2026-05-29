# React Native Lifecycle & Platform Recipes

React Native ID Capture apps share one set of Scandit APIs (the settings, listener, scanner, overlay, and `CapturedId` access in `references/integration.md`), but they vary on three orthogonal concerns: **the navigation library** (does the scan screen pause when the user navigates away?), **the dev platform** (bare RN vs Expo), and **where the SDK handles live** (refs vs global state). This file covers each.

## 1. React Navigation — pause the camera when the screen loses focus

The base `integration.md` uses `AppState` to handle the OS background/foreground transition, with `navigation.isFocused()` as a guard. That handles **system-level** transitions only. **In-app** navigation — pushing another screen onto a stack, switching tabs, going back — does *not* fire `AppState 'change'` and the camera keeps running, draining battery and producing ghost captures.

Use `useFocusEffect` from `@react-navigation/native` for the in-app case. Together with `AppState`, the camera follows both the OS state and the route:

```tsx
import { useCallback, useEffect, useRef } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import {
  DataCaptureContext, DataCaptureView, Camera, FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import {
  IdCapture, IdCaptureOverlay, /* …settings imports from integration.md… */
} from 'scandit-react-native-datacapture-id';

type Sdk = { context: DataCaptureContext; camera: Camera; idCapture: IdCapture };

export function ScanScreen() {
  const sdkRef = useRef<Sdk | null>(null);
  const isFocused = useRef(false);

  // One-time setup + teardown (mode + view).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const context = DataCaptureContext.initialize(
        '-- ENTER YOUR SCANDIT LICENSE KEY HERE --',
      );
      // ... settings, listener, scanner from integration.md ...
      const settings = /* … */;
      const idCapture = new IdCapture(settings);
      await idCapture.addListener({ /* didCaptureId, didRejectId */ });
      await context.setMode(idCapture);

      const camera = Camera.default;
      if (!camera) throw new Error('No camera available on this device');
      await camera.applySettings(IdCapture.createRecommendedCameraSettings());
      await context.setFrameSource(camera);

      if (cancelled) return;
      sdkRef.current = { context, camera, idCapture };
    })();

    return () => {
      cancelled = true;
      const sdk = sdkRef.current;
      if (!sdk) return;
      sdk.idCapture.isEnabled = false;
      void sdk.camera.switchToDesiredState(FrameSourceState.Off);
      void sdk.context.removeMode(sdk.idCapture);
    };
  }, []);

  // Route focus/blur: pair with AppState below.
  useFocusEffect(
    useCallback(() => {
      isFocused.current = true;
      const sdk = sdkRef.current;
      if (sdk) {
        void sdk.camera.switchToDesiredState(FrameSourceState.On);
        sdk.idCapture.isEnabled = true;
      }
      return () => {
        isFocused.current = false;
        const s = sdkRef.current;
        if (!s) return;
        s.idCapture.isEnabled = false;
        void s.camera.switchToDesiredState(FrameSourceState.Off);
      };
    }, []),
  );

  // OS-level transitions: only resume if the route is still focused.
  useEffect(() => {
    const sub = AppState.addEventListener('change', (next: AppStateStatus) => {
      const sdk = sdkRef.current;
      if (!sdk) return;
      if (next.match(/inactive|background/)) {
        sdk.idCapture.isEnabled = false;
        void sdk.camera.switchToDesiredState(FrameSourceState.Off);
      } else if (next === 'active' && isFocused.current) {
        void sdk.camera.switchToDesiredState(FrameSourceState.On);
        sdk.idCapture.isEnabled = true;
      }
    });
    return () => sub.remove();
  }, []);

  return (
    <DataCaptureView
      style={{ flex: 1 }}
      context={sdkRef.current?.context!}
      ref={view => {
        const sdk = sdkRef.current;
        if (view && sdk) view.addOverlay(new IdCaptureOverlay(sdk.idCapture));
      }}
    />
  );
}
```

The two effects don't fight: `useFocusEffect` handles **route changes** (push / pop / tab switch), `AppState` handles **system state**, and the `isFocused.current` flag prevents `AppState 'active'` from starting the camera on a route the user has already left.

> If you're using **Expo Router** instead of `@react-navigation/native` directly, `useFocusEffect` re-exports from `expo-router` with the same signature — swap the import only.

## 2. Expo: dev-client required, permissions via `expo-camera`

**Scandit's RN packages are native modules** (Android `aar` / iOS pod). They are **not compatible with Expo Go**. The customer needs a [custom Expo dev client](https://docs.expo.dev/develop/development-builds/introduction/) or the bare workflow (`expo prebuild` + `expo run:android` / `expo run:ios`).

### `app.json` / `app.config.ts`

Add the Scandit packages as autolinked dependencies (no custom config plugin is required for the base packages, but you'll typically declare `expo-camera` for the permission UX):

```json
{
  "expo": {
    "name": "id-scanner",
    "ios": {
      "bundleIdentifier": "com.example.idscanner",
      "infoPlist": {
        "NSCameraUsageDescription": "Required to scan identity documents"
      }
    },
    "android": {
      "package": "com.example.idscanner",
      "permissions": ["android.permission.CAMERA"]
    },
    "plugins": [
      [
        "expo-camera",
        { "cameraPermission": "Required to scan identity documents" }
      ]
    ]
  }
}
```

### Build and run a dev client

```sh
# After installing scandit-react-native-datacapture-core and -id:
npx expo prebuild --clean
# Build the dev client:
npx expo run:android   # or: npx expo run:ios  (after pod install)
# Or via EAS:
# eas build --profile development --platform ios
```

Subsequent JS-only changes hot-reload as usual; only native changes (e.g. installing another Scandit add-on package) require a fresh prebuild / native rebuild.

### Permissions

Use `expo-camera`'s permission API instead of `PermissionsAndroid` (it works on both platforms):

```tsx
import { Camera as ExpoCamera } from 'expo-camera';

const { status } = await ExpoCamera.requestCameraPermissionsAsync();
if (status !== 'granted') throw new Error('Camera permission denied');
```

Call before navigating to the scan screen.

### What does NOT work on Expo

- Expo Go.
- `expo start --tunnel` against Expo Go.
- Any flow that doesn't run a native build of the app. If the customer says "I just want to test in Expo Go," surface the limitation upfront — there's no fix; they need a dev client or a bare project.

## 3. Where to keep the SDK handles (refs, not Redux)

`DataCaptureContext`, `IdCapture`, `Camera`, and `DataCaptureView` are **native bridge handles** — not plain JSON. Putting them in Redux / Zustand / Recoil state will work technically but is wasteful (they're not serializable, can't time-travel, and persisting them across reloads is meaningless). Keep them in `useRef` on the scan screen, or — if shared across screens — in a small React Context with a stable `Provider` near the root:

```tsx
import { createContext, useContext, useRef, useEffect, ReactNode } from 'react';
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

const ScanditContextRef = createContext<{ current: DataCaptureContext | null }>({ current: null });

export function ScanditProvider({ children }: { children: ReactNode }) {
  const ref = useRef<DataCaptureContext | null>(null);
  useEffect(() => {
    ref.current = DataCaptureContext.initialize(
      '-- ENTER YOUR SCANDIT LICENSE KEY HERE --',
    );
    return () => { /* release on app teardown */ };
  }, []);
  return <ScanditContextRef.Provider value={ref}>{children}</ScanditContextRef.Provider>;
}

export const useScanditContext = () => useContext(ScanditContextRef).current;
```

Stash only **serializable** values in the global store: license key, the last `CapturedId` decoded from `rejectionDiagnosticJSON` (string) or selected fields, user-facing flags. Never the SDK objects.

## Cross-platform rules that don't change

- **Always** await `addListener`, `removeListener`, `setMode`, `addMode`, `removeMode`, `applySettings`, `setFrameSource`, and `switchToDesiredState` — they all return Promises on React Native.
- **Always** pair `useFocusEffect` (route transitions) with an `AppState` listener (system state). Either alone leaks the camera on the case it doesn't cover.
- **Always** dispose on unmount: `idCapture.isEnabled = false`, `camera.switchToDesiredState(FrameSourceState.Off)`, `await context.removeMode(idCapture)`. Run these in the `useEffect` cleanup, not in `useFocusEffect` cleanup (cleanup there fires on every blur).
- **Don't** call `DataCaptureContext.initialize(licenseKey)` more than once per app session — either at app bootstrap behind a context/provider, or once per scan screen if you accept fresh contexts on every navigation (simpler, slightly higher startup cost).
- **Don't** stash native SDK handles (`IdCapture`, `Camera`, `DataCaptureView`) in Redux / Zustand / global state. Use refs or a React Context whose value is a ref.
- App-state lifecycle on **bare RN** still uses `AppState` from `react-native`; the same code works inside an Expo dev client.

## Reference links

- Skill: `references/integration.md` (the unchanged Scandit code: settings, listener, scanner, overlay, reading `CapturedId`).
- Skill: `references/supplementary-modules.md` (voided / Europe-DL / AAMVA add-on packages).
- [React Navigation `useFocusEffect`](https://reactnavigation.org/docs/use-focus-effect/)
- [Expo development builds](https://docs.expo.dev/develop/development-builds/introduction/)
- [`expo-camera` permissions](https://docs.expo.dev/versions/latest/sdk/camera/#permissions)
