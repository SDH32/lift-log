#!/bin/sh
# Start the headless Android emulator (Pixel 8, Android 16) and connect to its Chrome.
# One-time setup was: brew install openjdk@21; brew install --cask android-commandlinetools;
#   sdkmanager "platform-tools" "emulator" "system-images;android-36;google_apis_playstore;arm64-v8a";
#   avdmanager create avd -n liftlog-pixel -k "system-images;android-36;google_apis_playstore;arm64-v8a" -d pixel_8
# Stop it afterwards with: adb emu kill
export ANDROID_HOME=${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
nohup emulator -avd liftlog-pixel -no-window -no-audio -no-boot-anim -gpu swiftshader_indirect > /tmp/emulator.log 2>&1 &
adb wait-for-device
until [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" = "1" ]; do sleep 2; done
adb shell am start -a android.intent.action.VIEW -d "https://sdh32.github.io/lift-log/" com.android.chrome >/dev/null
sleep 5
adb forward tcp:9222 localabstract:chrome_devtools_remote >/dev/null
echo "Emulator ready; Android Chrome debuggable at http://localhost:9222"
