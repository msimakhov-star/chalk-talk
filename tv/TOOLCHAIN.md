# Android TV toolchain on this Mac (Fire OS stand-in)

Installed with Homebrew only, no Android Studio. One system image.

```sh
brew install openjdk@17
brew install --cask android-commandlinetools   # sdkmanager/avdmanager at /opt/homebrew/share/android-commandlinetools
```

Environment (put in ~/.zshrc or source before every command):

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export ANDROID_HOME=$HOME/Library/Android/sdk
export ANDROID_SDK_ROOT=$ANDROID_HOME
export PATH=$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH
```

SDK packages (react-native-tvos 0.83 needs compileSdk 36, build-tools 36.0.0, NDK 27.1.12297006):

```sh
SDKM=/opt/homebrew/share/android-commandlinetools/cmdline-tools/latest/bin/sdkmanager
yes | $SDKM --sdk_root=$ANDROID_HOME --licenses
$SDKM --sdk_root=$ANDROID_HOME "platform-tools" "emulator" "cmdline-tools;latest" \
  "platforms;android-36" "build-tools;36.0.0" "ndk;27.1.12297006" "cmake;3.22.1" \
  "system-images;android-34;android-tv;arm64-v8a"
```

AVD (1080p Android TV, API 34, arm64 so it runs natively on Apple silicon):

```sh
avdmanager create avd -n firetv -k "system-images;android-34;android-tv;arm64-v8a" -d "tv_1080p"
tv/scripts/emulator.sh            # starts it with a window and waits for sys.boot_completed=1
adb devices                       # emulator-5554  device
```

App:

```sh
cd tv/app && npm install
npx react-native run-android      # debug build + Metro, installs on the emulator
cd android && ./gradlew assembleRelease && cp app/build/outputs/apk/release/app-release.apk ../../release/chalk-talk.apk
```

Driving the emulator from the shell (what the D-pad does on the Court screen):

```sh
adb shell input keyevent KEYCODE_DPAD_RIGHT    # next beat
adb shell input keyevent KEYCODE_DPAD_LEFT     # previous beat
adb shell input keyevent KEYCODE_DPAD_CENTER   # play / pause
adb shell input keyevent KEYCODE_DPAD_UP       # toggle paths overlay
adb shell input keyevent KEYCODE_DPAD_DOWN     # cycle counters (needs the backend)
adb shell input keyevent KEYCODE_BACK          # back to Pair
adb exec-out screencap -p > tv/screenshots/court.png
```

Self-check (no emulator needed): `node --no-warnings tv/scripts/check_demo_play.mjs`
