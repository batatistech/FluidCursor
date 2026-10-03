"""
Physics engine for FluidCursor.
Handles:
- Dynamic exponential smoothing (lerp) and spring dynamics
- Real-time velocity tracking and dynamic motion tilt
- Click shrink & elastic bounce animation
- Click accuracy enforcement (instant snap/convergence on click)
- Click shockwave ripples
"""

import math
import time
from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class ClickRipple:
    x: float
    y: float
    radius: float = 4.0
    max_radius: float = 38.0
    progress: float = 0.0  # 0.0 -> 1.0
    color: Tuple[int, int, int] = (255, 255, 255)
    line_width: float = 2.5

    def update(self, dt: float) -> bool:
        """Updates ripple state. Returns False when ripple expires."""
        speed = 4.0  # complete in ~0.25s
        self.progress += speed * dt
        if self.progress >= 1.0:
            return False
        self.radius = 4.0 + (self.max_radius - 4.0) * math.sin(self.progress * math.pi / 2)
        return True

    @property
    def current_alpha(self) -> float:
        """Fades out smoothly as progress reaches 1.0."""
        return max(0.0, 1.0 - self.progress)


class CursorPhysics:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        # Position states
        self.x: float = x
        self.y: float = y
        self.target_x: float = x
        self.target_y: float = y
        self.prev_hw_x: float = x
        self.prev_hw_y: float = y

        # Velocity states
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.hw_vx: float = 0.0
        self.hw_vy: float = 0.0
        self.speed: float = 0.0

        # Motion tilt
        self.tilt_angle: float = 0.0       # Current degrees
        self.target_tilt: float = 0.0      # Target degrees
        self.held_tilt_target: float = 0.0 # Held degrees during return delay
        self.motion_heading = None  # Circularly smoothed direction, in degrees
        self.tilt_dir_x: float = 0.0       # Dedicated recent hardware direction vector
        self.tilt_dir_y: float = 0.0       # Avoids X/Y staircase jitter on diagonal strokes
        self.tilt_motion_samples = []       # Short rolling hardware displacement history
        self.held_raw_dir: float = 0.0     # Raw heading/direction of held stroke
        self.last_motion_time: float = time.perf_counter() # Timestamp of latest active movement

        # Scale states ("shrink on click")
        self.scale: float = 1.0
        self.target_scale: float = 1.0
        self.scale_velocity: float = 0.0

        # Click state
        self.is_left_down: bool = False
        self.is_right_down: bool = False
        self.was_any_down: bool = False

        # Ripples
        self.ripples: List[ClickRipple] = []

        # Motion Trail
        self.trail_points: List[Tuple[float, float, float]] = []  # (x, y, age)

        # Timing
        self.last_time = time.perf_counter()

    def update(
        self,
        hw_x: int,
        hw_y: int,
        left_down: bool,
        right_down: bool,
        middle_down: bool,
        enable_advanced_physics: bool = False,
        smoothing_type: str = "exponential",
        responsiveness: float = 0.38,
        spring_stiffness: float = 280.0,
        spring_damping: float = 24.0,
        prediction_factor: float = 0.025,
        drag_friction: float = 18.0,
        drag_boost: bool = False,
        shrink_factor: float = 0.72,
        tilt_enabled: bool = True,
        tilt_mode: str = "velocity",
        tilt_strength: float = 1.0,
        tilt_deadzone: float = 35.0,
        tilt_decay_enabled: bool = True,
        tilt_decay_speed: float = 0.5,
        tilt_delay_enabled: bool = True,
        tilt_return_delay: float = 0.35,
        tilt_disable_return: bool = False,
        ripples_enabled: bool = True,
        snap_on_click: bool = True,
        trail_enabled: bool = False,
        ripple_color: Tuple[int, int, int] = (100, 200, 255)
    ):
        """
        Advances the physics simulation by elapsed dt using the chosen smoothing model.
        """
        now = time.perf_counter()
        dt = min(max(now - self.last_time, 0.001), 0.05)
        self.last_time = now

        self.target_x = float(hw_x)
        self.target_y = float(hw_y)

        # Estimate hardware mouse velocity for predictive extrapolation & inertia
        hw_dx = self.target_x - self.prev_hw_x
        hw_dy = self.target_y - self.prev_hw_y
        hw_dist = math.hypot(hw_dx, hw_dy)
        hw_raw_vx = hw_dx / dt
        hw_raw_vy = hw_dy / dt
        vel_filter = 1.0 - math.exp(-24.0 * dt)
        self.hw_vx += (hw_raw_vx - self.hw_vx) * vel_filter
        self.hw_vy += (hw_raw_vy - self.hw_vy) * vel_filter
        self.prev_hw_x = self.target_x
        self.prev_hw_y = self.target_y

        any_down = left_down or right_down or middle_down
        just_pressed = any_down and not self.was_any_down
        just_released = not any_down and self.was_any_down

        # 1. Click Accuracy Enforcement & Shrink trigger
        if just_pressed:
            if snap_on_click:
                # Snap instantly to the native hardware click coordinate
                self.x = self.target_x
                self.y = self.target_y
                self.vx = 0.0
                self.vy = 0.0

            # Target shrink scale
            self.target_scale = shrink_factor
            
            # Spawn ripple at the exact click point
            if ripples_enabled:
                self.ripples.append(
                    ClickRipple(
                        x=self.target_x,
                        y=self.target_y,
                        max_radius=42.0,
                        color=ripple_color
                    )
                )
        elif just_released:
            # Pop back to normal scale
            self.target_scale = 1.0

        self.is_left_down = left_down
        self.is_right_down = right_down
        self.was_any_down = any_down

        # 2. Position Smoothing Algorithms
        if just_pressed and snap_on_click:
            # Firmly anchored to exact hardware position on click frame
            self.x = self.target_x
            self.y = self.target_y
            self.vx = 0.0
            self.vy = 0.0
        else:
            active_resp = responsiveness
            if any_down and drag_boost:
                # Maximize responsiveness during click & drag for zero cursor slip
                active_resp = min(1.0, responsiveness * 1.6 + 0.25)

            prev_x, prev_y = self.x, self.y

            active_algo = smoothing_type if enable_advanced_physics else "exponential"

            if active_algo == "spring":
                # 2nd-Order Spring-Damper / Elastic Harmonic Oscillator
                k = spring_stiffness * (1.8 if (any_down and drag_boost) else 1.0)
                c = spring_damping * (1.4 if (any_down and drag_boost) else 1.0)
                force_x = -k * (self.x - self.target_x) - c * self.vx
                force_y = -k * (self.y - self.target_y) - c * self.vy
                self.vx += force_x * dt
                self.vy += force_y * dt
                self.x += self.vx * dt
                self.y += self.vy * dt

                # Safety guard against extreme divergence
                dist = math.hypot(self.x - self.target_x, self.y - self.target_y)
                if dist > 800.0:
                    self.x = self.target_x
                    self.y = self.target_y
                    self.vx = 0.0
                    self.vy = 0.0

            elif active_algo == "smoothstep":
                # Distance-Adaptive Sigmoidal Ease Curve
                dist = math.hypot(self.target_x - self.x, self.target_y - self.y)
                t = min(1.0, max(0.0, dist / 260.0))
                ease = t * t * (3.0 - 2.0 * t)  # SmoothStep curve
                effective_resp = active_resp * (0.55 + 0.9 * ease)
                smooth_rate = -math.log(max(1.0 - min(0.99, effective_resp), 0.001)) * 60.0
                lerp_amount = max(0.01, min(1.0, 1.0 - math.exp(-smooth_rate * dt)))
                self.x += (self.target_x - self.x) * lerp_amount
                self.y += (self.target_y - self.y) * lerp_amount
                self.vx = (self.x - prev_x) / dt
                self.vy = (self.y - prev_y) / dt

            elif active_algo == "predictive":
                # Velocity Look-Ahead Extrapolation (Compensates display & input latency)
                lead_x = self.target_x + self.hw_vx * prediction_factor
                lead_y = self.target_y + self.hw_vy * prediction_factor
                smooth_rate = -math.log(max(1.0 - active_resp, 0.001)) * 60.0
                lerp_amount = max(0.01, min(1.0, 1.0 - math.exp(-smooth_rate * dt)))
                self.x += (lead_x - self.x) * lerp_amount
                self.y += (lead_y - self.y) * lerp_amount
                self.vx = (self.x - prev_x) / dt
                self.vy = (self.y - prev_y) / dt

            elif active_algo == "drag":
                # Kinematic Drag with Air Friction
                accel_rate = 70.0 * active_resp
                friction = max(2.0, drag_friction)
                dx = self.target_x - self.x
                dy = self.target_y - self.y
                self.vx += (dx * accel_rate - self.vx * friction) * dt
                self.vy += (dy * accel_rate - self.vy * friction) * dt
                self.x += self.vx * dt
                self.y += self.vy * dt

            else:
                # Default: Adaptive Exponential Lerp
                smooth_rate = -math.log(max(1.0 - active_resp, 0.001)) * 60.0
                lerp_amount = max(0.01, min(1.0, 1.0 - math.exp(-smooth_rate * dt)))
                self.x += (self.target_x - self.x) * lerp_amount
                self.y += (self.target_y - self.y) * lerp_amount
                self.vx = (self.x - prev_x) / dt
                self.vy = (self.y - prev_y) / dt

            self.speed = math.hypot(self.vx, self.vy)

        # 3. Scale Spring Physics ("shrink on click" with elastic bounce)
        spring_k = 320.0   # stiffness
        damping_c = 24.0   # damping
        displacement = self.scale - self.target_scale
        spring_force = -spring_k * displacement - damping_c * self.scale_velocity
        self.scale_velocity += spring_force * dt
        self.scale += self.scale_velocity * dt
        self.scale = max(0.3, min(1.3, self.scale))

        # 4. Motion Tilt Dynamics
        if tilt_enabled and abs(tilt_strength) > 0.01:
            speed = self.speed
            hw_speed = math.hypot(self.hw_vx, self.hw_vy)
            neutral_angle = -112.2  # Resting pointer heading (~22.5Â° left of North)

            deadzone = max(0.0, tilt_deadzone)
            deadzone_span = max(18.0, deadzone * 0.6)
            full_speed_threshold = deadzone + deadzone_span

            # Active motion requires physical displacement or filtered speed above slow-movement deadzone
            is_active_move = (hw_dist > 0.15 or hw_speed > deadzone) and (speed > deadzone)

            if is_active_move:
                self.last_motion_time = now

                # Track direction separately from speed. Windows quantises smooth
                # diagonal motion into alternating X/Y pixel steps. A short rolling
                # displacement vector reconstructs the physical stroke direction.
                if hw_dist > 0.15:
                    self.tilt_motion_samples.append((hw_dx, hw_dy))
                    if len(self.tilt_motion_samples) > 8:
                        del self.tilt_motion_samples[0]

                if self.tilt_motion_samples:
                    dir_x = sum(v[0] for v in self.tilt_motion_samples)
                    dir_y = sum(v[1] for v in self.tilt_motion_samples)
                    norm = math.hypot(dir_x, dir_y)
                    if norm > 1e-6:
                        self.tilt_dir_x, self.tilt_dir_y = dir_x / norm, dir_y / norm

                if abs(self.tilt_dir_x) + abs(self.tilt_dir_y) > 1e-6:
                    measured_angle = math.degrees(math.atan2(self.tilt_dir_y, self.tilt_dir_x))
                else:
                    measured_angle = math.degrees(math.atan2(self.hw_vy, self.hw_vx))

                if self.motion_heading is None:
                    self.motion_heading = measured_angle
                else:
                    turn = ((measured_angle - self.motion_heading + 180.0) % 360.0) - 180.0
                    # Tiny changes are pixel quantisation; deliberate turns remain fast.
                    if abs(turn) > 0.65:
                        steer_rate = 30.0 if abs(turn) > 24.0 else 20.0
                        self.motion_heading += turn * (1.0 - math.exp(-steer_rate * dt))
                move_angle = self.motion_heading

                # Smoothly ramp in tilt past deadzone threshold to eliminate abrupt direction jumps
                t_ramp = min(1.0, max(0.0, (speed - deadzone) / deadzone_span))
                deadzone_ease = t_ramp * t_ramp * (3.0 - 2.0 * t_ramp)

                if tilt_mode == "physics_forward":
                    raw_delta = ((move_angle - neutral_angle + 180.0) % 360.0) - 180.0
                    raw_dir = raw_delta
                    speed_factor = min(1.0, (speed * max(1.0, tilt_strength * 1.25)) / 35.0)
                    target_deflection = raw_delta * min(1.0, tilt_strength) * speed_factor

                elif tilt_mode in ("physics_opposing", "physics"):
                    opposing_angle = move_angle + 180.0
                    raw_delta = ((opposing_angle - neutral_angle + 180.0) % 360.0) - 180.0
                    raw_dir = raw_delta
                    speed_factor = min(1.0, (speed * max(1.0, tilt_strength * 1.25)) / 35.0)
                    target_deflection = raw_delta * min(1.0, tilt_strength) * speed_factor

                else:
                    # Classic velocity tilt with true left/right visual symmetry compensation
                    # Boost diagonal/downward horizontal responsiveness so angling down-left/down-right tilts decisively
                    diag_boost = 1.0 + min(1.2, abs(self.vy) / 100.0)
                    raw_dir = 1.0 if self.vx > 0 else -1.0
                    if self.vx > 0:
                        tilt_target = (self.vx * 2.7 / 120.0) * tilt_strength * 18.0 * diag_boost
                        max_r = min(150.0, 70.0 * tilt_strength)
                        target_deflection = min(max_r, tilt_target)
                    else:
                        tilt_target = (self.vx / 120.0) * tilt_strength * 18.0 * diag_boost
                        max_l = min(150.0, 26.0 * tilt_strength)
                        target_deflection = max(-max_l, tilt_target)

                # Continuous Phase Unwrapping:
                # Eliminates the +-180Â° branch cut jump at down-right (+67.8Â°) by wrapping relative to current target
                if abs(self.held_tilt_target) > 2.0:
                    step = ((target_deflection - self.held_tilt_target + 180.0) % 360.0) - 180.0
                    continuous_target = self.held_tilt_target + step
                else:
                    # At the antipodal heading, +/-180 is the same orientation.
                    # Choose one side consistently for a newly started stroke.
                    continuous_target = (abs(target_deflection) if
                                         abs(target_deflection) >= 170.0 and
                                         tilt_mode in ("physics_forward", "physics_opposing", "physics")
                                         else target_deflection)

                active_target = continuous_target * deadzone_ease

                # True steering detection based on physical stroke heading change, not deceleration speed
                if tilt_mode in ("physics_forward", "physics_opposing", "physics"):
                    ang_steered = abs(((raw_dir - self.held_raw_dir + 180.0) % 360.0) - 180.0)
                    steered = (ang_steered > 4.0)
                    is_tracking = speed >= full_speed_threshold or steered or abs(continuous_target) > abs(self.held_tilt_target)
                else:
                    steered = (self.held_raw_dir != 0.0 and raw_dir != self.held_raw_dir)
                    is_tracking = steered or abs(continuous_target) > abs(self.held_tilt_target)

                # While actively moving or steering in any angle, steer responsively in real time!
                if is_tracking:
                    self.held_tilt_target = continuous_target
                    self.held_raw_dir = raw_dir
                    self.target_tilt = active_target if abs(self.held_tilt_target) < 5.0 else continuous_target
                else:
                    # Decelerating into stop in the same heading: hold peak tilt target
                    if tilt_disable_return or tilt_delay_enabled:
                        self.target_tilt = self.held_tilt_target
                    else:
                        self.target_tilt = active_target

                lerp_rate = 36.0 * max(1.0, tilt_strength * 0.75)

            else:
                # Mouse hardware has stopped or is moving slowly within deadzone
                time_stopped = now - self.last_motion_time

                if tilt_disable_return:
                    # Never return back to original position: hold the tilted pose indefinitely
                    self.target_tilt = self.held_tilt_target
                    lerp_rate = 18.0
                elif tilt_delay_enabled and time_stopped < tilt_return_delay:
                    # Hold delay active: maintain rotated pose rather than trying to correct at every millisecond
                    self.target_tilt = self.held_tilt_target
                    lerp_rate = 18.0
                else:
                    # Delay elapsed (or disabled): return to neutral resting orientation
                    self.target_tilt = round(self.tilt_angle / 360.0) * 360.0
                    if tilt_decay_enabled:
                        # Smooth slow return to neutral orientation
                        decay_rate = max(0.6, 6.5 - tilt_decay_speed * 5.5)
                        lerp_rate = decay_rate
                    else:
                        # Direct return
                        lerp_rate = 22.0

                    if abs(self.tilt_angle - self.target_tilt) < 0.5:
                        self.held_tilt_target = 0.0
                        self.held_raw_dir = 0.0
                        self.motion_heading = None
                        self.tilt_dir_x = 0.0
                        self.tilt_dir_y = 0.0
                        self.tilt_motion_samples.clear()
                        self.tilt_angle = 0.0
                        self.target_tilt = 0.0

            # Angular interpolation taking shortest rotational arc
            # Targets are already unwrapped against the previous heading.
            # Re-wrapping here makes the tilt reverse at the 180-degree seam.
            diff = self.target_tilt - self.tilt_angle
            tilt_lerp = 1.0 - math.exp(-lerp_rate * dt)
            self.tilt_angle += diff * tilt_lerp
        else:
            self.tilt_angle = 0.0
            self.held_tilt_target = 0.0
            self.held_raw_dir = 0.0
            self.motion_heading = None
            self.tilt_dir_x = 0.0
            self.tilt_dir_y = 0.0
            self.tilt_motion_samples.clear()

        # 5. Update Click Ripples
        alive_ripples = []
        for r in self.ripples:
            if r.update(dt):
                alive_ripples.append(r)
        self.ripples = alive_ripples

        # 6. Update Motion Trail
        if not trail_enabled:
            self.trail_points.clear()
        else:
            # Fade existing echoes even after the hardware cursor stops.
            self.trail_points = [(tx, ty, age + dt * 3.2)
                                 for tx, ty, age in self.trail_points
                                 if age + dt * 3.2 < 1.0]
            if self.speed > 80.0 and (not self.trail_points or
                math.hypot(self.x - self.trail_points[-1][0],
                           self.y - self.trail_points[-1][1]) >= 10.0):
                self.trail_points.append((self.x, self.y, 0.0))
                if len(self.trail_points) > 9:
                    del self.trail_points[:-9]

    def get_render_state(self):
        """Returns the current state needed by the renderer."""
        return {
            "x": self.x,
            "y": self.y,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "scale": self.scale,
            "tilt": self.tilt_angle,
            "speed": self.speed,
            "is_down": self.was_any_down,
            "ripples": self.ripples,
            "trail": self.trail_points
        }
