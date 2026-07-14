# SubTrack Mobile (iOS + Android) — Capacitor Setup

SubTrack's UI is a React + Vite + TypeScript app. We package it as **native iOS and
Android apps with Capacitor** — the same code, wrapped in a native shell (real WebView,
native splash/icon/status bar), ready for the App Store and Google Play. No UI rewrite.

> Note: the app is still fundamentally a web build running in a native WebView. If you
> later want 100% native UI components (native list/scroll feel, native navigation),
> that would be a React Native rewrite — out of scope here.

## Project layout
```
code/frontend/
  capacitor.config.ts      # appId, appName, webDir=dist
  android/                 # generated native Android project (open in Android Studio)
  ios/                     # generated native iOS project (open in Xcode, on a Mac)
```
The web source stays in `src/` — you keep editing React; `npm run mobile:build` rebuilds
and syncs into both native projects.

## Prerequisites
| Tool | Needed for | Install |
|------|-----------|---------|
| Node 22+ | build web | done |
| Android Studio + JDK 17+ + Android SDK | Android build/run | https://developer.android.com/studio |
| macOS + Xcode 15+ + CocoaPods | iOS build/run | App Store (Xcode) |

> iOS **cannot be built on Linux** — this dev box is Linux, so the `ios/` project is
> generated here but must be opened in **Xcode on a Mac** to build/sign/publish.

## Backend URL
The app talks to the FastAPI backend. Set it at build time via env:
```bash
# Point the built app at your API (https recommended for production):
export VITE_API_BASE="https://api.subtrack.app"   # or http://10.0.2.2:8000 for emulator dev
npm run mobile:build        # vite build + cap sync (copies assets into android/ and ios/)
```
- `VITE_API_BASE` empty → uses same-origin `/api` (works when API is behind the same host,
  e.g. the nginx Docker setup).
- Android emulator reaches the dev machine at `http://10.0.2.2:8000`. The repo's
  `android/.../network_security_config.xml` already allows cleartext to `10.0.2.2`/`localhost`
  for dev — **remove it for production** and use https.

## Android — build & run
```bash
cd code/frontend
npm run mobile:build
npx cap sync android
# Open in Android Studio and run on emulator/device:
npx cap open android
# or build an APK/AAB from the CLI (needs Android SDK + JDK 17+):
cd android && ./gradlew assembleDebug        # debug APK
cd android && ./gradlew bundleRelease        # AAB for Play Store (sign with your keystore)
```
Upload the AAB to the **Google Play Console** (Play App Signing recommended).

## iOS — build & run (on a Mac)
```bash
cd code/frontend
npm run mobile:build
npx cap sync ios
# Open in Xcode (requires macOS + Xcode + CocoaPods):
npx cap open ios
```
In Xcode: set your **Team/signing**, bump version, then run on simulator/device or
Archive → Upload to **App Store Connect**.

## Dev workflow (live reload)
```bash
# Terminal 1 — start Vite dev server (host 0.0.0.0 so the emulator can reach it)
npm run dev
# Terminal 2 — run on device/emulator with live reload
npx cap run android --livereload --port 5173
```

## Scripts (code/frontend/package.json)
- `npm run dev` — Vite dev server
- `npm run build` — production web build → `dist/`
- `npm run mobile:build` — `vite build` + `cap sync` (regenerate native assets)
- `npm run cap:android` / `npm run cap:ios` — (re)add native platforms

## Store listing assets
- App icons: `android/app/src/main/res/mipmap-*` and `ios/App/App/Assets.xcassets/AppIcon`.
  Replace with your branded icons (keep the required densities/sizes).
- Splash: `android/app/src/main/res/drawable-*/splash.png`, `ios/App/App/Assets.xcassets/Splash`.
- App name: `capacitor.config.ts` `appName` + `android/app/src/main/res/values/strings.xml`
  + iOS target name in Xcode.

## Gotchas
- After changing `src/`, always `npm run mobile:build` (or `cap sync`) before opening the
  native IDE — the native projects only contain a *copy* of `dist/`.
- Keep `android/local.properties` and any `*.keystore` out of git (git-ignored).
- `credentials.yaml` (backend secrets) is never part of the app bundle.
