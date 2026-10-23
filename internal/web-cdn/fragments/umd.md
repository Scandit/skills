**UMD build, last resort.** Use the classic-script bundles only when the target browsers support neither ES modules nor the [`es-module-shims`]({{es_module_shims_link}}) polyfill: they cannot be tree-shaken, so the page downloads more code and starts slower. Load them in this order, since each bundle reads the globals of the ones before it:

```html
{{umd_scripts}}
```

{{umd_globals}}

A classic `<script>` has no top-level `await`: take the exports off these globals (`const { DataCaptureContext } = SDCCore;`) and wrap the set-up in an async function.
