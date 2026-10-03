# FluidCursor development handoff

Updated: 2026-10-03.

## Start a new chat

Paste this and add the feature or issue you want to work on:

> Continue developing FluidCursor at `C:\Users\osama\.gemini\antigravity\scratch\fluid_cursor`. Read `AGENTS.md` and `DEVELOPMENT_GUIDE.md`, inspect Git status and the relevant source, and preserve my local preferences. Keep `FluidCursor.exe` as the single application executable. Implement the requested change, run relevant Windows tests, and distinguish automated checks from real desktop verification. My next request is: ...

Repository: https://github.com/batatistech/FluidCursor, branch `main`.

Pre-cleanup recovery branch: `backup/pre-cleanup-2026-10-03`, commit `cded8fe87947acd7b9ffa10f917805eb3c8c1446`. It contains all source changes present before cleanup, previous reports, preview images, batch scripts and the original settings snapshot. Main has the cleaned layout. No remote history was rewritten.

## Run and develop

Windows is required because the overlay uses Win32 APIs. Verified interpreter: CPython 3.12. Installed versions during cleanup: PyQt6 6.11.0, pywin32 312, PyQt6-Fluent-Widgets 1.11.3. `requirements.txt` declares supported ranges rather than locking this environment.

```powershell
Set-Location 'C:\Users\osama\.gemini\antigravity\scratch\fluid_cursor'
python -m pip install -r requirements.txt
python main.py
```

For daily launch, double-click `FluidCursor.exe`. It is a small C# launcher for `main.py`; keep the Python source, assets, locale and installed dependencies available. It is not a self-contained packaged Python application.

`launcher.cs` first checks this machine's Python 3.12 installation, then searches PATH for `pythonw.exe` / `python.exe`. An optional development virtual environment must be run directly because the current launcher does not automatically select `.venv`. On another machine, make a suitable interpreter available to the launcher or update/rebuild its lookup.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

| Option | Behavior |
| --- | --- |
| no option | Starts cursor/tray and opens settings |
| `--tray` | Starts without opening settings |
| `--settings` | Opens settings on a fresh launch; the default also opens settings |
| `--restore` | Restores the Windows cursor and exits |
| `--settings-process --ipc NAME` | Internal settings-child entry point; use the tray to open settings |

A named Win32 mutex enforces one resident instance. Launching again while it runs does not reload modules. Fully exit from the tray before testing changed source. The launcher manifest requests administrator access for elevated windows; ordinary automated shell checks do not request elevation.

## Project map

| File/directory | Responsibility |
| --- | --- |
| `main.py` | Arguments, single-instance mutex, lifecycle, shutdown restoration and wiring |
| `core/config.py` | Typed defaults, JSON persistence and legacy preference normalization |
| `core/win32_cursor.py` | Input queries, shortcuts, Windows cursor roles, hiding and restoration |
| `core/cursor_capture.py` | Native cloning, glyph dimensions and hotspot handling |
| `core/physics.py` | Smoothing algorithms, shrink spring, tilt and ripples |
| `core/theme.py` | Vector cursor and role artwork |
| `core/fun_modes.py`, `fun_art.py` | Fun-mode state and artwork |
| `core/chain_physics.py`, `ribbon_physics.py` | Constrained Verlet chain and ribbon solvers |
| `core/hotkeys.py`, `i18n.py`, `theme_preference.py` | Shortcut normalization, translation lookup and system-theme detection |
| `ui/overlay.py` | Click-through layered overlay, invalidation and adaptive polling |
| `ui/tray.py`, `tray_palette.py`, `tray_icon.py` | Tray actions, nonmodal popup and vector tray icon |
| `ui/settings_bridge.py` | Local newline-delimited JSON IPC |
| `ui/settings_host.py` | Disposable settings child process |
| `ui/settings_window.py`, `theme_styles.py`, `rtl_navigation.py` | Lazy settings pages, styling and RTL navigation |
| `locales/ar.json` | Arabic translations; English source strings are the fallback |
| `assets/icon.png`, `assets/icon.ico` | Required application/executable icons |
| `launcher.cs`, `app.manifest`, `build_launcher.ps1` | Single-executable launcher source, manifest and rebuild command |
| `tests/` | Regression tests, integration smoke and settings benchmark |
| `tests/manual/probe_layered_window.py` | Privileged band-16 Win32 diagnostic; excluded from normal discovery |

## Behavior to preserve

