#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ANDROID_HOME="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

mkdir -p "$ANDROID_HOME"
echo "sdk.dir=$ANDROID_HOME" > "$ROOT/local.properties"

if ! command -v sdkmanager >/dev/null 2>&1; then
  echo "Install Android command-line tools first:"
  echo "  brew install --cask android-commandlinetools android-platform-tools"
  exit 1
fi

echo "Accepting Android SDK licenses..."
yes | sdkmanager --licenses >/dev/null

echo "Installing SDK packages..."
sdkmanager \
  "platform-tools" \
  "platforms;android-35" \
  "build-tools;35.0.0" \
  "build-tools;34.0.0"

echo "Building sample banking app..."
cd "$ROOT"
./gradlew :sample-banking-app:assembleDebug

APK="$ROOT/sample-banking-app/build/outputs/apk/debug/sample-banking-app-debug.apk"
echo ""
echo "Setup complete."
echo "  ANDROID_HOME=$ANDROID_HOME"
echo "  JAVA_HOME=$JAVA_HOME"
echo "  APK=$APK"
echo ""
echo "Start FIDES backend (from repo root):"
echo "  uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Install on a connected device/emulator:"
echo "  adb install -r \"$APK\""
