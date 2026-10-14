import heapq
import math
from collections import deque

import numpy as np


def occupancy_to_free(data, width, height, occupied_threshold=50):
    if width * height == 0:
        return np.zeros((height, width), dtype=bool)
    grid = np.asarray(data, dtype=np.int16).reshape(height, width)
    return (grid >= 0) & (grid < occupied_threshold)


def world_to_cell(x, y, origin_x, origin_y, resolution):
    col = int(math.floor((x - origin_x) / resolution))
    row = int(math.floor((y - origin_y) / resolution))
    return row, col


def cell_to_world(row, col, origin_x, origin_y, resolution):
    x = origin_x + (col + 0.5) * resolution
    y = origin_y + (row + 0.5) * resolution
    return x, y


def in_bounds(grid, row, col):
    height, width = grid.shape
    return 0 <= row < height and 0 <= col < width


def disk_offsets(radius_cells):
    r = int(math.floor(radius_cells))
    offsets = [(dr, dc)
               for dr in range(-r, r + 1)
               for dc in range(-r, r + 1)
               if dr * dr + dc * dc <= radius_cells * radius_cells]
    return np.array(offsets, dtype=int).reshape(-1, 2)


def erode(free, radius_cells):
    r = int(math.floor(radius_cells))
    height, width = free.shape
    padded = np.zeros((height + 2 * r, width + 2 * r), dtype=bool)
    padded[r:r + height, r:r + width] = free
    result = free.copy()
    for dr, dc in disk_offsets(radius_cells):
        result &= padded[r + dr:r + dr + height, r + dc:r + dc + width]
    return result


def nearest_true_cell(mask, row, col):
    cells = np.argwhere(mask)
    if len(cells) == 0:
        return None
    dist2 = (cells[:, 0] - row) ** 2 + (cells[:, 1] - col) ** 2
    best = cells[int(np.argmin(dist2))]
    return int(best[0]), int(best[1])


def connected_component(mask, start_cell):
    component = np.zeros_like(mask, dtype=bool)
    row0, col0 = start_cell
    if not in_bounds(mask, row0, col0) or not mask[row0, col0]:
        return component
    component[row0, col0] = True
    queue = deque([start_cell])
    while queue:
        row, col = queue.popleft()
        for nr, nc in ((row + 1, col), (row - 1, col), (row, col + 1), (row, col - 1)):
            if in_bounds(mask, nr, nc) and mask[nr, nc] and not component[nr, nc]:
                component[nr, nc] = True
                queue.append((nr, nc))
    return component


def erosion_radius_cells(resolution, robot_radius=0.105, safety_margin=0.05):
    return int(math.ceil((robot_radius + safety_margin) / resolution - 1e-9))


def reachable_mask(free, start_cell, resolution, robot_radius=0.105, safety_margin=0.05):
    eroded = erode(free, erosion_radius_cells(resolution, robot_radius, safety_margin))
    row, col = start_cell
    if not (in_bounds(eroded, row, col) and eroded[row, col]):
        nearest = nearest_true_cell(eroded, row, col)
        if nearest is None:
            return np.zeros_like(free, dtype=bool)
        row, col = nearest
    return connected_component(eroded, (row, col))


def restrict_to_rect(free, origin_x, origin_y, resolution, rect):
    free = np.asarray(free, dtype=bool)
    if rect is None or len(rect) == 0:
        return free.copy()
    if len(rect) != 4:
        raise ValueError('rect doit contenir 4 valeurs (xmin, ymin, xmax, ymax)')
    xmin, ymin, xmax, ymax = (float(v) for v in rect)
    if not (xmin < xmax and ymin < ymax):
        raise ValueError('rect invalide : il faut xmin < xmax et ymin < ymax')
    height, width = free.shape
    xs = origin_x + (np.arange(width) + 0.5) * resolution
    ys = origin_y + (np.arange(height) + 0.5) * resolution
    cols_in = (xs >= xmin) & (xs <= xmax)
    rows_in = (ys >= ymin) & (ys <= ymax)
    return free & np.outer(rows_in, cols_in)


