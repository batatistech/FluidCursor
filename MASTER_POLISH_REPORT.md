# FluidCursor — UI master-polish handoff

Date: 2026-09-20. Scope: settings UX, scrolling, navigation and regression safety; no cursor physics or configuration schema migration.

## Changes

- Replaced the oversized, blank Motion page hint with a fixed 66 px navigation card. The **Open Tilt** button switches to the correct page and remains keyboard accessible.
- Advanced motion settings now use progressive disclosure: when the advanced engine is off, its controls are hidden; when enabled, only the current algorithm's applicable controls are displayed. Drag accuracy remains independently accessible.
- Shortened algorithm choices and help text, improving clarity in narrower windows. Existing config enum values and behavior are unchanged.
- Disabled the Fluent scroll animation on all settings pages, retaining the native Qt mouse-wheel and precision-trackpad handling. This eliminates a long animated delay and reduces repeated repaints while scrolling.
- Replaced per-card resize callbacks and repeated queued label layout passes with one 55 ms coalescing timer. The existing elision and tooltip behavior remains available.
- Kept the prior page-level accent colors, section icons, readable fixed-height setting rows, deferred page construction and disposable settings process.

## Reproducible performance evidence

The scroll benchmark uses a single synthetic mouse-wheel notch on the Tilt page in Qt offscreen mode. Before: wheel was initially stationary, then progressed through 22 scrollbar updates to 96 px in roughly 625 ms. After: 96 px immediately with one scrollbar update, remaining at 96 px after 625 ms. These are synthetic event measurements, **not** an FPS or real-world subjective smoothness guarantee.

One offscreen construction comparison: approximately 321 ms before versus 260 ms after. This is a single-run comparison; machine load and font rendering can vary. Settings RAM architecture from the preceding pass remains unchanged.

## Feature-development guardrails

- Preserve the existing `core/` physics, Windows cursor capture and recovery interfaces. F9, click precision and restoration are safety-critical and require regression checks after edits.
- Add new settings by extending `CursorConfig` with defaults; keep settings and overlay IPC updates in sync. Avoid touching `config.json` during UI tests; use a fresh config with `save` replaced by a no-op.
- Add controls to the appropriate lazy-created page in `ui/settings_window.py`. Respect the available width at 760 px and 960 px, and verify that no horizontal scrollbar appears.
- For controls that only apply to one algorithm, show them only when relevant. Keep dependent options disabled when their parent switch is off; retain all settings when hidden.
- The standalone settings UI (`ui/settings_host.py`) runs in a child process while the cursor/tray parent stays alive. Closing the settings window should exit only the child process; opening from the tray should launch it again.
- Keep navigation cards fixed-size or bounded. Do not let a secondary info card stretch to fill a page; verify with a visual capture and a height regression test.

## Verification and limitations

Automated checks: `python -m unittest discover -s tests -p test_master_polish.py -v` and the existing targeted UI, tilt, tray-memory, IPC and overlay tests. Integration smoke: `python tests/smoke_test_app.py`. Real-monitor wheel/trackpad feel and text rendering should be checked manually after relaunch; offscreen screenshots do not reproduce every Windows compositor effect.

Backup preceding this pass: `C:\Users\osama\.gemini\antigravity\scratch\fluid_cursor_backup_master_polish_20260920`. The live user configuration was not reset. Restart the running tray app to load these Python source changes.

Final automated run after the label changes: **31 targeted tests passed**, plus the **30-frame integration smoke test**. New cases cover native immediate scrolling, the functional Tilt shortcut, algorithm-dependent control visibility and compact-width overflow. `git diff --check` passed. The pre/post-run SHA-256 of the live `config.json` was identical.

## Follow-up: cursor roles and black tray menu (2026-09-20)

