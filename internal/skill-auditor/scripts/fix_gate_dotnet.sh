#!/usr/bin/env bash
# Fix-verification gate — .NET (net-android / net-ios / net-maui share the managed API).
# Builds a .cs file against the resolved REAL Scandit NuGet packages via `dotnet build`
# on a plain net8.0 project (the package multi-targets down to net8.0, so NO android/ios
# workloads are needed — the net8.0 managed slice carries the full cross-platform API
# surface incl. BarcodeCountView/overlays). Anti-hallucination only; NOT runtime.
# Platform-UI-only types (Android.Views.*, UIKit.*) won't resolve here — keep those out of
# the gated snippet or gate them with the platform workload separately.
#
# Usage: fix_gate_dotnet.sh [--maui] <cs-file> [version] [extra-pkg ...]
#   version default 8.4.0; always references Scandit.DataCapture.Core + .Barcode.
#   extra-pkg e.g. Scandit.DataCapture.Id  Scandit.DataCapture.Label
#   --maui: <cs-file> is Page.xaml.cs with Page.xaml beside it; adds Maui.Controls + *.Maui pkgs.
# Toolchain: `dotnet` (>=8) on PATH or in ~/.dotnet, or set $DOTNET. Exit 3 = toolchain absent, 2 = bad --maui input.
set -euo pipefail
MAUI=0
if [ "${1:-}" = "--maui" ]; then MAUI=1; shift; fi
FILE=${1:?usage: fix_gate_dotnet.sh [--maui] <cs-file> [version] [extra-pkg ...]}; shift || true
if [ "$MAUI" = 1 ]; then
  case "$FILE" in *.xaml.cs) ;; *) echo "GATE-FAIL: --maui needs a Page.xaml.cs file, got $FILE"; exit 2;; esac
  [ -f "${FILE%.cs}" ] || { echo "GATE-FAIL: --maui needs ${FILE%.cs} beside $FILE"; exit 2; }
fi
VER=${1:-8.4.0}; [ $# -gt 0 ] && shift || true
EXTRA=("$@")
DOTNET=${DOTNET:-$(command -v dotnet 2>/dev/null || true)}
[ -x "$DOTNET" ] || DOTNET="$HOME/.dotnet/dotnet"
[ -x "$DOTNET" ] || { echo "GATE-SKIP: dotnet not found (set \$DOTNET; install: dotnet-install.sh --channel 8.0)"; exit 3; }
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
DIR=$(mktemp -d); trap 'rm -rf "$DIR"' EXIT
if [ "$MAUI" = 1 ]; then cp "$FILE" "${FILE%.cs}" "$DIR/"; else cp "$FILE" "$DIR/Gate.cs"; fi
refs="    <PackageReference Include=\"Scandit.DataCapture.Core\" Version=\"$VER\" />
    <PackageReference Include=\"Scandit.DataCapture.Barcode\" Version=\"$VER\" />"
for p in ${EXTRA[@]+"${EXTRA[@]}"}; do refs="$refs
    <PackageReference Include=\"$p\" Version=\"$VER\" />"; done
props="<Nullable>enable</Nullable><LangVersion>latest</LangVersion>"
usings=""
if [ "$MAUI" = 1 ]; then
  refs="$refs
    <PackageReference Include=\"Scandit.DataCapture.Core.Maui\" Version=\"$VER\" />
    <PackageReference Include=\"Scandit.DataCapture.Barcode.Maui\" Version=\"$VER\" />
    <PackageReference Include=\"Microsoft.Maui.Controls\" Version=\"8.0.100\" />"
  props="<ImplicitUsings>enable</ImplicitUsings> $props <OutputType>Library</OutputType>"
  usings='  <ItemGroup>
    <Using Include="Microsoft.Maui" /><Using Include="Microsoft.Maui.Controls" />
    <Using Include="Microsoft.Maui.ApplicationModel" /><Using Include="Microsoft.Maui.Graphics" />
  </ItemGroup>'
fi
cat > "$DIR/gate.csproj" <<EOF
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net8.0</TargetFramework>$props</PropertyGroup>
  <ItemGroup>
$refs
  </ItemGroup>
$usings
</Project>
EOF
LOG=$(cd "$DIR" && "$DOTNET" build -v q -nologo 2>&1 || true)
if grep -qiE "Build succeeded" <<<"$LOG"; then
  echo "GATE-PASS: $FILE vs Scandit.DataCapture.* $VER"
else
  grep -iE "error CS" <<<"$LOG" | awk '!seen[$0]++' | head || true
  echo "GATE-FAIL: $FILE vs Scandit.DataCapture.* $VER"; exit 1
fi
