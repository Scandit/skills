# ID Capture Web Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check in this order:

1. **package.json** — open `<ProjectRoot>/package.json` and look for `@scandit/web-datacapture-core` / `@scandit/web-datacapture-id` (v7+) or `scandit-web-datacapture-core` / `scandit-web-datacapture-id` (v6). The version number is in the value field.
2. **Lock files** — if package.json uses a version range, check the exact installed version in `package-lock.json`, `yarn.lock`, or `pnpm-lock.yaml`.
3. **Code heuristics** — the API in use tells you the era even when the manifest is ambiguous:
   - `supportedDocuments` / `IdDocumentType` / `supportedSides` / `IdCaptureSession` → **v6-era code**
   - `settings.scannerType = new FullDocumentScanner()` and/or `configure({...})` + `DataCaptureContext.create()` → **v7-era code**
   - `settings.scanner = new IdCaptureScanner({ physicalDocument: ... })` and `DataCaptureContext.forLicenseKey(...)` → already **v8-shaped**

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If you cannot find the version in package.json or lock files, ask the user which version they are migrating from.

---

## Step 2: Update the package version

Before touching source files, update the SDK version in the package manager:

- **npm**: `npm install @scandit/web-datacapture-core@latest @scandit/web-datacapture-id@latest`
- **yarn**: `yarn add @scandit/web-datacapture-core@latest @scandit/web-datacapture-id@latest`
- **pnpm**: `pnpm add @scandit/web-datacapture-core@latest @scandit/web-datacapture-id@latest`

> **Note:** v6 used unscoped package names (`scandit-web-datacapture-core`, `scandit-web-datacapture-id`). When migrating from v6, remove the old unscoped packages and install the new scoped ones. Update all import statements accordingly.

Ask the user which package manager they use if it's not clear from the project.

---

## Step 3: Apply source code changes