- Windows handles actual clicks. Artwork is anchored around the hotspot and snap-on-click uses the hardware coordinate. Keep the overlay click-through.
- Standard motion includes exponential, spring, smoothstep, predictive and drag. Tilt strength is clamped to 0 through 100%; delay, decay and retained rotation are independent preferences.
- Default pause/resume is F9; supported choices are F6 through F12. Retain tray pause/resume, Restore Windows Cursor and Exit recovery.
- Preserve text, link, resize and loading cursor roles. Reset `CURSORINFO.cbSize` before every `GetCursorInfo` call. Avoid expensive arbitrary cursor decoding on each frame.
- Keep `qfluentwidgets` imports outside the resident cursor/tray process. Closing settings releases its child by default; the tray can reopen it.
- Prewarm the nonmodal tray popup before hiding the native pointer. Preserve responsiveness and avoid conflicting topmost reassertions while its menu is open.
- Fun is opt-in and retains ordinary preferences for restoration. Current modes: Follower Tile, Stardust, Linked Chain, Comet, Orbit, Bouncy Yo-yo, Silk Ribbon and Fidget Spinner. Retired fish preferences migrate to Chain.
- Chain supports 6 through 32 links and pins its first segment to the pointer tail. Preserve constraint corrections in Verlet history, velocity bounds, damping and jump recovery.
- Yo-yo uses an elastic tether and click impulse; Spinner uses angular energy/friction; Ribbon uses its own pinned 18-node solver with variable-timestep substeps and click flick.
- Preserve English/Arabic layout and system/light/dark themes. Test narrow layouts, both languages and tray theme changes for UI edits.

Historical reports and synthetic benchmark figures remain on the backup branch. They contain superseded designs and earlier test counts; measure current behavior before making new performance claims.

## Preferences and cleanup

The existing `config.json` was preserved byte-for-byte and is now ignored locally. Fresh clones create defaults from `CursorConfig`; original preferences remain in the recovery branch. Set `FLUIDCURSOR_CONFIG_PATH` before starting Python to use separate test preferences. UI tests should also mock/no-op saving. Clear test overrides before normal launch.

`.gitignore` excludes bytecode, virtual environments, local preferences, logs, temporary files, archives, build directories and root preview screenshots. The root `FluidCursor.exe` is the one executable intentionally tracked. Application images belong in `assets/`; put temporary captures/logs/scripts under ignored `work/`.

Cleanup moved four bytecode-cache folders, nine obsolete root PNGs, `run.bat`, `restore_cursor.bat`, and the two superseded development reports to the Windows Recycle Bin. Source, required assets, locale and regression coverage remain. The layered-window diagnostic was moved into `tests/manual/` to keep its privileged API out of ordinary discovery.

## Verification

Run from the project root with the development interpreter:

```powershell
New-Item -ItemType Directory -Path work -Force | Out-Null
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:QT_QPA_PLATFORM = 'offscreen'
$env:FLUIDCURSOR_CONFIG_PATH = Join-Path $PWD 'work\test-config.json'
python -m unittest discover -s tests -p 'test_*.py' -v
python tests\smoke_test_app.py
git diff --check
Remove-Item Env:QT_QPA_PLATFORM,Env:FLUIDCURSOR_CONFIG_PATH,Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
```

The smoke runs 30 frames with the native pointer visible and saving disabled. Regression tests still use some Windows APIs; they are Windows checks. For focused tests, supply a specific discovery pattern such as `test_spinner_ribbon.py`. `python tests\benchmark_ui.py` is an optional settings-construction benchmark.

Offscreen results cannot prove physical cursor smoothness, real Explorer tray latency or every compositor effect. After relevant changes, manually verify click alignment, hotkeys, tray open/close, settings reopening, exit/restoration, contextual roles and monitor boundaries. Check settings at 760px and 960px, English/Arabic and light/dark themes.

Measure committed/private memory as well as working set; trimming working set alone does not prove lower allocation. Measure resident and settings child separately.

### Cleanup verification results

- Full ordinary Windows regression discovery: **126 tests passed** (141 seconds).
- Integration smoke: **30 frames completed successfully**.
- All **56 Python source files** parsed successfully; staged `git diff --check` passed.
- Launcher rebuild script compiled successfully in a temporary verification directory. That directory was recycled; the project's original executable was retained byte-for-byte.
- Exactly **one executable** remains in the project: `FluidCursor.exe`. No bytecode-cache folders or obsolete screenshots/batch launchers remain.
- Live `config.json` matched the pre-cleanup SHA-256 exactly. Application Python/C# code, dependency requirements and manifest were unchanged.
- Fixed an existing timing-dependent palette test: loading-spinner image comparisons now freeze `core.theme.time.time` so both images use the same animation phase. No application behavior was changed by this test correction.
- The privileged layered-window diagnostic and physical desktop/compositor checks were not run as part of cleanup.

## Rebuild the launcher

Rebuild only when `launcher.cs`, `app.manifest` or its icon changes. Python edits load after full app restart and do not require recompiling.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_launcher.ps1
```

The script uses the Windows .NET Framework C# compiler, embeds the icon/manifest and overwrites the root `FluidCursor.exe` in place, without an alternate executable or build directory. The existing executable was retained during cleanup.

## Back up future work

```powershell
git status --short
git diff --check
git add -A
git diff --cached --stat
git commit -m 'Describe the completed change'
git push origin main
```

Inspect staged files before committing. Commit source and relevant tests; keep live preferences/generated files local. Do not force-push or delete the recovery branch. Inspect removed files without restoring clutter:

```powershell
git show backup/pre-cleanup-2026-10-03:MASTER_POLISH_REPORT.md
git show backup/pre-cleanup-2026-10-03:config.json
```
