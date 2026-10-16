#!/usr/bin/env bash
# Fix-verification gate — TypeScript (web / React Native / Capacitor).
# Type-checks a .ts file against the resolved REAL Scandit published npm packages via
# `tsc --noEmit` (anti-hallucination: every Scandit symbol must resolve; NOT runtime).
#
# Usage: fix_gate_ts.sh <platform: web|rn|capacitor> <ts-tsx-js-or-vue-file> [version] [extra-file...]
#   version default 8.4.0; .vue = its script block; FIX_GATE_TS_ANY_MODULE=1 types non-Scandit imports as any
#   and drops implicit-any errors only on callbacks handed straight to them (a bare Scandit listener keeps its).
#   Files are gated flat under their basenames (.vue as .ts); two files with one basename = exit 2.
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
VUE_SCRIPT='/<script[ >]/ && /<\/script>/ {sub(/^.*<script[^>]*>/, ""); sub(/<\/script>.*$/, ""); print; next}
  /<script[ >]/ {on=1; print ""; next} /<\/script>/ {on=0; print ""; next} on {print; next} {print ""}'
VUE=0
for f in "${FILES[@]}"; do
  base=$(basename "$f"); case "$base" in *.vue) base="${base%.vue}.ts";; esac
  [ ! -e "$DIR/src/$base" ] || { echo "fix_gate_ts: two files map to src/$base; rename one"; exit 2; }
  case "$f" in
    # Blank every line outside the script block so error line numbers still match the .vue file.
    *.vue) awk "$VUE_SCRIPT" "$f" > "$DIR/src/$base"; VUE=1;;
    *) cp "$f" "$DIR/src/$base";;
  esac
done
# <script setup> compiler macros: globals the Vue compiler provides.
[ "$VUE" = 0 ] || printf '%s\n' 'declare function defineProps<T = any>(props?: any): T;' \
  'declare function defineEmits<T = any>(emits?: any): T;' 'declare function defineExpose(exposed?: any): void;' \
  'declare function withDefaults<T>(props: T, defaults?: any): T;' 'declare function defineOptions(options?: any): void;' \
  'declare function defineModel<T = any>(...args: any[]): { value: T };' 'declare function defineSlots<T = any>(): T;' \
  > "$DIR/src/vue-macros.d.ts"
# Shim: an import that resolves to nothing installed or copied (never a Scandit one) becomes an any-module.
# Prints the errors only those any-modules cause: an untyped generic call, or one of their names used as a type.
read -r -d '' SHIM_JS <<'JS' || true
const fs = require("fs"), path = require("path"), dir = process.argv[1], specs = new Set(), names = new Set();
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), pkg = (s) => s.split("/").slice(0, s[0] === "@" ? 2 : 1);
const real = (s) => /^@?scandit/i.test(s) || (s.startsWith(".")
  ? [".ts", ".tsx", ".js"].some((e) => fs.existsSync(path.join(dir, s + e)))
  : fs.existsSync(path.join(dir, "../node_modules", ...pkg(s))));
