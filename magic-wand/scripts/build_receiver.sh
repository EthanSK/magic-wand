#!/bin/zsh
# Build Wand Receiver.app from receiver/ into build.noindex/. Needs the Xcode command line tools.
# The app is ad-hoc signed for this Mac only; nothing here installs, launches or replaces an app.
set -euo pipefail
ROOT="${0:A:h:h}"
APP="$ROOT/build.noindex/Wand Receiver.app"
python3 "$ROOT/scripts/build.py" --check
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$ROOT/receiver/Info.plist" "$APP/Contents/Info.plist"
# All receiver source files are owned by this target, including device adapters.
swiftc -O "$ROOT/receiver/Sources/"*.swift \
  -o "$APP/Contents/MacOS/WandReceiver"
# The receiver sends only code over the slow UART link; the readable bridge keeps its comments.
cp "$ROOT/device/generated/wand-mode-bridge.compact.js" "$APP/Contents/Resources/wand-mode-bridge.js"
cp "$ROOT/device/generated/wand-power-policy.compact.js" "$APP/Contents/Resources/wand-power-policy.js"
cp "$ROOT/device/generated/wand-commands.json" "$ROOT/device/generated/wand-runtime-version.txt" "$APP/Contents/Resources/"
# Sense profile: the canonical Puck program run on the Mac. The readable base keeps its
# function declarations for the shim's in-place replaceWith; it is the same source whose
# body hash is wand-runtime-version.txt. The shim is the website/test Espruino host, unchanged.
cp "$ROOT/device/wand-mouse-prototype.js" "$APP/Contents/Resources/wand-base.js"
cp "$ROOT/../docs/sim/espruino.js" "$APP/Contents/Resources/wand-espruino.js"
cp "$ROOT/device/sense/wand-sense-host.js" "$APP/Contents/Resources/wand-sense-host.js"
# Public original artwork, generated alongside the website icons by scripts/make_images.py.
cp "$ROOT/receiver/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"
codesign --force --sign - --identifier com.ethansk.wand-receiver -r='designated => identifier "com.ethansk.wand-receiver"' "$APP"
codesign --verify --strict "$APP"
echo "Built $APP"
