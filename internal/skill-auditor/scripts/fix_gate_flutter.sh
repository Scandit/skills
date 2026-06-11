#!/usr/bin/env bash
# Fix-verification gate — Flutter (anti-hallucination, NOT runtime behaviour).
# Compiles a Dart file against the resolved REAL Scandit Flutter SDK via `flutter analyze`,
# so every Scandit symbol used must exist in the released package and the file must compile.
#
# Usage: fix_gate_flutter.sh <dart-file> [version] [pub-package]
#   version      default 8.4.0
#   pub-package   default scandit_flutter_datacapture_barcode
#                 (use scandit_flutter_datacapture_label / _id for those products)
# Toolchain: `flutter` on PATH, or set $FLUTTER. Exit 3 = toolchain absent (skip, don't pretend).
set -euo pipefail
FILE=${1:?usage: fix_gate_flutter.sh <dart-file> [version] [pub-package]}
VER=${2:-8.4.0}
PKG=${3:-scandit_flutter_datacapture_barcode}
FLUTTER=${FLUTTER:-$(command -v flutter 2>/dev/null || true)}
[ -x "$FLUTTER" ] || { echo "GATE-SKIP: flutter not found (set \$FLUTTER)"; exit 3; }
DIR=$(mktemp -d); trap 'rm -rf "$DIR"' EXIT
mkdir -p "$DIR/lib"; cp "$FILE" "$DIR/lib/gate.dart"
cat > "$DIR/pubspec.yaml" <<EOF
name: fix_gate
publish_to: none
environment: { sdk: '>=3.0.0 <4.0.0' }
dependencies:
  flutter: { sdk: flutter }
  $PKG: '$VER'
EOF
( cd "$DIR" && "$FLUTTER" pub get >/dev/null 2>&1 && "$FLUTTER" analyze lib/gate.dart ) \
  && echo "GATE-PASS: $FILE vs $PKG $VER" \
  || { echo "GATE-FAIL: $FILE vs $PKG $VER"; exit 1; }
