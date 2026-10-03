# Fun! ? exclusive effects

Fun overrides normal appearance and motion only while enabled. Your standard settings are retained. System & recovery stays unlocked. Clicks still use the actual Windows mouse location.

- Follower Tile: a separate physics follower.
- Stardust: a star and a bounded trail.
- Linked Chain: 6?32 constrained Verlet links, a real arrow with a tail attachment, simulated weight and adjustable liveliness. The overlay expands only for long chains.
- Comet: a glowing cursor and short trail.
- Orbit: adjustable satellites.
- Bouncy Yo-yo: an elastic tether with a weighted ball. Click to launch it.
- Silk Ribbon: a tapered, continuously deforming strip. Click to add a short wave.

The independent smoothness control applies only to Fun. Change your pause/resume key in System & recovery (F6?F12, F9 by default). The tray has permanent Restore Windows Cursor and Exit commands.

After changing source code, fully quit the previous tray process and restart. Verify live movement, the tray menu, click alignment, other cursor roles and multi-monitor edges. Unit tests and Qt offscreen previews cannot prove physical desktop smoothness.

## Yo-yo, Spinner and Silk Ribbon (September 2026)

- **Bouncy Yo-yo:** A two-rim yo-yo with a visible axle and elastic string. Click to launch it; its own string-length control limits the distance from the cursor.
- **Fidget Spinner:** A three-lobed, vector-drawn spinner beside the pointer. Mouse movement imparts angular momentum, clicking boosts rotation, and friction lets it coast to a stop. Its Spin energy slider is independent of normal cursor physics.
- **Silk Ribbon:** Uses a separate 18-node pinned Verlet cloth strip with variable-timestep substeps, fixed segment lengths, damping, gravity and a click-triggered flick. The Ribbon flow slider varies liveliness, and the artwork uses smoother curved edges.

All three remain exclusive Fun effects; standard cursor preferences and the Windows mouse hotspot are not altered. Tests cover persistence, animation, UI controls, variable frame timing and jump recovery. Restart the resident tray process to load changed source code.
