#!/usr/bin/env bash
# Fix-verification gate — TypeScript (web / React Native / Capacitor).
# Type-checks a .ts file against the resolved REAL Scandit published npm packages via
# `tsc --noEmit` (anti-hallucination: every Scandit symbol must resolve; NOT runtime).
#
# Usage: fix_gate_ts.sh <platform: web|rn|capacitor> <ts-tsx-js-or-vue-file> [version] [extra-file...]
#   version default 8.4.0; .vue = its script block; FIX_GATE_TS_ANY_MODULE=1 types unresolved app imports as any.
# Note: cordova re-exports the shared frameworks package, so its signatures are covered by
#   the rn/capacitor check; cordova plain-JS syntax is checked separately with `node --check`.
# Toolchain: node + npm on PATH. Exit 3 = toolchain absent.
set -euo pipefail
PLAT=${1:?usage: fix_gate_ts.sh <web|rn|capacitor> <ts-tsx-js-or-vue-file> [version] [extra-file...]}
FILE=${2:?usage: fix_gate_ts.sh <web|rn|capacitor> <ts-tsx-js-or-vue-file> [version] [extra-file...]}
VER=${3:-8.4.0}
EXTRAS=("${@:4}")
TS_VERSION=7.0.2
for tool in node npm; do
  command -v "$tool" >/dev/null 2>&1 || { echo "GATE-SKIP: $tool not found"; exit 3; }
done
case "$PLAT" in
  web)       CORE="@scandit/web-datacapture-core"; BC="@scandit/web-datacapture-barcode";;
  rn)        CORE="scandit-react-native-datacapture-core"; BC="scandit-react-native-datacapture-barcode";;
  capacitor) CORE="scandit-capacitor-datacapture-core"; BC="scandit-capacitor-datacapture-barcode";;
  *) echo "unknown platform: $PLAT (web|rn|capacitor)"; exit 2;;
esac
DIR=$(mktemp -d); trap 'rm -rf "$DIR"' EXIT
# A .tsx file (React / React Native screen) keeps its extension and gets React types.
EXT=ts; EXTRA_DEPS=""
FILES=("$FILE" ${EXTRAS[@]+"${EXTRAS[@]}"})
for f in "${FILES[@]}"; do
  case "$f" in *.tsx)
    EXTRA_DEPS=', "react":"19.1.0", "@types/react":"19.1.0"'
    [ "$PLAT" = rn ] && EXTRA_DEPS="$EXTRA_DEPS"', "react-native":"0.81.4"';;
  esac
done
# A plain-JS main file (Capacitor / web snippet) is checked as JS (allowJs + checkJs), not as TS.
case "$FILE" in *.js) EXT=js;; esac
# Capacitor apps import Capacitor from @capacitor/core (e.g. the getPlatform() web guard).
[ "$PLAT" = capacitor ] && EXTRA_DEPS="$EXTRA_DEPS"', "@capacitor/core":"8.5.3"'
# JS cannot annotate, so implicit-any is not a hallucination signal there; Scandit symbols still must resolve.
NOIMPLICITANY=true; [ "$EXT" = js ] && NOIMPLICITANY=false
# web and capacitor code (.ts and .js) runs in a WebView/browser: give it the DOM globals.
LIB='"es2019"'; [ "$PLAT" != rn ] && LIB='"es2019", "dom"'
mkdir -p "$DIR/src"
VUE_SCRIPT='/<script[ >]/ {on=1; print ""; next} /<\/script>/ {on=0; print ""; next} on {print; next} {print ""}'
for f in "${FILES[@]}"; do
  base=$(basename "$f")
  case "$f" in
    # Blank every line outside the script block so error line numbers still match the .vue file.
    *.vue) awk "$VUE_SCRIPT" "$f" > "$DIR/src/${base%.vue}.ts";;
    *) cp "$f" "$DIR/src/$base";;
  esac
done
# App modules typed as any cannot carry types or implicit-any context, so those side effects are not findings.
SHIM_ERRORS='error TS(2347|2694|2709):'
if [ -n "${FIX_GATE_TS_ANY_MODULE:-}" ]; then
  printf 'declare module "*";\ninterface ImportMeta { readonly env: any }\n' > "$DIR/src/any-module.d.ts"
  NOIMPLICITANY=false
fi
cat > "$DIR/package.json" <<EOF
{ "name":"fix-gate-ts","private":true,
  "dependencies": { "$CORE":"$VER", "$BC":"$VER", "typescript":"$TS_VERSION"$EXTRA_DEPS } }
EOF
cat > "$DIR/tsconfig.json" <<EOF
{ "compilerOptions": { "strict": true, "noEmit": true, "skipLibCheck": true,
  "module": "esnext", "moduleResolution": "bundler", "esModuleInterop": true, "target": "es2019",
  "allowJs": true, "checkJs": true, "noImplicitAny": $NOIMPLICITANY,
  "jsx": "react-jsx", "lib": [$LIB], "types": [] }, "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.js"] }
EOF
( cd "$DIR" && npm install --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 ) \
  || { echo "GATE-FAIL: npm install of $BC $VER ($PLAT)"; exit 1; }
OUT=$(cd "$DIR" && node_modules/.bin/tsc --noEmit 2>&1) && RC=0 || RC=$?
if [ -n "${FIX_GATE_TS_ANY_MODULE:-}" ] && printf '%s\n' "$OUT" | grep -q 'error TS'; then
  OUT=$(printf '%s\n' "$OUT" | grep -Ev "$SHIM_ERRORS" || true)
  printf '%s\n' "$OUT" | grep -q 'error TS' || RC=0
fi
[ -z "$OUT" ] || printf '%s\n' "$OUT"
[ "$RC" = 0 ] && echo "GATE-PASS: $FILE vs $BC $VER ($PLAT)" || { echo "GATE-FAIL: $FILE vs $BC $VER ($PLAT)"; exit 1; }
