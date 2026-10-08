#!/usr/bin/env bash
# Fix-verification gate — TypeScript (web / React Native / Capacitor).
# Type-checks a .ts file against the resolved REAL Scandit published npm packages via
# `tsc --noEmit` (anti-hallucination: every Scandit symbol must resolve; NOT runtime).
#
# Usage: fix_gate_ts.sh <platform: web|rn|capacitor> <ts-file> [version]
#   version default 8.4.0
# Note: cordova re-exports the shared frameworks package, so its signatures are covered by
#   the rn/capacitor check; cordova plain-JS syntax is checked separately with `node --check`.
# Toolchain: node + npm on PATH. Exit 3 = toolchain absent.
set -euo pipefail
PLAT=${1:?usage: fix_gate_ts.sh <web|rn|capacitor> <ts-file> [version]}
FILE=${2:?usage: fix_gate_ts.sh <web|rn|capacitor> <ts-file> [version]}
VER=${3:-8.4.0}
TS_VERSION=7.0.2
command -v npm >/dev/null 2>&1 || { echo "GATE-SKIP: npm not found"; exit 3; }
case "$PLAT" in
  web)       CORE="@scandit/web-datacapture-core"; BC="@scandit/web-datacapture-barcode"; LIB='"es2019", "dom"';;
  rn)        CORE="scandit-react-native-datacapture-core"; BC="scandit-react-native-datacapture-barcode"; LIB='"es2019"';;
  capacitor) CORE="scandit-capacitor-datacapture-core"; BC="scandit-capacitor-datacapture-barcode"; LIB='"es2019", "dom"';;
  *) echo "unknown platform: $PLAT (web|rn|capacitor)"; exit 2;;
esac
DIR=$(mktemp -d); trap 'rm -rf "$DIR"' EXIT
mkdir -p "$DIR/src"; cp "$FILE" "$DIR/src/gate.ts"
cat > "$DIR/package.json" <<EOF
{ "name":"fix-gate-ts","private":true,
  "dependencies": { "$CORE":"$VER", "$BC":"$VER", "typescript":"$TS_VERSION" } }
EOF
cat > "$DIR/tsconfig.json" <<EOF
{ "compilerOptions": { "strict": true, "noEmit": true, "skipLibCheck": true,
  "module": "esnext", "moduleResolution": "bundler", "esModuleInterop": true, "target": "es2019",
  "lib": [$LIB], "types": [] }, "include": ["src/**/*.ts"] }
EOF
( cd "$DIR" && npm install --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 && node_modules/.bin/tsc --noEmit ) \
  && echo "GATE-PASS: $FILE vs $BC $VER ($PLAT)" \
  || { echo "GATE-FAIL: $FILE vs $BC $VER ($PLAT)"; exit 1; }
