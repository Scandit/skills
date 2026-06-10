#!/usr/bin/env bash
# Fix-verification gate — iOS Swift.
# Type-checks a .swift file against the resolved REAL Scandit xcframeworks via
# `swiftc -typecheck` (anti-hallucination: every Scandit symbol must resolve; NOT runtime).
# A bare `swiftc File.swift` is a FALSE gate — it can't resolve com.scandit/Scandit* without
# the frameworks on the search path, so this points -F at the resolved xcframework slices.
#
# Usage: fix_gate_swift.sh <swift-file> [frameworks-csv]
#   frameworks-csv default "ScanditCaptureCore,ScanditBarcodeCapture"
#                  (add ScanditIdCapture / ScanditLabelCapture etc. for those products)
# Frameworks are located from an SPM-resolved DerivedData artifacts dir; override with
# $SCANDIT_XCFRAMEWORKS (a dir containing <name>.xcframework/ios-arm64_x86_64-simulator).
# Toolchain: Xcode (xcrun + iphonesimulator SDK). Exit 3 = toolchain/frameworks absent.
set -euo pipefail
FILE=${1:?usage: fix_gate_swift.sh <swift-file> [frameworks-csv]}
FWS=${2:-ScanditCaptureCore,ScanditBarcodeCapture}
command -v xcrun >/dev/null 2>&1 || { echo "GATE-SKIP: xcrun/Xcode not found"; exit 3; }
SDK=$(xcrun --sdk iphonesimulator --show-sdk-path 2>/dev/null || true)
[ -n "$SDK" ] || { echo "GATE-SKIP: iphonesimulator SDK not found"; exit 3; }
# Locate the SPM artifacts dir holding the resolved xcframeworks.
ART=${SCANDIT_XCFRAMEWORKS:-}
if [ -z "$ART" ]; then
  ART=$(find "$HOME/Library/Developer/Xcode/DerivedData" -type d -path "*SourcePackages/artifacts/datacapture-spm" 2>/dev/null | head -1)
fi
[ -n "$ART" ] && [ -d "$ART" ] || { echo "GATE-SKIP: no resolved Scandit xcframeworks (set \$SCANDIT_XCFRAMEWORKS or build an SPM sample once)"; exit 3; }
FFLAGS=()
IFS=',' read -ra NAMES <<< "$FWS"
for n in "${NAMES[@]}"; do
  slice=$(find "$ART" -type d -path "*/$n.xcframework/ios-arm64_x86_64-simulator" 2>/dev/null | head -1)
  [ -n "$slice" ] || { echo "GATE-SKIP: $n.xcframework simulator slice not found under $ART"; exit 3; }
  FFLAGS+=( -F "$slice" )
done
if xcrun swiftc -typecheck -sdk "$SDK" -target arm64-apple-ios15.0-simulator "${FFLAGS[@]}" "$FILE"; then
  echo "GATE-PASS: $FILE vs $FWS"
else
  echo "GATE-FAIL: $FILE vs $FWS"; exit 1
fi
