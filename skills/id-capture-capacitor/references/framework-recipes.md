# Capacitor + Host-Framework Lifecycle Recipes

Capacitor apps are almost always built on top of a UI framework — Ionic Angular, Ionic React, or Vue (with or without Ionic / Quasar). The **Scandit API itself is identical** across all of them: the settings, listener, scanner, overlay, and `CapturedId` access live in `references/integration.md` and do not change. What differs per framework is the **lifecycle glue** — *where* you call `initializePlugins()`, *where* you mount the view, and *where* you start / stop the camera.

This file shows one canonical skeleton per framework. Drop the settings / listener / `CapturedId` code from `references/integration.md` into the `// ... settings, listener, scanner from integration.md ...` placeholders.

## App bootstrap (call once, in every framework)

Initialize the Scandit plugins **before** the framework boots, in your `main.ts` (or `main.tsx`). Doing it at app bootstrap — not per scan page — avoids racing the first `DataCaptureContext.initialize(...)` call when the user navigates straight to a scan route on cold start.

```ts
// main.ts (Vue example — same shape for Ionic Angular's main.ts and Ionic React's index.tsx)
import { ScanditCaptureCorePlugin } from 'scandit-capacitor-datacapture-core';
import { createApp } from 'vue';
import App from './App.vue';

(async () => {
  await ScanditCaptureCorePlugin.initializePlugins();
  createApp(App).mount('#app');
})();
```

Every subsequent `DataCaptureContext.initialize(licenseKey)` call assumes the plugins are already registered.

---

## 1. Ionic Angular

Use a page-component class. `@ViewChild` resolves the host `<div>`. Ionic gives you a second pair of lifecycle hooks (`ionViewWillEnter` / `ionViewWillLeave`) that fire on *route* transitions — use them for camera start/stop, and use `ngOnDestroy` for the one-time teardown when the component itself is destroyed.

```ts
import { Component, ElementRef, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { DataCaptureContext, DataCaptureView, Camera, FrameSourceState }
  from 'scandit-capacitor-datacapture-core';
import { IdCapture, IdCaptureOverlay /* …settings imports from integration.md… */ }
  from 'scandit-capacitor-datacapture-id';

@Component({
  selector: 'app-scan-page',
  template: `<div #captureView style="width:100%;height:100%"></div>`,
})
export class ScanPage implements AfterViewInit, OnDestroy {
  @ViewChild('captureView', { static: true })
  captureViewEl!: ElementRef<HTMLDivElement>;

  private context!: DataCaptureContext;
  private camera!: Camera;
  private idCapture!: IdCapture;
  private view!: DataCaptureView;

  async ngAfterViewInit() {
    this.context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
    // ... settings, listener, scanner from integration.md ...
    const settings = /* … */;
    this.idCapture = new IdCapture(settings);
    await this.idCapture.addListener({ /* didCaptureId, didRejectId */ });
    await this.context.setMode(this.idCapture);

    const cam = Camera.withSettings(IdCapture.createRecommendedCameraSettings());
    if (!cam) throw new Error('No camera available on this device');
    this.camera = cam;
    await this.context.setFrameSource(this.camera);

    this.view = DataCaptureView.forContext(this.context);
    this.view.connectToElement(this.captureViewEl.nativeElement);
    this.view.addOverlay(new IdCaptureOverlay(this.idCapture));
  }

  ionViewWillEnter() {
    this.camera.switchToDesiredState(FrameSourceState.On);
    this.idCapture.isEnabled = true;
  }

  ionViewWillLeave() {
    this.idCapture.isEnabled = false;
    this.camera.switchToDesiredState(FrameSourceState.Off);
  }

  async ngOnDestroy() {
    this.view.detachFromElement();
    await this.context.removeMode(this.idCapture);
  }
}
```

If the page is not inside an Ionic router (plain Angular), drop the `ionView*` methods and start the camera at the end of `ngAfterViewInit` instead.

---

## 2. Ionic React

Use a function component with `useRef` for the host div and a single `useEffect` for setup + teardown. Ionic's `useIonViewWillEnter` / `useIonViewWillLeave` cover the route-transition camera start/stop.

```tsx
import { useEffect, useRef } from 'react';
import { useIonViewWillEnter, useIonViewWillLeave } from '@ionic/react';
import { DataCaptureContext, DataCaptureView, Camera, FrameSourceState }
  from 'scandit-capacitor-datacapture-core';
import { IdCapture, IdCaptureOverlay /* …settings imports from integration.md… */ }
  from 'scandit-capacitor-datacapture-id';

type Sdk = {
  context: DataCaptureContext;
  camera: Camera;
  idCapture: IdCapture;
  view: DataCaptureView;
};

