#!/usr/bin/env bash
# Fix-verification gate — .NET (net-android / net-ios / maui share the managed API).
# Builds a .cs file against the resolved REAL Scandit NuGet packages via `dotnet build`
# on a plain net8.0 project (the package multi-targets down to net8.0, so NO android/ios
# workloads are needed — the net8.0 managed slice carries the full cross-platform API
# surface incl. BarcodeCountView/overlays). Anti-hallucination only; NOT runtime.
# Platform-UI-only types (Android.Views.*, UIKit.*) won't resolve here — keep those out of
# the gated snippet or gate them with the platform workload separately.
#
# Usage: fix_gate_dotnet.sh <cs-file> [version] [extra-pkg ...]
#   version default 8.4.0; always references Scandit.DataCapture.Core + .Barcode.
#   extra-pkg e.g. Scandit.DataCapture.Id  Scandit.DataCapture.Label
# Toolchain: `dotnet` (>=8) on PATH or in ~/.dotnet, or set $DOTNET. Exit 3 = toolchain absent.
set -euo pipefail
FILE=${1:?usage: fix_gate_dotnet.sh <cs-file> [version] [extra-pkg ...]}; shift || true
VER=${1:-8.4.0}; [ $# -gt 0 ] && shift || true
EXTRA=("$@")
DOTNET=${DOTNET:-$(command -v dotnet 2>/dev/null || true)}
[ -x "$DOTNET" ] || DOTNET="$HOME/.dotnet/dotnet"
[ -x "$DOTNET" ] || { echo "GATE-SKIP: dotnet not found (set \$DOTNET; install: dotnet-install.sh --channel 8.0)"; exit 3; }
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
DIR=$(mktemp -d); trap 'rm -rf "$DIR"' EXIT
cp "$FILE" "$DIR/Gate.cs"
refs="    <PackageReference Include=\"Scandit.DataCapture.Core\" Version=\"$VER\" />
    <PackageReference Include=\"Scandit.DataCapture.Barcode\" Version=\"$VER\" />"
for p in ${EXTRA[@]+"${EXTRA[@]}"}; do refs="$refs
    <PackageReference Include=\"$p\" Version=\"$VER\" />"; done
cat > "$DIR/gate.csproj" <<EOF
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net8.0</TargetFramework><Nullable>enable</Nullable><LangVersion>latest</LangVersion></PropertyGroup>
  <ItemGroup>
$refs
  </ItemGroup>
</Project>
EOF
if ( cd "$DIR" && "$DOTNET" build -v q -nologo 2>&1 | grep -qiE "Build succeeded" ); then
  echo "GATE-PASS: $FILE vs Scandit.DataCapture.* $VER"
else
  ( cd "$DIR" && "$DOTNET" build -v q -nologo 2>&1 | grep -iE "error CS" | head )
  echo "GATE-FAIL: $FILE vs Scandit.DataCapture.* $VER"; exit 1
fi
