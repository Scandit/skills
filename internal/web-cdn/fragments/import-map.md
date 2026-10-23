**Import map.** Load the SDK as ES modules through an import map, as in the docs' [complete CDN example]({{complete_cdn_example_link}}). Pin one exact version in every URL: a floating `@{{sdk_major}}` is resolved separately for each file, so after a new {{sdk_major}}.x release the JavaScript and the engine can come from different releases, which breaks start-up. The `es-module-shims` script adds import-map support to browsers that lack it.

```html
<script type="importmap">
  {
    "imports": {
      {{import_map_entries}}
    }
  }
</script>
<script async src="https://cdn.jsdelivr.net/npm/es-module-shims@{{es_module_shims_version}}/dist/es-module-shims.js"></script>
```

Use the same version in `libraryLocation`: `{{library_location}}`.
