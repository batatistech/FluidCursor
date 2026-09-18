"""
Configuration manager for FluidCursor.
Persists settings to config.json and provides typed configuration data.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

@dataclass
class CursorConfig:
    enabled: bool = True
    enable_advanced_physics: bool = False # Master toggle for advanced physics engine (Disabled by default)
    smoothing_type: str = "exponential" # exponential, spring, smoothstep, predictive, drag
    responsiveness: float = 0.38        # Smoothing factor: 0.05 (floaty) -> 1.0 (snappy)
    spring_stiffness: float = 280.0     # Spring tension (50 to 600)
    spring_damping: float = 24.0        # Spring friction/damping (8 to 60)
    prediction_factor: float = 0.025    # Predictive look-ahead lead factor (0.005 to 0.08)
    drag_friction: float = 18.0         # Kinematic drag friction (5 to 45)
    drag_boost: bool = False            # Maximize precision while dragging/clicking (Disabled by default)
    shrink_factor: float = 0.72         # Scale down factor when clicked (0.4 to 0.95)
    snap_on_click: bool = True          # Instant snap to hardware position on click for 100% accuracy
    tilt_enabled: bool = True           # Dynamic tilt in movement direction
    tilt_mode: str = "velocity"         # "velocity", "physics_forward", "physics_opposing"
    tilt_strength: float = 1.0          # Multiplier for tilt angle (0.1 to 5.0)
    tilt_deadzone: float = 35.0         # Slow movement deadzone threshold in px/s to prevent low-speed jitter (0 to 120 px/s)
    tilt_decay_enabled: bool = True     # Slowly return cursor to original resting rotation instead of snapping
    tilt_decay_speed: float = 0.5       # Smoothness / duration of rotation return (0.1 to 1.0; higher = slower, smoother decay)
    tilt_delay_enabled: bool = True     # Return to original rotation after delay rather than immediately correcting
    tilt_return_delay: float = 0.35     # Delay before returning in seconds (0.05 to 2.0s / 50ms to 2000ms)
    tilt_disable_return: bool = False   # Disable returning to original position (maintain tilt angle indefinitely)
    ripples_enabled: bool = True        # Click ripple shockwave animation
    trail_enabled: bool = False         # Motion trail ghosting
    hide_system_cursor: bool = True     # Hides Windows default cursor
    show_precision_dot: bool = False    # Tiny pixel dot at exact hardware coordinates (Disabled by default)
    precision_dot_white_outline: bool = False # Crisp white outline around precision dot (Disabled by default)
    cursor_size: int = 28               # Cursor size in pixels (16 to 64)
    cursor_theme: str = "aero_modern"   # aero_modern, neon_glow, macos_fluid, minimal_dot, cyber_arrow
    use_system_cursor_clone: bool = True # Clone and animate active Windows cursor
    primary_color: str = "#FFFFFF"      # Inner fill color
    border_color: str = "#1E293B"       # Outer stroke color
    ripple_color: str = "#00D2FF"       # Click ripple color
    toggle_hotkey: str = "F9"           # Hotkey to toggle on/off
    ram_optimization_mode: bool = True  # Aggressive RAM mode: destroys GUI when minimized & trims working set

    @classmethod
    def load(cls, path: str = DEFAULT_CONFIG_PATH) -> 'CursorConfig':
        if not os.path.exists(path):
            config = cls()
            config.save(path)
            return config
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Filter unknown keys to prevent crashes on schema changes
            valid_keys = cls.__dataclass_fields__.keys()
            filtered_data = {k: v for k, v in data.items() if k in valid_keys}
            return cls(**filtered_data)
        except Exception:
            return cls()

    def save(self, path: str = DEFAULT_CONFIG_PATH):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")
