import math
import random

FORWARD = 'FORWARD'
TURN = 'TURN'


def normalize_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def is_valid_range(r, range_min, range_max):
    return math.isfinite(r) and range_min <= r <= range_max


def front_min_distance(ranges, angle_min, angle_increment, range_min, range_max, front_angle):
    best = math.inf
    for i, r in enumerate(ranges):
        angle = normalize_angle(angle_min + i * angle_increment)
        if abs(angle) <= front_angle and is_valid_range(r, range_min, range_max):
            best = min(best, r)
    return best


class RandomWalkerLogic:

    def __init__(self, seed, forward_speed=0.15, turn_speed=1.0, stop_distance=0.25,
                 min_turn_deg=90.0, max_turn_deg=180.0):
        if turn_speed <= 0.0:
            raise ValueError('turn_speed doit être > 0')
        self.rng = random.Random(seed)
        self.forward_speed = forward_speed
        self.turn_speed = turn_speed
        self.stop_distance = stop_distance
        self.min_turn = math.radians(min_turn_deg)
        self.max_turn = math.radians(max_turn_deg)
        self.state = FORWARD
        self.turn_direction = 1.0
        self.turn_end_s = 0.0

    def start_turn(self, now_s):
        angle = self.rng.uniform(self.min_turn, self.max_turn)
        self.turn_direction = self.rng.choice((-1.0, 1.0))
        self.turn_end_s = now_s + angle / self.turn_speed
        self.state = TURN

    def turn_command(self):
        return 0.0, self.turn_direction * self.turn_speed

    def update(self, now_s, front_distance):
        blocked = front_distance < self.stop_distance
        if self.state == FORWARD:
            if blocked:
                self.start_turn(now_s)
                return self.turn_command()
            return self.forward_speed, 0.0
        if now_s < self.turn_end_s:
            return self.turn_command()
        if blocked:
            self.start_turn(now_s)
            return self.turn_command()
        self.state = FORWARD
        return self.forward_speed, 0.0


def parse_fence(fence):
    if fence is None or len(fence) == 0:
        return None
    if len(fence) != 4:
        raise ValueError('fence doit contenir 4 valeurs (xmin, ymin, xmax, ymax)')
    xmin, ymin, xmax, ymax = (float(v) for v in fence)
    if not (xmin < xmax and ymin < ymax):
        raise ValueError('fence invalide : il faut xmin < xmax et ymin < ymax')
    return xmin, ymin, xmax, ymax


def point_in_rect(x, y, rect):
    xmin, ymin, xmax, ymax = rect
    return xmin <= x <= xmax and ymin <= y <= ymax


def ray_exit_distance(x, y, angle, rect):
    xmin, ymin, xmax, ymax = rect
    dx, dy = math.cos(angle), math.sin(angle)
    eps = 1e-12
    t_x = math.inf
    if dx > eps:
        t_x = (xmax - x) / dx
    elif dx < -eps:
        t_x = (xmin - x) / dx
    t_y = math.inf
    if dy > eps:
        t_y = (ymax - y) / dy
    elif dy < -eps:
        t_y = (ymin - y) / dy
    return max(0.0, min(t_x, t_y))


def ray_angles(yaw, front_angle, n_rays):
    if n_rays <= 1:
        return [yaw]
    step = 2.0 * front_angle / (n_rays - 1)
    return [yaw - front_angle + i * step for i in range(n_rays)]


def heading_towards_center(x, y, yaw, rect):
    xmin, ymin, xmax, ymax = rect
    to_center = math.atan2((ymin + ymax) / 2.0 - y, (xmin + xmax) / 2.0 - x)
    return abs(normalize_angle(to_center - yaw)) < math.pi / 2.0


def fence_distance_ahead(x, y, yaw, fence, front_angle, n_rays=7):
    rect = parse_fence(fence)
    if rect is None:
        return math.inf
    if not point_in_rect(x, y, rect):
        return math.inf if heading_towards_center(x, y, yaw, rect) else 0.0
    return min(ray_exit_distance(x, y, a, rect) for a in ray_angles(yaw, front_angle, n_rays))
