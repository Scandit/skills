# scandit-sdk-skills — repo rules

## Never commit unverified platform code (HARD RULE)

A skill's `evals/fixtures/*` files and the code snippets in `SKILL.md` / `references/*.md`
are authoritative — the model executing the skill emits them to customers. So **no fixture
or reference code snippet may be committed until it has been compiled against the resolved
real Scandit SDK.**

- String/semantic evals validate API *shape* in prose. They pass non-compiling code and
  wrong-language code (Java-style Kotlin has shipped this way). They do **not** catch
  hallucinated APIs. They are not a substitute for a build.
- The bar is **anti-hallucination**: every Scandit symbol used (class / method / property /
  enum case / import / signature) must exist in the released SDK and the file must compile.
  Runtime behaviour ("does it actually scan") is QA, not this gate.
- A gate is only real with the **Scandit packages resolved on the classpath**. A bare
  `kotlinc File.kt` / `swiftc File.swift` is a false gate (it can't resolve
  `com.scandit.datacapture.*`, so it can't tell a real API from a hallucinated one).
  Compile inside a deps-resolved project / local sample app.

Decision rule (Option C):
- Cheap deps-resolved gate available (Flutter `analyze`; TS `tsc` against installed
  `@scandit/*`; .NET `dotnet build`; Cordova `node --check` + export check) → run it,
  require a pass, then commit.
- Heavy toolchain (Kotlin + gradle + Android SDK; Swift + xcodebuild) → do NOT bare-compile
  and do NOT commit. Hand the proposed code to `skill-creator` to build in a local sample
  app. The auditor finds gaps; it does not vouch for a fix it could not build.

This is the standing correction behind `internal/skill-auditor` — see its `SKILL.md`
(`audit evals` step 5) and `references/eval-conventions.md` ("Fix-verification gate").
