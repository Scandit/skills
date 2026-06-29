# SparkScan Web Troubleshooting & Deployment

Runtime and hosting problems that are easy to misdiagnose. These are environment issues, not API mistakes — the code can be perfectly correct and still fail here.

## Camera never opens on a phone / LAN IP — secure-context requirement

**Symptom:** scanning works on `localhost` during development, but when you open the same dev server on a phone over `http://192.168.x.x:5173` (or any LAN IP), the camera permission prompt never appears and the preview stays black.

**Cause:** the browser camera API (`getUserMedia`) only runs in a **secure context**. `localhost` is exempted and treated as secure, but a plain `http://` LAN address is not — so `getUserMedia` is unavailable and the camera silently never opens. This is the single most common "camera doesn't open on device" cause.

**Fix:** serve the dev app over HTTPS so the device loads it in a secure context.

- **Any bundler / framework:** use a tool like **[portless.sh](https://portless.sh)** to expose your local dev server over HTTPS (and reach it from a device).
- **Vite projects:** add the **[`@vitejs/plugin-basic-ssl`](https://www.npmjs.com/package/@vitejs/plugin-basic-ssl)** plugin, which provisions a self-signed certificate and enables `https` on the dev server:

  ```ts
  // vite.config.ts
  import { defineConfig } from "vite";
  import basicSsl from "@vitejs/plugin-basic-ssl";

  export default defineConfig({
      plugins: [basicSsl()],
      server: { host: true }, // expose on the LAN so a phone can reach it
  });
  ```

  The device will show a one-time self-signed-certificate warning — accept it to proceed. (`server.host: true` makes Vite listen on the LAN interface, not just localhost.)

This is a development concern; in production you serve over HTTPS anyway, so the secure context is already satisfied.

## Remote images break after enabling cross-origin isolation — the COOP/COEP trade-off

**Symptom:** after adding `Cross-Origin-Embedder-Policy: require-corp` (and `Cross-Origin-Opener-Policy: same-origin`) — for example by copying the headers from the official sample — cross-origin subresources such as product images from your CDN stop loading.

**Cause:** the multithreaded SDK engine benefits from **cross-origin isolation**, which is what those two headers enable. But `COEP: require-corp` also forbids the page from loading *any* cross-origin resource that doesn't explicitly opt in (via CORP/CORS headers). Your remote images are collateral damage.

**The key point:** SparkScan does **not** hard-require `crossOriginIsolated`. The SDK has a **single-threaded fallback** and runs fine without these headers. So you usually don't need them at all:

- **Simplest, recommended for most apps:** self-host the `sdc-lib` engine files **same-origin** (e.g. served from your app's `public/` directory) and **do not set COOP/COEP**. Scanning works on the single-threaded path, and your cross-origin images keep loading. The official sample sets these headers unconditionally — treat that as opt-in, not mandatory.
- **Only if you specifically need multithreading** (e.g. `ScanIntention.Smart` / `SmartSelection`, which require it): keep the headers, and then make your cross-origin images compatible — serve them with a `Cross-Origin-Resource-Policy: cross-origin` (or CORS) header and add `crossorigin` to the `<img>`, or use `COEP: credentialless` when hosting the engine from a CDN.

When in doubt, start without the headers (single-threaded) and only add cross-origin isolation if profiling shows you need the multithreaded engine.

## "Works for a second, then dies" / `forLicenseKey ... already initializing`

This is almost always a `DataCaptureContext` lifecycle problem in React — the shared singleton being disposed on component unmount, amplified by StrictMode's dev double-mount. See the `DataCaptureContext` singleton section in `react.md` (configure it once in a context provider; dispose only at final app teardown, never on a component or route unmount).