for (const f of fs.readdirSync(dir)) {
  const src = fs.readFileSync(path.join(dir, f), "utf8");
  for (const [, s] of src.matchAll(/\b(?:from|import|require)\s*\(?\s*["']([^"'\n]+)["']/g))
    if (!real(s) && !s.startsWith(".")) specs.add(s);
  for (const [, a, b, s] of src.matchAll(/\b(?:import\s+(?:type\s+)?([^"';]+?)\s+from|(?:const|let|var)\s+([^=;]+?)\s*=\s*(?:await\s+)?(?:import|require)\s*\()\s*["']([^"'\n]+)["']/g))
    if (!real(s)) for (const n of (a ?? b).split(/[{},]/)) { const m = n.match(/([\w$]+)\s*$/); if (m) names.add(m[1]); }
}
const mods = [...specs, "./*", "../*"], id = [...names].map(esc).join("|") || "$^";
fs.writeFileSync(path.join(dir, "../shim-names.json"), JSON.stringify([...names]));
fs.writeFileSync(path.join(dir, "any-module.d.ts"),
  mods.map((s) => `declare module "${s}";\n`).join("") + "interface ImportMeta { readonly env: any }\n");
console.log(`error TS2347:|error TS2694: Namespace '"(${mods.map(esc).join("|")})"'|error TS2709: Cannot use namespace '(${id})'`);
JS
# Drops implicit-any params (TS7006/TS7031) only on a callback passed to a call rooted at a shimmed import or
# initialized under a shimmed type; react, Object, app-local callees and bare listener objects keep the error.
read -r -d '' CALLBACK_JS <<'JS' || true
const fs = require("fs"), path = require("path"), dir = process.argv[1], cache = {};
const shimmed = new Set(JSON.parse(fs.readFileSync(path.join(dir, "shim-names.json"), "utf8")));
const code = (f) => cache[f] ??= fs.readFileSync(path.join(dir, f), "utf8").replace(
  /\/\*[\s\S]*?\*\/|\/\/[^\n]*|`(?:\\[\s\S]|[^\\`])*`|(["'])(?:\\.|(?!\1)[^\\\n])*\1/g, (m) => m.replace(/[^\n]/g, " "));
const outer = (s, i) => { for (let d = 0; --i >= 0; ) if (")]}".includes(s[i])) d++; else if ("([{".includes(s[i]) && d-- === 0) return i; return -1; };
const prev = (s, i) => { while (--i >= 0 && /\s/.test(s[i])); return i; };
function root(s, k) {
  for (let name = ""; ; ) {
    if (s[k] === ">" && s[k - 1] !== "=") {
      for (let d = 0; k >= 0; k--) if (s[k] === ">" && s[k - 1] !== "=") d++; else if (s[k] === "<" && --d === 0) break;
      k = prev(s, k); continue;
    }
    if (s[k] === ")" || s[k] === "]") { k = prev(s, outer(s, k)); continue; }
    let i = k + 1; while (i > 0 && /[\w$]/.test(s[i - 1])) i--;
    if (i > k) return name;
    name = s.slice(i, k + 1); k = prev(s, i);
    if (s[k] !== ".") return name;
    k = prev(s, s[k - 1] === "?" ? k - 1 : k);
  }
}
function shimmedCallback(s, at, binding) {
  let j = /^[\w$]+\s*=>/.test(s.slice(at)) ? at : outer(s, at);
  while (binding && j >= 0 && s[j] !== "(") j = outer(s, j);
  while (--j >= 0 && /[\w$*\s]/.test(s[j]));
  for (;;) {
    if (s[j] === "=") return shimmed.has(s.slice(s.lastIndexOf("\n", j) + 1, j).match(/\b(?:const|let|var)\s+[\w$]+\s*:\s*([\w$]+)[^=]*$/)?.[1]);
    if (j < 0 || !"([{,:".includes(s[j])) return false;
    const o = "([{".includes(s[j]) ? j : outer(s, j), k = o < 0 ? -1 : prev(s, o);
    if (o < 0) return false;
    if (s[o] === "(" && /[\w$)\]>]/.test(s[k] ?? "")) return shimmed.has(root(s, k));
    if (s[o] !== "(" && !/[(,:=[?]/.test(s[k] ?? "")) return false;
    j = k;
  }
}
const at = (s, line, col) => { let o = 0; while (--line > 0) o = s.indexOf("\n", o) + 1; return o + col - 1; };
console.log(fs.readFileSync(0, "utf8").split("\n").filter((l) => {
  const m = l.match(/^(.+?)\((\d+),(\d+)\): error TS70(06|31):/);
  return !m || !shimmedCallback(code(m[1]), at(code(m[1]), +m[2], +m[3]), m[4] === "31");
}).join("\n"));
JS
SHIM=0; [ "${FIX_GATE_TS_ANY_MODULE:-0}" = 1 ] && SHIM=1
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
if [ "$SHIM" = 1 ]; then SHIM_ERRORS=$(node -e "$SHIM_JS" "$DIR/src"); fi
OUT=$(cd "$DIR" && node_modules/.bin/tsc --noEmit 2>&1) && RC=0 || RC=$?
if [ "$SHIM" = 1 ] && printf '%s\n' "$OUT" | grep -q 'error TS'; then
  OUT=$(printf '%s\n' "$OUT" | { grep -Ev "$SHIM_ERRORS" || [ $? = 1 ]; } | node -e "$CALLBACK_JS" "$DIR") \
    || { echo "GATE-FAIL: implicit-any filter failed on $FILE ($PLAT)"; exit 1; }
  printf '%s\n' "$OUT" | grep -q 'error TS' || RC=0
fi
[ -z "$OUT" ] || printf '%s\n' "$OUT"
[ "$RC" = 0 ] && echo "GATE-PASS: $FILE vs $BC $VER ($PLAT)" || { echo "GATE-FAIL: $FILE vs $BC $VER ($PLAT)"; exit 1; }
