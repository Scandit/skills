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
for your framework.

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

## Key wiring

A key in `.env` does not reach the app by itself: the reference code passes the
placeholder, and most platforms have no built-in `.env` loading. Each skill's
`## Licence key` section carries its row's sentence verbatim. Machine-read by
`common.licence_wiring()`; keys resolve exactly as in the mapping above.

| Skill | Wiring |
| --- | --- |
| `-web` | Read it through the bundler's env support, for example `import.meta.env` in Vite (which only exposes `VITE_`-prefixed names unless `envPrefix` says otherwise). |
| `-android` | Read it in Gradle and expose it as a `BuildConfig` field (this needs `buildFeatures { buildConfig = true }`). |
| `-ios` | Map the value through an `.xcconfig` file into `Info.plist`, then read it with `Bundle.main.object(forInfoDictionaryKey:)`. |
| `-net-android` | .NET does not load `.env` by itself, so use the simplest route below. |
| `-net-ios` | .NET does not load `.env` by itself, so use the simplest route below. |
| `-net-maui` | .NET does not load `.env` by itself, so use the simplest route below. |
| `-rn` | React Native does not load `.env` by itself: add a loader such as `react-native-config`, or use the simplest route below. |
| `-flutter` | Pass it at build time with `--dart-define-from-file=.env` and read it with `String.fromEnvironment`. |
| `-capacitor` | Read it through the web bundler's env support, for example `import.meta.env` in Vite (which only exposes `VITE_`-prefixed names unless `envPrefix` says otherwise). |
| `-cordova` | Cordova does not load `.env` by itself, so use the simplest route below. |
| `-kmp` | Kotlin Multiplatform does not load `.env` by itself, so use the simplest route below. |
| `id-bolt` | Read it through the bundler's env support, for example `import.meta.env` in Vite (which only exposes `VITE_`-prefixed names unless `envPrefix` says otherwise). |
