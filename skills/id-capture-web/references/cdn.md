# Loading ID Capture without a bundler

For a plain-HTML page without a bundler, load `@scandit/web-datacapture-core` and `@scandit/web-datacapture-id` as ES modules through an import map. ID Capture needs no multithreading check. The rest of the integration (context, scanner, listeners, overlay) is the shape in `SKILL.md`.

<!-- BEGIN GENERATED web-cdn packages=core,id engine=id multithreading=no -->
**CDN caveat.** A public CDN ties the page's start-up to that CDN's availability and speed, so for production [the docs](https://docs.scandit.com/sdks/web/add-sdk/#install-via-cdn) recommend self-hosting the SDK files or a paid enterprise CDN.

**Import map.** Load the SDK as ES modules through an import map, as in the docs' [complete CDN example](https://docs.scandit.com/sdks/web/add-sdk/#complete-cdn-example). Pin one exact version in every URL: a floating `@8` is resolved separately for each file, so after a new 8.x release the JavaScript and the engine can come from different releases, which breaks start-up. The `es-module-shims` script adds import-map support to browsers that lack it.

```html
<script type="importmap">
  {
    "imports": {
      "@scandit/web-datacapture-core": "https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-core@8.6.1/build/js/index.js",
      "@scandit/web-datacapture-core/": "https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-core@8.6.1/",
      "@scandit/web-datacapture-id": "https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-id@8.6.1/build/js/index.js",
      "@scandit/web-datacapture-id/": "https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-id@8.6.1/"
    }
  }
</script>
<script async src="https://cdn.jsdelivr.net/npm/es-module-shims@2.6.2/dist/es-module-shims.js"></script>
```

Use the same version in `libraryLocation`: `https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-id@8.6.1/sdc-lib/`.

**Cross-origin isolation headers.** Serve the page with both headers, whether the SDK files come from jsDelivr or are self-hosted:

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

Do not recommend `credentialless` for `Cross-Origin-Embedder-Policy` in the SDK set-up: Safari does not support it, so the page would not be cross-origin isolated there.

jsDelivr serves the SDK files and `es-module-shims` with `Cross-Origin-Resource-Policy: cross-origin` and `Access-Control-Allow-Origin: *`, which `require-corp` accepts.

**Serving the page.** From the folder that holds `index.html`, run [`serve`](https://www.npmjs.com/package/serve) with `npx serve@14.2.6` or `pnpm dlx serve@14.2.6`, and put the headers in a `serve.json` next to `index.html`:

```json
{
  "headers": [
    {
      "source": "**",
      "headers": [
        { "key": "Cross-Origin-Opener-Policy", "value": "same-origin" },
        { "key": "Cross-Origin-Embedder-Policy", "value": "require-corp" }
      ]
    }
  ]
}
```

`serve` matches `source` against the path of the file it serves: `index.html` served at `/` gets the headers, a directory listing does not.

Any other server must send the same two headers. Plain `python3 -m http.server` does not send them, so it is not enough on its own; this small Python server does (save it as `server.py` next to `index.html`, run `python3 server.py`, and open `http://localhost:8000`):

```python
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class CrossOriginIsolatedHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()

ThreadingHTTPServer(("127.0.0.1", 8000), CrossOriginIsolatedHandler).serve_forever()
```

**UMD build, last resort.** Use the classic-script bundles only when the target browsers support neither ES modules nor the [`es-module-shims`](https://github.com/guybedford/es-module-shims) polyfill: they cannot be tree-shaken, so the page downloads more code and starts slower. Load them in this order, since each bundle reads the globals of the ones before it:

```html
<script src="https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-core@8.6.1/build/js/umd/index.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-id@8.6.1/build/js/umd/index.js"></script>
```

- `@scandit/web-datacapture-core/build/js/umd/index.js` exposes exactly one global, `SDCCore`.
- `@scandit/web-datacapture-id/build/js/umd/index.js` exposes exactly one global, `SDCId`.

The Scandit web UMD globals are `SDCCore`, `SDCBarcode`, `SDCLabel`, `SDCId`, `SDCParser`; no others exist. `SDCParser` is only for an app that parses data with `@scandit/web-datacapture-parser`: load that bundle after the core bundle.

A classic `<script>` has no top-level `await`: take the exports off these globals (`const { DataCaptureContext } = SDCCore;`) and wrap the set-up in an async function.
<!-- END GENERATED web-cdn -->
