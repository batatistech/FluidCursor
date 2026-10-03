"""Optional, bounded cursor toys. Never changes real mouse input or normal settings."""
import math
import time
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QBrush, QPen, QPainterPath
from core.fun_art import FunArtwork
from core.chain_physics import advance_chain
from core.ribbon_physics import advance_ribbon

MODES = ("tile", "stardust", "chain", "comet", "orbit", "yoyo", "ribbon", "spinner")


def smoothness_physics(value):
    """Independent Fun spring: increasing smoothness reduces speed and oscillation."""
    smooth = max(0, min(100, int(value)))
    return 480.0 - 4.0 * smooth, 26.0 + 0.14 * smooth


class FunEngine:
    """One lightweight state machine for exclusive visual modes."""
    def __init__(self):
        self.mode = None
        self.heading = 0.0
        self.last_xy = None
        self.last_time = time.perf_counter()
        self.last_emit = self.last_time
        self.particles = []  # [screen x, screen y, age, lifetime, radius]
        self.tile_x = self.tile_y = None
        self.chain_points = []
        self.yoyo = None
        self.yoyo_anchor = None
        self.ribbon_points = []
        self.spinner_angle = 0.0
        self.spinner_velocity = 0.0
        self.was_clicking = False
        self.emitted = 0

    def reset(self, mode=None):
        self.mode = mode if mode in MODES else None
        self.heading = 0.0
        self.last_xy = None
        self.tile_x = self.tile_y = None
        self.chain_points = []
        self.yoyo = None
        self.yoyo_anchor = None
        self.ribbon_points = []
        self.spinner_angle = 0.0
        self.spinner_velocity = 0.0
        self.was_clicking = False
        self.emitted = 0
        self.particles.clear()
        self.last_time = time.perf_counter()
        self.last_emit = self.last_time

    def update(self, config, x, y, hw_x, hw_y, clicking=False, anchor=None):
        mode = ("chain" if config.fun_mode == "fish" else config.fun_mode) if config.fun_enabled else None
        if mode != self.mode:
            self.reset(mode)
        if not self.mode:
            return
        now = time.perf_counter()
        dt = min(0.05, max(0.001, now - self.last_time))
        self.last_time = now
        old = self.last_xy
        self.last_xy = (hw_x, hw_y)
        dx, dy = (hw_x - old[0], hw_y - old[1]) if old else (0, 0)
        if dx * dx + dy * dy > 2:
            target = math.degrees(math.atan2(dy, dx))
            delta = (target - self.heading + 180) % 360 - 180
            self.heading += delta * min(1.0, (18.0 - 0.14 * max(0, min(100, config.fun_smoothness))) * dt)
        if self.mode == "tile":
            distance = max(14, min(48, int(config.fun_tile_distance)))
            tx = x - math.cos(math.radians(self.heading)) * distance
            ty = y - math.sin(math.radians(self.heading)) * distance
            if self.tile_x is None:
                self.tile_x, self.tile_y = tx, ty
            follow = 1.0 - math.exp(-(18.0 - 0.15 * max(0, min(100, config.fun_smoothness))) * dt)
            self.tile_x += (tx - self.tile_x) * follow
            self.tile_y += (ty - self.tile_y) * follow
        if self.mode == "chain":
            # The arrow tail (not its clicking hotspot) owns the first link.
            attach = anchor if anchor is not None else (x + 9, y + 23)
            advance_chain(self.chain_points, attach, config.fun_chain_length,
                          dt, config.fun_smoothness, config.fun_chain_swing)
        if self.mode == "yoyo":
            ax, ay = anchor if anchor is not None else (x + 9, y + 22)
            self.yoyo_anchor = (ax, ay)
            if self.yoyo is None or math.hypot(self.yoyo[0]-ax, self.yoyo[1]-ay)>300:
                self.yoyo = [ax + 22, ay + min(70, config.fun_yoyo_length), 0.0, 0.0]
            bx, by, vx, vy = self.yoyo
            # Elastic tether, downward gravity and friction; click launches ball.
            stiffness = 48 + (100-config.fun_smoothness)*0.8
            vx += ((ax-bx)*stiffness)*dt
            length = max(45, min(120, int(config.fun_yoyo_length)))
            vy += ((ay+length-350/stiffness-by)*stiffness + 350)*dt
            if clicking and not self.was_clicking:
                vy -= 290
                vx += 150
            decay = math.exp(-3.5*dt)
            vx, vy = vx*decay, vy*decay
            bx += max(-750,min(750,vx))*dt
            by += max(-750,min(750,vy))*dt
            dx, dy = bx-ax, by-ay
            distance = math.hypot(dx,dy)
            if distance > length:
                bx,by = ax+dx*length/distance, ay+dy*length/distance
                vx,vy = vx*.5,vy*.5
            self.yoyo = [bx,by,vx,vy]
        if self.mode == "ribbon":
            attach = anchor if anchor is not None else (x + 9, y + 22)
            advance_ribbon(self.ribbon_points, attach, dt, config.fun_smoothness,
                           config.fun_ribbon_flow, clicking and not self.was_clicking)
        if self.mode == "spinner":
            energy = max(0, min(100, int(config.fun_spinner_speed)))
            drive = (dx * .7 + dy * .45) * (.35 + energy * .013)
            self.spinner_velocity += max(-190, min(190, drive))
            if clicking and not self.was_clicking:
                self.spinner_velocity += 310 + energy * 5
            drag = 2.8 - energy * .017
            self.spinner_velocity *= math.exp(-drag * dt)
            self.spinner_velocity = max(-1100., min(1100., self.spinner_velocity))
            if abs(self.spinner_velocity) < .12:
                self.spinner_velocity = 0.
            self.spinner_angle = (self.spinner_angle + self.spinner_velocity * dt) % 360.
        self.was_clicking = bool(clicking)
        if self.mode in ("stardust", "comet"):
            self.particles = [p for p in self.particles if p[2] + dt < p[3]]
            for p in self.particles:
                p[2] += dt
            density = max(0, min(100, int(config.fun_particles)))
            interval = 0.18 - density * 0.0011
            if density and (dx * dx + dy * dy > 9 or clicking) and now - self.last_emit >= interval:
                self.last_emit = now
                # Deterministic positions; avoids RNG overhead in the 7 ms loop.
                a = math.radians(self.heading)
                ex = x - math.cos(a) * 10
                ey = y - math.sin(a) * 10
                self.emitted += 1
                variation=(self.emitted*7)%11
                radius=1.2 + variation*.10
                life=.6
                drift=(-1 if self.emitted%2 else 1)*(6+variation*1.3)
                self.particles.append([ex, ey, 0.0, life, radius, drift])
                if len(self.particles) > 16:
                    self.particles.pop(0)

    def frame_key(self):
        if not self.mode:
            return None
        return (self.mode, round(self.heading,1),
                round(self.tile_x or 0,1),round(self.tile_y or 0,1),
                tuple((round(p[0],1),round(p[1],1),round(p[2],2)) for p in self.particles),
                tuple((round(n[0],1),round(n[1],1)) for n in self.chain_points),
                tuple(round(v,1) for v in self.yoyo[:2]) if self.yoyo else None,
                tuple((round(n[0],1),round(n[1],1)) for n in self.ribbon_points),
                round(self.spinner_angle,1) if self.mode == 'spinner' else 0,
                int(time.perf_counter()*24) if self.mode == 'orbit' else 0)

    def draw(self, painter, x, y, window_x, window_y, config):
        if not self.mode:
            return
        painter.save()
        for particle in self.particles:
            FunArtwork.particle(painter,self.mode,particle,window_x,window_y)
        if self.mode == 'chain':
            FunArtwork.chain(painter,self.chain_points,window_x,window_y)
        elif self.mode == 'yoyo' and self.yoyo:
            FunArtwork.yoyo(painter,self.yoyo_anchor,self.yoyo,window_x,window_y)
        elif self.mode == 'ribbon':
            FunArtwork.ribbon(painter,self.ribbon_points,window_x,window_y)
        else:
            painter.translate(x,y)
            if self.mode == 'tile':
                painter.translate((self.tile_x if self.tile_x is not None else window_x)-window_x-x,
                                  (self.tile_y if self.tile_y is not None else window_y)-window_y-y)
                self._tile(painter)
            elif self.mode == 'stardust': self._star(painter)
            elif self.mode == 'comet': FunArtwork.comet(painter)
            elif self.mode == 'orbit': FunArtwork.orbit(painter,config.fun_orbit_count)
            elif self.mode == 'spinner':
                painter.translate(38, 26)
                FunArtwork.spinner(painter, self.spinner_angle)
        painter.restore()

    @staticmethod
    def _tile(painter):
        FunArtwork.tile(painter)

    @staticmethod
    def _star(painter):
        FunArtwork.star(painter)
