# FluidCursor development

Read `DEVELOPMENT_GUIDE.md` before editing. It is the handoff for continuing this project from a new chat.

- Preserve the user's local `config.json`; use `FLUIDCURSOR_CONFIG_PATH` for test preferences.
- Keep one application executable at the project root: `FluidCursor.exe`. Keep its Python source and required assets beside it.
- Keep caches, screenshots, logs, temporary files and build directories out of Git. Put scratch work in `work/`.
- Preserve click precision, cursor-role matching, configured hotkeys and cursor restoration on exit.
- Keep Fluent settings UI imports in the disposable settings process, outside the resident cursor/tray process.
- Use the guide's Windows regression and smoke commands after behavior changes. Report real desktop verification separately from offscreen results.
- `tests/manual/probe_layered_window.py` is a privileged Win32 diagnostic, excluded from ordinary discovery.
- Review the diff and relevant checks before committing. Do not overwrite remote history.
