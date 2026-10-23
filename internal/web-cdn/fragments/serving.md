**Serving the page.** From the folder that holds `index.html`, run [`serve`](https://www.npmjs.com/package/serve) with `npx serve@{{serve_version}}` or `pnpm dlx serve@{{serve_version}}`, and put the headers in a `serve.json` next to `index.html`:

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
