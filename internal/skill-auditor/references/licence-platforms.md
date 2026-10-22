# Licence products and platforms

The single source for the licence **product** and **licence platforms** each skill
names in its `## Licence key` section. Nothing else in the repo derives this — the
per-skill sections carry their own values literally, and
`lint_structure.py` checks them against the tables below, so the two cannot drift.

Copied from *Scandit MCP Server Setup and Usage* → **Products and platforms**
(Confluence `UT/8379760810`), read 2026-09-21. When that page changes, change this
file; the lint gate will then name every skill whose section disagrees.

## Products and platforms

`ensure_scanner_setup` takes the product your agent selected (`sdk`, `native`,
`express`, `id-bolt`, `enterprise-browser`, or `wedge`) plus the licence platforms
for your framework. The skills pass `env_var` `SCANDIT_LICENSE_KEY` because the
server requires one, never run the command it returns, and fetch the key with
`get_license_key` instead. The agent writes the key straight into the licence-key
call: the Claude plugin directory flags any skill that reads a key from a dotenv
file or the environment, the app's build included.

| Framework | Licence platforms |
| --- | --- |
| Web | `webassembly` |
| iOS | `ios` |
| Android | `android` |
| React Native, Flutter, Capacitor, Cordova, .NET MAUI | `ios`, `android` |

Kotlin Multiplatform is not listed on that page. It builds the Android and iOS
targets, so it takes the same pair as the other cross-platform frameworks.

`express`, `enterprise-browser` and `wedge` are Scandit products with no skill in
this repo; they are listed only so the product set here matches the server's.

## Skill mapping

Machine-read by `common.licence_platforms()`. Each row is a skill-directory
**suffix** (leading `-`) or an exact **directory name**; the longest matching
suffix wins, and an exact name beats every suffix. Keep the backticks — the parser
reads the backticked tokens, and the platform cell may hold more than one.

| Skill | Licence product | Licence platforms |
| --- | --- | --- |
| `-web` | `sdk` | `webassembly` |
| `-android` | `native` | `android` |
| `-ios` | `native` | `ios` |
| `-net-android` | `native` | `android` |
| `-net-ios` | `native` | `ios` |
| `-net-maui` | `native` | `ios`, `android` |
| `-rn` | `native` | `ios`, `android` |
| `-flutter` | `native` | `ios`, `android` |
| `-capacitor` | `native` | `ios`, `android` |
| `-cordova` | `native` | `ios`, `android` |
| `-kmp` | `native` | `ios`, `android` |
| `id-bolt` | `id-bolt` | `webassembly` |
