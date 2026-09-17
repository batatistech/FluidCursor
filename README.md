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
- **🛡️ Bulletproof System Cursor Restore**: Hides the default Windows cursor while running, and automatically restores it upon exit, app crash, or whenever you press **`F9`**.
- **⚙️ Modern Settings Control Panel & System Tray**: Sliders for smoothing, size, shrink factor, colors, and live interactive test canvas.

---

## 🚀 How to Run

### Quick Start
Double-click `run.bat` or run from PowerShell / Terminal:
```powershell
python main.py
```

To open settings directly:
```powershell
python main.py --settings
```

### Shortcuts & Controls
- **`F9`**: Instant toggle to switch between FluidCursor and standard Windows cursor anytime.
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
│   ├── overlay.py            # Transparent, 144Hz click-through fullscreen canvas
│   ├── settings_window.py    # Dark-themed control panel with interactive preview
│   └── tray.py               # System tray manager with context menu
├── main.py                   # App lifecycle, DPI awareness, crash-safe exit handlers
├── run.bat                   # 1-click launcher
└── restore_cursor.bat        # Emergency recovery script
```
