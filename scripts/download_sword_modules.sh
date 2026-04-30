#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)/bible/sword_modules"
mkdir -p "$DIR"
curl -fSL -o "$DIR/LvGluck8.zip" \
  https://crosswire.org/ftpmirror/pub/sword/packages/rawzip/LvGluck8.zip
echo "Downloaded LvGluck8.zip to $DIR"
