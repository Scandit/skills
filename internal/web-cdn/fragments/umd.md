**UMD build, last resort.** Use the classic-script bundles only when the target browsers support neither ES modules nor the [`es-module-shims`]({{es_module_shims_link}}) polyfill: they cannot be tree-shaken, so the page downloads more code and starts slower. Load them in this order, since each bundle reads the globals of the ones before it:

```html
{{umd_scripts}}
```

{{umd_globals}}

The Scandit web UMD globals are {{umd_all_globals}}; no others exist. `{{umd_parser_global}}` is only for an app that parses data with `{{umd_parser_npm}}`: load that bundle after the core bundle.

A classic `<script>` has no top-level `await`: take the exports off these globals (`const { DataCaptureContext } = SDCCore;`) and wrap the set-up in an async function.