def mark_covered(covered, reachable, row, col, radius_cells):
    offsets = disk_offsets(radius_cells)
    rows = offsets[:, 0] + row
    cols = offsets[:, 1] + col
    height, width = covered.shape
    inside = (rows >= 0) & (rows < height) & (cols >= 0) & (cols < width)
    rows, cols = rows[inside], cols[inside]
    new = reachable[rows, cols] & ~covered[rows, cols]
    covered[rows[new], cols[new]] = True
    return int(np.count_nonzero(new))


def coverage_percent(covered, reachable):
    total = int(np.count_nonzero(reachable))
    if total == 0:
        return 0.0
    done = int(np.count_nonzero(covered & reachable))
    return 100.0 * done / total


def row_segments(line):
    padded = np.concatenate(([False], line, [False])).astype(np.int8)
    changes = np.diff(padded)
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1) - 1
    return list(zip(starts.tolist(), ends.tolist()))


def sweep_rows(reachable, spacing_cells):
    rows_with_cells = np.flatnonzero(reachable.any(axis=1))
    if len(rows_with_cells) == 0:
        return []
    row_min, row_max = int(rows_with_cells[0]), int(rows_with_cells[-1])
    half = spacing_cells // 2
    inner = (row_max - half) - (row_min + half)
    if inner <= 0:
        return [(row_min + row_max) // 2]
    n_gaps = math.ceil(inner / spacing_cells)
    extra = n_gaps * spacing_cells - inner
    first = row_min + half - extra // 2
    return [first + k * spacing_cells for k in range(n_gaps + 1)]


def segment_waypoints(row, segment, left_to_right, origin_x, origin_y, resolution):
    col_start, col_end = segment
    yaw = 0.0 if left_to_right else math.pi
    cols = [col_start, col_end] if left_to_right else [col_end, col_start]
    if col_start == col_end:
        cols = [col_start]
    waypoints = []
    for col in cols:
        x, y = cell_to_world(row, col, origin_x, origin_y, resolution)
        waypoints.append((x, y, yaw))
    return waypoints


def boustrophedon_waypoints(reachable, origin_x, origin_y, resolution, sweep_spacing=0.18):
    spacing_cells = max(1, int(round(sweep_spacing / resolution)))
    waypoints = []
    left_to_right = True
    for row in sweep_rows(reachable, spacing_cells):
        segments = row_segments(reachable[row])
        if not segments:
            continue
        if not left_to_right:
            segments = segments[::-1]
        for segment in segments:
            waypoints += segment_waypoints(row, segment, left_to_right,
                                           origin_x, origin_y, resolution)
        left_to_right = not left_to_right
    return waypoints


def line_of_sight(reachable, p0, p1, origin_x, origin_y, resolution):
    (x0, y0), (x1, y1) = p0[:2], p1[:2]
    cuts = {0.0, 1.0}
    cuts |= _grid_crossings(x0, x1, origin_x, resolution)
    cuts |= _grid_crossings(y0, y1, origin_y, resolution)
    cuts = sorted(cuts)
    if x0 == x1 and y0 == y1:
        cuts = [0.0, 0.0]
    for t_a, t_b in zip(cuts[:-1], cuts[1:]):
        t = 0.5 * (t_a + t_b)
        row, col = world_to_cell(x0 + t * (x1 - x0), y0 + t * (y1 - y0),
                                 origin_x, origin_y, resolution)
        if not (in_bounds(reachable, row, col) and reachable[row, col]):
            return False
    return True


def _grid_crossings(v0, v1, origin, resolution):
    if v0 == v1:
        return set()
    lo, hi = sorted((v0, v1))
    k_first = int(math.floor((lo - origin) / resolution)) + 1
    k_last = int(math.ceil((hi - origin) / resolution)) - 1
    crossings = set()
    for k in range(k_first, k_last + 1):
        t = (origin + k * resolution - v0) / (v1 - v0)
        if 0.0 < t < 1.0:
            crossings.add(t)
    return crossings


def shortest_path_cells(reachable, start, goal):
    dist = {start: 0.0}
    parent = {start: None}
    heap = [(0.0, start)]
    while heap:
        d, cell = heapq.heappop(heap)
        if cell == goal:
            break
        if d > dist[cell]:
            continue
        for nxt, cost in _neighbors8(reachable, cell):
            nd = d + cost
            if nd < dist.get(nxt, math.inf):
                dist[nxt] = nd
                parent[nxt] = cell
                heapq.heappush(heap, (nd, nxt))
    if goal not in parent:
        return None
    path = []
    cell = goal
    while cell is not None:
        path.append(cell)
        cell = parent[cell]
    return path[::-1]


def _neighbors8(reachable, cell):
    row, col = cell
    result = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = row + dr, col + dc
            if not (in_bounds(reachable, nr, nc) and reachable[nr, nc]):
                continue
            if dr != 0 and dc != 0:
                if not (reachable[row + dr, col] and reachable[row, col + dc]):
                    continue
                result.append(((nr, nc), math.sqrt(2.0)))
            else:
                result.append(((nr, nc), 1.0))
    return result


def simplify_path(points, reachable, origin_x, origin_y, resolution):
    if len(points) <= 2:
        return list(points)
    kept = [points[0]]
    for i in range(2, len(points)):
        if not line_of_sight(reachable, kept[-1], points[i], origin_x, origin_y, resolution):
            kept.append(points[i - 1])
    kept.append(points[-1])
    return kept


def split_long_legs(points, max_step):
    if len(points) < 2:
        return list(points)
    result = [points[0]]
    for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
        n = max(1, int(math.ceil(math.hypot(x1 - x0, y1 - y0) / max_step)))
        for k in range(1, n + 1):
            result.append((x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n))
    return result


def _cell_in_mask(reachable, x, y, origin_x, origin_y, resolution):
    row, col = world_to_cell(x, y, origin_x, origin_y, resolution)
    if in_bounds(reachable, row, col) and reachable[row, col]:
        return row, col
    return nearest_true_cell(reachable, row, col)


def detour_points(reachable, wp_a, wp_b, origin_x, origin_y, resolution, max_step):
    if line_of_sight(reachable, wp_a, wp_b, origin_x, origin_y, resolution):
        return []
    start = _cell_in_mask(reachable, wp_a[0], wp_a[1], origin_x, origin_y, resolution)
    goal = _cell_in_mask(reachable, wp_b[0], wp_b[1], origin_x, origin_y, resolution)
    if start is None or goal is None:
        return None
    cells = shortest_path_cells(reachable, start, goal)
    if cells is None:
        return None
    points = [tuple(wp_a[:2])]
    points += [cell_to_world(r, c, origin_x, origin_y, resolution) for r, c in cells]
    points.append(tuple(wp_b[:2]))
    points = simplify_path(points, reachable, origin_x, origin_y, resolution)
    points = split_long_legs(points, max_step)
    return points[1:-1]


def plan_transitions(reachable, waypoints, origin_x, origin_y, resolution, max_step=0.3):
    if len(waypoints) < 2:
        return list(waypoints), 0
    result = [waypoints[0]]
    n_unresolved = 0
    for wp_a, wp_b in zip(waypoints[:-1], waypoints[1:]):
        extra = detour_points(reachable, wp_a, wp_b, origin_x, origin_y, resolution, max_step)
        if extra is None:
            n_unresolved += 1
            extra = []
        result += _orient_towards_next(extra, wp_b)
        result.append(wp_b)
    return result, n_unresolved


def _orient_towards_next(points, next_wp):
    oriented = []
    targets = list(points[1:]) + [next_wp[:2]]
    for (x, y), (tx, ty) in zip(points, targets):
        oriented.append((x, y, math.atan2(ty - y, tx - x)))
    return oriented
