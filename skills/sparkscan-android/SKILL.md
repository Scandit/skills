---
name: sparkscan-android
description: SparkScan single-barcode scanning with the pre-built scanning UI in native Android (Kotlin/Java) projects. Use for integration, scan settings, result handling, UI customization, SDK version migration, replacing a third-party barcode scanning library, or troubleshooting.
license: Apache-2.0
metadata:
  author: scandit
  version: "1.0.1"
---

# SparkScan Android Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The SparkScan API changes significantly between major SDK versions — properties get renamed, removed, or restructured.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or property names. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating SparkScan from scratch** (e.g. "add SparkScan to my app", "set up barcode scanning", "how do I use SparkScan", "how do I handle feedback in SparkScan") → read [references/integration.md](references/integration.md) and follow the instructions there.
- **Migrating or upgrading an existing SparkScan integration** (e.g. "upgrade from v6 to v7", "migrate my SparkScan", "what changed between SDK versions") → read [references/migration.md](references/migration.md) and follow the instructions there.
- **Replacing a third-party barcode scanner with SparkScan** (e.g. "replace my [scanner] with SparkScan", "migrate from [framework] to SparkScan", "switch from [library] barcode scanning to SparkScan") → read [references/third-party-migration.md](references/third-party-migration.md) and follow the instructions there.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess method signatures, parameters, or property names. If unsure whether an API exists or how it is called — or if a compile error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:
1. First check whether the page you already fetched (e.g. the Advanced Configurations page) contains a direct hyperlink to it — topic pages link directly to relevant API symbols. Always request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

URL structures can vary (e.g. `api/ui/` subdirectory) and guessing will lead to 404s.

## Licence key

Scanning needs a Scandit licence key. For this skill the licence product is `native` and the licence platform is `android`.

Work through these in order — never block the user on MCP:

1. **The Scandit MCP server is connected** — call `ensure_scanner_setup` with product `native` and platforms `android`, then run the command `get_license_env_command` returns, which writes the key into the project's `.env`. Show at most a masked preview in chat; never print a full key.
2. **It is not connected** — offer to connect it once, then continue from step 1:
   - Claude Code: `claude mcp add --transport http scandit https://ssl.scandit.com/mcp`
   - Cursor: add `{"mcpServers": {"scandit": {"url": "https://ssl.scandit.com/mcp"}}}` to `~/.cursor/mcp.json`
   - VS Code: add `{"servers": {"scandit": {"type": "http", "url": "https://ssl.scandit.com/mcp"}}}` to the MCP user configuration

   Authentication is browser-based, so it is **not supported headless or in CI**. The server provisions **trial** keys only; it never creates, revokes, or modifies production licences.
3. **The user declines, or has no MCP client** — they generate a key themselves at <https://ssl.scandit.com> (no account yet: <https://ssl.scandit.com/dashboard/sign-up?p=test>) and paste it in.

## References

Direct users to the right resource based on their question:

| Topic | Resource |
|---|---|
| Get Started | [Get Started](https://docs.scandit.com/sdks/android/sparkscan/get-started/) · [Sample](https://github.com/Scandit/datacapture-android-samples/tree/master/01_Single_Scanning_Samples/01_Barcode_Scanning_with_Pre_Built_UI/ListBuildingSample) |
| Advanced topics (custom feedback, hardware triggers, scanning modes, UI customization) | [Advanced Configurations](https://docs.scandit.com/sdks/android/sparkscan/advanced/) |
| Full API reference | [SparkScan API](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html) |
