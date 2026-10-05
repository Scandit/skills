#!/usr/bin/env bash
# Compile check for third-party-migration outputs: `flutter analyze` against fixtures/pubspec.yaml
# with the third-party scanner block removed, so any leftover mobile_scanner / ML Kit / camera use fails.
#
# Usage: analyze_migration.sh [--before] <dart-file> [stub-override ...]
#   --before        keep the third-party scanners (checks an unmigrated fixture resolves)
#   stub-override   migrated copy of a fixtures/stubs/ file; replaces the stub of the same name
# Exit 0 = no errors, 1 = errors, 3 = flutter not found (set $FLUTTER).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
KEEP=0; [ "${1:-}" = "--before" ] && { KEEP=1; shift; }
FILE=${1:?usage: analyze_migration.sh [--before] <dart-file> [stub-override ...]}; shift
FLUTTER=${FLUTTER:-$(command -v flutter 2>/dev/null || true)}
[ -x "$FLUTTER" ] || { echo "ANALYZE-SKIP: flutter not found (set \$FLUTTER)"; exit 3; }
DIR=$(mktemp -d); trap 'rm -rf "$DIR"' EXIT
mkdir -p "$DIR/lib"; cp -R "$HERE/fixtures/stubs" "$DIR/lib/stubs"
for s in "$@"; do cp "$s" "$DIR/lib/stubs/$(basename "$s")"; done
cp "$FILE" "$DIR/lib/$(basename "$FILE")"
if [ $KEEP = 1 ]; then cp "$HERE/fixtures/pubspec.yaml" "$DIR/pubspec.yaml"
else sed '/# BEGIN third-party scanners/,/# END third-party scanners/d' "$HERE/fixtures/pubspec.yaml" > "$DIR/pubspec.yaml"; fi
( cd "$DIR" && "$FLUTTER" pub get >/dev/null 2>&1 \
  && "$FLUTTER" analyze --no-fatal-infos --no-fatal-warnings "lib/$(basename "$FILE")" ) \
  && echo "ANALYZE-PASS: $FILE" \
  || { echo "ANALYZE-FAIL: $FILE"; exit 1; }
