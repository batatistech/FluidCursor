"""Bounded, frame-rate-independent cloth-strip motion for Silk Ribbon."""
import math

NODES = 18
SPACING = 6.6


def advance_ribbon(points, anchor, dt, smoothness=55, flow=60, click=False):
    """Pinned Verlet strip with drag, gravity, bend resistance and exact lengths.

    Previous positions encode velocity. Correct them after projection to avoid
    injecting energy on every frame. Never modifies the real pointer position.
    """
    ax, ay = float(anchor[0]), float(anchor[1])
    if (len(points) != NODES or not all(math.isfinite(v) for p in points for v in p)
            or (points and math.dist(points[0][:2], (ax, ay)) > 230)):
        points[:] = [[ax, ay + i * SPACING, ax, ay + i * SPACING] for i in range(NODES)]
    old_ax, old_ay = points[0][:2]
    dt = max(.001, min(.042, float(dt)))
    flow = max(0., min(100., float(flow))) / 100.
    smooth = max(0., min(100., float(smoothness))) / 100.
    steps = max(1, min(4, math.ceil(dt / .011)))
    h = dt / steps
    damping = (.80 + .145 * flow - .025 * smooth) ** (h * 60)
    gravity = (100 + 85 * flow) * h * h
    for step in range(steps):
        t = (step + 1) / steps
        pin_x = old_ax + (ax - old_ax) * t
        pin_y = old_ay + (ay - old_ay) * t
        for i in range(1, NODES):
            node = points[i]
            x, y, px, py = node
            vx = max(-16., min(16., (x - px) * damping))
            vy = max(-16., min(16., (y - py) * damping))
            node[:] = [x + vx, y + vy + gravity, x, y]
            if click and step == 0 and i >= 4:
                # A single, bounded flick travels down the cloth.
                node[2] += 1.8 * math.sin(i * .48) * flow
        for _ in range(5):
            points[0][:] = [pin_x, pin_y, pin_x, pin_y]
            for i in range(1, NODES):
                a, b = points[i - 1], points[i]
                dx, dy = b[0] - a[0], b[1] - a[1]
                length = math.hypot(dx, dy)
                if length < 1e-8:
                    dx, dy, length = 0., SPACING, SPACING
                adjustment = (length - SPACING) / length
                if i == 1:
                    b[0] -= dx * adjustment
                    b[1] -= dy * adjustment
                else:
                    a[0] += .5 * dx * adjustment
                    a[1] += .5 * dy * adjustment
                    b[0] -= .5 * dx * adjustment
                    b[1] -= .5 * dy * adjustment
        # A length-preserving forward pass removes residual stretch at the root.
        points[0][:] = [pin_x, pin_y, pin_x, pin_y]
        for i in range(1, NODES):
            a, b = points[i - 1], points[i]
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if length < 1e-8:
                dx, dy, length = 0., SPACING, SPACING
            new_x = a[0] + dx * SPACING / length
            new_y = a[1] + dy * SPACING / length
            # The projection is not an impulse: keep prior positions in sync.
            b[2] += new_x - b[0]
            b[3] += new_y - b[1]
            b[0], b[1] = new_x, new_y
        points[0][:] = [pin_x, pin_y, pin_x, pin_y]
    return points