- Tray right-click menu now uses an explicit near-black (`#09090B`) palette and stylesheet, with white text, subdued separators and a dark hover state. Verified with a screenshot of the rendered Qt menu.
- Added `match_cursor_roles: bool = True` to `CursorConfig`. Existing JSON files missing this setting automatically retain the default; the live config was not overwritten.
- **Appearance → Match Windows cursor shapes** toggles text-beam, hand/link, resize and other contextual cursor behavior. Changes propagate to the cursor/tray process through the existing IPC without a restart after the updated app has launched.
- `GetCursorInfo` now distinguishes unfamiliar cursor handles rather than silently classifying them as the standard arrow. Standard Windows cursor roles use their matching vector or pre-captured native shapes.
- Unfamiliar application-owned cursors are captured and cached by handle. If Windows is already showing that native cursor, the overlay does not draw a second pointer; if the native shape is not visible, the overlay can render the captured shape. Fully transparent captures fall back to the visible standard pointer.
- Wait/loading cursors repaint their spinner phase while active, without enabling perpetual repaints for an idle normal pointer.
- The role toggle affects the overlay immediately, is saved by the existing debounced settings workflow, and is carried through the typed local IPC settings update.

Verification: **43 targeted unit/integration tests passed**, including seven cursor-role tests; 30-frame application smoke, Python compilation and `git diff --check` also passed. The pre/post SHA-256 of `config.json` matched. Actual text/link/resize behavior in individual third-party programs still requires a manual desktop check, because those programs may supply custom cursor handles.

Backup preceding these edits: `C:\Users\osama\.gemini\antigravity\scratch\fluid_cursor_backup_cursor_roles_20260920_0507`. Exit the existing FluidCursor tray process completely and relaunch to load source changes.

## Cursor roles: verified corrective fix (2026-09-20)

User-reported regression: the cursor remained an arrow over text, links and resize edges despite the earlier role-rendering changes. A Windows API diagnostic reproduced the root cause: after its first successful call, `GetCursorInfo` zeroed the reusable `CURSORINFO.cbSize` input field. Every subsequent call failed with Win32 error 87 (`ERROR_INVALID_PARAMETER`), and the role detector silently returned `normal`.

`core/win32_cursor.py` now resets `cbSize` to `sizeof(CURSORINFO)` immediately before **every** query. A real Qt test window demonstrated arrow, I-beam, hand and horizontal-resize detection after Windows cursors were hidden; the probe restored the original system cursor and mouse position in `finally`. Two new automated tests simulate the Windows field mutation and exercise the full overlay role-routing path across successive frames.

Verification: 45 targeted tests, the 30-frame application smoke test, compilation and `git diff --check` all passed. Live `config.json` SHA-256 was unchanged. The existing role matching option remains enabled. Restart FluidCursor fully from the tray to reload its resident process; confirm the actual behavior in your browser and editor. Backup: `C:\Users\osama\.gemini\antigravity\scratch\fluid_cursor_backup_role_detection_fix_20260920`.

## Cursor geometry and tray responsiveness pass (2026-09-20)

- Measured the installed cloned pointer at a 32x32 canvas with 21 px of visible ink; the installed I-beam used a 128x128 canvas with 62 px of visible ink. The cloner now normalizes unusually tall I-beams *once at startup*, using visible glyph height rather than canvas size, and scales the hotspot with the image. Its visible height is now 24 px while the pointer remains 21 px; float hotspots are drawn through `QPointF` to retain correct alignment.
- Reworked the non-cloned link hand with a recognizable finger, thumb, knuckle separators and clear dark outline. Refined the non-cloned I-beam with balanced serifs and contrasting strokes. Swapped the diagonal resize rotations: NW-SE descends right; NE-SW ascends right. A vector preview and geometry-based regression test confirm these directions.
- Removed all synchronous decoding of unfamiliar cursor handles from the 7 ms overlay tick. Unrecognized app cursors that remain natively visible are left alone; an invisible, unrecognized cursor falls back to a known pointer. This avoids performing expensive bitmap extraction on the UI thread during tray interactions. While the tray menu is open, the overlay also skips its periodic topmost reassertion so it does not compete with Explorer's menu.
- Regression coverage checks ink proportions, cloned rendering with fractional hotspots, the two diagonal orientations, absence of custom cursor capture in successive ticks, and pause/resume of z-order maintenance during tray menu opening. Existing F9, cursor recovery, IPC and UI tests remain in place.
- **Verification:** 50 targeted tests passed, the 30-frame smoke test passed, compileall passed, git diff --check passed and the user's config.json SHA-256 was unchanged against the pre-edit backup.
- **Limit:** The right-click delay was mitigated at two likely synchronous UI paths, but the actual Explorer tray right-click latency on the user's desktop has not been measured with physical interaction. Recheck after completely exiting the old tray process and relaunching. If a delay remains, capture a timed real-session trace before claiming the issue resolved.

