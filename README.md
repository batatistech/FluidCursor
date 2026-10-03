# FluidCursor

An animated Windows cursor with smoothing, tilt, click shrink/ripples, contextual cursor shapes, optional cursor toys, and English/Arabic settings.

## Launch

Double-click **FluidCursor.exe**. It is the only application executable in this project and opens the cursor/tray app with its settings panel.

The executable launches `main.py`; it requires the surrounding source, assets and an installed Python environment. Python 3.12 is the verified development version. Install dependencies once:

```powershell
python -m pip install -r requirements.txt
```

The launcher requests administrator access for elevated Windows applications. See `launcher.cs` and `app.manifest` for interpreter lookup and privilege behavior.

## Controls and recovery

- **F9** pauses/resumes by default; choose F6 through F12 in System & recovery.
- Right-click the tray icon for settings, pause/resume, **Restore Windows Cursor**, or Exit.
- Closing settings releases its process by default; cursor/tray continues running.
- Exit from the tray before relaunching after source changes.

Developer/recovery commands from this folder:

```powershell
python main.py --tray
python main.py --settings
python main.py --restore
```

`--restore` resets the Windows cursor and exits. The same option can be passed to `FluidCursor.exe`.

## Continue development

Read [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) for architecture, setup, testing, launcher rebuilding and a prompt for a new chat. `AGENTS.md` points development agents to that guide.

The project is backed up at [batatistech/FluidCursor](https://github.com/batatistech/FluidCursor). The [pre-cleanup recovery branch](https://github.com/batatistech/FluidCursor/tree/backup/pre-cleanup-2026-10-03) preserves old screenshots, reports, scripts and the original settings snapshot. Current local preferences remain in ignored `config.json`; fresh checkouts create defaults from `core/config.py`.