Find the files that use ID Capture (search for `IdCapture`, `IdCaptureSettings`, `IdCaptureOverlay`, `idCaptureLoader`, `CapturedId`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### Package and hosting changes

v7 introduces critical changes to how the Web SDK is installed and hosted:

| Change | Old (v6) | New (v7+) |
|---|---|---|
| NPM scope | `scandit-web-datacapture-core`, `scandit-web-datacapture-id` | `@scandit/web-datacapture-core`, `@scandit/web-datacapture-id` |
| Engine directory | `build/engine` | `sdc-lib` |

Apply these changes:
1. Update all import statements to use the new scoped package names
2. Update `libraryLocation` paths from `build/engine` to `sdc-lib` (or the project's equivalent self-hosted path)

### Document selection model replaced

In v6, `supportedDocuments` controlled both which document types to scan AND which zones to read (the VIZ / MRZ / Barcode suffix of each `IdDocumentType` entry encoded the zone), with `supportedSides` selecting the sides. In v7+, these are separated: document **types** go in `acceptedDocuments` (document objects with explicit regions), and zone/side selection goes in the **scanner**. You need to translate both.

```ts
// v6 (removed): settings.supportedDocuments with IdDocumentType.* entries + settings.supportedSides
// v7+:
settings.acceptedDocuments = [new IdCard(Region.Any), new Passport(Region.Any), new DriverLicense(Region.Any)];
settings.scanner = new IdCaptureScanner({ physicalDocument: new FullDocumentScanner() }); // v8 form — see note below
```

**Step 1 — translate document types to `acceptedDocuments`:**

| v6 `IdDocumentType` value | v7+ `acceptedDocuments` entry |
|---|---|
| `IdCardViz`, `IdCardMrz` | `new IdCard(Region.Any)` |
| `DlViz`, `DlBarcode` (US AAMVA) | `new DriverLicense(Region.Any)` / `new DriverLicense(Region.Us)` |
| `PassportMrz`, `PassportViz` | `new Passport(Region.Any)` |
| `VisaMrz` | `new VisaIcao(Region.Any)` |
| `AamvaBarcode` | `new DriverLicense(Region.Us)` |
| `HealthInsuranceCardFront` | `new HealthInsuranceCard(Region.Any)` |

**Step 2 — translate zone suffixes and `supportedSides` to a scanner:**

| v6 zones / sides in use | v7+ scanner |
|---|---|
| Barcode only | `new SingleSideScanner(true, false, false)` |
| MRZ only | `new SingleSideScanner(false, true, false)` |
| VIZ only | `new SingleSideScanner(false, false, true)` |
| Multiple zones / `supportedSides = FrontAndBack` | `new FullDocumentScanner()` |

`SingleSideScanner(barcode, machineReadableZone, visualInspectionZone)` takes three positional booleans. `FullDocumentScanner` reads all zones from both sides and the UI automatically guides the user through flipping the document.

> **Skip the v7 intermediate if targeting v8.** v7.x assigned the scanner directly to `settings.scannerType`. v8 renamed the property to `scanner` and wrapped it in `IdCaptureScanner`. When migrating from v6 straight to v8, write the v8 form shown above directly.

Remove every reference to `supportedDocuments`, `IdDocumentType`, and `supportedSides` — these names no longer exist.

### Listener callbacks redesigned

The v6 callback contract was session-based: callbacks received an `IdCaptureSession` and read partial results from `session.newlyCapturedId`, with a separate timeout callback. In v7+ there are exactly two callbacks, and they receive the `CapturedId` directly:

```ts
// v7+ (current contract)
idCapture.addListener({
  didCaptureId: async (capturedId: CapturedId) => {
    await idCapture.setEnabled(false);
    // fires once per COMPLETE document (for FullDocumentScanner: only after all sides are captured)
  },
  didRejectId: async (capturedId: CapturedId, reason: RejectionReason) => {
    await idCapture.setEnabled(false);
    // timeouts now arrive here as RejectionReason.Timeout — the separate timeout callback is gone
  },
});
```

**What to change:**
- Delete all `IdCaptureSession` / `session.newlyCapturedId` references — the session class was removed; read the `CapturedId` parameter directly.
- Move timeout handling into `didRejectId` (`reason === RejectionReason.Timeout`).
- Apps that relied on partial per-zone results must be rewritten: `didCaptureId` now fires exactly once per complete document.

### Result model flattened

| v6 | v7+ |
|---|---|
| `capturedId.aamvaBarcodeResult` (and other per-document barcode results) | `capturedId.barcode` |
| Per-document MRZ result variants | `capturedId.mrzResult` |
| `capturedId.documentType` (enum) | `capturedId.document` (an `IdCaptureDocument`; check with e.g. `capturedId.isPassport()`) |
| `capturedId.issuingCountry` as `string` | `capturedId.issuingCountry` as a `Region` enum value |

### Image types consolidated

The per-side image types were consolidated: `IdFront` / `IdBack` are replaced by `IdImageType.CroppedDocument`, with the side selected at access time. Opt in via settings, then read base64 data-URL strings from `capturedId.images`:

```ts
settings.setShouldPassImageTypeToResult(IdImageType.CroppedDocument, true);
settings.setShouldPassImageTypeToResult(IdImageType.Face, true);

// in didCaptureId — all return `string | null` (a data:image/... URL):
const front = capturedId.images.getCroppedDocument(IdSide.Front);
const back = capturedId.images.getCroppedDocument(IdSide.Back);
const face = capturedId.images.face;
```

### Verification changes

- **Data-consistency checks** (VIZ vs MRZ vs barcode comparison verifiers in v6) are settings-driven in v7+: set `settings.rejectInconsistentData = true` and handle `RejectionReason.InconsistentData` in `didRejectId`; details are on `capturedId.verificationResult.dataConsistency`.
- **AAMVA forged-barcode verification** stays a standalone class on Web: `await AamvaBarcodeVerifier.create(context)` then `await verifier.verify(capturedId)`. (Do **not** copy the native platforms' `rejectForgedAamvaBarcodes` setting — it does not exist on Web.)

---

## Migration: 7 → 8

### DataCaptureContext initialization change

v8 replaces the two-step `configure()` + `DataCaptureContext.create()` pattern with a single `DataCaptureContext.forLicenseKey()` call. The `idCaptureLoader` moves with it:

**Old (v7):**
```ts
import { configure, DataCaptureContext } from "@scandit/web-datacapture-core";
import { idCaptureLoader } from "@scandit/web-datacapture-id";

await configure({
    libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
    licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
    moduleLoaders: [idCaptureLoader({ enableVIZDocuments: true })],
});
const context = await DataCaptureContext.create();
```

**New (v8):**
```ts
import { DataCaptureContext } from "@scandit/web-datacapture-core";
import { idCaptureLoader } from "@scandit/web-datacapture-id";

const context = await DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
    libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
    moduleLoaders: [idCaptureLoader({ enableVIZDocuments: true })],
});
```

Apply this change:
1. Remove the `configure` import from `@scandit/web-datacapture-core`
2. Replace the `configure({ ... })` call and `DataCaptureContext.create()` with `DataCaptureContext.forLicenseKey(licenseKey, { libraryLocation, moduleLoaders })`
3. Keep `idCaptureLoader({ enableVIZDocuments: true })` in `moduleLoaders` — without it ID Capture will not work

### `scannerType` → `scanner` with `IdCaptureScanner` wrapper

**Old (v7):**
```ts
settings.scannerType = new FullDocumentScanner();
// or: settings.scannerType = new SingleSideScanner(true, false, false);
```

**New (v8):**
```ts
settings.scanner = new IdCaptureScanner({ physicalDocument: new FullDocumentScanner() });
// or: settings.scanner = new IdCaptureScanner({ physicalDocument: new SingleSideScanner(true, false, false) });

// to also scan mobile-presented documents:
settings.scanner = new IdCaptureScanner({
    physicalDocument: new FullDocumentScanner(),
    mobileDocument: new MobileDocumentScanner(),
});
```

> The Web wrapper takes an **options object** — `new IdCaptureScanner({ physicalDocument: ... })`. Do not use the positional form (`new IdCaptureScanner(new FullDocumentScanner())`) seen on React Native and other platforms.

After upgrading, make sure both `scanner` AND `acceptedDocuments` are explicitly set — a default-constructed `IdCaptureSettings` captures nothing.

### `DateResult.toDate` removed

Replace `dateResult.toDate()` with `dateResult.toLocalDate()` or `dateResult.toUtcDate()` (e.g. on `capturedId.dateOfBirth`, `capturedId.dateOfExpiry`).

### What does NOT change on Web (do not apply native-platform migrations)

- **`AamvaBarcodeVerifier` remains a standalone class.** iOS/Android/RN removed it at v8 in favor of a `rejectForgedAamvaBarcodes` setting — the Web SDK did NOT. Keep `await AamvaBarcodeVerifier.create(context)` / `await verifier.verify(capturedId)`.
- **`settings.setShouldPassImageTypeToResult(...)` is unchanged.** iOS renamed its image opt-in to `setIncludeImage` — Web keeps the v7 name.
- The listener contract (`didCaptureId` / `didRejectId`), `IdCapture.forContext(...)`, and `IdCaptureOverlay.withIdCaptureForView(...)` are unchanged.

### New in v8 (optional, mention only if relevant)

- **Full-frame anonymization** support in ID Capture.
- **`MobileDocumentScanner` data retention** — an elements-to-retain configuration required for ISO 18013-5 mdoc compliance; verify the exact API against the docs before using.
- **`capturedId.mobileDocumentOcr`** replaces the previous `decodeMobileDriverLicenseViz` result handling.
- **`capturedId.isCitizenPassport()`** document check.

---

## After applying changes

1. Build the project (`tsc --noEmit` is a quick check) and fix any remaining type or build errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: <https://docs.scandit.com/sdks/web/migrate-6-to-7/>
   - 7 → 8: <https://docs.scandit.com/sdks/web/migrate-7-to-8/>
3. Show the user a summary of only the changes actually made: which files were edited, which properties were renamed/removed, and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
4. If type or build errors persist after the changes above, fetch the [ID Capture API reference](https://docs.scandit.com/data-capture-sdk/web/id-capture/api.html) to find the correct API before guessing.
