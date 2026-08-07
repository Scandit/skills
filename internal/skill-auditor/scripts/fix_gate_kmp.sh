#!/usr/bin/env bash
# Fix-verification gate — Kotlin Multiplatform (anti-hallucination, NOT runtime behaviour).
# Compiles one KMP fixture/snippet against the RESOLVED REAL Scandit KMP SDK, so every
# `com.kmp.datacapture.*` symbol used must exist and the file must type-check.
#
# Unlike the plain-Android Kotlin gate (heavy, audit-only), this reuses the KMP SDK's own
# `DebugApp` umbrella — it already resolves every scandit-kmp-datacapture-* module plus
# Compose Multiplatform in commonMain, so an incremental `compileDebugKotlinAndroid` is a
# few seconds with a warm Gradle cache. The fixture is injected into DebugApp's source tree,
# compiled, then removed (the tree is left exactly as found).
#
# Usage: fix_gate_kmp.sh <kotlin-file>
#   One self-contained file per run (like the other fix_gate_* scripts). A fixture that
#   references a sibling (e.g. an Android host importing its commonMain ScreenModel) must be
#   concatenated with that sibling into one temp file before gating, or it reads as GATE-FAIL
#   on the unresolved sibling symbol.
# Env:
#   KMP_DEBUGAPP           path to frameworks/kmp/DebugApp (default: derive from the SDK
#                          checkout registered in sources.local.yaml sdk_source path).
#   GITLAB_PRIVATE_TOKEN   required — DebugApp resolves the scandit maven mirror with it.
# Exit 3 = toolchain/inputs absent (skip, don't pretend). 0 = GATE-PASS, 1 = GATE-FAIL.
set -euo pipefail
FILE=${1:?usage: fix_gate_kmp.sh <kotlin-file>}
[ -f "$FILE" ] || { echo "GATE-SKIP: no such file: $FILE"; exit 3; }

# Locate DebugApp. Default: <sdk_source>/frameworks/kmp/DebugApp.
DEBUGAPP=${KMP_DEBUGAPP:-}
if [ -z "$DEBUGAPP" ]; then
  SDK=$(sed -n 's/^[[:space:]]*path:[[:space:]]*\(.*data-capture-sdk\)[[:space:]]*$/\1/p' \
        "$(dirname "$0")/../sources.local.yaml" 2>/dev/null | head -1)
  [ -n "$SDK" ] && DEBUGAPP="$SDK/frameworks/kmp/DebugApp"
fi
[ -n "$DEBUGAPP" ] && [ -d "$DEBUGAPP" ] || { echo "GATE-SKIP: DebugApp not found (set \$KMP_DEBUGAPP)"; exit 3; }
GRADLEW="$DEBUGAPP/../gradlew"
[ -x "$GRADLEW" ] || { echo "GATE-SKIP: kmp gradlew not found at $GRADLEW"; exit 3; }
[ -n "${GITLAB_PRIVATE_TOKEN:-}" ] || { echo "GATE-SKIP: GITLAB_PRIVATE_TOKEN unset (needed to resolve scandit maven mirror)"; exit 3; }

# androidMain if the file touches Android-only surface, else commonMain.
if grep -qE '^import (android\.|androidx\.compose\.ui\.viewinterop\.|androidx\.compose\.ui\.platform\.LocalContext)|toAndroidView' "$FILE"; then
  SRC="androidMain"
else
  SRC="commonMain"
fi
GATEDIR="$DEBUGAPP/shared/src/$SRC/kotlin/_fix_gate"
mkdir -p "$GATEDIR"
DEST="$GATEDIR/$(basename "$FILE")"
cp "$FILE" "$DEST"
trap 'rm -rf "$GATEDIR"; rmdir "$DEBUGAPP/shared/src/$SRC/kotlin" 2>/dev/null || true' EXIT

if "$GRADLEW" -p "$DEBUGAPP" :shared:compileDebugKotlinAndroid --console=plain 2>&1 | grep -q "BUILD SUCCESSFUL"; then
  echo "GATE-PASS: $FILE ($SRC vs real KMP SDK)"
else
  echo "GATE-FAIL: $FILE ($SRC vs real KMP SDK)"
  exit 1
fi
