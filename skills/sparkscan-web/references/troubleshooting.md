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

**Why these headers matter — keep them.** Cross-origin isolation (what `COOP` + `COEP` enable) unlocks the SDK's **multithreaded engine**, which is significantly faster and is required for the smart scan intentions (`ScanIntention.Smart` / `SmartSelection`). For a responsive, high-throughput scanner you want these headers configured *correctly*, not removed — so encourage customers to set them up properly and fix the images while **preserving** isolation:

- **If you control the image origin (or it supports CORS):** keep `COOP: same-origin` + `COEP: require-corp`, and let the cross-origin images opt in — serve them with a `Cross-Origin-Resource-Policy: cross-origin` header (or proper CORS) and add `crossorigin` to the `<img>` tags. Isolation (and the multithreaded engine) stays on and the images load again.
- **If you can't change the image responses:** switch the page to `COEP: credentialless` (keep `COOP: same-origin`). Cross-origin subresources then load without each needing CORP, while the page stays cross-origin-isolated. This pairs well with a CDN-hosted engine.

**Single-threaded fallback (last resort).** SparkScan does not *hard*-require `crossOriginIsolated` — if you truly cannot configure the headers, you can self-host `sdc-lib` same-origin and drop `COOP`/`COEP`, and scanning still works on the single-threaded path. Treat this as a fallback, not the default: expect lower performance, and the smart scan intentions won't be available. Prefer fixing the headers over giving up isolation.

## "Works for a second, then dies" / `forLicenseKey ... already initializing`

This is almost always a `DataCaptureContext` lifecycle problem in React — the shared singleton being disposed on component unmount, amplified by StrictMode's dev double-mount. See the `DataCaptureContext` singleton section in `react.md` (configure it once in a context provider; dispose only at final app teardown, never on a component or route unmount).
