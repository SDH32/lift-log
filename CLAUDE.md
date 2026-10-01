# Lift Log

A lightweight workout tracker for lifting sessions: a single-file web app, installed to the
phone's home screen. Live at https://sdh32.github.io/lift-log/ (GitHub Pages from `main`).

## Product rules

- **Keep it basic.** The app should do what it says and nothing more. Push back on features
  that add complexity; prefer small quality-of-life fixes over new features.
- **No accounts, no tracking, no network dependence.** All data stays on the device (localStorage)
  and belongs to the user. No analytics, crash-reporting, or ad SDKs — ever (the stores' privacy
  answer is "Data Not Collected").
- If it's ever sold in app stores: one-time purchase, no subscription.
- Themes are on hold. If ever added, **accent colors only** (a validated light + dark shade per
  accent) — full palette themes are ruled out as bloat.

## Files

- `index.html` — the whole app: CSS, then a small `<head>` script (`applyTheme`, runs before first
  paint), then the main script. Sections are marked `// ---------- Name ----------`
  (Views, Progress chart, Template editor, Navigation, Dialogs, Actions).
- `sw.js` — service worker: network-first with a 3s fallback to cache, `cache: 'no-cache'` so
  updates aren't held back by GitHub Pages' 10-minute cache.
- `manifest.webmanifest`, `icons/` — installability. `icons/icon.svg` is the source; PNGs are
  rendered from it (keep the barbell inside the maskable safe zone).
- `tests/` — browser tests (see Testing).

## How the app works

- **State** (`localStorage['liftlog.v1']`): `{ unit, theme, exercises[], templates[{name, exercises[]}],
  active, sessions[{name, start, end, exercises[{name, sets[{weight, reps, done}]}]}] }`.
  `load()` back-fills new fields (`??=`) so old data and old backup files keep working — do the
  same for any new field, and in `importData`. A set with no weight is a bodyweight set.
- **Rendering**: views return HTML strings; `render(anim)` redraws `#view` and the header. Escape
  user text with `esc()` in templates; use `textContent` when building DOM directly.
- **Navigation**: every sub-screen (exercise detail, template editor) and every dialog is a *layer*
  with its own history entry. Going back is always `history.back()` → `popstate` closes whatever
  is above the new depth. Use `goBack()` for app-initiated backs. Switching tabs unwinds layers.
  The template editor guards unsaved edits on any kind of exit.
- **iOS back swipe is native** (Safari and home-screen apps). Never add a custom swipe handler —
  it caused a double animation. System backs on iOS skip the app's slide animation.
- **Dialogs**: never use `alert`/`confirm`/`prompt`. Use `await ask({...})`, `await askText({...})`,
  and `toast(msg)`. Destructive confirms pass `danger: true`.
- **Export** uses the share sheet on touch devices (`navigator.share` with a file), falling back
  to a download; Android Chrome can't share `.json`, so it downloads.

## UI rules

- Colors come only from the CSS variables in the two `:root` blocks (dark default,
  `[data-theme="light"]`). Every text/background pair must meet WCAG AA (4.5:1; chart line 3:1) —
  `tests/test_theme.py` enforces this. Button fills use `--accent-fill` / `--danger-fill`.
- Form fields stay at **16px or larger** text (iOS zooms into smaller fields and stays zoomed).
- Respect `env(safe-area-inset-*)`; header and tabs line up with the 640px content column.
- Animations must respect `prefers-reduced-motion`.

## Testing

Tests use Playwright (Python, installed with `pip3 --user`; uses the macOS command-line-tools
Python at `/usr/bin/python3`).

- `sh tests/run_all.sh` — every `tests/test_*.py` on both Chromium and WebKit (Safari's engine).
  Single file: `python3 tests/test_navigation.py`; engine: `BROWSER=webkit python3 ...`.
- Known WebKit **test-tool** limits (not app bugs): no synthetic `Touch` (those checks skip), and
  `set_offline` crashes with a service worker (`test_install.py` stops its server instead).
  WebKit's simulated wheel reports unclamped scroll positions.
- When fixing a bug, first show the test fails on the old version (`git show HEAD:index.html`),
  then passes on the new one. Look at screenshots after layout changes, not just pass counts.
- **Android emulator** (headless Pixel 8, Android 16): `sh tests/android/start_emulator.sh`, then
  `python3 tests/android/test_android_back.py` (drives Android Chrome over CDP on :9222 and presses
  the real back key with adb). Stop with `adb emu kill`. SDK: `/opt/homebrew/share/android-commandlinetools`.
- **iOS simulator** (Xcode 27): simulators are managed by
  `/Applications/Xcode.app/Contents/Applications/DeviceHub.app` (there is no Simulator.app), and
  render black unless DeviceHub is open. Prefix commands with
  `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer` (`xcode-select` points at the
  command-line tools; don't switch it, or `python3` loses Playwright). `simctl openurl` and
  `simctl io <udid> screenshot` work; `simctl` can't tap.
- Simulated tests can't reproduce native OS behavior (gestures, system animations, the iOS status
  bar). Say clearly what was and wasn't verified, and ask the user to check on their iPhone.

## Shipping

- Pushing to `main` deploys to GitHub Pages in about a minute. After pushing, confirm the live
  site serves the new version (e.g. `curl` it and grep for a string from the change).
- Commit only with this repo's configured identity: the GitHub **noreply** address. The repo is
  public — never commit a personal email address or other personal details.
- Users get updates by closing and reopening the app.

## Possible app-store build (not started)

Planned route is Capacitor wrapping this same code. Known to-dos: native share for Export, Android
back button → `history.back()`, enable WKWebView back/forward swipe gestures, sturdier storage
than localStorage, a privacy policy page, and checking the app name is free in both stores.
