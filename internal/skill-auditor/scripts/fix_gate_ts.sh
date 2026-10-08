#!/usr/bin/env bash
# Fix-verification gate — TypeScript (web / React Native / Capacitor).
# Type-checks a .ts file against the resolved REAL Scandit published npm packages via
# `tsc --noEmit` (anti-hallucination: every Scandit symbol must resolve; NOT runtime).
#
# Usage: fix_gate_ts.sh <platform: web|rn|capacitor> <ts-tsx-or-js-file> [version]
#   version default 8.4.0
# Note: cordova re-exports the shared frameworks package, so its signatures are covered by
#   the rn/capacitor check; cordova plain-JS syntax is checked separately with `node --check`.
# Toolchain: node + npm + npx on PATH. Exit 3 = toolchain absent.
set -euo pipefail
PLAT=${1:?usage: fix_gate_ts.sh <web|rn|capacitor> <ts-tsx-or-js-file> [version]}
FILE=${2:?usage: fix_gate_ts.sh <web|rn|capacitor> <ts-tsx-or-js-file> [version]}
VER=${3:-8.4.0}
command -v npm >/dev/null 2>&1 && command -v npx >/dev/null 2>&1 || { echo "GATE-SKIP: npm/npx not found"; exit 3; }
case "$PLAT" in
  web)       CORE="@scandit/web-datacapture-core"; BC="@scandit/web-datacapture-barcode";;
  rn)        CORE="scandit-react-native-datacapture-core"; BC="scandit-react-native-datacapture-barcode";;
  capacitor) CORE="scandit-capacitor-datacapture-core"; BC="scandit-capacitor-datacapture-barcode";;
  *) echo "unknown platform: $PLAT (web|rn|capacitor)"; exit 2;;
esac
DIR=$(mktemp -d); trap 'rm -rf "$DIR"' EXIT
# A .tsx file (React / React Native screen) keeps its extension and gets React types.
EXT=ts; EXTRA_DEPS=""
case "$FILE" in *.tsx)
  EXT=tsx; EXTRA_DEPS=', "react":"19.1.0", "@types/react":"19.1.0"'
  [ "$PLAT" = rn ] && EXTRA_DEPS="$EXTRA_DEPS"', "react-native":"0.81.4"';;
# A plain-JS file (Capacitor / web snippet) is checked as JS (allowJs + checkJs), not as TS.
*.js) EXT=js;;
esac
# Capacitor apps import Capacitor from @capacitor/core (e.g. the getPlatform() web guard).
[ "$PLAT" = capacitor ] && EXTRA_DEPS="$EXTRA_DEPS"', "@capacitor/core":"8.5.3"'
# JS cannot annotate, so implicit-any is not a hallucination signal there; Scandit symbols still must resolve.
NOIMPLICITANY=true; [ "$EXT" = js ] && NOIMPLICITANY=false
# web and capacitor code (.ts and .js) runs in a WebView/browser: give it the DOM globals.
LIB='"es2019"'; [ "$PLAT" != rn ] && LIB='"es2019", "dom"'
mkdir -p "$DIR/src"; cp "$FILE" "$DIR/src/gate.$EXT"
cat > "$DIR/package.json" <<EOF
{ "name":"fix-gate-ts","private":true,
  "dependencies": { "$CORE":"$VER", "$BC":"$VER"$EXTRA_DEPS } }
EOF
cat > "$DIR/tsconfig.json" <<EOF
{ "compilerOptions": { "strict": true, "noEmit": true, "skipLibCheck": true,
  "moduleResolution": "node", "esModuleInterop": true, "target": "es2019",
  "allowJs": true, "checkJs": true, "noImplicitAny": $NOIMPLICITANY,
  "jsx": "react-jsx", "lib": [$LIB], "types": [] }, "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.js"] }
EOF
( cd "$DIR" && npm install --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 && npx --yes tsc --noEmit ) \
  && echo "GATE-PASS: $FILE vs $BC $VER ($PLAT)" \
  || { echo "GATE-FAIL: $FILE vs $BC $VER ($PLAT)"; exit 1; }