Backup: `C:\Users\osama\.gemini\antigravity\scratch\fluid_cursor_backup_polish_20260920_053217`.

## Tray interaction and hand-tilt follow-up (2026-09-20)

- The vector link hand now uses the full physics rotation rather than scaling it to 60%, allowing the finger to point down during downward steering; the native clone path remains unchanged.
- The tray now handles Context activation itself and queues the near-black popup on the following Qt event-loop turn, rather than invoking Qt's synchronous Windows tray-context-menu path. `aboutToShow`/`aboutToHide` still guard overlay z-order operations.
- Overlay input polling remains 7 ms while the cursor moves, drops to 30 ms after twelve identical frames, and uses 25 ms while the tray menu is visible. Movement returns it to 7 ms. The system cursor is never hidden/restored merely to show the menu.
- Synthetic context-menu timing: menu-show callback approximately 7 ms after context activation. This does not measure the actual Explorer mouse callback or prove the reported real-world pause is gone; verify with a physical tray right-click after restarting.
- New regression tests cover the queued popup, down-tilt rendering, and active/idle/menu polling. 53 targeted automated tests passed and the 30-frame smoke test exited successfully. User `config.json` hash unchanged.
- Backup: `C:\Users\osama\.gemini\antigravity\scratch\fluid_cursor_backup_tray_hand_20260920_054533`. Fully exit and relaunch the running tray process before testing.

## Fun! extension — 2026-09-20

Added a new deferred, gold-accented **Fun!** page with an opt-in master switch and three exclusive modes: Swimming Fish (directional spring movement and bounded bubbles), Follower Tile (a companion tile behind a fixed-size pointer), and Stardust (a gold star with transient sparkles). Controls appear only for the selected mode. Existing appearance/motion/click preferences are left unchanged and resume when Fun! is disabled. No new dependency, service or permanent desktop-sized overlay is introduced.

Safety: native mouse input is never intercepted, click snapping is forced in Fun!, F9/restore paths are preserved, and the original Windows cursor is hidden only while the effect is active (or if the original preference already requires hiding). Unknown visible app-owned cursors are left native rather than rendering duplicates. Particle lifetime is limited to 0.75 seconds and count to 16, inside the existing 192×192 overlay.

Final targeted verification: **60 automated tests passed**, plus the existing **30-frame smoke test**; user `config.json` is byte-for-byte unchanged versus the pre-feature backup. New tests cover persistence/default-off, exclusive mode resets, particle bounds, physics override without preference mutation, hide/restore behavior, mode rendering and 760/960-pixel settings width. Preview images were generated in Qt offscreen mode; actual-monitor fish aesthetics and Windows compositor performance still require the user's live check after relaunch. See `FUN_MODES.md`.

## Fun lab — smoothness, exclusivity and visual redesign (September 20, 2026)

Added independent Fun-only `fun_smoothness` (0–100%; default 55) to configuration, spring physics, fish heading and tile follow response. Replaced the mode combobox with three illustrated, color-coded selection cards, reduced redundant master controls to a single switch inside an always-visible status banner, and added explicit active/paused/standard mode messaging. While Fun is enabled, Essentials, Appearance, Motion, Click effects and Tilt sections are disabled; System & recovery remains accessible, and normal preferences remain stored without mutation. Sliders for irrelevant effects are hidden and all Fun sliders are inactive while Fun is off.

Verification: 64 selected regression tests passed; 30-frame smoke test passed; compileall and git diff --check succeeded. Offscreen UI preview inspected at 960×740; earlier compact-size tests detected no horizontal overflow. Normal cursor preferences were compared against a pre-change backup and remain identical. Fun values changed while the live settings window was open, so they were not overwritten by an automated restoration. The current running app must be fully restarted for updated Python modules to load. Manual desktop smoothness check remains necessary.

2026-09-20 tray FPS fix: removed menu-specific 25 ms polling cap. Asynchronous tray popup and z-order suspension retained; active motion continues at 7 ms, unchanged idle frames still poll at 30 ms outside the menu. Updated tray regression, verified 15 focused tests and 30-frame smoke test. Restart resident process to apply.

