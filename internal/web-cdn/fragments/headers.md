**Cross-origin isolation headers.** Serve the page with both headers, whether the SDK files come from jsDelivr or are self-hosted:

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

Do not recommend `credentialless` for `Cross-Origin-Embedder-Policy` in the SDK set-up: Safari does not support it, so the page would not be cross-origin isolated there.

jsDelivr serves the SDK files and `es-module-shims` with `Cross-Origin-Resource-Policy: cross-origin` and `Access-Control-Allow-Origin: *`, which `require-corp` accepts.
