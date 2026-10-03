"""Stable, bounded Verlet rope anchored to the rendered arrow tail."""
import math

SPACING = 6.5
MAX_LINKS = 32


def advance_chain(points, anchor, count, dt, smoothness=55, swing=65):
    """Simulate an inextensible chain without changing hardware click position.

    Nodes are [x, y, previous_x, previous_y]; node zero is pinned. A reset
    on extreme pointer jumps prevents numerical explosions and offscreen tails.
    """
    count = max(6, min(MAX_LINKS, int(count)))
    ax, ay = float(anchor[0]), float(anchor[1])
    if len(points) != count or (points and
            math.hypot(ax-points[0][0], ay-points[0][1]) > 320):
        points[:] = [[ax, ay + i*SPACING, ax, ay + i*SPACING]
                     for i in range(count)]
    dt = max(.001, min(.035, float(dt)))
    smooth = max(0, min(100, float(smoothness)))
    liveliness = max(0, min(100, float(swing))) / 100.0
    friction = (0.88 + 0.075*liveliness) ** (dt*60)
    acceleration = (245 + liveliness*435) * dt*dt
    velocity_cap = min(35.0, 2600.0*dt)
    for index in range(1, count):
        node = points[index]
        x, y, px, py = node
        vx = max(-velocity_cap, min(velocity_cap, (x-px)*friction))
        vy = max(-velocity_cap, min(velocity_cap, (y-py)*friction))
        node[:] = [x+vx, y+vy+acceleration*(1.8 if index==count-1 else 1), x, y]
    predicted = [(node[0], node[1]) for node in points]
    # Bidirectional constraint relaxation transmits momentum along the rope.
    # The anchor is immutable and never acquires velocity from the links.
    for _ in range(7):
        points[0][:] = [ax, ay, ax, ay]
        for i in range(1, count):
            a, b = points[i-1], points[i]
            dx, dy = b[0]-a[0], b[1]-a[1]
            distance = math.hypot(dx, dy)
            if distance < 1e-7:
                dx, dy, distance = 0.0, SPACING, SPACING
            excess = (distance-SPACING)/distance
            if i == 1:
                b[0] -= dx*excess
                b[1] -= dy*excess
            else:
                correction = .5*excess
                a[0] += dx*correction
                a[1] += dy*correction
                b[0] -= dx*correction
                b[1] -= dy*correction
    # A final forward pass gives exact link length, including near the anchor.
    points[0][:] = [ax, ay, ax, ay]
    for i in range(1, count):
        a, b = points[i-1], points[i]
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length < 1e-7:
            dx, dy, length = 0.0, SPACING, SPACING
        b[0], b[1] = a[0]+dx*SPACING/length, a[1]+dy*SPACING/length
    # Project Verlet history with the corrections: otherwise each constraint
    # artificially becomes next-frame velocity and injects energy into the chain.
    correction_damping = 1.0 - 0.024*liveliness
    for node, (x, y) in zip(points[1:], predicted[1:]):
        node[2] += (node[0]-x)*correction_damping
        node[3] += (node[1]-y)*correction_damping
    return points
