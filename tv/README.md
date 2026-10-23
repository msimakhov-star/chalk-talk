# Chalk Talk TV

react-native-tvos app for Android TV (the hackathon's accepted Fire OS stand-in). Android only.

- `src/` the app: `App.tsx` (pairing, long-poll, D-pad), `CourtScreen.tsx` (animated court), `PairScreen.tsx`, `court.ts` (pure geometry), `demoPlay.ts` (offline fallback play), `config.ts` (backend URL).
- `app/` the react-native-tvos project shell (Android project, Metro, package.json). `app/index.js` imports `../src/App`.
- `scripts/emulator.sh` starts the Android TV emulator; `scripts/check_demo_play.mjs` is the self-check.
- `release/chalk-talk.apk` sideloadable release build. `screenshots/` taken on the emulator.
- `TOOLCHAIN.md` exact install and env for this Mac.

## Run

```sh
tv/scripts/emulator.sh                    # boots the "firetv" AVD
cd tv/app && npm install && npx react-native run-android
```

Sideload the release APK on a Fire TV or the emulator: `adb install -r tv/release/chalk-talk.apk`.

## Behaviour

On launch the TV calls `POST /api/tv/pair`, shows the 4-letter code, and long-polls `GET /api/tv/{code}/state?wait=1`. When the phone sends a play the Court screen opens. If the backend is unreachable the app shows an "OFFLINE DEMO" badge and plays the embedded pick and roll (press OK on the Pair screen).

D-pad: right/left step beats, OK play/pause, up toggles the dotted paths overlay, down asks the backend for the next counter (man, switch, hedge, drop, zone), back returns to Pair.

Check: `node --no-warnings tv/scripts/check_demo_play.mjs` (validates the demo play against CONTRACTS.md and the geometry helpers).
