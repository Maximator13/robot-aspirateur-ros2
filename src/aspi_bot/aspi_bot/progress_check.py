import math


def segment_length(p, q):
    return math.hypot(q[0] - p[0], q[1] - p[1])


class ProgressMonitor:

    def __init__(self, min_ratio=0.3, min_expected=0.15, max_suspects=2, max_elapsed=2.0):
        if not 0.0 < min_ratio <= 1.0:
            raise ValueError('min_ratio doit être dans ]0, 1]')
        if min_expected < 0.0:
            raise ValueError('min_expected doit être >= 0')
        if max_suspects < 1:
            raise ValueError('max_suspects doit être >= 1')
        if not max_elapsed > 0.0:
            raise ValueError('max_elapsed doit être > 0')
        self.min_ratio = float(min_ratio)
        self.min_expected = float(min_expected)
        self.max_suspects = int(max_suspects)
        self.max_elapsed = float(max_elapsed)
        self._suspects = 0

    def on_waypoint_reached(self, expected_dist: float, traveled_dist: float,
                            elapsed_s=None) -> bool:
        if not (math.isfinite(expected_dist) and math.isfinite(traveled_dist)):
            return self._suspects >= self.max_suspects
        if expected_dist < self.min_expected:
            return self._suspects >= self.max_suspects
        too_little = traveled_dist < self.min_ratio * expected_dist
        time_known = (elapsed_s is not None and not math.isnan(elapsed_s)
                      and elapsed_s >= 0.0)
        too_fast = (not time_known) or elapsed_s < self.max_elapsed
        if too_little and too_fast:
            self._suspects += 1
        else:
            self._suspects = 0
        return self._suspects >= self.max_suspects

    @property
    def suspects(self) -> int:
        return self._suspects
