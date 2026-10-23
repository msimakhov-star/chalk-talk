#!/bin/sh
# Starts the Android TV emulator used as the Fire OS stand-in and waits for boot.
# Usage: tv/scripts/emulator.sh [extra emulator flags]
# Env: see tv/TOOLCHAIN.md. GPU: tries the host GPU; set GPU=swiftshader_indirect to force software.
set -eu
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
AVD="${AVD:-firetv}"
GPU="${GPU:-host}"

# One instance only: a second caller (another shell, another agent) waits for
# the running one instead of launching a rival against the same AVD.
if pgrep -f "qemu-system-aarch64.* -avd $AVD" > /dev/null; then
  echo "emulator already running, waiting for boot"
else
  nohup "$ANDROID_HOME/emulator/emulator" -avd "$AVD" -no-snapshot -no-boot-anim -no-metrics -gpu "$GPU" "$@" \
    > /tmp/chalk-talk-emulator.log 2>&1 &
  echo "emulator starting (log: /tmp/chalk-talk-emulator.log)"
fi
adb wait-for-device
until [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do sleep 2; done
echo "booted: $(adb devices | grep emulator)"
