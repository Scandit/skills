**Multithreading check.** Start `BrowserHelper.checkMultithreadingSupport()` without awaiting it, then await `DataCaptureContext.forLicenseKey()`: the two run in parallel, so set-up never waits for the check. The check needs no engine and no context. It resolves `false` when the page is not cross-origin isolated (the COOP/COEP headers are missing) or the device has fewer than 2 CPU cores or no nested workers. Scanning then still works, single-threaded and slower, and the SDK logs its own console warning, so do not add another: tell the person scanning with the dialog below instead.

**Dialog helper.** Save this module as `multithreading-warning.js` next to `index.html`, or as `multithreading-warning.ts` in a TypeScript app: it has no type annotations, so it is valid as either. `index.html` needs no markup for it: the helper adds the dialog to the page itself, unless the page already has a `<dialog id="multithreading-warning">`. The dialog shows at most once per page load (a module-level flag, so a scanner restart does not reopen it), and not again during the browser session once it was closed with the checkbox ticked. Every `sessionStorage` access sits in a `try`/`catch`: storage can be blocked, and that only means the dialog may show again on the next page load.

```typescript
const multithreadingWarningDismissedKey = "scandit-multithreading-warning-dismissed";
let multithreadingWarningShown = false;

export function isMultithreadingWarningDismissed() {
  try {
    return sessionStorage.getItem(multithreadingWarningDismissedKey) === "true";
  } catch {
    return false;
  }
}

export function rememberMultithreadingWarningDismissed() {
  try {
    sessionStorage.setItem(multithreadingWarningDismissedKey, "true");
  } catch {}
}

function multithreadingWarningDialog() {
  if (!document.getElementById("multithreading-warning")) {
    document.body.insertAdjacentHTML(
      "beforeend",
      `<dialog id="multithreading-warning">
        <form method="dialog">
          <h2>Scanning may be slower</h2>
          <p>This browser or device can't use all of its processing power for scanning. You can keep scanning, but scanning may take longer.</p>
          <p><a href="{{multithreading_link}}" target="_blank" rel="noopener">Learn more</a></p>
          <label><input type="checkbox" /> Don't show this again during this session</label>
          <button autofocus>OK</button>
        </form>
      </dialog>`
    );
  }
  return document.getElementById("multithreading-warning");
}

export function showMultithreadingWarning() {
  if (multithreadingWarningShown || isMultithreadingWarningDismissed()) {
    return;
  }
  const dialog = multithreadingWarningDialog();
  if (!(dialog instanceof HTMLDialogElement)) {
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
```

**Starting the check.** Import the helper and start the check before `forLicenseKey()`. The dialog opens as soon as the check resolves `false`, while the engine keeps loading. This snippet has no type annotations either, so it runs as is in a `<script type="module">`:

```typescript
import { BrowserHelper, DataCaptureContext } from "@scandit/web-datacapture-core";
import { {{engine_loader}} } from "{{engine_npm}}";
import { showMultithreadingWarning } from "./multithreading-warning.js";

BrowserHelper.checkMultithreadingSupport()
  .then((supported) => {
    if (!supported) {
      showMultithreadingWarning();
    }
  })
  .catch(console.error);

await DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
  libraryLocation: "{{library_location}}",
  moduleLoaders: [{{engine_loader}}()],
});
```

If the user explicitly asks to run single-threaded, leave the check and the dialog out.