### Tray responsiveness and premium Fun expansion — 2026-09-20

Reproduced the right-click regression with a 7 ms heartbeat: the first QMenu popup blocked the event loop for 485–515 ms, including without an active overlay. Replaced QMenu with a non-modal, black QWidget tray palette and prewarmed its first native show **before** enabling the overlay. A repeat benchmark with the overlay active recorded approximately 7 ms intervals while the tray panel was opening and visible; the first-show cost moved into startup and is not eliminated. Preserved outside-click/activation dismissal, action routing, F9 and recovery.

New `core/fun_art.py` provides higher-detail gradient fish, translucent bubbles, improved tile/star, comet, orbit, and a linked-chain illustration. `core/fun_modes.py` adds bounded chain simulation, heterogeneous bubble movement, three new modes, and mode-aware repaint keys. The centered 288×288 overlay accommodates the longer chain. Settings now show six illustrated choices in a compact two-column grid with Chain length (6–16) and Satellites (2–6) sliders. Both are persisted independently, with ordinary preferences unchanged. Synthetic QImage rendering-only timings at 16 particles were 1.17 ms p95 for fish, 0.59 ms for Stardust, 0.56 ms for Comet; chain was 0.75 ms p95. These are not end-to-end cursor FPS measurements.

Regression coverage includes UI layout at 760/960 widths, all six renderers, chain constraints, bubble lifecycle, existing cursor roles, emergency recovery and tray responsiveness. A live user desktop check is still needed for the real system tray and visual feel.

## Status / chain / icon revision
The current five Fun modes supersede the earlier six-mode descriptions in this historical report. The fish artwork and UI were removed, with old fish preferences migrated to Chain at load. Chain uses constrained Verlet momentum and pins its first segment to the rendered arrow stem. The Essentials status card is now two rows. The tray icon is a programmatic white arrow with a thin black outline and transparent background; app icon unchanged. User config preserved.


## Shortcut / chain / visual refresh (2026-09-20)

Current behavior supersedes historical notes above: status is now a 56px single-row strip; the tray icon is supersampled white-on-transparent with a dark outline; the non-cloned hand has a compact vector silhouette. Tilt strength is 0?100% and legacy values above 100% are clamped on load. System & recovery offers F6?F12 shortcuts; default is F9 and the resident overlay now polls the configured key (edge-triggered). Chain supports 6?32 links, adjustable liveliness and a 480px canvas only when more than 16 links are selected. Its solver uses constrained bidirectional Verlet positions, damping, gravity, jump recovery and a permanently pinned arrow-tail attachment. Bouncy Yo-yo and Silk Ribbon are new interaction-driven Fun modes; they are not particle variants. Prior fish mode remains retired. Backups were taken before editing and the original config is left untouched by development.

## Settings text / chain stability / resident memory — 2026-09-20

- Settings labels are no longer permanently elided before Qt assigns their final widths. Full descriptions wrap, card heights are measured from actual text geometry, and an initial delayed layout pass handles sidebar expansion. Checked 760px and 960px layouts.
- Chain: the solver now carries position-correction adjustments into its Verlet history; previously constraint corrections became phantom velocity on subsequent frames, creating exaggerated whiplash. Added velocity bounds and controlled swing damping while retaining exact cursor-tail attachment and 6–32 linked segments.
- Deterministic 32-link, 150px mouse sweep/stop diagnostic: old chain maximum end displacement 61.85px per frame, end error 50.0px after 700 frames; revised chain 4.69px per frame, end error 0.01px. Physics-only p95 0.466ms before, 0.491ms after. Synthetic results are not a live-display FPS guarantee.
- Memory attribution from a separate safe, simulated tray/overlay run: Python alone 6.23MB private; Qt application baseline 12.80MB private; overlay and tray 23.54MB private (working set 45.41MB). This is not a measurement of the user's actual installed running instance. A large reduction below ~20MB private is not credible without a separately scoped native-service rewrite; avoid working-set trimming as a substitute for real private-memory reduction.
- User configuration is backed up and restored byte-for-byte after test previews. Emergency restore and live Windows user interaction require final validation on the desktop.