export function ScanPage() {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const sdkRef = useRef<Sdk | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
      // ... settings, listener, scanner from integration.md ...
      const settings = /* … */;
      const idCapture = new IdCapture(settings);
      await idCapture.addListener({ /* didCaptureId, didRejectId */ });
      await context.setMode(idCapture);

      const camera = Camera.withSettings(IdCapture.createRecommendedCameraSettings());
      if (!camera) throw new Error('No camera available on this device');
      await context.setFrameSource(camera);

      const view = DataCaptureView.forContext(context);
      if (hostRef.current) view.connectToElement(hostRef.current);
      view.addOverlay(new IdCaptureOverlay(idCapture));

      if (cancelled) return;
      sdkRef.current = { context, camera, idCapture, view };
    })();

    return () => {
      cancelled = true;
      const sdk = sdkRef.current;
      if (!sdk) return;
      sdk.view.detachFromElement();
      void sdk.context.removeMode(sdk.idCapture);
    };
  }, []);

  useIonViewWillEnter(() => {
    const sdk = sdkRef.current;
    if (!sdk) return;
    sdk.camera.switchToDesiredState(FrameSourceState.On);
    sdk.idCapture.isEnabled = true;
  });

  useIonViewWillLeave(() => {
    const sdk = sdkRef.current;
    if (!sdk) return;
    sdk.idCapture.isEnabled = false;
    sdk.camera.switchToDesiredState(FrameSourceState.Off);
  });

  return <div ref={hostRef} style={{ width: '100%', height: '100%' }} />;
}
```

For plain React (no Ionic), drop the `useIonView*` hooks and call `switchToDesiredState(FrameSourceState.On)` + `idCapture.isEnabled = true` at the end of the setup async function instead.

---

## 3. Vue 3 (Composition API)

Use a template `ref` for the host div, `onMounted` for setup, `onBeforeUnmount` for teardown. If the page sits behind `<keep-alive>`, add `onActivated` / `onDeactivated` for camera start/stop on route transitions.

```vue
<template>
  <div ref="captureViewRef" style="width: 100%; height: 100%"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, onActivated, onDeactivated } from 'vue';
import { DataCaptureContext, DataCaptureView, Camera, FrameSourceState }
  from 'scandit-capacitor-datacapture-core';
import { IdCapture, IdCaptureOverlay /* …settings imports from integration.md… */ }
  from 'scandit-capacitor-datacapture-id';

const captureViewRef = ref<HTMLDivElement | null>(null);

let context: DataCaptureContext;
let camera: Camera;
let idCapture: IdCapture;
let view: DataCaptureView;

onMounted(async () => {
  context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
  // ... settings, listener, scanner from integration.md ...
  const settings = /* … */;
  idCapture = new IdCapture(settings);
  await idCapture.addListener({ /* didCaptureId, didRejectId */ });
  await context.setMode(idCapture);

  const cam = Camera.withSettings(IdCapture.createRecommendedCameraSettings());
  if (!cam) throw new Error('No camera available on this device');
  camera = cam;
  await context.setFrameSource(camera);

  view = DataCaptureView.forContext(context);
  if (captureViewRef.value) view.connectToElement(captureViewRef.value);
  view.addOverlay(new IdCaptureOverlay(idCapture));

  await camera.switchToDesiredState(FrameSourceState.On);
  idCapture.isEnabled = true;
});

// Optional, only if the page is inside <keep-alive>:
onActivated(async () => {
  await camera?.switchToDesiredState(FrameSourceState.On);
  if (idCapture) idCapture.isEnabled = true;
});
onDeactivated(async () => {
  if (idCapture) idCapture.isEnabled = false;
  await camera?.switchToDesiredState(FrameSourceState.Off);
});

onBeforeUnmount(async () => {
  if (idCapture) idCapture.isEnabled = false;
  await camera?.switchToDesiredState(FrameSourceState.Off);
  view?.detachFromElement();
  if (idCapture) await context.removeMode(idCapture);
});
</script>
```

---

## Cross-framework rules that don't change

- **Always** await `addListener`, `removeListener`, `setMode`, `addMode`, `removeMode`, `applySettings`, `setFrameSource`, and `switchToDesiredState`.
- **Always** call `view.detachFromElement()` before destroying the host component / route.
- **Always** call `await context.removeMode(idCapture)` on full teardown (page destroy), not just on route blur.
- **Don't** call `ScanditCaptureCorePlugin.initializePlugins()` per page — do it once at app bootstrap.
- **Don't** call `DataCaptureContext.initialize(licenseKey)` more than once per app session. Either create the context once at bootstrap and inject it (DI for Angular, context/provider for React, a Pinia store for Vue) or accept that the per-page flow above will create a fresh context each navigation (acceptable for simple apps).
- App-state lifecycle (`@capacitor/app` `appStateChange`) can live in a single app-level listener that flips `idCapture.isEnabled` and the camera state on background / foreground — independent of the per-page route lifecycle above.

## Reference links

- Skill: `references/integration.md` (the unchanged Scandit code: settings, listener, scanner, overlay, reading `CapturedId`).
- Skill: `references/supplementary-modules.md` (voided / Europe-DL / AAMVA add-on packages).
- [Capacitor App plugin](https://capacitorjs.com/docs/apis/app)
- [Ionic Angular lifecycle](https://ionicframework.com/docs/angular/lifecycle)
- [Ionic React lifecycle](https://ionicframework.com/docs/react/lifecycle)
- [Vue 3 lifecycle hooks](https://vuejs.org/api/composition-api-lifecycle.html)
