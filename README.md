# ⚡ FluidCursor

A lightweight, physics-smoothed, animated cursor replacement for Windows that delivers satisfying visual fluidity while maintaining **100% click precision**.

---

## ✨ Features

- **🎯 100% Click Accuracy**: The animated visual cursor strictly anchors its hotspot at `(0, 0)` (the tip). On button press, it instantly locks to the exact hardware mouse coordinate. All clicks pass natively to Windows with zero latency or displacement.
- **🤏 Shrink on Click**: When you press any mouse button, the cursor squashes down smoothly with spring dynamics (customizable scale from 40% to 95%) and pops back with a subtle elastic bounce upon release.
- **🌊 Buttery Movement Smoothing**: Adaptive exponential smoothing (lerp) smoothly bridges mouse movements without feeling sluggish or floaty.
- **📐 Dynamic Motion Tilt**: The pointer tilts dynamically into the direction of motion based on horizontal and diagonal velocity (reminiscent of modern fluid interfaces).
- **💥 Click Shockwaves**: Expands a sleek translucent ripple ring from the exact click coordinates.
- **🎨 5 Built-in Cursor Styles**:
  - **Aero Modern**: Sleek curved pointer with subtle lighting and soft drop shadow.
  - **Neon Glow**: Cyberpunk luminous edge pointer with vibrant aura.
  - **macOS Fluid**: High-contrast monochrome pointer with rounded edges.
  - **Cyber Arrow**: Sci-Fi angular chevron.
  - **Minimalist Dot & Crosshair**: Precision gaming dot with reticle ring.
- **🛡️ Bulletproof System Cursor Restore**: Hides the default Windows cursor while running, and restores it on exit or when paused using your configurable shortcut (default **`F9`**).
- **⚙️ Responsive Settings & System Tray**: Color-coded sections, readable single-line descriptions with full tooltips, adaptive controls, and on-demand pages.
- **🖱️ Contextual cursor shapes**: Text, links and resizing use their matching cursor types by default. Unfamiliar application-owned cursors remain native to avoid duplicates; turn this off in Appearance → Match Windows cursor shapes.
- **⬛ Black tray menu**: High-contrast near-black right-click menu with subtle hover styling.
- **🧠 Low-memory tray mode**: The settings panel runs in a separate process and exits on close when "Release settings when closed" is enabled. Its Fluent libraries do not remain loaded in the cursor/tray process.

---

See [MASTER_POLISH_REPORT.md](MASTER_POLISH_REPORT.md) for the UI performance benchmarks, regression checklist and feature-development guardrails.

## 🎮 Fun! (opt-in)

Open Settings > **Fun!** to choose Follower Tile, Stardust, Linked Chain, Comet, Orbit, Bouncy Yo-yo or Silk Ribbon. Fun has independent controls and restores your normal cursor preferences when turned off. Chain supports 6?32 links, momentum and a separate liveliness control. Yo-yo bounces on click; Ribbon flows behind the pointer. See [FUN_MODES.md](FUN_MODES.md).

## 🚀 How to Run

### Quick Start
Double-click `run.bat` or run from PowerShell / Terminal:
```powershell
python main.py
```

Install dependencies first with `python -m pip install -r requirements.txt`. The `FluidCursor.exe` launcher also runs `main.py` from this folder.

To open settings directly:
```powershell
python main.py --settings
```

For a tray-only launch (without constructing the settings window until needed), run `python main.py --tray`. Closing settings releases its process by default; double-click the tray icon to reopen. The Python/Qt overlay still needs memory while running; working-set trimming does not reduce the application's committed allocation. Restart an older running instance to use the new split-process architecture.

### Shortcuts & Controls
- **`F9`** by default: Toggle FluidCursor. Change it to F6?F12 under System & recovery > Keyboard shortcut. Tray recovery always remains available.
- **System Tray**: Right-click the FluidCursor icon near the Windows clock to open Settings, pause/resume, or exit.
- **Emergency Restore**: Run `restore_cursor.bat` or `python main.py --restore` to reset Windows cursors immediately.

---

## 📁 Architecture

```
fluid_cursor/
├── config.json               # Persisted user preferences
├── core/
│   ├── win32_cursor.py       # Win32 APIs: hide/restore system cursor, GetCursorPos, GetAsyncKeyState
│   ├── physics.py            # Exponential lerp, spring-damper scale, dynamic tilt, ripples
│   ├── theme.py              # High-DPI vector renderers anchored strictly at tip (0, 0)
│   └── config.py             # Typed dataclass config with JSON persistence
├── ui/
│   ├── overlay.py            # Click-through native layered window; skips unchanged frames
│   ├── settings_window.py    # Readable color-coded settings pages and responsive controls
│   ├── settings_host.py      # Disposable GUI process (released on close)
│   ├── settings_bridge.py    # Local IPC for live updates without resident Fluent UI
│   └── tray.py               # System tray manager with context menu
├── main.py                   # App lifecycle, DPI awareness, crash-safe exit handlers
├── run.bat                   # 1-click launcher
└── restore_cursor.bat        # Emergency recovery script
```
