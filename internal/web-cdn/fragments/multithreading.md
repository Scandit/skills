**Multithreading check.** Await `BrowserHelper.checkMultithreadingSupport()` before `DataCaptureContext.forLicenseKey()`; it needs no engine and no context. It returns `false` when the page is not cross-origin isolated (the COOP/COEP headers are missing) or the device has fewer than 2 CPU cores or no nested workers. Scanning then still works, single-threaded and slower, and the SDK logs its own console warning, so do not add another: tell the person scanning with this dialog in `index.html` instead.

```html
<dialog id="multithreading-warning">
  <form method="dialog">
    <h2>Scanning may be slower</h2>
    <p>This browser or device can't use all of its processing power for scanning. You can keep scanning, but barcodes may take longer to read.</p>
    <p><a href="{{multithreading_link}}" target="_blank" rel="noopener">Learn more</a></p>
    <label><input type="checkbox" /> Don't show this again during this session</label>
    <button autofocus>OK</button>
  </form>
</dialog>
```

Set-up does not wait for the dialog: `forLicenseKey()` runs while it is open. It shows at most once per page load (a module-level flag, so a scanner restart does not reopen it), and not again during the browser session once it was closed with the checkbox ticked. Every `sessionStorage` access sits in a `try`/`catch`: storage can be blocked, and that only means the dialog may show again on the next page load. The snippet has no type annotations, so it also runs as is in a `<script type="module">`:

```typescript
import { BrowserHelper, DataCaptureContext } from "@scandit/web-datacapture-core";
import { {{engine_loader}} } from "{{engine_npm}}";

const multithreadingWarningDismissedKey = "scandit-multithreading-warning-dismissed";
let multithreadingWarningShown = false;

function isMultithreadingWarningDismissed() {
  try {
    return sessionStorage.getItem(multithreadingWarningDismissedKey) === "true";
  } catch {
    return false;
  }
}

function rememberMultithreadingWarningDismissed() {
  try {
    sessionStorage.setItem(multithreadingWarningDismissedKey, "true");
  } catch {}
}

function showMultithreadingWarning() {
  const dialog = document.getElementById("multithreading-warning");
  if (multithreadingWarningShown || isMultithreadingWarningDismissed() || !(dialog instanceof HTMLDialogElement)) {
    return;
  }
  multithreadingWarningShown = true;
  dialog.addEventListener(
    "close",
    () => {
      const dontShowAgain = dialog.querySelector('input[type="checkbox"]');
      if (dontShowAgain instanceof HTMLInputElement && dontShowAgain.checked) {
        rememberMultithreadingWarningDismissed();
      }
    },
    { once: true }
  );
  dialog.showModal();
}

const multithreadingSupported = await BrowserHelper.checkMultithreadingSupport();
if (!multithreadingSupported) {
  showMultithreadingWarning();
}

await DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
  libraryLocation: "{{library_location}}",
  moduleLoaders: [{{engine_loader}}()],
});
```

If the user explicitly asks to run single-threaded, leave the check and the dialog out.
