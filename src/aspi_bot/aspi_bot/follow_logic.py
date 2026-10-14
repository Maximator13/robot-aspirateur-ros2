import math


def wrap_angle(a):
    return math.atan2(math.sin(a), math.cos(a))


def follow_step(x, y, yaw, tx, ty, driving, linear_speed=0.10, angular_speed=0.6,
                goal_tolerance=0.08, heading_tolerance=0.35):
    dx, dy = tx - x, ty - y
    dist = math.hypot(dx, dy)
    if dist < goal_tolerance:
        return 0.0, 0.0, True, False
    err = wrap_angle(math.atan2(dy, dx) - yaw)
    limit = 2.0 * heading_tolerance if driving else heading_tolerance
    if abs(err) > limit:
        return 0.0, math.copysign(angular_speed, err), False, False
    w = max(-angular_speed, min(angular_speed, 2.0 * err))
    v = linear_speed if dist > 0.2 else max(0.04, linear_speed * dist / 0.2)
    return v, w, False, True
